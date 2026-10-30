type AstSpan { startByte: Int, endByte: Int, line: Int, column: Int }
type AstValue = AstAbsent() | AstInteger(Int, AstSpan) | AstBoolean(Bool, AstSpan) | AstString(List[Str], AstSpan) | AstName(Str, AstSpan) | AstHole(Str, AstSpan) | AstCall(Str, List[AstValue], AstSpan) | AstBinary(Str, AstValue, AstValue, AstSpan) | AstUnary(Str, AstValue, AstSpan) | AstList(List[AstValue], AstSpan) | AstIfExpression(AstValue, AstValue, AstValue, AstSpan) | AstRecordField(Str, AstValue, AstSpan) | AstRecordExpression(Str, List[AstValue], AstSpan) | AstFieldAccess(AstValue, Str, AstSpan) | AstMatchExpression(AstValue, List[AstValue], AstSpan) | AstWildcardPattern(AstSpan) | AstBindingPattern(Str, AstSpan) | AstConstructorPattern(Str, List[AstValue], AstSpan) | AstMatchArm(AstValue, AstValue, AstSpan) | AstTypeScalar(Str, AstSpan) | AstTypeNamed(Str, AstSpan) | AstTypeList(AstValue, AstSpan) | AstTypeParameter(Str, AstSpan) | AstParameter(Str, AstValue, AstSpan) | AstFieldDeclaration(Str, AstValue, AstSpan) | AstVariantDeclaration(Str, List[AstValue], AstSpan) | AstRecordDeclaration(Str, List[AstValue], AstSpan) | AstUnionDeclaration(Str, List[AstValue], AstSpan) | AstLet(Str, AstValue, AstValue, AstSpan) | AstVar(Str, AstValue, AstValue, AstSpan) | AstAssignment(Str, AstValue, AstSpan) | AstReturn(AstValue, AstSpan) | AstBlock(List[AstValue], AstSpan) | AstIfStatement(AstValue, List[AstValue], List[AstValue], AstSpan) | AstForIn(Str, AstValue, List[AstValue], AstSpan) | AstWhile(AstValue, List[AstValue], AstSpan) | AstExpressionStatement(AstValue, AstSpan) | AstFunction(Str, List[AstValue], List[AstValue], AstValue, List[AstValue], AstSpan)

type FlatAstNode {
  id: Int,
  parentId: Int,
  childIndex: Int,
  role: Str,
  kind: Str,
  text: Str,
  integerValue: Int,
  booleanValue: Bool,
  stringParts: List[Str],
  startByte: Int,
  endByte: Int,
  line: Int,
  column: Int
}
fn empty_node() -> FlatAstNode {
  return FlatAstNode { id: -1, parentId: -1, childIndex: -1, role: "", kind: "", text: "", integerValue: 0, booleanValue: false, stringParts: [], startByte: 0, endByte: 0, line: 0, column: 0 }
}
fn count_children(nodes: List[FlatAstNode], parent: Int, role: Str) -> Int {
  var count = 0
  for node in nodes { if node.parentId == parent && node.role == role { count = count + 1 } else {} }
  return count
}
type FlatState { nextId: Int, nodesReversed: List[FlatAstNode] }

type ParserStream {
  lexCursor: LexCursor,
  bufferedTokens: List[LexToken],
  lexDone: Bool,
  lexErrorCode: Str,
  lexErrorStart: Int,
  lexErrorEnd: Int,
  lexErrorLine: Int,
  lexErrorColumn: Int
}
type ParserCursor {
  document: Str,
  revision: Str,
  stream: ParserStream,
  nextNodeId: Int,
  done: Bool,
  functionActive: Bool,
  functionName: Str,
  functionStartByte: Int,
  functionLine: Int,
  functionColumn: Int,
  functionRootId: Int,
  functionChildIndex: Int,
  topLevelChildIndex: Int,
  frames: List[ParserFrame]
}
type ParserFrame {
  kind: Str,
  nodeId: Int,
  parentId: Int,
  rootChildIndex: Int,
  rootRole: Str,
  startByte: Int,
  line: Int,
  column: Int,
  text: Str,
  bodyChildIndex: Int
}
type ParserContext { parentId: Int, childIndex: Int, role: Str }
type TokenRead { token: LexToken, stream: ParserStream, ok: Bool }
type AstParse {
  value: AstValue,
  stream: ParserStream,
  ok: Bool,
  errorCode: Str,
  message: Str,
  errorStart: Int,
  errorEnd: Int,
  errorLine: Int,
  errorColumn: Int
}
type BlockParse { statements: List[AstValue], stream: ParserStream, opening: LexToken, closing: LexToken, ok: Bool, errorCode: Str, message: Str, errorStart: Int, errorEnd: Int, errorLine: Int, errorColumn: Int }
type ParserProgress {
  document: Str,
  revision: Str,
  status: Str,
  nodes: List[FlatAstNode],
  done: Bool,
  errorCode: Str,
  message: Str,
  errorStart: Int,
  errorEnd: Int,
  errorLine: Int,
  errorColumn: Int
}
type ParserChunk {
  document: Str,
  revision: Str,
  status: Str,
  nodes: List[FlatAstNode],
  cursor: ParserCursor,
  done: Bool,
  errorCode: Str,
  message: Str,
  errorStart: Int,
  errorEnd: Int,
  errorLine: Int,
  errorColumn: Int
}

fn ast_span(token: LexToken) -> AstSpan {
  return AstSpan {
    startByte: token.startByte, endByte: token.endByte,
    line: token.line, column: token.column
  }
}

fn ast_combine(left: AstSpan, right: AstSpan) -> AstSpan {
  return AstSpan {
    startByte: left.startByte, endByte: right.endByte,
    line: left.line, column: left.column
  }
}

fn ast_value_span(value: AstValue) -> AstSpan {
  return match value {
    AstCall(name, args, span) => span
    AstBinary(op, left, right, span) => span
    AstUnary(op, operand, span) => span
    AstName(name, span) => span
    AstFunction(name, typeParameters, parameters, result, body, span) => span
    _ => ast_value_span_part_1(value)
  }
}
fn ast_value_span_part_1(value: AstValue) -> AstSpan {
  return match value {
    AstInteger(number, span) => span
    AstBoolean(flag, span) => span
    _ => ast_value_span_part_2(value)
  }
}
fn ast_value_span_part_2(value: AstValue) -> AstSpan {
  return match value {
    AstString(parts, span) => span
    AstName(name, span) => span
    _ => ast_value_span_part_3(value)
  }
}
fn ast_value_span_part_3(value: AstValue) -> AstSpan {
  return match value {
    AstHole(name, span) => span
    AstCall(name, args, span) => span
    _ => ast_value_span_part_4(value)
  }
}
fn ast_value_span_part_4(value: AstValue) -> AstSpan {
  return match value {
    AstBinary(op, left, right, span) => span
    AstUnary(op, operand, span) => span
    _ => ast_value_span_part_5(value)
  }
}
fn ast_value_span_part_5(value: AstValue) -> AstSpan {
  return match value {
    AstList(items, span) => span
    AstIfExpression(condition, yes, no, span) => span
    _ => ast_value_span_part_6(value)
  }
}
fn ast_value_span_part_6(value: AstValue) -> AstSpan {
  return match value {
    AstRecordField(name, value, span) => span
    AstRecordExpression(name, fields, span) => span
    _ => ast_value_span_part_7(value)
  }
}
fn ast_value_span_part_7(value: AstValue) -> AstSpan {
  return match value {
    AstFieldAccess(value, field, span) => span
    AstMatchExpression(value, arms, span) => span
    _ => ast_value_span_part_8(value)
  }
}
fn ast_value_span_part_8(value: AstValue) -> AstSpan {
  return match value {
    AstWildcardPattern(span) => span
    AstBindingPattern(name, span) => span
    _ => ast_value_span_part_9(value)
  }
}
fn ast_value_span_part_9(value: AstValue) -> AstSpan {
  return match value {
    AstConstructorPattern(name, args, span) => span
    AstMatchArm(pattern, result, span) => span
    _ => ast_value_span_part_10(value)
  }
}
fn ast_value_span_part_10(value: AstValue) -> AstSpan {
  return match value {
    AstTypeScalar(name, span) => span
    AstTypeNamed(name, span) => span
    _ => ast_value_span_part_11(value)
  }
}
fn ast_value_span_part_11(value: AstValue) -> AstSpan {
  return match value {
    AstTypeList(element, span) => span
    AstTypeParameter(name, span) => span
    _ => ast_value_span_part_12(value)
  }
}
fn ast_value_span_part_12(value: AstValue) -> AstSpan {
  return match value {
    AstParameter(name, ty, span) => span
    AstFieldDeclaration(name, ty, span) => span
    _ => ast_value_span_part_13(value)
  }
}
fn ast_value_span_part_13(value: AstValue) -> AstSpan {
  return match value {
    AstVariantDeclaration(name, args, span) => span
    AstRecordDeclaration(name, fields, span) => span
    _ => ast_value_span_part_14(value)
  }
}
fn ast_value_span_part_14(value: AstValue) -> AstSpan {
  return match value {
    AstUnionDeclaration(name, variants, span) => span
    AstLet(name, annotation, value, span) => span
    _ => ast_value_span_part_15(value)
  }
}
fn ast_value_span_part_15(value: AstValue) -> AstSpan {
  return match value {
    AstVar(name, annotation, value, span) => span
    AstAssignment(name, value, span) => span
    _ => ast_value_span_part_16(value)
  }
}
fn ast_value_span_part_16(value: AstValue) -> AstSpan {
  return match value {
    AstReturn(value, span) => span
    AstBlock(statements, span) => span
    _ => ast_value_span_part_17(value)
  }
}
fn ast_value_span_part_17(value: AstValue) -> AstSpan {
  return match value {
    AstIfStatement(condition, yes, no, span) => span
    AstForIn(name, values, body, span) => span
    _ => ast_value_span_part_18(value)
  }
}
fn ast_value_span_part_18(value: AstValue) -> AstSpan {
  return match value {
    AstWhile(condition, body, span) => span
    AstExpressionStatement(value, span) => span
    _ => ast_value_span_part_19(value)
  }
}
fn ast_value_span_part_19(value: AstValue) -> AstSpan {
  return match value {
    AstFunction(name, typeParameters, parameters, result, body, span) => span
    AstAbsent() => AstSpan { startByte: 0, endByte: 0, line: 1, column: 1 }
    _ => AstSpan { startByte: 0, endByte: 0, line: 1, column: 1 }
  }
}
fn flat_make(
  id: Int, parentId: Int, childIndex: Int, role: Str, kind: Str,
  text: Str, integerValue: Int, booleanValue: Bool, stringParts: List[Str],
  span: AstSpan
) -> FlatAstNode {
  return FlatAstNode {
    id: id, parentId: parentId, childIndex: childIndex, role: role, kind: kind,
    text: text, integerValue: integerValue, booleanValue: booleanValue,
    stringParts: stringParts, startByte: span.startByte, endByte: span.endByte,
    line: span.line, column: span.column
  }
}

fn flat_plain(
  value: AstValue, parentId: Int, childIndex: Int, role: Str,
  kind: Str, text: Str, integerValue: Int, booleanValue: Bool,
  stringParts: List[Str], state: FlatState
) -> FlatState {
  let id = state.nextId
  let node = flat_make(id, parentId, childIndex, role, kind, text,
    integerValue, booleanValue, stringParts, ast_value_span(value))
  return FlatState { nextId: id + 1, nodesReversed: prepend(state.nodesReversed, node) }
}

fn flat_children(
  values: List[AstValue], parentId: Int, role: Str, state: FlatState
) -> FlatState {
  var current = state
  var index = 0
  for value in values {
    current = flat_node(value, parentId, index, role, current)
    index = index + 1
  }
  return current
}

fn flat_composite(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  kind: Str, text: Str, children: List[AstValue], childRole: Str,
  state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, kind, text, 0, false, [], state)
  return flat_children(children, parent.nextId - 1, childRole, parent)
}

fn flat_named_binary(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  kind: Str, text: Str, left: AstValue, right: AstValue, state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, kind, text, 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withLeft = flat_node(left, nodeId, 0, "annotation_or_left", parent)
  return flat_node(right, nodeId, 1, "value_or_right", withLeft)
}
fn flat_binary(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  op: Str, left: AstValue, right: AstValue, state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, "binary", op, 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withLeft = flat_node(left, nodeId, 0, "left", parent)
  return flat_node(right, nodeId, 1, "right", withLeft)
}

fn flat_if_expression(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  condition: AstValue, yes: AstValue, no: AstValue, state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, "if_expression", "", 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withCondition = flat_node(condition, nodeId, 0, "condition", parent)
  let withYes = flat_node(yes, nodeId, 1, "then", withCondition)
  return flat_node(no, nodeId, 2, "else", withYes)
}

fn flat_match_expression(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  subject: AstValue, arms: List[AstValue], state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, "match", "", 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withSubject = flat_node(subject, nodeId, 0, "value", parent)
  return flat_children(arms, nodeId, "arm", withSubject)
}

fn flat_match_arm(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  pattern: AstValue, result: AstValue, state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, "match_arm", "", 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withPattern = flat_node(pattern, nodeId, 0, "pattern", parent)
  return flat_node(result, nodeId, 1, "result", withPattern)
}

fn flat_loop(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  kind: Str, text: Str, head: AstValue, body: List[AstValue], headRole: Str,
  bodyRole: Str, state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, kind, text, 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withHead = flat_node(head, nodeId, 0, headRole, parent)
  return flat_children(body, nodeId, bodyRole, withHead)
}

fn flat_binding(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  kind: Str, name: Str, annotation: AstValue, expression: AstValue,
  state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, kind, name, 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withAnnotation = flat_node(annotation, nodeId, 0, "annotation", parent)
  return flat_node(expression, nodeId, 0, "value", withAnnotation)
}
fn flat_if_statement(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  condition: AstValue, yes: List[AstValue], no: List[AstValue], state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, "if_statement", "", 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withCondition = flat_node(condition, nodeId, 0, "condition", parent)
  let withYes = flat_children(yes, nodeId, "then", withCondition)
  return flat_children(no, nodeId, "else", withYes)
}
fn flat_function(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  name: Str, typeParameters: List[AstValue], parameters: List[AstValue], result: AstValue,
  body: List[AstValue], state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, "function", name, 0, false, [], state)
  let nodeId = parent.nextId - 1
  let withTypeParameters = flat_children(typeParameters, nodeId, "type_parameter", parent)
  let withParameters = flat_children(parameters, nodeId, "parameter", withTypeParameters)
  let withResult = flat_node(result, nodeId, 0, "return_type", withParameters)
  return flat_children(body, nodeId, "statement", withResult)
}
fn flat_record_field_value(value: AstValue, parentId: Int, childIndex: Int,
  role: Str, name: Str, fieldValue: AstValue, state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, "record_field", name, 0, false, [], state)
  return flat_node(fieldValue, parent.nextId - 1, 0, "value", parent)
}
fn flat_record_field(value: AstValue, parentId: Int, childIndex: Int,
  role: Str, state: FlatState) -> FlatState {
  return match value {
    AstRecordField(name, fieldValue, span) => flat_record_field_value(value, parentId, childIndex, role, name, fieldValue, state)
    _ => flat_node(value, parentId, childIndex, role, state)
  }
}
fn flat_record_children(fields: List[AstValue], parentId: Int,
  state: FlatState) -> FlatState {
  var current = state
  var index = 0
  for field in fields {
    current = flat_record_field(field, parentId, index, "field", current)
    index = index + 1
  }
  return current
}
fn flat_record_expression(value: AstValue, parentId: Int, childIndex: Int,
  role: Str, name: Str, fields: List[AstValue], state: FlatState) -> FlatState {
  let parent = flat_plain(value, parentId, childIndex, role, "record", name, 0, false, [], state)
  return flat_record_children(fields, parent.nextId - 1, parent)
}

fn flat_node(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return flat_node_fast_1(value, parentId, childIndex, role, state)
}
fn flat_node_fast_1(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstAbsent() => state
    AstName(name, span) => flat_plain(value, parentId, childIndex, role, "name", name, 0, false, [], state)
    _ => flat_node_fast_2(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_2(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstCall(name, args, span) => flat_composite(value, parentId, childIndex, role, "call", name, args, "argument", state)
    AstFieldAccess(base, field, span) => flat_composite(value, parentId, childIndex, role, "field_access", field, [base], "value", state)
    _ => flat_node_fast_3(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_3(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstBinary(op, left, right, span) => flat_binary(value, parentId, childIndex, role, op, left, right, state)
    AstRecordField(name, fieldValue, span) => flat_record_field(value, parentId, childIndex, role, state)
    _ => flat_node_fast_4(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_4(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstRecordExpression(name, fields, span) => flat_record_expression(value, parentId, childIndex, role, name, fields, state)
    AstFunction(name, typeParameters, parameters, result, body, span) => flat_function(value, parentId, childIndex, role, name, typeParameters, parameters, result, body, state)
    _ => flat_node_fast_5(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_5(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstIfStatement(condition, yes, no, span) => flat_if_statement(value, parentId, childIndex, role, condition, yes, no, state)
    AstIfExpression(condition, yes, no, span) => flat_if_expression(value, parentId, childIndex, role, condition, yes, no, state)
    _ => flat_node_fast_6(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_6(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstLet(name, annotation, expression, span) => flat_binding(value, parentId, childIndex, role, "let", name, annotation, expression, state)
    AstVar(name, annotation, expression, span) => flat_binding(value, parentId, childIndex, role, "var", name, annotation, expression, state)
    _ => flat_node_fast_7(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_7(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstReturn(expression, span) => flat_composite(value, parentId, childIndex, role, "return", "", [expression], "value", state)
    AstUnary(op, operand, span) => flat_composite(value, parentId, childIndex, role, "unary", op, [operand], "operand", state)
    _ => flat_node_fast_8(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_8(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstInteger(number, span) => flat_plain(value, parentId, childIndex, role, "integer", "", number, false, [], state)
    AstBoolean(flag, span) => flat_plain(value, parentId, childIndex, role, "boolean", "", 0, flag, [], state)
    _ => flat_node_fast_9(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_9(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstString(parts, span) => flat_plain(value, parentId, childIndex, role, "string", "", 0, false, parts, state)
    AstMatchExpression(subject, arms, span) => flat_match_expression(value, parentId, childIndex, role, subject, arms, state)
    _ => flat_node_fast_10(value, parentId, childIndex, role, state)
  }
}
fn flat_node_fast_10(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstMatchArm(pattern, result, span) => flat_match_arm(value, parentId, childIndex, role, pattern, result, state)
    _ => flat_node_part_1(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_1(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstAbsent() => state
    AstInteger(number, span) => flat_plain(value, parentId, childIndex, role, "integer", "", number, false, [], state)
    _ => flat_node_part_2(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_2(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstBoolean(flag, span) => flat_plain(value, parentId, childIndex, role, "boolean", "", 0, flag, [], state)
    AstString(parts, span) => flat_plain(value, parentId, childIndex, role, "string", "", 0, false, parts, state)
    _ => flat_node_part_3(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_3(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstName(name, span) => flat_plain(value, parentId, childIndex, role, "name", name, 0, false, [], state)
    AstHole(name, span) => flat_plain(value, parentId, childIndex, role, "hole", name, 0, false, [], state)
    _ => flat_node_part_4(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_4(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstCall(name, args, span) => flat_composite(value, parentId, childIndex, role, "call", name, args, "argument", state)
    AstBinary(op, left, right, span) => flat_binary(value, parentId, childIndex, role, op, left, right, state)
    _ => flat_node_part_5(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_5(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstUnary(op, operand, span) => flat_composite(value, parentId, childIndex, role, "unary", op, [operand], "operand", state)
    AstList(items, span) => flat_composite(value, parentId, childIndex, role, "list", "", items, "element", state)
    _ => flat_node_part_6(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_6(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstIfExpression(condition, yes, no, span) => flat_if_expression(value, parentId, childIndex, role, condition, yes, no, state)
    AstRecordField(name, fieldValue, span) => flat_record_field(value, parentId, childIndex, role, state)
    _ => flat_node_part_7(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_7(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstRecordExpression(name, fields, span) => flat_record_expression(value, parentId, childIndex, role, name, fields, state)
    AstFieldAccess(base, field, span) => flat_composite(value, parentId, childIndex, role, "field_access", field, [base], "value", state)
    _ => flat_node_part_8(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_8(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstMatchExpression(subject, arms, span) => flat_match_expression(value, parentId, childIndex, role, subject, arms, state)
    AstWildcardPattern(span) => flat_plain(value, parentId, childIndex, role, "wildcard_pattern", "", 0, false, [], state)
    _ => flat_node_part_9(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_9(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstBindingPattern(name, span) => flat_plain(value, parentId, childIndex, role, "binding_pattern", name, 0, false, [], state)
    AstConstructorPattern(name, args, span) => flat_composite(value, parentId, childIndex, role, "constructor_pattern", name, args, "argument", state)
    _ => flat_node_part_10(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_10(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstMatchArm(pattern, result, span) => flat_match_arm(value, parentId, childIndex, role, pattern, result, state)
    AstTypeScalar(name, span) => flat_plain(value, parentId, childIndex, role, "type_scalar", name, 0, false, [], state)
    _ => flat_node_part_11(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_11(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstTypeNamed(name, span) => flat_plain(value, parentId, childIndex, role, "type_named", name, 0, false, [], state)
    AstTypeList(element, span) => flat_composite(value, parentId, childIndex, role, "type_list", "", [element], "element_type", state)
    _ => flat_node_part_12(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_12(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstTypeParameter(name, span) => flat_plain(value, parentId, childIndex, role, "type_parameter", name, 0, false, [], state)
    AstParameter(name, ty, span) => flat_composite(value, parentId, childIndex, role, "parameter", name, [ty], "type", state)
    _ => flat_node_part_13(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_13(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstFieldDeclaration(name, ty, span) => flat_composite(value, parentId, childIndex, role, "field_declaration", name, [ty], "type", state)
    AstVariantDeclaration(name, args, span) => flat_composite(value, parentId, childIndex, role, "variant_declaration", name, args, "field_type", state)
    _ => flat_node_part_14(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_14(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstRecordDeclaration(name, fields, span) => flat_composite(value, parentId, childIndex, role, "record_declaration", name, fields, "field", state)
    AstUnionDeclaration(name, variants, span) => flat_composite(value, parentId, childIndex, role, "union_declaration", name, variants, "variant", state)
    _ => flat_node_part_15(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_15(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstLet(name, annotation, expression, span) => flat_binding(value, parentId, childIndex, role, "let", name, annotation, expression, state)
    AstVar(name, annotation, expression, span) => flat_binding(value, parentId, childIndex, role, "var", name, annotation, expression, state)
    _ => flat_node_part_16(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_16(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstAssignment(name, expression, span) => flat_composite(value, parentId, childIndex, role, "assignment", name, [expression], "value", state)
    AstReturn(expression, span) => flat_composite(value, parentId, childIndex, role, "return", "", [expression], "value", state)
    _ => flat_node_part_17(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_17(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstBlock(statements, span) => flat_composite(value, parentId, childIndex, role, "block", "", statements, "statement", state)
    AstIfStatement(condition, yes, no, span) => flat_if_statement(value, parentId, childIndex, role, condition, yes, no, state)
    _ => flat_node_part_18(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_18(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstForIn(name, iterable, body, span) => flat_loop(value, parentId, childIndex, role, "for_in", name, iterable, body, "iterable", "body", state)
    AstWhile(condition, body, span) => flat_loop(value, parentId, childIndex, role, "while", "", condition, body, "condition", "body", state)
    _ => flat_node_part_19(value, parentId, childIndex, role, state)
  }
}
fn flat_node_part_19(value: AstValue, parentId: Int, childIndex: Int, role: Str,
  state: FlatState) -> FlatState {
  return match value {
    AstExpressionStatement(expression, span) => flat_composite(value, parentId, childIndex, role, "expression_statement", "", [expression], "value", state)
    AstFunction(name, typeParameters, parameters, result, body, span) => flat_function(value, parentId, childIndex, role, name, typeParameters, parameters, result, body, state)
    _ => state
  }
}
fn token_at(tokens: List[LexToken], index: Int) -> LexToken {
  var currentIndex = 0
  for token in tokens {
    if currentIndex == index { return token } else { }
    currentIndex = currentIndex + 1
  }
  return make_token("eof", "", 0, [], 0, 0, 1, 1)
}

fn tokens_drop(tokens: List[LexToken], count: Int) -> List[LexToken] {
  var currentIndex = 0
  var reversed: List[LexToken] = []
  for token in tokens {
    if count <= currentIndex { reversed = prepend(reversed, token) } else { }
    currentIndex = currentIndex + 1
  }
  return reverse(reversed)
}

fn parser_stream(lexCursor: LexCursor) -> ParserStream {
  return ParserStream {
    lexCursor: lexCursor, bufferedTokens: [], lexDone: false,
    lexErrorCode: "", lexErrorStart: 0, lexErrorEnd: 0,
    lexErrorLine: 0, lexErrorColumn: 0
  }
}

fn stream_fill(stream: ParserStream, ahead: Int) -> ParserStream {
  var current = stream
  while length(current.bufferedTokens) <= ahead && !current.lexDone && current.lexErrorCode == "" {
    let progress = lexer_step(current.lexCursor)
    var errorCode = current.lexErrorCode
    var errorStart = current.lexErrorStart
    var errorEnd = current.lexErrorEnd
    var errorLine = current.lexErrorLine
    var errorColumn = current.lexErrorColumn
    if progress.errorCode != "" {
      errorCode = progress.errorCode
      errorStart = progress.errorStart
      errorEnd = progress.errorEnd
      errorLine = progress.errorLine
      errorColumn = progress.errorColumn
    } else { }
    var tokenBuffer = current.bufferedTokens
    for token in progress.tokens { tokenBuffer = append(tokenBuffer, token) }
    current = ParserStream {
      lexCursor: progress.cursor,
      bufferedTokens: tokenBuffer,
      lexDone: progress.done, lexErrorCode: errorCode,
      lexErrorStart: errorStart, lexErrorEnd: errorEnd,
      lexErrorLine: errorLine, lexErrorColumn: errorColumn
    }
  }
  return current
}

fn stream_peek(stream: ParserStream, ahead: Int) -> TokenRead {
  let ready = stream_fill(stream, ahead)
  if ready.lexErrorCode != "" {
    let token = make_token("eof", "", 0, [], ready.lexErrorStart,
      ready.lexErrorEnd, ready.lexErrorLine, ready.lexErrorColumn)
    return TokenRead { token: token, stream: ready, ok: false }
  } else { }
  if length(ready.bufferedTokens) <= ahead {
    let token = make_token("eof", "", 0, [], ready.lexCursor.offset,
      ready.lexCursor.offset, ready.lexCursor.line, ready.lexCursor.column)
    return TokenRead { token: token, stream: ready, ok: true }
  } else {
    return TokenRead { token: token_at(ready.bufferedTokens, ahead), stream: ready, ok: true }
  }
}

fn stream_take(stream: ParserStream) -> TokenRead {
  let peeked = stream_peek(stream, 0)
  if !peeked.ok || peeked.token.kind == "eof" {
    return peeked
  } else {
    let next = ParserStream {
      lexCursor: peeked.stream.lexCursor,
      bufferedTokens: tokens_drop(peeked.stream.bufferedTokens, 1),
      lexDone: peeked.stream.lexDone,
      lexErrorCode: peeked.stream.lexErrorCode,
      lexErrorStart: peeked.stream.lexErrorStart,
      lexErrorEnd: peeked.stream.lexErrorEnd,
      lexErrorLine: peeked.stream.lexErrorLine,
      lexErrorColumn: peeked.stream.lexErrorColumn
    }
    return TokenRead { token: peeked.token, stream: next, ok: true }
  }
}

fn parse_ok(value: AstValue, stream: ParserStream) -> AstParse {
  return AstParse {
    value: value, stream: stream, ok: true, errorCode: "", message: "",
    errorStart: 0, errorEnd: 0, errorLine: 0, errorColumn: 0
  }
}

fn parse_lex_error(stream: ParserStream) -> AstParse {
  return AstParse {
    value: AstAbsent(), stream: stream, ok: false,
    errorCode: stream.lexErrorCode, message: "Invalid source encoding",
    errorStart: stream.lexErrorStart, errorEnd: stream.lexErrorEnd,
    errorLine: stream.lexErrorLine, errorColumn: stream.lexErrorColumn
  }
}

fn parse_error(code: Str, message: Str, token: LexToken, stream: ParserStream) -> AstParse {
  return AstParse {
    value: AstAbsent(), stream: stream, ok: false, errorCode: code, message: message,
    errorStart: token.startByte, errorEnd: token.endByte,
    errorLine: token.line, errorColumn: token.column
  }
}

fn expect_symbol(stream: ParserStream, symbol: Str) -> TokenRead {
  let read = stream_take(stream)
  if !read.ok || read.token.kind != "symbol" || read.token.text != symbol {
    return TokenRead { token: read.token, stream: read.stream, ok: false }
  } else { return read }
}

fn parse_pattern(stream: ParserStream, depth: Int) -> AstParse {
  if depth <= 64 { } else {
    let read = stream_peek(stream, 0)
    return parse_error("PEP_PARSE_DEPTH_LIMIT", "Pattern nesting limit exceeded", read.token, read.stream)
  }
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind == "hole" && name.token.text == "" {
    return parse_ok(AstWildcardPattern(ast_span(name.token)), name.stream)
  } else { }
  if name.token.kind != "identifier" {
    return parse_error("PEP_PARSE_PATTERN", "Expected a constructor pattern, binding, or wildcard", name.token, name.stream)
  } else { }
  if name.token.text == "_" {
    return parse_ok(AstWildcardPattern(ast_span(name.token)), name.stream)
  } else { }
  let next = stream_peek(name.stream, 0)
  if next.token.kind != "symbol" || next.token.text != "(" {
    return parse_ok(AstBindingPattern(name.token.text, ast_span(name.token)), name.stream)
  } else { }
  let open = stream_take(next.stream)
  var args: List[AstValue] = []
  let firstArg = stream_peek(open.stream, 0)
  var current = firstArg.stream
  if firstArg.token.kind == "symbol" && firstArg.token.text == ")" { } else {
    let arg = parse_pattern(current, depth + 1)
    if !arg.ok { return arg } else { }
    args = prepend(args, arg.value)
    current = arg.stream
    var more = true
    while more {
      let separator = stream_peek(current, 0)
      current = separator.stream
      if separator.token.kind == "symbol" && separator.token.text == "," {
        current = stream_take(current).stream
        let after = stream_peek(current, 0)
        current = after.stream
        if after.token.kind == "symbol" && after.token.text == ")" { more = false } else {
          let nextArg = parse_pattern(current, depth + 1)
          if !nextArg.ok { return nextArg } else { }
          args = prepend(args, nextArg.value)
          current = nextArg.stream
        }
      } else { more = false }
    }
  }
  let close = stream_peek(current, 0)
  let expected = expect_symbol(close.stream, ")")
  if !expected.ok {
    if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected ')'", expected.token, expected.stream)
  } else { }
  let span = AstSpan { startByte: name.token.startByte, endByte: close.token.endByte,
    line: name.token.line, column: name.token.column }
  return parse_ok(AstConstructorPattern(name.token.text, reverse(args), span), expected.stream)
}

fn parse_if_expression_after(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let condition = parse_expression(stream, 0, false, depth + 1)
  if !condition.ok { return condition } else { }
  let openYes = expect_symbol(condition.stream, "{")
  if !openYes.ok {
    if openYes.stream.lexErrorCode != "" { return parse_lex_error(openYes.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '{'", openYes.token, openYes.stream)
  } else { }
  let yes = parse_expression(openYes.stream, 0, true, depth + 1)
  if !yes.ok { return yes } else { }
  let closeYes = stream_peek(yes.stream, 0)
  let expectedYes = expect_symbol(closeYes.stream, "}")
  if !expectedYes.ok {
    if expectedYes.stream.lexErrorCode != "" { return parse_lex_error(expectedYes.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '}'", expectedYes.token, expectedYes.stream)
  } else { }
  let elseToken = stream_peek(expectedYes.stream, 0)
  if elseToken.token.kind != "identifier" || elseToken.token.text != "else" {
    if !elseToken.ok { return parse_lex_error(elseToken.stream) } else { }
    return parse_error("PEP_PARSE_ELSE", "Expected else after the true branch", elseToken.token, elseToken.stream)
  } else { }
  let afterElse = stream_take(elseToken.stream)
  let openNo = expect_symbol(afterElse.stream, "{")
  if !openNo.ok {
    if openNo.stream.lexErrorCode != "" { return parse_lex_error(openNo.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '{'", openNo.token, openNo.stream)
  } else { }
  let no = parse_expression(openNo.stream, 0, true, depth + 1)
  if !no.ok { return no } else { }
  let closeNo = stream_peek(no.stream, 0)
  let expectedNo = expect_symbol(closeNo.stream, "}")
  if !expectedNo.ok {
    if expectedNo.stream.lexErrorCode != "" { return parse_lex_error(expectedNo.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '}'", expectedNo.token, expectedNo.stream)
  } else { }
  let span = AstSpan { startByte: first.startByte, endByte: closeNo.token.endByte,
    line: first.line, column: first.column }
  return parse_ok(AstIfExpression(condition.value, yes.value, no.value, span), expectedNo.stream)
}

fn parse_match_expression_after(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let subject = parse_expression(stream, 0, false, depth + 1)
  if !subject.ok { return subject } else { }
  let open = expect_symbol(subject.stream, "{")
  if !open.ok {
    if open.stream.lexErrorCode != "" { return parse_lex_error(open.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '{'", open.token, open.stream)
  } else { }
  var current = open.stream
  var arms: List[AstValue] = []
  let firstArm = stream_peek(current, 0)
  current = firstArm.stream
  var more = !(firstArm.token.kind == "symbol" && firstArm.token.text == "}")
  while more {
    let pattern = parse_pattern(current, depth + 1)
    if !pattern.ok { return pattern } else { }
    let arrow = expect_symbol(pattern.stream, "=>")
    if !arrow.ok {
      if arrow.stream.lexErrorCode != "" { return parse_lex_error(arrow.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected '=>'", arrow.token, arrow.stream)
    } else { }
    let result = parse_expression(arrow.stream, 0, true, depth + 1)
    if !result.ok { return result } else { }
    let armSpan = ast_combine(ast_value_span(pattern.value), ast_value_span(result.value))
    arms = prepend(arms, AstMatchArm(pattern.value, result.value, armSpan))
    current = result.stream
    let next = stream_peek(current, 0)
    current = next.stream
    more = !(next.token.kind == "symbol" && next.token.text == "}")
    if !next.ok { return parse_lex_error(current) } else { }
  }
  let close = stream_peek(current, 0)
  let expected = expect_symbol(close.stream, "}")
  if !expected.ok {
    if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '}'", expected.token, expected.stream)
  } else { }
  let span = AstSpan { startByte: first.startByte, endByte: close.token.endByte,
    line: first.line, column: first.column }
  return parse_ok(AstMatchExpression(subject.value, reverse(arms), span), expected.stream)
}
fn parse_type_syntax(stream: ParserStream, depth: Int) -> AstParse {
  if depth <= 64 { } else {
    let read = stream_peek(stream, 0)
    return parse_error("PEP_PARSE_DEPTH_LIMIT", "Type nesting limit exceeded", read.token, read.stream)
  }
  let first = stream_take(stream)
  if !first.ok { return parse_lex_error(first.stream) } else { }
  if first.token.kind != "identifier" {
    return parse_error("PEP_PARSE_TYPE", "Expected a type name", first.token, first.stream)
  } else { }
  if first.token.text == "List" {
    let open = expect_symbol(first.stream, "[")
    if !open.ok {
      if open.stream.lexErrorCode != "" { return parse_lex_error(open.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected '['", open.token, open.stream)
    } else { }
    let element = parse_type_syntax(open.stream, depth + 1)
    if !element.ok { return element } else { }
    let close = stream_peek(element.stream, 0)
    let expected = expect_symbol(close.stream, "]")
    if !expected.ok {
      if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected ']'", expected.token, expected.stream)
    } else { }
    let span = AstSpan { startByte: first.token.startByte, endByte: close.token.endByte,
      line: first.token.line, column: first.token.column }
    return parse_ok(AstTypeList(element.value, span), expected.stream)
  } else { }
  if first.token.text == "Int" || first.token.text == "Bool" || first.token.text == "Str" || first.token.text == "SourceBytes" || first.token.text == "Unit" {
    return parse_ok(AstTypeScalar(first.token.text, ast_span(first.token)), first.stream)
  } else {
    return parse_ok(AstTypeNamed(first.token.text, ast_span(first.token)), first.stream)
  }
}

fn parse_type_field(stream: ParserStream, depth: Int) -> AstParse {
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind != "identifier" { return parse_error("PEP_PARSE_NAME", "Expected a name", name.token, name.stream) } else { }
  let colon = expect_symbol(name.stream, ":")
  if !colon.ok {
    if colon.stream.lexErrorCode != "" { return parse_lex_error(colon.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected ':'", colon.token, colon.stream)
  } else { }
  let fieldType = parse_type_syntax(colon.stream, depth + 1)
  if !fieldType.ok { return fieldType } else { }
  return parse_ok(AstFieldDeclaration(name.token.text, fieldType.value,
    ast_combine(ast_span(name.token), ast_value_span(fieldType.value))), fieldType.stream)
}

fn parse_variant_declaration(stream: ParserStream, depth: Int) -> AstParse {
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind != "identifier" { return parse_error("PEP_PARSE_NAME", "Expected a name", name.token, name.stream) } else { }
  let open = expect_symbol(name.stream, "(")
  if !open.ok {
    if open.stream.lexErrorCode != "" { return parse_lex_error(open.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '('", open.token, open.stream)
  } else { }
  var args: List[AstValue] = []
  var current = open.stream
  let firstArg = stream_peek(current, 0)
  current = firstArg.stream
  if firstArg.token.kind == "symbol" && firstArg.token.text == ")" { } else {
    let arg = parse_type_syntax(current, depth + 1)
    if !arg.ok { return arg } else { }
    args = prepend(args, arg.value)
    current = arg.stream
    var more = true
    while more {
      let separator = stream_peek(current, 0)
      current = separator.stream
      if separator.token.kind == "symbol" && separator.token.text == "," {
        current = stream_take(current).stream
        let after = stream_peek(current, 0)
        current = after.stream
        if after.token.kind == "symbol" && after.token.text == ")" { more = false } else {
          let nextArg = parse_type_syntax(current, depth + 1)
          if !nextArg.ok { return nextArg } else { }
          args = prepend(args, nextArg.value)
          current = nextArg.stream
        }
      } else { more = false }
    }
  }
  let close = stream_peek(current, 0)
  let expected = expect_symbol(close.stream, ")")
  if !expected.ok {
    if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected ')'", expected.token, expected.stream)
  } else { }
  let span = AstSpan { startByte: name.token.startByte, endByte: close.token.endByte,
    line: name.token.line, column: name.token.column }
  return parse_ok(AstVariantDeclaration(name.token.text, reverse(args), span), expected.stream)
}

fn parse_type_declaration_after(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind != "identifier" { return parse_error("PEP_PARSE_NAME", "Expected a name", name.token, name.stream) } else { }
  let next = stream_peek(name.stream, 0)
  if next.token.kind == "symbol" && next.token.text == "=" {
    let afterEquals = stream_take(next.stream)
    var current = afterEquals.stream
    var variants: List[AstValue] = []
    let firstVariant = parse_variant_declaration(current, depth + 1)
    if !firstVariant.ok { return firstVariant } else { }
    variants = prepend(variants, firstVariant.value)
    current = firstVariant.stream
    var more = true
    while more {
      let separator = stream_peek(current, 0)
      current = separator.stream
      if separator.token.kind == "symbol" && separator.token.text == "|" {
        let after = stream_take(current)
        let variant = parse_variant_declaration(after.stream, depth + 1)
        if !variant.ok { return variant } else { }
        variants = prepend(variants, variant.value)
        current = variant.stream
      } else { more = false }
    }
    let reversed = reverse(variants)
    var lastSpan = ast_span(first)
    for variant in reversed { lastSpan = ast_value_span(variant) }
    return parse_ok(AstUnionDeclaration(name.token.text, reversed,
      ast_combine(ast_span(first), lastSpan)), current)
  } else {
    let open = expect_symbol(next.stream, "{")
    if !open.ok {
      if open.stream.lexErrorCode != "" { return parse_lex_error(open.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected '{'", open.token, open.stream)
    } else { }
    var current = open.stream
    var fields: List[AstValue] = []
    var more = true
    while more {
      let nextField = stream_peek(current, 0)
      current = nextField.stream
      if !nextField.ok { return parse_lex_error(current) } else { }
      if nextField.token.kind == "symbol" && nextField.token.text == "}" { more = false } else {
        if nextField.token.kind == "eof" { more = false } else {
          let field = parse_type_field(current, depth + 1)
          if !field.ok { return field } else { }
          fields = prepend(fields, field.value)
          current = field.stream
          let separator = stream_peek(current, 0)
          current = separator.stream
          if separator.token.kind == "symbol" && (separator.token.text == "," || separator.token.text == ";") {
            current = stream_take(current).stream
          } else { }
        }
      }
    }
    let close = stream_peek(current, 0)
    let expected = expect_symbol(close.stream, "}")
    if !expected.ok {
      if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected '}'", expected.token, expected.stream)
    } else { }
    let span = AstSpan { startByte: first.startByte, endByte: close.token.endByte,
      line: first.line, column: first.column }
    return parse_ok(AstRecordDeclaration(name.token.text, reverse(fields), span), expected.stream)
  }
}

fn parse_parameter(stream: ParserStream, depth: Int) -> AstParse {
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind != "identifier" { return parse_error("PEP_PARSE_NAME", "Expected a name", name.token, name.stream) } else { }
  let colon = expect_symbol(name.stream, ":")
  if !colon.ok {
    if colon.stream.lexErrorCode != "" { return parse_lex_error(colon.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected ':'", colon.token, colon.stream)
  } else { }
  let parameterType = parse_type_syntax(colon.stream, depth + 1)
  if !parameterType.ok { return parameterType } else { }
  return parse_ok(AstParameter(name.token.text, parameterType.value,
    ast_span(name.token)), parameterType.stream)
}

fn block_parse_error(code: Str, message: Str, token: LexToken, stream: ParserStream) -> BlockParse {
  return BlockParse { statements: [], stream: stream,
    opening: make_token("eof", "", 0, [], token.startByte, token.startByte, token.line, token.column),
    closing: token, ok: false, errorCode: code, message: message,
    errorStart: token.startByte, errorEnd: token.endByte,
    errorLine: token.line, errorColumn: token.column }
}

fn block_parse_from_error(parsed: AstParse) -> BlockParse {
  let token = make_token("eof", "", 0, [], parsed.errorStart, parsed.errorEnd,
    parsed.errorLine, parsed.errorColumn)
  return block_parse_error(parsed.errorCode, parsed.message, token, parsed.stream)
}

fn statement_from_block_error(block: BlockParse) -> AstParse {
  return AstParse { value: AstAbsent(), stream: block.stream, ok: false,
    errorCode: block.errorCode, message: block.message,
    errorStart: block.errorStart, errorEnd: block.errorEnd,
    errorLine: block.errorLine, errorColumn: block.errorColumn }
}

fn parse_optional_semicolon(stream: ParserStream) -> TokenRead {
  let next = stream_peek(stream, 0)
  if !next.ok { return next } else { }
  if next.token.kind == "symbol" && next.token.text == ";" {
    return stream_take(next.stream)
  } else { return next }
}

fn parse_block_after(stream: ParserStream, depth: Int) -> BlockParse {
  let open = expect_symbol(stream, "{")
  if !open.ok { return block_parse_error("PEP_PARSE_EXPECTED", "Expected '{'", open.token, open.stream) } else { }
  var current = open.stream
  var reversed: List[AstValue] = []
  var finished = false
  while !finished {
    let next = stream_peek(current, 0)
    current = next.stream
    if !next.ok { return block_parse_error(current.lexErrorCode, "Invalid source encoding",
      next.token, current) } else { }
    if next.token.kind == "symbol" && next.token.text == "}" { finished = true } else {
      if next.token.kind == "eof" { finished = true } else {
        let statement = parse_statement(current, depth + 1)
        if !statement.ok { return block_parse_from_error(statement) } else { }
        reversed = prepend(reversed, statement.value)
        current = statement.stream
      }
    }
  }
  let close = stream_peek(current, 0)
  let expected = expect_symbol(close.stream, "}")
  if !expected.ok { return block_parse_error("PEP_PARSE_EXPECTED", "Expected '}'", expected.token, expected.stream) } else { }
  return BlockParse { statements: reverse(reversed), stream: expected.stream,
    opening: open.token, closing: close.token, ok: true, errorCode: "", message: "",
    errorStart: 0, errorEnd: 0, errorLine: 0, errorColumn: 0 }
}

fn parse_binding_statement(first: LexToken, stream: ParserStream, mutableBinding: Bool, depth: Int) -> AstParse {
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind != "identifier" { return parse_error("PEP_PARSE_NAME", "Expected a name", name.token, name.stream) } else { }
  let afterName = stream_peek(name.stream, 0)
  var current = afterName.stream
  var annotation: AstValue = AstAbsent()
  if afterName.token.kind == "symbol" && afterName.token.text == ":" {
    let type = parse_type_syntax(stream_take(current).stream, depth + 1)
    if !type.ok { return type } else { }
    annotation = type.value
    current = type.stream
  } else { }
  let equals = expect_symbol(current, "=")
  if !equals.ok {
    if equals.stream.lexErrorCode != "" { return parse_lex_error(equals.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '='", equals.token, equals.stream)
  } else { }
  let value = parse_expression(equals.stream, 0, true, depth + 1)
  if !value.ok { return value } else { }
  let semicolon = parse_optional_semicolon(value.stream)
  if !semicolon.ok { return parse_lex_error(semicolon.stream) } else { }
  let span = ast_combine(ast_span(first), ast_value_span(value.value))
  if mutableBinding {
    return parse_ok(AstVar(name.token.text, annotation, value.value, span), semicolon.stream)
  } else { return parse_ok(AstLet(name.token.text, annotation, value.value, span), semicolon.stream) }
}

fn parse_return_statement(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let value = parse_expression(stream, 0, true, depth + 1)
  if !value.ok { return value } else { }
  let semicolon = parse_optional_semicolon(value.stream)
  if !semicolon.ok { return parse_lex_error(semicolon.stream) } else { }
  return parse_ok(AstReturn(value.value, ast_combine(ast_span(first), ast_value_span(value.value))), semicolon.stream)
}

fn parse_if_statement_after(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let condition = parse_expression(stream, 0, false, depth + 1)
  if !condition.ok { return condition } else { }
  let yes = parse_block_after(condition.stream, depth + 1)
  if !yes.ok { return statement_from_block_error(yes) } else { }
  let elseToken = stream_peek(yes.stream, 0)
  if !elseToken.ok { return parse_lex_error(elseToken.stream) } else { }
  if elseToken.token.kind != "identifier" || elseToken.token.text != "else" {
    return parse_error("PEP_PARSE_ELSE", "Expected else after if block", elseToken.token, elseToken.stream)
  } else { }
  let no = parse_block_after(stream_take(elseToken.stream).stream, depth + 1)
  if !no.ok { return statement_from_block_error(no) } else { }
  let span = AstSpan { startByte: first.startByte, endByte: no.closing.endByte,
    line: first.line, column: first.column }
  return parse_ok(AstIfStatement(condition.value, yes.statements, no.statements, span), no.stream)
}

fn parse_while_statement_after(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let condition = parse_expression(stream, 0, false, depth + 1)
  if !condition.ok { return condition } else { }
  let body = parse_block_after(condition.stream, depth + 1)
  if !body.ok { return statement_from_block_error(body) } else { }
  let span = AstSpan { startByte: first.startByte, endByte: body.closing.endByte,
    line: first.line, column: first.column }
  return parse_ok(AstWhile(condition.value, body.statements, span), body.stream)
}

fn parse_for_statement_after(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind != "identifier" { return parse_error("PEP_PARSE_NAME", "Expected a name", name.token, name.stream) } else { }
  let inToken = stream_peek(name.stream, 0)
  if !inToken.ok { return parse_lex_error(inToken.stream) } else { }
  if inToken.token.kind != "identifier" || inToken.token.text != "in" {
    return parse_error("PEP_PARSE_FOR_IN", "Expected 'in' after the loop variable", inToken.token, inToken.stream)
  } else { }
  let values = parse_expression(stream_take(inToken.stream).stream, 0, false, depth + 1)
  if !values.ok { return values } else { }
  let body = parse_block_after(values.stream, depth + 1)
  if !body.ok { return statement_from_block_error(body) } else { }
  let span = AstSpan { startByte: first.startByte, endByte: body.closing.endByte,
    line: first.line, column: first.column }
  return parse_ok(AstForIn(name.token.text, values.value, body.statements, span), body.stream)
}

fn parse_statement(stream: ParserStream, depth: Int) -> AstParse {
  let firstRead = stream_peek(stream, 0)
  if !firstRead.ok { return parse_lex_error(firstRead.stream) } else { }
  let first = firstRead.token
  if first.kind == "eof" { return parse_error("PEP_PARSE_EXPRESSION", "Expected an expression", first, firstRead.stream) } else { }
  let afterFirst = stream_take(firstRead.stream)
  if first.kind == "identifier" && (first.text == "let" || first.text == "var") {
    return parse_binding_statement(first, afterFirst.stream, first.text == "var", depth)
  } else { }
  if first.kind == "identifier" && first.text == "return" {
    return parse_return_statement(first, afterFirst.stream, depth)
  } else { }
  if first.kind == "identifier" && first.text == "if" {
    return parse_if_statement_after(first, afterFirst.stream, depth)
  } else { }
  if first.kind == "identifier" && first.text == "while" {
    return parse_while_statement_after(first, afterFirst.stream, depth)
  } else { }
  if first.kind == "identifier" && first.text == "for" {
    return parse_for_statement_after(first, afterFirst.stream, depth)
  } else { }
  if first.kind == "symbol" && first.text == "{" {
    let block = parse_block_after(firstRead.stream, depth + 1)
    if !block.ok { return statement_from_block_error(block) } else { }
    let span = AstSpan { startByte: block.opening.startByte, endByte: block.closing.endByte,
      line: block.opening.line, column: block.opening.column }
    return parse_ok(AstBlock(block.statements, span), block.stream)
  } else { }
  let expression = parse_expression(firstRead.stream, 0, true, depth + 1)
  if !expression.ok { return expression } else { }
  let afterExpression = stream_peek(expression.stream, 0)
  if !afterExpression.ok { return parse_lex_error(afterExpression.stream) } else { }
  let expressionSpan = ast_value_span(expression.value)
  if first.kind == "identifier" && expressionSpan.startByte == first.startByte && expressionSpan.endByte == first.endByte &&
     afterExpression.token.kind == "symbol" && afterExpression.token.text == "=" {
    let value = parse_expression(stream_take(afterExpression.stream).stream, 0, true, depth + 1)
    if !value.ok { return value } else { }
    let semicolon = parse_optional_semicolon(value.stream)
    if !semicolon.ok { return parse_lex_error(semicolon.stream) } else { }
    return parse_ok(AstAssignment(first.text, value.value,
      ast_combine(ast_span(first), ast_value_span(value.value))), semicolon.stream)
  } else { }
  let semicolon = parse_optional_semicolon(expression.stream)
  if !semicolon.ok { return parse_lex_error(semicolon.stream) } else { }
  return parse_ok(AstExpressionStatement(expression.value, expressionSpan), semicolon.stream)
}
fn parse_type_parameters(stream: ParserStream, depth: Int) -> AstParse {
  let first = stream_peek(stream, 0)
  if !(first.token.kind == "symbol" && first.token.text == "[") {
    return parse_ok(AstList([], AstSpan { startByte: 0, endByte: 0, line: 1, column: 1 }), first.stream)
  } else { }
  let open = stream_take(first.stream)
  var current = open.stream
  let firstParameter = stream_peek(current, 0)
  current = firstParameter.stream
  if firstParameter.token.kind == "symbol" && firstParameter.token.text == "]" {
    return parse_error("PEP_EMPTY_TYPE_PARAMETERS", "A generic parameter list cannot be empty", firstParameter.token, current)
  } else { }
  var reversedParameters: List[AstValue] = []
  var more = true
  while more {
    let parameter = stream_take(current)
    if !parameter.ok { return parse_lex_error(parameter.stream) } else { }
    if parameter.token.kind != "identifier" {
      return parse_error("PEP_PARSE_TYPE_PARAMETER", "Expected a generic type parameter name", parameter.token, parameter.stream)
    } else { }
    reversedParameters = prepend(reversedParameters, AstTypeParameter(parameter.token.text, ast_span(parameter.token)))
    let separator = stream_peek(parameter.stream, 0)
    current = separator.stream
    if separator.token.kind == "symbol" && separator.token.text == "," {
      current = stream_take(current).stream
      let afterComma = stream_peek(current, 0)
      current = afterComma.stream
      if afterComma.token.kind == "symbol" && afterComma.token.text == "]" {
        return parse_error("PEP_PARSE_TYPE_PARAMETER", "Expected a type parameter after ','", afterComma.token, current)
      } else { }
    } else { more = false }
  }
  let close = expect_symbol(current, "]")
  if !close.ok {
    if close.stream.lexErrorCode != "" { return parse_lex_error(close.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected ']'", close.token, close.stream)
  } else { }
  return parse_ok(AstList(reverse(reversedParameters), ast_combine(ast_span(open.token), ast_span(close.token))), close.stream)
}

fn parse_function_header_after(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind != "identifier" { return parse_error("PEP_PARSE_NAME", "Expected a name", name.token, name.stream) } else { }
  let parsedTypeParameters = parse_type_parameters(name.stream, depth + 1)
  if !parsedTypeParameters.ok { return parsedTypeParameters } else { }
  let typeParameters = match parsedTypeParameters.value {
    AstList(items, _) => items
    _ => []
  }
  let open = expect_symbol(parsedTypeParameters.stream, "(")
  if !open.ok {
    if open.stream.lexErrorCode != "" { return parse_lex_error(open.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '('", open.token, open.stream)
  } else { }
  var parameters: List[AstValue] = []
  var current = open.stream
  let firstParam = stream_peek(current, 0)
  current = firstParam.stream
  if firstParam.token.kind == "symbol" && firstParam.token.text == ")" { } else {
    let parameter = parse_parameter(current, depth + 1)
    if !parameter.ok { return parameter } else { }
    parameters = prepend(parameters, parameter.value)
    current = parameter.stream
    var more = true
    while more {
      let separator = stream_peek(current, 0)
      current = separator.stream
      if separator.token.kind == "symbol" && separator.token.text == "," {
        current = stream_take(current).stream
        let after = stream_peek(current, 0)
        current = after.stream
        if after.token.kind == "symbol" && after.token.text == ")" { more = false } else {
          let nextParameter = parse_parameter(current, depth + 1)
          if !nextParameter.ok { return nextParameter } else { }
          parameters = prepend(parameters, nextParameter.value)
          current = nextParameter.stream
        }
      } else { more = false }
    }
  }
  let close = expect_symbol(current, ")")
  if !close.ok {
    if close.stream.lexErrorCode != "" { return parse_lex_error(close.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected ')'", close.token, close.stream)
  } else { }
  let arrow = expect_symbol(close.stream, "->")
  if !arrow.ok {
    if arrow.stream.lexErrorCode != "" { return parse_lex_error(arrow.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected '->'", arrow.token, arrow.stream)
  } else { }
  let result = parse_type_syntax(arrow.stream, depth + 1)
  if !result.ok { return result } else { }
  let functionSpan = AstSpan { startByte: first.startByte,
    endByte: ast_value_span(result.value).endByte, line: first.line, column: first.column }
  return parse_ok(AstFunction(name.token.text, typeParameters, reverse(parameters), result.value, [], functionSpan), result.stream)
}

fn parse_function_after(first: LexToken, stream: ParserStream, depth: Int) -> AstParse {
  let header = parse_function_header_after(first, stream, depth)
  if !header.ok { return header } else { }
  let body = parse_block_after(header.stream, depth + 1)
  if !body.ok {
    return AstParse { value: AstAbsent(), stream: body.stream, ok: false,
      errorCode: body.errorCode, message: body.message, errorStart: body.errorStart,
      errorEnd: body.errorEnd, errorLine: body.errorLine, errorColumn: body.errorColumn }
  } else { }
  return match header.value {
    AstFunction(name, typeParameters, parameters, resultType, bodyItems, span) => parse_complete_function(
      name, typeParameters, parameters, resultType, span, body)
    _ => parse_error("PEP_PARSER_INTERNAL", "Function header did not produce a function", body.opening, body.stream)
  }
}

fn parse_complete_function(name: Str, typeParameters: List[AstValue], parameters: List[AstValue], resultType: AstValue,
  span: AstSpan, body: BlockParse) -> AstParse {
  let functionSpan = AstSpan { startByte: span.startByte, endByte: body.closing.endByte,
    line: span.line, column: span.column }
  return parse_ok(AstFunction(name, typeParameters, parameters, resultType, body.statements, functionSpan), body.stream)
}
fn parse_expression(stream: ParserStream, minimumPrecedence: Int, recordAllowed: Bool, depth: Int) -> AstParse {
  if depth <= 64 { } else {
    let read = stream_peek(stream, 0)
    return parse_error("PEP_PARSE_DEPTH_LIMIT", "Expression nesting limit exceeded", read.token, read.stream)
  }
  let firstRead = stream_take(stream)
  if !firstRead.ok { return parse_lex_error(firstRead.stream) } else { }
  let first = firstRead.token
  var current = firstRead.stream
  var left: AstValue = AstAbsent()
  var failed: AstParse = parse_ok(AstAbsent(), current)
  var prefixOk = false
  if first.kind == "identifier" && first.text == "if" {
    let parsedIf = parse_if_expression_after(first, current, depth)
    if !parsedIf.ok { return parsedIf } else { }
    left = parsedIf.value
    current = parsedIf.stream
    prefixOk = true
  } else { if first.kind == "identifier" && first.text == "match" {
    let parsedMatch = parse_match_expression_after(first, current, depth)
    if !parsedMatch.ok { return parsedMatch } else { }
    left = parsedMatch.value
    current = parsedMatch.stream
    prefixOk = true
  } else { } }

  if prefixOk { } else { if first.kind == "integer" {
    left = AstInteger(first.integerValue, ast_span(first))
  } else { if first.kind == "string" {
    left = AstString(first.stringParts, ast_span(first))
  } else { if first.kind == "hole" {
    left = AstHole(first.text, ast_span(first))
  } else { if first.kind == "identifier" && first.text == "true" {
    left = AstBoolean(true, ast_span(first))
  } else { if first.kind == "identifier" && first.text == "false" {
    left = AstBoolean(false, ast_span(first))
  } else { if first.kind == "symbol" && first.text == "[" {
    var items: List[AstValue] = []
    let peek = stream_peek(current, 0)
    current = peek.stream
    if peek.token.kind == "symbol" && peek.token.text == "]" {
    } else {
      let item = parse_expression(current, 0, true, depth + 1)
      if !item.ok { return item } else { }
      items = prepend(items, item.value)
      current = item.stream
      var more = true
      while more {
        let separator = stream_peek(current, 0)
        current = separator.stream
        if separator.token.kind == "symbol" && separator.token.text == "," {
          let consumed = stream_take(current)
          current = consumed.stream
          let after = stream_peek(current, 0)
          current = after.stream
          if after.token.kind == "symbol" && after.token.text == "]" {
            more = false
          } else {
            let nextItem = parse_expression(current, 0, true, depth + 1)
            if !nextItem.ok { return nextItem } else { }
            items = prepend(items, nextItem.value)
            current = nextItem.stream
          }
        } else { more = false }
      }
    }
    let close = stream_peek(current, 0)
    current = close.stream
    let expected = expect_symbol(current, "]")
    if !expected.ok {
      if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected ']'", expected.token, expected.stream)
    } else { }
    current = expected.stream
    left = AstList(reverse(items), ast_combine(ast_span(first), ast_span(close.token)))
  } else { if first.kind == "symbol" && first.text == "!" {
    let operand = parse_expression(current, 30, recordAllowed, depth + 1)
    if !operand.ok { return operand } else { }
    current = operand.stream
    left = AstUnary("!", operand.value, ast_combine(ast_span(first), ast_value_span(operand.value)))
  } else { if first.kind == "symbol" && first.text == "-" {
    let operand = parse_expression(current, 30, recordAllowed, depth + 1)
    if !operand.ok { return operand } else { }
    current = operand.stream
    let zero = AstInteger(0, ast_span(first))
    left = AstBinary("neg", zero, operand.value, ast_combine(ast_span(first), ast_value_span(operand.value)))
  } else { if first.kind == "symbol" && first.text == "(" {
    let inside = parse_expression(current, 0, recordAllowed, depth + 1)
    if !inside.ok { return inside } else { }
    current = inside.stream
    let close = stream_peek(current, 0)
    current = close.stream
    let expected = expect_symbol(current, ")")
    if !expected.ok {
      if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected ')'", expected.token, expected.stream)
    } else { }
    current = expected.stream
    let grouped = ast_combine(ast_span(first), ast_span(close.token))
    left = ast_set_span(inside.value, grouped)
  } else { if first.kind == "identifier" {
    let afterName = stream_peek(current, 0)
    current = afterName.stream
    if afterName.token.kind == "symbol" && afterName.token.text == "(" {
      let open = stream_take(current)
      current = open.stream
      var args: List[AstValue] = []
      let firstArg = stream_peek(current, 0)
      current = firstArg.stream
      if firstArg.token.kind == "symbol" && firstArg.token.text == ")" {
      } else {
        let arg = parse_expression(current, 0, true, depth + 1)
        if !arg.ok { return arg } else { }
        current = arg.stream
        args = prepend(args, arg.value)
        var more = true
        while more {
          let separator = stream_peek(current, 0)
          current = separator.stream
          if separator.token.kind == "symbol" && separator.token.text == "," {
            let consumed = stream_take(current)
            current = consumed.stream
            let next = stream_peek(current, 0)
            current = next.stream
            if next.token.kind == "symbol" && next.token.text == ")" {
              more = false
            } else {
              let nextArg = parse_expression(current, 0, true, depth + 1)
              if !nextArg.ok { return nextArg } else { }
              current = nextArg.stream
              args = prepend(args, nextArg.value)
            }
          } else { more = false }
        }
      }
      let close = stream_peek(current, 0)
      current = close.stream
      let expected = expect_symbol(current, ")")
      if !expected.ok {
        if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
        return parse_error("PEP_PARSE_EXPECTED", "Expected ')'", expected.token, expected.stream)
      } else { }
      current = expected.stream
      left = AstCall(first.text, reverse(args), ast_combine(ast_span(first), ast_span(close.token)))
    } else {
      let brace = stream_peek(current, 0)
      current = brace.stream
      if recordAllowed && brace.token.kind == "symbol" && brace.token.text == "{" && brace.token.line == first.line {
        let open = stream_take(current)
        current = open.stream
        var fields: List[AstValue] = []
        let fieldStart = stream_peek(current, 0)
        current = fieldStart.stream
        if fieldStart.token.kind == "symbol" && fieldStart.token.text == "}" {
        } else {
          let field = parse_record_field(current, depth + 1)
          if !field.ok { return field } else { }
          current = field.stream
          fields = prepend(fields, field.value)
          var moreFields = true
          while moreFields {
            let separator = stream_peek(current, 0)
            current = separator.stream
            if separator.token.kind == "symbol" && separator.token.text == "," {
              let consumed = stream_take(current)
              current = consumed.stream
              let next = stream_peek(current, 0)
              current = next.stream
              if next.token.kind == "symbol" && next.token.text == "}" {
                moreFields = false
              } else {
                let nextField = parse_record_field(current, depth + 1)
                if !nextField.ok { return nextField } else { }
                current = nextField.stream
                fields = prepend(fields, nextField.value)
              }
            } else { moreFields = false }
          }
        }
        let close = stream_peek(current, 0)
        current = close.stream
        let expected = expect_symbol(current, "}")
        if !expected.ok {
          if expected.stream.lexErrorCode != "" { return parse_lex_error(expected.stream) } else { }
          return parse_error("PEP_PARSE_EXPECTED", "Expected '}'", expected.token, expected.stream)
        } else { }
        current = expected.stream
        left = AstRecordExpression(first.text, reverse(fields), ast_combine(ast_span(first), ast_span(close.token)))
      } else { left = AstName(first.text, ast_span(first)) }
    }
  } else { if first.kind == "symbol" && first.text == "if" {
    let condition = parse_expression(current, 0, false, depth + 1)
    if !condition.ok { return condition } else { }
    current = condition.stream
    let openYes = expect_symbol(current, "{")
    if !openYes.ok {
      if openYes.stream.lexErrorCode != "" { return parse_lex_error(openYes.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected '{'", openYes.token, openYes.stream)
    } else { }
    let yes = parse_expression(openYes.stream, 0, true, depth + 1)
    if !yes.ok { return yes } else { }
    let closeYes = stream_peek(yes.stream, 0)
    let expectedYes = expect_symbol(closeYes.stream, "}")
    if !expectedYes.ok {
      if expectedYes.stream.lexErrorCode != "" { return parse_lex_error(expectedYes.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected '}'", expectedYes.token, expectedYes.stream)
    } else { }
    let elseToken = stream_peek(expectedYes.stream, 0)
    if elseToken.token.kind != "identifier" || elseToken.token.text != "else" {
      if !elseToken.ok { return parse_lex_error(elseToken.stream) } else { }
      return parse_error("PEP_PARSE_ELSE", "Expected else after the true branch", elseToken.token, elseToken.stream)
    } else { }
    let afterElse = stream_take(elseToken.stream)
    let openNo = expect_symbol(afterElse.stream, "{")
    if !openNo.ok {
      if openNo.stream.lexErrorCode != "" { return parse_lex_error(openNo.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected '{'", openNo.token, openNo.stream)
    } else { }
    let no = parse_expression(openNo.stream, 0, true, depth + 1)
    if !no.ok { return no } else { }
    let closeNo = stream_peek(no.stream, 0)
    let expectedNo = expect_symbol(closeNo.stream, "}")
    if !expectedNo.ok {
      if expectedNo.stream.lexErrorCode != "" { return parse_lex_error(expectedNo.stream) } else { }
      return parse_error("PEP_PARSE_EXPECTED", "Expected '}'", expectedNo.token, expectedNo.stream)
    } else { }
    current = expectedNo.stream
    left = AstIfExpression(condition.value, yes.value, no.value, ast_combine(ast_span(first), ast_span(closeNo.token)))
  } else {
    return parse_error("PEP_PARSE_EXPRESSION", "Expected an expression", first, current)
  } } } } } } } } } } } }

  var more = true
  while more {
    let next = stream_peek(current, 0)
    current = next.stream
    if !next.ok { return parse_lex_error(current) } else { }
    if next.token.kind == "symbol" && next.token.text == "." {
      let dot = stream_take(current)
      let field = stream_take(dot.stream)
      if !field.ok { return parse_lex_error(field.stream) } else { }
      if field.token.kind != "identifier" {
        return parse_error("PEP_PARSE_NAME", "Expected a name", field.token, field.stream)
      } else { }
      let fieldSpan = ast_combine(ast_value_span(left), ast_span(field.token))
      left = AstFieldAccess(left, field.token.text, fieldSpan)
      current = field.stream
    } else {
      let op = next.token.text
      let precedence = if op == "||" { 1 } else { if op == "&&" { 2 } else { if op == "==" || op == "!=" { 3 } else { if op == "<=" { 5 } else { if op == "+" || op == "-" { 10 } else { if op == "*" || op == "/" { 20 } else { -1 } } } } } }
      if next.token.kind == "symbol" && minimumPrecedence <= precedence {
        let operatorToken = stream_take(current)
        let right = parse_expression(operatorToken.stream, precedence + 1, recordAllowed, depth + 1)
        if !right.ok { return right } else { }
        left = AstBinary(op, left, right.value, ast_combine(ast_value_span(left), ast_value_span(right.value)))
        current = right.stream
      } else { more = false }
    }
  }
  return parse_ok(left, current)
}

fn parse_record_field(stream: ParserStream, depth: Int) -> AstParse {
  let name = stream_take(stream)
  if !name.ok { return parse_lex_error(name.stream) } else { }
  if name.token.kind != "identifier" {
    return parse_error("PEP_PARSE_NAME", "Expected a name", name.token, name.stream)
  } else { }
  let colon = expect_symbol(name.stream, ":")
  if !colon.ok {
    if colon.stream.lexErrorCode != "" { return parse_lex_error(colon.stream) } else { }
    return parse_error("PEP_PARSE_EXPECTED", "Expected ':'", colon.token, colon.stream)
  } else { }
  let value = parse_expression(colon.stream, 0, true, depth)
  if !value.ok { return value } else { }
  return parse_ok(AstRecordField(name.token.text, value.value,
    ast_combine(ast_span(name.token), ast_value_span(value.value))), value.stream)
}

fn ast_set_span(value: AstValue, span: AstSpan) -> AstValue {
  return ast_set_span_part_1(value, span)
}
fn ast_set_span_part_1(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstInteger(number, oldSpan) => AstInteger(number, span)
    AstBoolean(flag, oldSpan) => AstBoolean(flag, span)
    _ => ast_set_span_part_2(value, span)
  }
}
fn ast_set_span_part_2(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstString(parts, oldSpan) => AstString(parts, span)
    AstName(name, oldSpan) => AstName(name, span)
    _ => ast_set_span_part_3(value, span)
  }
}
fn ast_set_span_part_3(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstHole(name, oldSpan) => AstHole(name, span)
    AstCall(name, args, oldSpan) => AstCall(name, args, span)
    _ => ast_set_span_part_4(value, span)
  }
}
fn ast_set_span_part_4(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstBinary(op, left, right, oldSpan) => AstBinary(op, left, right, span)
    AstUnary(op, operand, oldSpan) => AstUnary(op, operand, span)
    _ => ast_set_span_part_5(value, span)
  }
}
fn ast_set_span_part_5(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstList(items, oldSpan) => AstList(items, span)
    AstIfExpression(condition, yes, no, oldSpan) => AstIfExpression(condition, yes, no, span)
    _ => ast_set_span_part_6(value, span)
  }
}
fn ast_set_span_part_6(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstRecordField(name, fieldValue, oldSpan) => AstRecordField(name, fieldValue, span)
    AstRecordExpression(name, fields, oldSpan) => AstRecordExpression(name, fields, span)
    _ => ast_set_span_part_7(value, span)
  }
}
fn ast_set_span_part_7(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstFieldAccess(base, field, oldSpan) => AstFieldAccess(base, field, span)
    AstMatchExpression(subject, arms, oldSpan) => AstMatchExpression(subject, arms, span)
    _ => ast_set_span_part_8(value, span)
  }
}
fn ast_set_span_part_8(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstWildcardPattern(oldSpan) => AstWildcardPattern(span)
    AstBindingPattern(name, oldSpan) => AstBindingPattern(name, span)
    _ => ast_set_span_part_9(value, span)
  }
}
fn ast_set_span_part_9(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstConstructorPattern(name, args, oldSpan) => AstConstructorPattern(name, args, span)
    AstMatchArm(pattern, result, oldSpan) => AstMatchArm(pattern, result, span)
    _ => ast_set_span_part_10(value, span)
  }
}
fn ast_set_span_part_10(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstTypeScalar(name, oldSpan) => AstTypeScalar(name, span)
    AstTypeNamed(name, oldSpan) => AstTypeNamed(name, span)
    _ => ast_set_span_part_11(value, span)
  }
}
fn ast_set_span_part_11(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstTypeList(element, oldSpan) => AstTypeList(element, span)
    AstTypeParameter(name, oldSpan) => AstTypeParameter(name, span)
    _ => ast_set_span_part_12(value, span)
  }
}
fn ast_set_span_part_12(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstParameter(name, ty, oldSpan) => AstParameter(name, ty, span)
    AstFieldDeclaration(name, ty, oldSpan) => AstFieldDeclaration(name, ty, span)
    _ => ast_set_span_part_13(value, span)
  }
}
fn ast_set_span_part_13(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstVariantDeclaration(name, args, oldSpan) => AstVariantDeclaration(name, args, span)
    AstRecordDeclaration(name, fields, oldSpan) => AstRecordDeclaration(name, fields, span)
    _ => ast_set_span_part_14(value, span)
  }
}
fn ast_set_span_part_14(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstUnionDeclaration(name, variants, oldSpan) => AstUnionDeclaration(name, variants, span)
    AstLet(name, annotation, expression, oldSpan) => AstLet(name, annotation, expression, span)
    _ => ast_set_span_part_15(value, span)
  }
}
fn ast_set_span_part_15(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstVar(name, annotation, expression, oldSpan) => AstVar(name, annotation, expression, span)
    AstAssignment(name, expression, oldSpan) => AstAssignment(name, expression, span)
    _ => ast_set_span_part_16(value, span)
  }
}
fn ast_set_span_part_16(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstReturn(expression, oldSpan) => AstReturn(expression, span)
    AstBlock(statements, oldSpan) => AstBlock(statements, span)
    _ => ast_set_span_part_17(value, span)
  }
}
fn ast_set_span_part_17(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstIfStatement(condition, yes, no, oldSpan) => AstIfStatement(condition, yes, no, span)
    AstForIn(name, iterable, body, oldSpan) => AstForIn(name, iterable, body, span)
    _ => ast_set_span_part_18(value, span)
  }
}
fn ast_set_span_part_18(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstWhile(condition, body, oldSpan) => AstWhile(condition, body, span)
    AstExpressionStatement(expression, oldSpan) => AstExpressionStatement(expression, span)
    _ => ast_set_span_part_19(value, span)
  }
}
fn ast_set_span_part_19(value: AstValue, span: AstSpan) -> AstValue {
  return match value {
    AstFunction(name, typeParameters, parameters, result, body, oldSpan) => AstFunction(name, typeParameters, parameters, result, body, span)
    AstAbsent() => AstAbsent()
    _ => AstAbsent()
  }
}
fn flatten_ast(value: AstValue, topLevelChildIndex: Int) -> List[FlatAstNode] {
  let state = flat_node(value, -1, topLevelChildIndex, "top_level",
    FlatState { nextId: 0, nodesReversed: [] })
  return reverse(state.nodesReversed)
}

fn flat_rebase_ids(nodes: List[FlatAstNode], offset: Int) -> List[FlatAstNode] {
  var reversed: List[FlatAstNode] = []
  for node in nodes {
    let parent = if node.parentId <= -1 { -1 } else { node.parentId + offset }
    reversed = prepend(reversed, FlatAstNode {
      id: node.id + offset, parentId: parent, childIndex: node.childIndex,
      role: node.role, kind: node.kind, text: node.text,
      integerValue: node.integerValue, booleanValue: node.booleanValue,
      stringParts: node.stringParts, startByte: node.startByte,
      endByte: node.endByte, line: node.line, column: node.column
    })
  }
  return reverse(reversed)
}

fn parser_progress(status: Str, nodes: List[FlatAstNode], done: Bool,
  code: Str, message: Str, start: Int, ending: Int, line: Int, column: Int
) -> ParserProgress {
  let info = semantic_snapshot()
  return ParserProgress {
    document: info.document, revision: info.revision, status: status,
    nodes: nodes, done: done, errorCode: code, message: message,
    errorStart: start, errorEnd: ending, errorLine: line, errorColumn: column
  }
}

fn parser_chunk(cursor: ParserCursor, status: Str, nodes: List[FlatAstNode], done: Bool,
  code: Str, message: Str, start: Int, ending: Int, line: Int, column: Int
) -> ParserChunk {
  let info = semantic_snapshot()
  return ParserChunk {
    document: info.document, revision: info.revision, status: status,
    nodes: nodes, cursor: cursor, done: done, errorCode: code, message: message,
    errorStart: start, errorEnd: ending, errorLine: line, errorColumn: column
  }
}

fn parse_top_level_item(stream: ParserStream, depth: Int) -> AstParse {
  let next = stream_peek(stream, 0)
  if !next.ok { return parse_lex_error(next.stream) } else { }
  if next.token.kind == "eof" { return parse_ok(AstAbsent(), next.stream) } else { }
  let beforeOffset = next.stream.lexCursor.offset
  let beforeCount = length(next.stream.bufferedTokens)
  var item: AstParse = parse_ok(AstAbsent(), next.stream)
  if next.token.kind == "identifier" && next.token.text == "fn" {
    let keyword = stream_take(next.stream)
    item = parse_function_after(keyword.token, keyword.stream, depth + 1)
  } else { if next.token.kind == "identifier" && next.token.text == "type" {
    let keyword = stream_take(next.stream)
    item = parse_type_declaration_after(keyword.token, keyword.stream, depth + 1)
  } else { item = parse_statement(next.stream, depth + 1) } }
  if !item.ok { return item } else { }
  if item.stream.lexCursor.offset == beforeOffset && length(item.stream.bufferedTokens) == beforeCount {
    let stuck = stream_peek(item.stream, 0)
    return parse_error("PEP_PARSE_NO_PROGRESS", "Parser made no progress", stuck.token, stuck.stream)
  } else { }
  return item
}

fn parser_start() -> ParserCursor {
  let info = semantic_snapshot()
  return ParserCursor {
    document: info.document, revision: info.revision,
    stream: parser_stream(lexer_start()), nextNodeId: 0, done: false,
    functionActive: false, functionName: "", functionStartByte: 0,
    functionLine: 1, functionColumn: 1,
    functionRootId: 0, functionChildIndex: 0, topLevelChildIndex: 0, frames: []
  }
}

fn parser_emit_item(cursor: ParserCursor, parsed: AstParse) -> ParserChunk {
  let nodes = flat_rebase_ids(flatten_ast(parsed.value, cursor.topLevelChildIndex), cursor.nextNodeId)
  let next = ParserCursor {
    document: cursor.document, revision: cursor.revision, stream: parsed.stream,
    nextNodeId: cursor.nextNodeId + length(nodes), done: false,
    functionActive: false, functionName: "", functionStartByte: 0,
    functionLine: 1, functionColumn: 1,
    functionRootId: 0, functionChildIndex: 0,
    topLevelChildIndex: cursor.topLevelChildIndex + 1, frames: []
  }
  return parser_chunk(next, "continuing", nodes, false, "", "", 0, 0, 0, 0)
}

fn parser_value_is_absent(value: AstValue) -> Bool {
  return match value {
    AstAbsent() => true
    _ => false
  }
}

fn parser_complete_absent(cursor: ParserCursor, parsed: AstParse) -> ParserChunk {
  let next = ParserCursor {
    document: cursor.document, revision: cursor.revision, stream: parsed.stream,
    nextNodeId: cursor.nextNodeId, done: true,
    functionActive: false, functionName: "", functionStartByte: 0,
    functionLine: 1, functionColumn: 1,
    functionRootId: 0, functionChildIndex: 0,
    topLevelChildIndex: cursor.topLevelChildIndex, frames: []
  }
  return parser_chunk(next, "complete", [], true, "", "", 0, 0, 0, 0)
}

fn parser_finish_step(cursor: ParserCursor, parsed: AstParse) -> ParserChunk {
  if !parsed.ok {
    let failed = ParserCursor {
      document: cursor.document, revision: cursor.revision, stream: parsed.stream,
      nextNodeId: cursor.nextNodeId, done: true,
      functionActive: cursor.functionActive, functionName: cursor.functionName,
      functionStartByte: cursor.functionStartByte, functionLine: cursor.functionLine,
      functionColumn: cursor.functionColumn, functionRootId: cursor.functionRootId,
      functionChildIndex: cursor.functionChildIndex,
      topLevelChildIndex: cursor.topLevelChildIndex, frames: cursor.frames
    }
    return parser_chunk(failed, parser_error_status(parsed), [], true,
      parsed.errorCode, parsed.message, parsed.errorStart, parsed.errorEnd,
      parsed.errorLine, parsed.errorColumn)
  } else { }
  if parser_value_is_absent(parsed.value) {
    return parser_complete_absent(cursor, parsed)
  } else {
    return parser_emit_item(cursor, parsed)
  }
}
fn parser_validation_chunk(cursor: ParserCursor) -> ParserChunk {
  var stream = cursor.stream
  var count = 0
  while count <= 7 && stream.lexCursor.stage == "validate" && stream.lexErrorCode == "" {
    let progress = lexer_step(stream.lexCursor)
    var errorCode = stream.lexErrorCode
    var errorStart = stream.lexErrorStart
    var errorEnd = stream.lexErrorEnd
    var errorLine = stream.lexErrorLine
    var errorColumn = stream.lexErrorColumn
    if progress.errorCode != "" {
      errorCode = progress.errorCode
      errorStart = progress.errorStart
      errorEnd = progress.errorEnd
      errorLine = progress.errorLine
      errorColumn = progress.errorColumn
    } else { }
    stream = ParserStream {
      lexCursor: progress.cursor, bufferedTokens: stream.bufferedTokens,
      lexDone: progress.done, lexErrorCode: errorCode,
      lexErrorStart: errorStart, lexErrorEnd: errorEnd,
      lexErrorLine: errorLine, lexErrorColumn: errorColumn
    }
    count = count + 1
  }
  let failed = stream.lexErrorCode != ""
  let next = ParserCursor {
    document: cursor.document, revision: cursor.revision, stream: stream,
    nextNodeId: cursor.nextNodeId, done: failed,
    functionActive: cursor.functionActive, functionName: cursor.functionName,
    functionStartByte: cursor.functionStartByte, functionLine: cursor.functionLine,
    functionColumn: cursor.functionColumn, functionRootId: cursor.functionRootId,
    functionChildIndex: cursor.functionChildIndex,
    topLevelChildIndex: cursor.topLevelChildIndex, frames: cursor.frames
  }
  if failed {
    return parser_chunk(next, "invalid", [], true, stream.lexErrorCode,
      "Invalid source encoding", stream.lexErrorStart, stream.lexErrorEnd,
      stream.lexErrorLine, stream.lexErrorColumn)
  } else {
    return parser_chunk(next, "continuing", [], false, "", "", 0, 0, 0, 0)
  }
}

fn parser_union_variant(cursor: ParserCursor, frame: ParserFrame, parsed: AstParse) -> ParserChunk {
  if !parsed.ok { return parser_finish_step(cursor, parsed) } else { }
  let variantSpan = ast_value_span(parsed.value)
  let state = flat_node(parsed.value, frame.nodeId, frame.bodyChildIndex, "variant",
    FlatState { nextId: cursor.nextNodeId, nodesReversed: [] })
  let nodes = reverse(state.nodesReversed)
  let after = stream_peek(parsed.stream, 0)
  if !after.ok { return parser_finish_step(cursor, parse_lex_error(after.stream)) } else { }
  if after.token.kind == "symbol" && after.token.text == "|" {
    let separator = stream_take(after.stream)
    let updated = ParserFrame { kind: frame.kind, nodeId: frame.nodeId,
      parentId: frame.parentId, rootChildIndex: frame.rootChildIndex,
      rootRole: frame.rootRole, startByte: frame.startByte, line: frame.line,
      column: frame.column, text: frame.text, bodyChildIndex: frame.bodyChildIndex + 1 }
    let next = ParserCursor {
      document: cursor.document, revision: cursor.revision, stream: separator.stream,
      nextNodeId: state.nextId, done: false, functionActive: false,
      functionName: "", functionStartByte: 0, functionLine: 1, functionColumn: 1,
      functionRootId: 0, functionChildIndex: 0,
      topLevelChildIndex: cursor.topLevelChildIndex, frames: [updated]
    }
    return parser_chunk(next, "continuing", nodes, false, "", "", 0, 0, 0, 0)
  } else { }
  let root = flat_make(frame.nodeId, frame.parentId, frame.rootChildIndex,
    frame.rootRole, "union_declaration", frame.text, 0, false, [],
    AstSpan { startByte: frame.startByte, endByte: variantSpan.endByte,
      line: frame.line, column: frame.column })
  let completedNodes = prepend(nodes, root)
  let next = ParserCursor {
    document: cursor.document, revision: cursor.revision, stream: after.stream,
    nextNodeId: state.nextId, done: false, functionActive: false,
    functionName: "", functionStartByte: 0, functionLine: 1, functionColumn: 1,
    functionRootId: 0, functionChildIndex: 0,
    topLevelChildIndex: cursor.topLevelChildIndex + 1, frames: []
  }
  return parser_chunk(next, "continuing", completedNodes, false, "", "", 0, 0, 0, 0)
}

fn parser_begin_union(cursor: ParserCursor, first: LexToken, name: LexToken,
  equals: ParserStream) -> ParserChunk {
  let rootId = cursor.nextNodeId
  let frame = ParserFrame { kind: "union", nodeId: rootId, parentId: -1,
    rootChildIndex: cursor.topLevelChildIndex, rootRole: "top_level",
    startByte: first.startByte, line: first.line, column: first.column,
    text: name.text, bodyChildIndex: 0 }
  let variant = parse_variant_declaration(equals, 1)
  return parser_union_variant(
    ParserCursor { document: cursor.document, revision: cursor.revision,
      stream: cursor.stream, nextNodeId: rootId + 1, done: false,
      functionActive: false, functionName: "", functionStartByte: 0,
      functionLine: 1, functionColumn: 1, functionRootId: 0,
      functionChildIndex: 0, topLevelChildIndex: cursor.topLevelChildIndex,
      frames: [frame] }, frame, variant)
}

fn parser_begin_type_union_or_fallback(cursor: ParserCursor, firstRead: TokenRead) -> ParserChunk {
  let first = stream_take(firstRead.stream)
  let name = stream_take(first.stream)
  if name.ok && name.token.kind == "identifier" {
    let equals = stream_take(name.stream)
    if equals.ok && equals.token.kind == "symbol" && equals.token.text == "=" {
      return parser_begin_union(cursor, first.token, name.token, equals.stream)
    } else { }
  } else { }
  return parser_finish_step(cursor, parse_top_level_item(cursor.stream, 0))
}

fn parser_step(cursor: ParserCursor) -> ParserChunk {
  let info = semantic_snapshot()
  if cursor.document != info.document || cursor.revision != info.revision {
    return parser_chunk(cursor, "invalid", [], true, "PEP_PARSER_CURSOR_REVISION",
      "Parser cursor belongs to a different document revision", 0, 0, 0, 0)
  } else { }
  if cursor.done { return parser_chunk(cursor, "complete", [], true, "", "", 0, 0, 0, 0) } else { }
  if cursor.stream.lexCursor.stage == "validate" {
    return parser_validation_chunk(cursor)
  } else { }
  if cursor.functionActive { return parser_step_function(cursor) } else { }
  if !(length(cursor.frames) <= 0) {
    let frame = parser_frame_top(cursor.frames)
    if frame.kind == "union" {
      return parser_union_variant(cursor, frame, parse_variant_declaration(cursor.stream, 1))
    } else { }
  } else { }
  let next = stream_peek(cursor.stream, 0)
  if !next.ok { return parser_finish_step(cursor, parse_lex_error(next.stream)) } else { }
  if next.token.kind == "eof" { return parser_finish_step(cursor, parse_ok(AstAbsent(), next.stream)) } else { }
  if next.token.kind == "identifier" && next.token.text == "fn" {
    let keyword = stream_take(next.stream)
    let header = parse_function_header_after(keyword.token, keyword.stream, 1)
    if !header.ok { return parser_finish_step(cursor, header) } else { }
    return parser_begin_function(cursor, header)
  } else { }
  if next.token.kind == "identifier" && next.token.text == "type" {
    return parser_begin_type_union_or_fallback(cursor, next)
  } else { }
  let parsed = parse_top_level_item(cursor.stream, 0)
  return parser_finish_step(cursor, parsed)
}

fn parser_begin_function(cursor: ParserCursor, header: AstParse) -> ParserChunk {
  let opening = expect_symbol(header.stream, "{")
  if !opening.ok {
    if opening.stream.lexErrorCode != "" { return parser_finish_step(cursor, parse_lex_error(opening.stream)) } else { }
    return parser_finish_step(cursor, parse_error("PEP_PARSE_EXPECTED", "Expected '{'", opening.token, opening.stream))
  } else { }
  return match header.value {
    AstFunction(name, typeParameters, parameters, resultType, body, span) => parser_function_header_chunk(
      cursor, opening.stream, name, typeParameters, parameters, resultType, span)
    _ => parser_finish_step(cursor, parse_error("PEP_PARSER_INTERNAL", "Function header did not produce a function",
      opening.token, opening.stream))
  }
}

fn parser_function_header_chunk(cursor: ParserCursor, stream: ParserStream, name: Str,
  typeParameters: List[AstValue], parameters: List[AstValue], resultType: AstValue, span: AstSpan) -> ParserChunk {
  let rootId = cursor.nextNodeId
  let start = FlatState { nextId: rootId + 1, nodesReversed: [] }
  let withTypeParameters = flat_children(typeParameters, rootId, "type_parameter", start)
  let withParameters = flat_children(parameters, rootId, "parameter", withTypeParameters)
  let withResult = flat_node(resultType, rootId, 0, "return_type", withParameters)
  let nodes = reverse(withResult.nodesReversed)
  let next = ParserCursor {
    document: cursor.document, revision: cursor.revision, stream: stream,
    nextNodeId: withResult.nextId, done: false, functionActive: true,
    functionName: name, functionStartByte: span.startByte,
    functionLine: span.line, functionColumn: span.column,
    functionRootId: rootId, functionChildIndex: 0,
    topLevelChildIndex: cursor.topLevelChildIndex, frames: cursor.frames
  }
  return parser_chunk(next, "continuing", nodes, false, "", "", 0, 0, 0, 0)
}

fn parser_empty_frame() -> ParserFrame {
  return ParserFrame { kind: "", nodeId: 0, parentId: -1, rootChildIndex: 0,
    rootRole: "", startByte: 0, line: 1, column: 1, text: "", bodyChildIndex: 0 }
}

fn parser_frame_top(frames: List[ParserFrame]) -> ParserFrame {
  var selected = parser_empty_frame()
  var found = false
  for frame in frames {
    if !found { selected = frame; found = true } else { }
  }
  return selected
}

fn parser_frame_pop(frames: List[ParserFrame]) -> List[ParserFrame] {
  var reversed: List[ParserFrame] = []
  var skipped = false
  for frame in frames {
    if !skipped { skipped = true } else { reversed = prepend(reversed, frame) }
  }
  return reverse(reversed)
}

fn parser_frame_replace_top(frames: List[ParserFrame], frame: ParserFrame) -> List[ParserFrame] {
  return prepend(parser_frame_pop(frames), frame)
}

fn parser_current_context(cursor: ParserCursor) -> ParserContext {
  if length(cursor.frames) == 0 {
    return ParserContext { parentId: cursor.functionRootId,
      childIndex: cursor.functionChildIndex, role: "statement" }
  } else { }
  let frame = parser_frame_top(cursor.frames)
  let role = if frame.kind == "if_then" { "then" } else {
    if frame.kind == "if_else" { "else" } else {
      if frame.kind == "block" { "statement" } else { "body" }
    }
  }
  return ParserContext { parentId: frame.nodeId, childIndex: frame.bodyChildIndex, role: role }
}

fn parser_consume_parent_slot(cursor: ParserCursor) -> ParserCursor {
  if length(cursor.frames) == 0 {
    return ParserCursor { document: cursor.document, revision: cursor.revision,
      stream: cursor.stream, nextNodeId: cursor.nextNodeId, done: cursor.done,
      functionActive: cursor.functionActive, functionName: cursor.functionName,
      functionStartByte: cursor.functionStartByte, functionLine: cursor.functionLine,
      functionColumn: cursor.functionColumn, functionRootId: cursor.functionRootId,
      functionChildIndex: cursor.functionChildIndex + 1,
      topLevelChildIndex: cursor.topLevelChildIndex, frames: cursor.frames }
  } else { }
  let top = parser_frame_top(cursor.frames)
  let updated = ParserFrame { kind: top.kind, nodeId: top.nodeId, parentId: top.parentId,
    rootChildIndex: top.rootChildIndex, rootRole: top.rootRole, startByte: top.startByte,
    line: top.line, column: top.column, text: top.text, bodyChildIndex: top.bodyChildIndex + 1 }
  return ParserCursor { document: cursor.document, revision: cursor.revision,
    stream: cursor.stream, nextNodeId: cursor.nextNodeId, done: cursor.done,
    functionActive: cursor.functionActive, functionName: cursor.functionName,
    functionStartByte: cursor.functionStartByte, functionLine: cursor.functionLine,
    functionColumn: cursor.functionColumn, functionRootId: cursor.functionRootId,
    functionChildIndex: cursor.functionChildIndex,
    topLevelChildIndex: cursor.topLevelChildIndex,
    frames: parser_frame_replace_top(cursor.frames, updated) }
}

fn parser_begin_frame(cursor: ParserCursor, stream: ParserStream, frame: ParserFrame,
  state: FlatState) -> ParserChunk {
  let parent = parser_consume_parent_slot(cursor)
  let next = ParserCursor { document: parent.document, revision: parent.revision,
    stream: stream, nextNodeId: state.nextId, done: false,
    functionActive: parent.functionActive, functionName: parent.functionName,
    functionStartByte: parent.functionStartByte, functionLine: parent.functionLine,
    functionColumn: parent.functionColumn, functionRootId: parent.functionRootId,
    functionChildIndex: parent.functionChildIndex,
    topLevelChildIndex: parent.topLevelChildIndex, frames: prepend(parent.frames, frame) }
  return parser_chunk(next, "continuing", reverse(state.nodesReversed), false, "", "", 0, 0, 0, 0)
}

fn parser_emit_frame(cursor: ParserCursor, frame: ParserFrame, stream: ParserStream,
  endByte: Int) -> ParserChunk {
  let kind = if frame.kind == "while" { "while" } else {
    if frame.kind == "for_in" { "for_in" } else {
      if frame.kind == "block" { "block" } else { "if_statement" }
    }
  }
  let root = FlatAstNode { id: frame.nodeId, parentId: frame.parentId,
    childIndex: frame.rootChildIndex, role: frame.rootRole, kind: kind, text: frame.text,
    integerValue: 0, booleanValue: false, stringParts: [], startByte: frame.startByte,
    endByte: endByte, line: frame.line, column: frame.column }
  let next = ParserCursor { document: cursor.document, revision: cursor.revision,
    stream: stream, nextNodeId: cursor.nextNodeId, done: false,
    functionActive: cursor.functionActive, functionName: cursor.functionName,
    functionStartByte: cursor.functionStartByte, functionLine: cursor.functionLine,
    functionColumn: cursor.functionColumn, functionRootId: cursor.functionRootId,
    functionChildIndex: cursor.functionChildIndex,
    topLevelChildIndex: cursor.topLevelChildIndex, frames: parser_frame_pop(cursor.frames) }
  return parser_chunk(next, "continuing", [root], false, "", "", 0, 0, 0, 0)
}

fn parser_close_frame(cursor: ParserCursor, frame: ParserFrame, close: TokenRead) -> ParserChunk {
  if frame.kind == "if_then" {
    let after = stream_peek(close.stream, 0)
    if !after.ok { return parser_finish_step(cursor, parse_lex_error(after.stream)) } else { }
    if after.token.kind == "identifier" && after.token.text == "else" {
      let opening = expect_symbol(stream_take(after.stream).stream, "{")
      if !opening.ok {
        if opening.stream.lexErrorCode != "" { return parser_finish_step(cursor, parse_lex_error(opening.stream)) } else { }
        return parser_finish_step(cursor, parse_error("PEP_PARSE_EXPECTED", "Expected '{'", opening.token, opening.stream))
      } else { }
      let updated = ParserFrame { kind: "if_else", nodeId: frame.nodeId,
        parentId: frame.parentId, rootChildIndex: frame.rootChildIndex,
        rootRole: frame.rootRole, startByte: frame.startByte, line: frame.line,
        column: frame.column, text: frame.text, bodyChildIndex: 0 }
      let next = ParserCursor { document: cursor.document, revision: cursor.revision,
        stream: opening.stream, nextNodeId: cursor.nextNodeId, done: false,
        functionActive: cursor.functionActive, functionName: cursor.functionName,
        functionStartByte: cursor.functionStartByte, functionLine: cursor.functionLine,
        functionColumn: cursor.functionColumn, functionRootId: cursor.functionRootId,
        functionChildIndex: cursor.functionChildIndex,
        topLevelChildIndex: cursor.topLevelChildIndex,
        frames: parser_frame_replace_top(cursor.frames, updated) }
      return parser_chunk(next, "continuing", [], false, "", "", 0, 0, 0, 0)
    } else {
      return parser_finish_step(cursor, parse_error("PEP_PARSE_ELSE", "Expected else after if block", after.token, after.stream))
    }
  } else { }
  return parser_emit_frame(cursor, frame, close.stream, close.token.endByte)
}

fn parser_start_control(cursor: ParserCursor, keyword: LexToken) -> ParserChunk {
  let context = parser_current_context(cursor)
  let rootId = cursor.nextNodeId
  if keyword.text == "{" {
    let opened = stream_take(cursor.stream)
    let frame = ParserFrame { kind: "block", nodeId: rootId, parentId: context.parentId,
      rootChildIndex: context.childIndex, rootRole: context.role, startByte: keyword.startByte,
      line: keyword.line, column: keyword.column, text: "", bodyChildIndex: 0 }
    return parser_begin_frame(cursor, opened.stream, frame,
      FlatState { nextId: rootId + 1, nodesReversed: [] })
  } else { }
  let consumed = stream_take(cursor.stream)
  if keyword.text == "if" || keyword.text == "while" {
    let condition = parse_expression(consumed.stream, 0, false, 1)
    if !condition.ok { return parser_finish_step(cursor, condition) } else { }
    let opening = expect_symbol(condition.stream, "{")
    if !opening.ok {
      if opening.stream.lexErrorCode != "" { return parser_finish_step(cursor, parse_lex_error(opening.stream)) } else { }
      return parser_finish_step(cursor, parse_error("PEP_PARSE_EXPECTED", "Expected '{'", opening.token, opening.stream))
    } else { }
    let kind = if keyword.text == "if" { "if_then" } else { "while" }
    let frame = ParserFrame { kind: kind, nodeId: rootId, parentId: context.parentId,
      rootChildIndex: context.childIndex, rootRole: context.role, startByte: keyword.startByte,
      line: keyword.line, column: keyword.column, text: "", bodyChildIndex: 0 }
    let state = flat_node(condition.value, rootId, 0, "condition",
      FlatState { nextId: rootId + 1, nodesReversed: [] })
    return parser_begin_frame(cursor, opening.stream, frame, state)
  } else { }
  if keyword.text == "for" {
    let name = stream_take(consumed.stream)
    if !name.ok { return parser_finish_step(cursor, parse_lex_error(name.stream)) } else { }
    if name.token.kind != "identifier" {
      return parser_finish_step(cursor, parse_error("PEP_PARSE_NAME", "Expected a loop variable", name.token, name.stream))
    } else { }
    let inToken = stream_peek(name.stream, 0)
    if !inToken.ok { return parser_finish_step(cursor, parse_lex_error(inToken.stream)) } else { }
    if inToken.token.kind != "identifier" || inToken.token.text != "in" {
      return parser_finish_step(cursor, parse_error("PEP_PARSE_FOR_IN", "Expected 'in' after the loop variable", inToken.token, inToken.stream))
    } else { }
    let iterable = parse_expression(stream_take(inToken.stream).stream, 0, false, 1)
    if !iterable.ok { return parser_finish_step(cursor, iterable) } else { }
    let opening = expect_symbol(iterable.stream, "{")
    if !opening.ok {
      if opening.stream.lexErrorCode != "" { return parser_finish_step(cursor, parse_lex_error(opening.stream)) } else { }
      return parser_finish_step(cursor, parse_error("PEP_PARSE_EXPECTED", "Expected '{'", opening.token, opening.stream))
    } else { }
    let frame = ParserFrame { kind: "for_in", nodeId: rootId, parentId: context.parentId,
      rootChildIndex: context.childIndex, rootRole: context.role, startByte: keyword.startByte,
      line: keyword.line, column: keyword.column, text: name.token.text, bodyChildIndex: 0 }
    let state = flat_node(iterable.value, rootId, 0, "iterable",
      FlatState { nextId: rootId + 1, nodesReversed: [] })
    return parser_begin_frame(cursor, opening.stream, frame, state)
  } else { }
  return parser_finish_step(cursor, parse_error("PEP_PARSER_INTERNAL", "Unknown control statement", keyword, consumed.stream))
}

fn parser_step_function(cursor: ParserCursor) -> ParserChunk {
  let next = stream_peek(cursor.stream, 0)
  if !next.ok { return parser_finish_step(cursor, parse_lex_error(next.stream)) } else { }
  if !(length(cursor.frames) <= 0) {
    let frame = parser_frame_top(cursor.frames)
    if next.token.kind == "symbol" && next.token.text == "}" {
      return parser_close_frame(cursor, frame, stream_take(next.stream))
    } else { }
  } else { }
  if length(cursor.frames) == 0 && next.token.kind == "symbol" && next.token.text == "}" {
    let close = stream_take(next.stream)
    let root = FlatAstNode {
      id: cursor.functionRootId, parentId: -1, childIndex: cursor.topLevelChildIndex, role: "top_level",
      kind: "function", text: cursor.functionName, integerValue: 0,
      booleanValue: false, stringParts: [], startByte: cursor.functionStartByte,
      endByte: close.token.endByte, line: cursor.functionLine, column: cursor.functionColumn
    }
    let doneCursor = ParserCursor {
      document: cursor.document, revision: cursor.revision, stream: close.stream,
      nextNodeId: cursor.nextNodeId, done: false, functionActive: false,
      functionName: "", functionStartByte: 0, functionLine: 1, functionColumn: 1,
      functionRootId: 0, functionChildIndex: 0,
      topLevelChildIndex: cursor.topLevelChildIndex + 1, frames: []
    }
    return parser_chunk(doneCursor, "continuing", [root], false, "", "", 0, 0, 0, 0)
  } else { }
  if next.token.kind == "eof" {
    return parser_finish_step(cursor, parse_error("PEP_PARSE_EXPECTED", "Expected '}'", next.token, next.stream))
  } else { }
  if next.token.kind == "identifier" &&
     (next.token.text == "if" || next.token.text == "while" || next.token.text == "for") {
    return parser_start_control(cursor, next.token)
  } else { }
  if next.token.kind == "symbol" && next.token.text == "{" {
    return parser_start_control(cursor, next.token)
  } else { }
  let parsed = parse_statement(next.stream, 1)
  if !parsed.ok { return parser_finish_step(cursor, parsed) } else { }
  if parsed.stream.lexCursor.offset == cursor.stream.lexCursor.offset &&
     length(parsed.stream.bufferedTokens) == length(cursor.stream.bufferedTokens) {
    let stuck = stream_peek(parsed.stream, 0)
    return parser_finish_step(cursor, parse_error("PEP_PARSE_NO_PROGRESS", "Parser made no progress", stuck.token, stuck.stream))
  } else { }
  let context = parser_current_context(cursor)
  let state = flat_node(parsed.value, context.parentId, context.childIndex,
    context.role, FlatState { nextId: cursor.nextNodeId, nodesReversed: [] })
  let nodes = reverse(state.nodesReversed)
  let consumed = parser_consume_parent_slot(cursor)
  let nextCursor = ParserCursor {
    document: consumed.document, revision: consumed.revision, stream: parsed.stream,
    nextNodeId: state.nextId, done: false, functionActive: consumed.functionActive,
    functionName: consumed.functionName, functionStartByte: consumed.functionStartByte,
    functionLine: consumed.functionLine, functionColumn: consumed.functionColumn,
    functionRootId: consumed.functionRootId, functionChildIndex: consumed.functionChildIndex,
    topLevelChildIndex: consumed.topLevelChildIndex, frames: consumed.frames
  }
  return parser_chunk(nextCursor, "continuing", nodes, false, "", "", 0, 0, 0, 0)
}

fn parse_program(stream: ParserStream, depth: Int) -> AstParse {
  var current = stream
  var reversed: List[AstValue] = []
  var firstSpan = AstSpan { startByte: 0, endByte: 0, line: 1, column: 1 }
  var lastSpan = firstSpan
  var hasItems = false
  var finished = false
  while !finished {
    let next = stream_peek(current, 0)
    current = next.stream
    if !next.ok { return parse_lex_error(current) } else { }
    if next.token.kind == "eof" { finished = true } else {
      let beforeOffset = current.lexCursor.offset
      let beforeCount = length(current.bufferedTokens)
      var item: AstParse = parse_ok(AstAbsent(), current)
      if next.token.kind == "identifier" && next.token.text == "fn" {
        let keyword = stream_take(current)
        item = parse_function_after(keyword.token, keyword.stream, depth + 1)
      } else { if next.token.kind == "identifier" && next.token.text == "type" {
        let keyword = stream_take(current)
        item = parse_type_declaration_after(keyword.token, keyword.stream, depth + 1)
      } else { item = parse_statement(current, depth + 1) } }
      if !item.ok { return item } else { }
      let itemSpan = ast_value_span(item.value)
      if !hasItems { firstSpan = itemSpan; hasItems = true } else { }
      lastSpan = itemSpan
      reversed = prepend(reversed, item.value)
      current = item.stream
      if current.lexCursor.offset == beforeOffset && length(current.bufferedTokens) == beforeCount {
        let stuck = stream_peek(current, 0)
        return parse_error("PEP_PARSE_NO_PROGRESS", "Parser made no progress", stuck.token, stuck.stream)
      } else { }
    }
  }
  let items = reverse(reversed)
  let programSpan = if hasItems { ast_combine(firstSpan, lastSpan) } else { firstSpan }
  return parse_ok(AstBlock(items, programSpan), current)
}

fn flatten_top_level(items: List[AstValue]) -> List[FlatAstNode] {
  let state = flat_children(items, -1, "top_level", FlatState { nextId: 0, nodesReversed: [] })
  return reverse(state.nodesReversed)
}

fn parser_error_status(error: AstParse) -> Str {
  let raw = source_bytes()
  if error.errorStart == byte_length(raw) && error.errorCode != "" {
    return "incomplete"
  } else { return "invalid" }
}

fn parser_parse_program() -> ParserProgress {
  let lex = lexer_start()
  let parsed = parse_program(parser_stream(lex), 0)
  if !parsed.ok {
    return parser_progress(parser_error_status(parsed), [], true, parsed.errorCode, parsed.message,
      parsed.errorStart, parsed.errorEnd, parsed.errorLine, parsed.errorColumn)
  } else { }
  return match parsed.value {
    AstBlock(items, span) => parser_progress("complete", flatten_top_level(items), true, "", "", 0, 0, 0, 0)
    _ => parser_progress("invalid", [], true, "PEP_PARSER_INTERNAL", "Parser did not produce a program root", 0, 0, 0, 0)
  }
}
fn parser_parse_expression() -> ParserProgress {
  let lex = lexer_start()
  let parsed = parse_expression(parser_stream(lex), 0, true, 0)
  if !parsed.ok {
    return parser_progress(parser_error_status(parsed), [], true, parsed.errorCode, parsed.message,
      parsed.errorStart, parsed.errorEnd, parsed.errorLine, parsed.errorColumn)
  } else { }
  let trailing = stream_peek(parsed.stream, 0)
  if !trailing.ok { return parser_progress("invalid", [], true,
    parsed.stream.lexErrorCode, "Invalid source encoding",
    parsed.stream.lexErrorStart, parsed.stream.lexErrorEnd,
    parsed.stream.lexErrorLine, parsed.stream.lexErrorColumn) } else { }
  if trailing.token.kind != "eof" {
    return parser_progress("invalid", [], true, "PEP_REPLACEMENT_TRAILING_INPUT",
      "Replacement must contain exactly one expression", trailing.token.startByte,
      trailing.token.endByte, trailing.token.line, trailing.token.column)
  } else { }
  return parser_progress("complete", flatten_ast(parsed.value, 0), true, "", "", 0, 0, 0, 0)
}
