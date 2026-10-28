type PepTypeShape { kind: Str, name: Str, listDepth: Int }
type CheckedFunction { semanticId: Int, syntaxId: Int, name: Str, arity: Int, returnType: Str, returnShape: PepTypeShape, startByte: Int, endByte: Int }
type ResolvedCall { callerId: Int, calleeId: Int, syntaxId: Int, startByte: Int, endByte: Int }
type CheckDiagnostic { code: Str, message: Str, syntaxId: Int, startByte: Int, endByte: Int }
type BindingFact { semanticId: Int, syntaxId: Int, name: Str, ownerFunctionId: Int, scopeId: Int, visibleFrom: Int, mutable: Bool, typeName: Str, typeShape: PepTypeShape }
type ResolvedName { syntaxId: Int, bindingId: Int, name: Str, startByte: Int, endByte: Int }
type ExpressionTypeFact { syntaxId: Int, typeName: Str, typeShape: PepTypeShape, startByte: Int, endByte: Int }
type HoleFact { semanticId: Int, syntaxId: Int, name: Str, expectedType: Str, scopeId: Int, visibleBindingIds: List[Int], candidateBindingIds: List[Int], startByte: Int, endByte: Int }
type BindingCollection { bindings: List[BindingFact], diagnostics: List[CheckDiagnostic] }
type NameResolution { references: List[ResolvedName], diagnostics: List[CheckDiagnostic] }
type TypeAnalysis { expressionTypes: List[ExpressionTypeFact], diagnostics: List[CheckDiagnostic], unreachable: UnreachableLookup }
type CheckerReport { document: Str, revision: Str, status: Str, syntaxNodeCount: Int, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName], calls: List[ResolvedCall], expressionTypes: List[ExpressionTypeFact], holes: List[HoleFact], diagnostics: List[CheckDiagnostic] }
type NodeLookup { found: Bool, node: FlatAstNode }
type UnreachableLookup { found: Bool, node: FlatAstNode }
type ChildRoleCount { role: Str, count: Int }
type ValidationFrame { nodeId: Int, node: FlatAstNode, roleCounts: List[ChildRoleCount] }
type ValidationParent { found: Bool, frames: List[ValidationFrame], parent: ValidationFrame }
type FunctionLookup { found: Bool, function: CheckedFunction }
type BindingLookup { found: Bool, binding: BindingFact }
type ReferenceLookup { found: Bool, reference: ResolvedName }
type PatternKeyNestedPart { position: Int, kind: Str, constructor: Str, payloadArity: Int }
type PatternKeyPart { position: Int, kind: Str, constructor: Str, payloadArity: Int, nestedParts: List[PatternKeyNestedPart] }
type ConstructorPatternKey { name: Str, syntaxId: Int, argumentCount: Int, argumentPatterns: List[PatternKeyPart] }
type PatternValidation { valid: Bool, covers: Bool, code: Str, node: FlatAstNode }


fn empty_type_shape() -> PepTypeShape {
  return PepTypeShape { kind: "", name: "", listDepth: 0 }
}
fn known_type_shape(nodes: List[FlatAstNode], typeName: Str) -> PepTypeShape {
  if typeName == "Int" || typeName == "Bool" || typeName == "Str" || typeName == "Unit" || typeName == "SourceBytes" {
    return PepTypeShape { kind: "builtin", name: typeName, listDepth: 0 }
  } else {}
  if record_declaration(nodes, typeName).found || union_declaration(nodes, typeName).found {
    return PepTypeShape { kind: "nominal", name: typeName, listDepth: 0 }
  } else {}
  return empty_type_shape()
}
fn same_type_shape(left: PepTypeShape, right: PepTypeShape) -> Bool {
  return left.kind != "" && right.kind != "" && left.kind == right.kind && left.name == right.name && left.listDepth == right.listDepth
}
fn with_one_more_list(shape: PepTypeShape) -> PepTypeShape {
  if shape.kind == "" { return empty_type_shape() } else {}
  return PepTypeShape { kind: shape.kind, name: shape.name, listDepth: shape.listDepth + 1 }
}
fn legacy_type_shape(nodes: List[FlatAstNode], typeName: Str) -> PepTypeShape {
  let element = list_element_type(typeName)
  if element != "" { return with_one_more_list(legacy_type_shape(nodes, element)) } else {}
  return known_type_shape(nodes, typeName)
}
fn type_shape_at(nodes: List[FlatAstNode], id: Int) -> PepTypeShape {
  var active = false
  var nextId = id
  var depth = 0
  for node in nodes {
    if !active && node.id == id { active = true } else {}
    if active && node.id == nextId {
      if node.kind == "type_list" { depth = depth + 1; nextId = node.id + 1 } else {}
      if node.kind == "type_scalar" { return PepTypeShape { kind: "builtin", name: node.text, listDepth: depth } } else {}
      if node.kind == "type_named" { return PepTypeShape { kind: "nominal", name: node.text, listDepth: depth } } else {}
      if node.kind != "type_list" { return empty_type_shape() } else {}
    } else {}
  }
  return empty_type_shape()
}
fn empty_node() -> FlatAstNode {
  return FlatAstNode { id: -1, parentId: -1, childIndex: -1, role: "", kind: "", text: "", integerValue: 0, booleanValue: false, stringParts: [], startByte: 0, endByte: 0, line: 1, column: 1 }
}
fn lookup_node(nodes: List[FlatAstNode], id: Int) -> NodeLookup {
  for node in nodes { if node.id == id { return NodeLookup { found: true, node: node } } else {} }
  return NodeLookup { found: false, node: empty_node() }
}
fn count_children(nodes: List[FlatAstNode], parent: Int, role: Str) -> Int {
  var count = 0
  for node in nodes { if node.parentId == parent && node.role == role { count = count + 1 } else {} }
  return count
}
fn child_at(nodes: List[FlatAstNode], parent: Int, role: Str, index: Int) -> NodeLookup {
  for node in nodes {
    if node.parentId == parent && node.role == role && node.childIndex == index {
      return NodeLookup { found: true, node: node }
    } else {}
  }
  return NodeLookup { found: false, node: empty_node() }
}
fn type_name_at(nodes: List[FlatAstNode], id: Int) -> Str {
  return legacy_type_name(type_shape_at(nodes, id))
}
fn insert_sorted(nodes: List[FlatAstNode], item: FlatAstNode) -> List[FlatAstNode] {
  var reversed: List[FlatAstNode] = []
  var inserted = false
  for node in nodes {
    if !inserted && item.id + 1 <= node.id { reversed = prepend(reversed, item); inserted = true } else {}
    reversed = prepend(reversed, node)
  }
  if !inserted { reversed = prepend(reversed, item) } else {}
  return reverse(reversed)
}
fn quick_sort_nodes(nodes: List[FlatAstNode]) -> List[FlatAstNode] {
  if length(nodes) <= 1 { return nodes } else {}
  let pivotIndex = length(nodes) / 2
  var position = 0
  var pivot = empty_node()
  for node in nodes {
    if position == pivotIndex { pivot = node } else {}
    position = position + 1
  }
  var less: List[FlatAstNode] = []
  var greater: List[FlatAstNode] = []
  for node in nodes {
    if node.id + 1 <= pivot.id { less = prepend(less, node) } else {}
    if pivot.id + 1 <= node.id { greater = prepend(greater, node) } else {}
  }
  let sortedLess = quick_sort_nodes(less)
  let sortedGreater = quick_sort_nodes(greater)
  var reversed: List[FlatAstNode] = []
  for node in sortedLess { reversed = prepend(reversed, node) }
  reversed = prepend(reversed, pivot)
  for node in sortedGreater { reversed = prepend(reversed, node) }
  return reverse(reversed)
}
fn sort_nodes(nodes: List[FlatAstNode]) -> List[FlatAstNode] {
  var ascending = true
  var descending = true
  var previousId = -1
  for node in nodes {
    if previousId != -1 {
      if node.id <= previousId { ascending = false } else {}
      if node.id + 1 != previousId { descending = false } else {}
    } else {}
    previousId = node.id
  }
  if ascending { return nodes } else {}
  if descending { return reverse(nodes) } else {}
  return quick_sort_nodes(nodes)
}
fn known_builtin(name: Str) -> Bool {
  return name == "say" || name == "int_text" || name == "length" || name == "append" || name == "prepend" || name == "reverse" || name == "source_bytes" || name == "byte_length" || name == "byte_at" || name == "byte_slice" || name == "utf8_slice" || name == "contains"
}
fn is_constructor(nodes: List[FlatAstNode], name: Str) -> Bool {
  for node in nodes { if node.kind == "variant_declaration" && node.text == name { return true } else {} }
  return false
}
fn record_declaration(nodes: List[FlatAstNode], name: Str) -> NodeLookup {
  for node in nodes { if node.parentId == -1 && node.kind == "record_declaration" && node.text == name { return NodeLookup { found: true, node: node } } else {} }
  return NodeLookup { found: false, node: empty_node() }
}
fn diagnostic_order_byte(nodes: List[FlatAstNode], candidate: CheckDiagnostic) -> Int {
  if candidate.code != "PEP_MISSING_FIELD" { return candidate.startByte } else {}
  let missingField = lookup_node(nodes, candidate.syntaxId)
  if !missingField.found || missingField.node.kind != "field_declaration" { return candidate.startByte } else {}
  let declaration = lookup_node(nodes, missingField.node.parentId)
  if !declaration.found || declaration.node.kind != "record_declaration" { return candidate.startByte } else {}
  var found = false
  var firstRecordByte = 0
  for record in nodes {
    if record.kind == "record" && record.text == declaration.node.text {
      var supplied = false
      for field in nodes {
        if field.parentId == record.id && field.kind == "record_field" && field.text == missingField.node.text {
          supplied = true
        } else {}
      }
      if !supplied && (!found || record.startByte + 1 <= firstRecordByte) {
        found = true
        firstRecordByte = record.startByte
      } else {}
    } else {}
  }
  if found { return firstRecordByte } else { return candidate.startByte }
}
fn union_declaration(nodes: List[FlatAstNode], name: Str) -> NodeLookup {
  for node in nodes { if node.parentId == -1 && node.kind == "union_declaration" && node.text == name { return NodeLookup { found: true, node: node } } else {} }
  return NodeLookup { found: false, node: empty_node() }
}
fn variant_declaration(nodes: List[FlatAstNode], name: Str) -> NodeLookup {
  for node in nodes { if node.kind == "variant_declaration" && node.text == name { return NodeLookup { found: true, node: node } } else {} }
  return NodeLookup { found: false, node: empty_node() }
}
fn constructor_union_type(nodes: List[FlatAstNode], name: Str) -> Str {
  let variant = variant_declaration(nodes, name)
  if variant.found {
    let owner = lookup_node(nodes, variant.node.parentId)
    if owner.found { return owner.node.text } else { return "" }
  } else { return "" }
}
fn variant_payload_type(nodes: List[FlatAstNode], variantName: Str, index: Int) -> Str {
  let variant = variant_declaration(nodes, variantName)
  if !variant.found { return "" } else {}
  let payload = child_at(nodes, variant.node.id, "field_type", index)
  if payload.found { return type_name_at(nodes, payload.node.id) } else { return "" }
}
fn variant_payload_shape(nodes: List[FlatAstNode], variantName: Str, index: Int) -> PepTypeShape {
  let variant = variant_declaration(nodes, variantName)
  if !variant.found { return empty_type_shape() } else {}
  let payload = child_at(nodes, variant.node.id, "field_type", index)
  if payload.found { return type_shape_at(nodes, payload.node.id) } else { return empty_type_shape() }
}
fn record_field_type(nodes: List[FlatAstNode], recordName: Str, fieldName: Str) -> Str {
  let record = record_declaration(nodes, recordName)
  if !record.found { return "" } else {}
  for field in nodes {
    if field.parentId == record.node.id && field.kind == "field_declaration" && field.text == fieldName {
      let fieldType = child_at(nodes, field.id, "type", 0)
      if fieldType.found { return type_name_at(nodes, fieldType.node.id) } else { return "" }
    } else {}
  }
  return ""
}
fn record_field_shape(nodes: List[FlatAstNode], recordName: Str, fieldName: Str) -> PepTypeShape {
  let record = record_declaration(nodes, recordName)
  if !record.found { return empty_type_shape() } else {}
  for field in nodes {
    if field.parentId == record.node.id && field.kind == "field_declaration" && field.text == fieldName {
      let fieldType = child_at(nodes, field.id, "type", 0)
      if fieldType.found { return type_shape_at(nodes, fieldType.node.id) } else { return empty_type_shape() }
    } else {}
  }
  return empty_type_shape()
}
fn find_function_by_syntax(functions: List[CheckedFunction], syntaxId: Int) -> FunctionLookup {
  for function in functions { if function.syntaxId == syntaxId { return FunctionLookup { found: true, function: function } } else {} }
  return FunctionLookup { found: false, function: CheckedFunction { semanticId: -1, syntaxId: -1, name: "", arity: 0, returnType: "", returnShape: empty_type_shape(), startByte: 0, endByte: 0 } }
}
fn find_function(functions: List[CheckedFunction], name: Str) -> FunctionLookup {
  for function in functions { if function.name == name { return FunctionLookup { found: true, function: function } } else {} }
  return FunctionLookup { found: false, function: CheckedFunction { semanticId: -1, syntaxId: -1, name: "", arity: 0, returnType: "", returnShape: empty_type_shape(), startByte: 0, endByte: 0 } }
}
fn find_binding(bindings: List[BindingFact], semanticId: Int) -> BindingLookup {
  for binding in bindings { if binding.semanticId == semanticId { return BindingLookup { found: true, binding: binding } } else {} }
  return BindingLookup { found: false, binding: BindingFact { semanticId: -1, syntaxId: -1, name: "", ownerFunctionId: -1, scopeId: -1, visibleFrom: 0, mutable: false, typeName: "", typeShape: empty_type_shape() } }
}
fn find_reference(references: List[ResolvedName], syntaxId: Int) -> ReferenceLookup {
  for reference in references { if reference.syntaxId == syntaxId { return ReferenceLookup { found: true, reference: reference } } else {} }
  return ReferenceLookup { found: false, reference: ResolvedName { syntaxId: -1, bindingId: -1, name: "", startByte: 0, endByte: 0 } }
}
fn inside_function(node: FlatAstNode, function: CheckedFunction) -> Bool {
  return node.id != function.syntaxId && function.startByte <= node.startByte && node.endByte <= function.endByte
}
fn fixed_child_index(parentKind: Str, role: Str) -> Int {
  if parentKind == "binary" { if role == "left" { return 0 } else { if role == "right" { return 1 } else { return -1 } } } else {}
  if parentKind == "unary" && role == "operand" { return 0 } else {}
  if parentKind == "if_expression" { if role == "condition" { return 0 } else { if role == "then" { return 1 } else { if role == "else" { return 2 } else { return -1 } } } } else {}
  if parentKind == "match" && role == "value" { return 0 } else {}
  if parentKind == "match_arm" { if role == "pattern" { return 0 } else { if role == "result" { return 1 } else { return -1 } } } else {}
  if parentKind == "record_field" && role == "value" { return 0 } else {}
  if parentKind == "type_list" && role == "element_type" { return 0 } else {}
  if parentKind == "parameter" && role == "type" { return 0 } else {}
  if parentKind == "field_declaration" && role == "type" { return 0 } else {}
  if parentKind == "function" && role == "return_type" { return 0 } else {}
  if parentKind == "let" || parentKind == "var" { if role == "annotation" || role == "value" { return 0 } else {} } else {}
  if parentKind == "assignment" && role == "value" { return 0 } else {}
  if parentKind == "return" && role == "value" { return 0 } else {}
  if parentKind == "expression_statement" && role == "value" { return 0 } else {}
  if parentKind == "for_in" && role == "iterable" { return 0 } else {}
  if parentKind == "while" && role == "condition" { return 0 } else {}
  return -1
}
fn role_child_count(counts: List[ChildRoleCount], role: Str) -> Int {
  for item in counts { if item.role == role { return item.count } else {} }
  return 0
}
fn increment_role_count(counts: List[ChildRoleCount], role: Str) -> List[ChildRoleCount] {
  var reversed: List[ChildRoleCount] = []
  var found = false
  for item in counts {
    if item.role == role {
      reversed = prepend(reversed, ChildRoleCount { role: role, count: item.count + 1 })
      found = true
    } else { reversed = prepend(reversed, item) }
  }
  if !found { reversed = prepend(reversed, ChildRoleCount { role: role, count: 1 }) } else {}
  return reverse(reversed)
}
fn validation_parent(stack: List[ValidationFrame], parentId: Int) -> ValidationParent {
  var reversed: List[ValidationFrame] = []
  var found = false
  var parent = ValidationFrame { nodeId: -1, node: empty_node(), roleCounts: [] }
  for frame in stack {
    if !found {
      if frame.nodeId == parentId {
        found = true
        parent = frame
        reversed = prepend(reversed, frame)
      } else {}
    } else { reversed = prepend(reversed, frame) }
  }
  return ValidationParent { found: found, frames: reverse(reversed), parent: parent }
}
fn replace_validation_top(stack: List[ValidationFrame], replacement: ValidationFrame) -> List[ValidationFrame] {
  var reversed: List[ValidationFrame] = []
  var replaced = false
  for frame in stack {
    if !replaced { reversed = prepend(reversed, replacement); replaced = true } else { reversed = prepend(reversed, frame) }
  }
  return reverse(reversed)
}
fn tree_is_valid(nodes: List[FlatAstNode], sourceLength: Int) -> Bool {
  var expectedId = 0
  var nextRoot = 0
  var valid = true
  var validationStack: List[ValidationFrame] = []
  for node in nodes {
    if node.id != expectedId || node.startByte <= -1 || node.endByte <= node.startByte && node.endByte != node.startByte || sourceLength <= node.endByte && node.endByte != sourceLength || node.line <= 0 || node.column <= 0 { valid = false } else {}
    let frame = ValidationFrame { nodeId: node.id, node: node, roleCounts: [] }
    if node.parentId == -1 {
      validationStack = []
      if node.role != "top_level" || node.childIndex != nextRoot { valid = false } else {}
      nextRoot = nextRoot + 1
      validationStack = prepend(validationStack, frame)
    } else {
      let parent = validation_parent(validationStack, node.parentId)
      if !parent.found || node.id <= node.parentId || node.childIndex <= -1 { valid = false } else {}
      if parent.found {
        let fixedIndex = fixed_child_index(parent.parent.node.kind, node.role)
        if fixedIndex != -1 {
          if node.childIndex != fixedIndex { valid = false } else {}
          validationStack = prepend(parent.frames, frame)
        } else {
          let expectedChild = role_child_count(parent.parent.roleCounts, node.role)
          if node.childIndex != expectedChild { valid = false } else {}
          let updatedParent = ValidationFrame { nodeId: parent.parent.nodeId, node: parent.parent.node, roleCounts: increment_role_count(parent.parent.roleCounts, node.role) }
          validationStack = replace_validation_top(parent.frames, updatedParent)
          validationStack = prepend(validationStack, frame)
        }
      } else { validationStack = [] }
    }
    expectedId = expectedId + 1
  }
  return valid
}
fn declared_return_type(nodes: List[FlatAstNode], functionId: Int) -> Str {
  let declared = child_at(nodes, functionId, "return_type", 0)
  if declared.found { return type_name_at(nodes, declared.node.id) } else { return "" }
}
fn declared_binding_type(nodes: List[FlatAstNode], node: FlatAstNode) -> Str {
  if node.kind == "parameter" {
    let declared = child_at(nodes, node.id, "type", 0)
    if declared.found { return type_name_at(nodes, declared.node.id) } else { return "" }
  } else {}
  let annotation = child_at(nodes, node.id, "annotation", 0)
  if annotation.found { return type_name_at(nodes, annotation.node.id) } else { return "" }
}
fn declared_return_shape(nodes: List[FlatAstNode], functionId: Int) -> PepTypeShape {
  if declared_return_type(nodes, functionId) != "" { return empty_type_shape() } else {}
  let declared = child_at(nodes, functionId, "return_type", 0)
  if declared.found { return type_shape_at(nodes, declared.node.id) } else { return empty_type_shape() }
}
fn declared_binding_shape(nodes: List[FlatAstNode], node: FlatAstNode) -> PepTypeShape {
  if declared_binding_type(nodes, node) != "" { return empty_type_shape() } else {}
  let role = if node.kind == "parameter" { "type" } else { "annotation" }
  let declared = child_at(nodes, node.id, role, 0)
  if declared.found { return type_shape_at(nodes, declared.node.id) } else { return empty_type_shape() }
}
fn collect_functions(nodes: List[FlatAstNode]) -> List[CheckedFunction] {
  var reversed: List[CheckedFunction] = []
  var ordinal = 0
  for node in nodes {
    if node.parentId == -1 && node.kind == "function" {
      let declaredResult = child_at(nodes, node.id, "return_type", 0)
      let resultShape = if declaredResult.found { type_shape_at(nodes, declaredResult.node.id) } else { empty_type_shape() }
      let resultType = if declaredResult.found { legacy_type_name(resultShape) } else { "" }
      let returnShape = if resultType != "" { empty_type_shape() } else { resultShape }
      reversed = prepend(reversed, CheckedFunction { semanticId: 100000 + ordinal, syntaxId: node.id, name: node.text, arity: count_children(nodes, node.id, "parameter"), returnType: resultType, returnShape: returnShape, startByte: node.startByte, endByte: node.endByte })
      ordinal = ordinal + 1
    } else {}
  }
  return reverse(reversed)
}
fn scope_key(node: FlatAstNode, role: Str) -> Int {
  if node.kind == "if_statement" && role == "else" { return 3000001 + node.id * 2 } else {}
  return 3000000 + node.id * 2
}
fn scope_chain(nodes: List[FlatAstNode], node: FlatAstNode, functionSyntaxId: Int, functionSemanticId: Int) -> List[Int] {
  var current = node
  var reversed: List[Int] = []
  var done = false
  var steps = 0
  while !done && steps <= length(nodes) {
    if current.parentId == functionSyntaxId { done = true } else {
      let parent = lookup_node(nodes, current.parentId)
      if !parent.found || current.parentId == -1 { done = true } else {
        if parent.node.kind == "block" && current.role == "statement" { reversed = prepend(reversed, scope_key(parent.node, current.role)) } else {}
        if parent.node.kind == "if_statement" && (current.role == "then" || current.role == "else") { reversed = prepend(reversed, scope_key(parent.node, current.role)) } else {}
        if parent.node.kind == "match_arm" && (current.role == "pattern" || current.role == "result") { reversed = prepend(reversed, scope_key(parent.node, current.role)) } else {}
        if (parent.node.kind == "for_in" || parent.node.kind == "while") && current.role == "body" { reversed = prepend(reversed, scope_key(parent.node, current.role)) } else {}
        current = parent.node
      }
    }
    steps = steps + 1
  }
  return append(reverse(reversed), functionSemanticId)
}
fn first_scope(scopes: List[Int], fallback: Int) -> Int {
  var answer = fallback
  var found = false
  for scope in scopes { if !found { answer = scope; found = true } else {} }
  return answer
}
fn pattern_binding_visible_from(nodes: List[FlatAstNode], pattern: FlatAstNode) -> Int {
  let arm = lookup_node(nodes, pattern.parentId)
  if arm.found {
    let result = child_at(nodes, arm.node.id, "result", 1)
    if result.found { return result.node.startByte } else {}
  } else {}
  let constructor = lookup_node(nodes, pattern.parentId)
  if constructor.found {
    let arm = lookup_node(nodes, constructor.node.parentId)
    if arm.found {
      let result = child_at(nodes, arm.node.id, "result", 1)
      if result.found { return result.node.startByte } else {}
    } else {}
  } else {}
  return pattern.endByte
}
fn collect_bindings(nodes: List[FlatAstNode], functions: List[CheckedFunction]) -> BindingCollection {
  var reversed: List[BindingFact] = []
  var reversedDiagnostics: List[CheckDiagnostic] = []
  var ordinal = 0
  if length(functions) != 1 {
    var activeFunctionId = -1
    var activeFunctionSyntaxId = -1
    var activeFunctionStart = 0
    var activeFunctionEnd = 0
    var nextFunctionOrdinal = 0
    for node in nodes {
      if node.parentId == -1 && node.kind == "function" {
        activeFunctionId = 100000 + nextFunctionOrdinal
        activeFunctionSyntaxId = node.id
        activeFunctionStart = node.startByte
        activeFunctionEnd = node.endByte
        nextFunctionOrdinal = nextFunctionOrdinal + 1
      } else {}
      let parameter = node.kind == "parameter" && node.parentId == activeFunctionSyntaxId
      let local = (node.kind == "let" || node.kind == "var" || node.kind == "for_in" || node.kind == "binding_pattern") && activeFunctionStart <= node.startByte && node.endByte <= activeFunctionEnd
      if activeFunctionId != -1 && (parameter || local) {
        let scopes = scope_chain(nodes, node, activeFunctionSyntaxId, activeFunctionId)
        let scope = if parameter { activeFunctionId } else { if node.kind == "for_in" { scope_key(node, "body") } else { first_scope(scopes, activeFunctionId) } }
        let visible = if parameter { node.startByte } else { if node.kind == "for_in" { node.startByte } else { if node.kind == "binding_pattern" { pattern_binding_visible_from(nodes, node) } else { node.endByte } } }
        var duplicate = false
        for prior in reversed { if prior.ownerFunctionId == activeFunctionId && prior.scopeId == scope && prior.name == node.text { duplicate = true } else {} }
        let binding = BindingFact { semanticId: 2000000 + ordinal, syntaxId: node.id, name: node.text, ownerFunctionId: activeFunctionId, scopeId: scope, visibleFrom: visible, mutable: node.kind == "var", typeName: if node.kind == "binding_pattern" { "" } else { declared_binding_type(nodes, node) }, typeShape: if node.kind == "binding_pattern" { empty_type_shape() } else { declared_binding_shape(nodes, node) } }
        if duplicate { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(if parameter { "PEP_DUPLICATE_PARAMETER" } else { "PEP_DUPLICATE_BINDING" }, "Binding name is declared more than once in this scope", node)) } else {}
        reversed = prepend(reversed, binding)
        ordinal = ordinal + 1
      } else {}
    }
    return BindingCollection { bindings: reverse(reversed), diagnostics: reverse(reversedDiagnostics) }
  } else {}
  for function in functions {
    for node in nodes {
      let parameter = node.kind == "parameter" && node.parentId == function.syntaxId
      let local = (node.kind == "let" || node.kind == "var" || node.kind == "for_in" || node.kind == "binding_pattern") && inside_function(node, function)
      if parameter || local {
        let scopes = scope_chain(nodes, node, function.syntaxId, function.semanticId)
        let scope = if parameter { function.semanticId } else { if node.kind == "for_in" { scope_key(node, "body") } else { first_scope(scopes, function.semanticId) } }
        let visible = if parameter { node.startByte } else { if node.kind == "for_in" { node.startByte } else { if node.kind == "binding_pattern" { pattern_binding_visible_from(nodes, node) } else { node.endByte } } }
        var duplicate = false
        for prior in reversed { if prior.ownerFunctionId == function.semanticId && prior.scopeId == scope && prior.name == node.text { duplicate = true } else {} }
        let binding = BindingFact { semanticId: 2000000 + ordinal, syntaxId: node.id, name: node.text, ownerFunctionId: function.semanticId, scopeId: scope, visibleFrom: visible, mutable: node.kind == "var", typeName: if node.kind == "binding_pattern" { "" } else { declared_binding_type(nodes, node) }, typeShape: if node.kind == "binding_pattern" { empty_type_shape() } else { declared_binding_shape(nodes, node) } }
        if duplicate { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(if parameter { "PEP_DUPLICATE_PARAMETER" } else { "PEP_DUPLICATE_BINDING" }, "Binding name is declared more than once in this scope", node)) } else {}
        reversed = prepend(reversed, binding)
        ordinal = ordinal + 1
      } else {}
    }
  }
  return BindingCollection { bindings: reverse(reversed), diagnostics: reverse(reversedDiagnostics) }
}
fn resolve_names(nodes: List[FlatAstNode], functions: List[CheckedFunction], bindings: List[BindingFact]) -> NameResolution {
  var reversedReferences: List[ResolvedName] = []
  var reversedDiagnostics: List[CheckDiagnostic] = []
  if length(functions) != 1 {
    var activeFunctionId = -1
    var activeFunctionSyntaxId = -1
    var activeFunctionStart = 0
    var activeFunctionEnd = 0
    var nextFunctionOrdinal = 0
    for node in nodes {
      if node.parentId == -1 && node.kind == "function" {
        activeFunctionId = 100000 + nextFunctionOrdinal
        activeFunctionSyntaxId = node.id
        activeFunctionStart = node.startByte
        activeFunctionEnd = node.endByte
        nextFunctionOrdinal = nextFunctionOrdinal + 1
      } else {}
      if (node.kind == "name" || node.kind == "assignment") && activeFunctionId != -1 && activeFunctionStart <= node.startByte && node.endByte <= activeFunctionEnd {
        let scopes = scope_chain(nodes, node, activeFunctionSyntaxId, activeFunctionId)
        var found = false
        var resolved = 0
        for scope in scopes {
          for binding in bindings {
            if !found && binding.ownerFunctionId == activeFunctionId && binding.scopeId == scope && binding.name == node.text && binding.visibleFrom <= node.startByte {
              found = true
              resolved = binding.semanticId
            } else {}
          }
        }
        if found { reversedReferences = prepend(reversedReferences, ResolvedName { syntaxId: node.id, bindingId: resolved, name: node.text, startByte: node.startByte, endByte: node.endByte }) } else {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNKNOWN_VARIABLE", "No visible variable has this name", node))
        }
      } else {}
    }
    return NameResolution { references: reverse(reversedReferences), diagnostics: reverse(reversedDiagnostics) }
  } else {}
  for function in functions {
    for node in nodes {
      if (node.kind == "name" || node.kind == "assignment") && inside_function(node, function) {
        let scopes = scope_chain(nodes, node, function.syntaxId, function.semanticId)
        var found = false
        var resolved = 0
        for scope in scopes {
          for binding in bindings {
            if !found && binding.ownerFunctionId == function.semanticId && binding.scopeId == scope && binding.name == node.text && binding.visibleFrom <= node.startByte {
              found = true
              resolved = binding.semanticId
            } else {}
          }
        }

        if found { reversedReferences = prepend(reversedReferences, ResolvedName { syntaxId: node.id, bindingId: resolved, name: node.text, startByte: node.startByte, endByte: node.endByte }) } else {
          let code = "PEP_UNKNOWN_VARIABLE"
          let message = "No visible variable has this name"
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(code, message, node))
        }
      } else {}
    }
  }
  return NameResolution { references: reverse(reversedReferences), diagnostics: reverse(reversedDiagnostics) }
}
fn owner_function(nodes: List[FlatAstNode], node: FlatAstNode, functions: List[CheckedFunction]) -> FunctionLookup {
  for function in functions { if inside_function(node, function) { return FunctionLookup { found: true, function: function } } else {} }
  return FunctionLookup { found: false, function: CheckedFunction { semanticId: -1, syntaxId: -1, name: "", arity: 0, returnType: "", returnShape: empty_type_shape(), startByte: 0, endByte: 0 } }
}
fn inside_any_function(nodes: List[FlatAstNode], node: FlatAstNode, functions: List[CheckedFunction]) -> Bool {
  return owner_function(nodes, node, functions).found
}
fn is_expression_kind(kind: Str) -> Bool {
  return kind == "integer" || kind == "boolean" || kind == "string" || kind == "name" || kind == "call" || kind == "binary" || kind == "unary" || kind == "list" || kind == "if_expression" || kind == "record" || kind == "field_access" || kind == "match" || kind == "hole"
}
fn function_parameter_type(nodes: List[FlatAstNode], functionId: Int, index: Int) -> Str {
  let parameter = child_at(nodes, functionId, "parameter", index)
  if !parameter.found { return "" } else {}
  let declared = child_at(nodes, parameter.node.id, "type", 0)
  if declared.found { return type_name_at(nodes, declared.node.id) } else { return "" }
}
fn function_parameter_shape(nodes: List[FlatAstNode], functionId: Int, index: Int) -> PepTypeShape {
  let parameter = child_at(nodes, functionId, "parameter", index)
  if !parameter.found { return empty_type_shape() } else {}
  let declared = child_at(nodes, parameter.node.id, "type", 0)
  if declared.found { return type_shape_at(nodes, declared.node.id) } else { return empty_type_shape() }
}
fn infer_expression_type(nodes: List[FlatAstNode], id: Int, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> Str {
  let found = lookup_node(nodes, id)
  if !found.found { return "" } else {}
  let node = found.node
  if node.kind == "integer" { return "Int" } else {}
  if node.kind == "boolean" { return "Bool" } else {}
  if node.kind == "string" { return "Str" } else {}
  if node.kind == "name" {
    let reference = find_reference(references, node.id)
    if !reference.found { return "" } else {}
    let binding = find_binding(bindings, reference.reference.bindingId)
    if binding.found { return binding.binding.typeName } else { return "" }
  } else {}
  if node.kind == "call" {
    let target = find_function(functions, node.text)
    if target.found { return target.function.returnType } else {}
    if node.text == "source_bytes" { return "SourceBytes" } else {}
    if node.text == "int_text" || node.text == "utf8_slice" { return "Str" } else {}
    if node.text == "say" { return "Unit" } else {}
    if node.text == "length" || node.text == "byte_length" || node.text == "byte_at" { return "Int" } else {}
    if node.text == "byte_slice" { return "SourceBytes" } else {}
    if node.text == "contains" { return "Bool" } else {}
    if node.text == "append" || node.text == "prepend" || node.text == "reverse" {
      let collection = child_at(nodes, node.id, "argument", 0)
      if collection.found { return infer_expression_type(nodes, collection.node.id, functions, bindings, references) } else { return "" }
    } else {}
    if is_constructor(nodes, node.text) { return constructor_union_type(nodes, node.text) } else {}
    return ""
  } else {}
  if node.kind == "binary" {
    if node.text == "&&" || node.text == "||" || node.text == "==" || node.text == "!=" || node.text == "<" || node.text == "<=" || node.text == ">" || node.text == ">=" { return "Bool" } else {}
    return "Int"
  } else {}
  if node.kind == "unary" { if node.text == "!" { return "Bool" } else { return "Int" } } else {}
  if node.kind == "list" {
    let expected = contextual_expected_type(nodes, node, functions, bindings, references)
    let expectedElement = list_element_type(expected)
    let parent = lookup_node(nodes, node.parentId)
    let nestedListContext = list_element_type(expectedElement) != "" ||
      (parent.found && parent.node.kind == "list" && node.role == "element") ||
      (parent.found && parent.node.kind == "call" && (parent.node.text == "append" || parent.node.text == "prepend") && node.role == "argument" && node.childIndex == 1)
    if expectedElement != "" && (nestedListContext || count_children(nodes, node.id, "element") == 0) { return expected } else {}
    for element in nodes {
      if element.parentId == node.id && element.role == "element" && element.kind != "hole" {
        let actual = infer_expression_type(nodes, element.id, functions, bindings, references)
        if actual != "" { return list_type_name(actual) } else {}
      } else {}
    }
    return ""
  } else {}
  if node.kind == "if_expression" {
    let expected = contextual_expected_type(nodes, node, functions, bindings, references)
    if expected != "" { return expected } else {}
    let thenValue = child_at(nodes, node.id, "then", 1)
    if thenValue.found {
      let thenType = infer_expression_type(nodes, thenValue.node.id, functions, bindings, references)
      if thenType != "" { return thenType } else {}
    } else {}
    let elseValue = child_at(nodes, node.id, "else", 2)
    if elseValue.found { return infer_expression_type(nodes, elseValue.node.id, functions, bindings, references) } else { return "" }
  } else {}
  if node.kind == "record" { if record_declaration(nodes, node.text).found { return node.text } else { return "" } } else {}
  if node.kind == "field_access" {
    let value = child_at(nodes, node.id, "value", 0)
    if value.found { return record_field_type(nodes, infer_expression_type(nodes, value.node.id, functions, bindings, references), node.text) } else { return "" }
  } else {}
  if node.kind == "match" {
    let expected = contextual_expected_type(nodes, node, functions, bindings, references)
    if expected != "" { return expected } else {}
    var resultType = ""
    for arm in nodes {
      if arm.parentId == node.id && arm.kind == "match_arm" {
        let result = child_at(nodes, arm.id, "result", 1)
        if resultType == "" && result.found {
          let actual = infer_expression_type(nodes, result.node.id, functions, bindings, references)
          if actual != "" { resultType = actual } else {}
        } else {}
      } else {}
    }
    if resultType != "" { return resultType } else { return "" }
  } else {}
  return ""
}
fn expression_type_shape(nodes: List[FlatAstNode], id: Int, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> PepTypeShape {
  let found = lookup_node(nodes, id)
  if !found.found { return empty_type_shape() } else {}
  if found.node.kind == "integer" { return PepTypeShape { kind: "builtin", name: "Int", listDepth: 0 } } else {}
  if found.node.kind == "boolean" { return PepTypeShape { kind: "builtin", name: "Bool", listDepth: 0 } } else {}
  if found.node.kind == "string" { return PepTypeShape { kind: "builtin", name: "Str", listDepth: 0 } } else {}
  if found.node.kind == "if_expression" {
    let thenValue = child_at(nodes, found.node.id, "then", 1)
    let elseValue = child_at(nodes, found.node.id, "else", 2)
    if !thenValue.found || !elseValue.found { return empty_type_shape() } else {}
    let thenShape = expression_type_shape(nodes, thenValue.node.id, functions, bindings, references)
    let elseShape = expression_type_shape(nodes, elseValue.node.id, functions, bindings, references)
    if thenShape.kind != "" && same_type_shape(thenShape, elseShape) { return thenShape } else {}
    return empty_type_shape()
  } else {}
  if found.node.kind == "record" { return PepTypeShape { kind: "nominal", name: found.node.text, listDepth: 0 } } else {}
  if found.node.kind == "name" {
    let reference = find_reference(references, found.node.id)
    if !reference.found { return empty_type_shape() } else {}
    let binding = find_binding(bindings, reference.reference.bindingId)
    if !binding.found { return empty_type_shape() } else {}
    if binding.binding.typeShape.kind != "" { return binding.binding.typeShape } else {}
    return legacy_type_shape(nodes, binding.binding.typeName)
  } else {}
  if found.node.kind == "call" {
    let target = find_function(functions, found.node.text)
    if target.found {
      if target.function.returnShape.kind != "" { return target.function.returnShape } else {}
      return legacy_type_shape(nodes, target.function.returnType)
    } else {}
    if is_constructor(nodes, found.node.text) {
      let unionName = constructor_union_type(nodes, found.node.text)
      return PepTypeShape { kind: "nominal", name: unionName, listDepth: 0 }
    } else {}
    if found.node.text == "append" || found.node.text == "prepend" || found.node.text == "reverse" {
      let collection = child_at(nodes, found.node.id, "argument", 0)
      if collection.found { return expression_type_shape(nodes, collection.node.id, functions, bindings, references) } else { return empty_type_shape() }
    } else {}
    if found.node.text == "length" || found.node.text == "byte_length" || found.node.text == "byte_at" { return PepTypeShape { kind: "builtin", name: "Int", listDepth: 0 } } else {}
    if found.node.text == "contains" { return PepTypeShape { kind: "builtin", name: "Bool", listDepth: 0 } } else {}
    let inferredName = infer_expression_type(nodes, id, functions, bindings, references)
    return legacy_type_shape(nodes, inferredName)
  } else {}
  if found.node.kind == "field_access" {
    let value = child_at(nodes, found.node.id, "value", 0)
    if !value.found { return empty_type_shape() } else {}
    let record = record_declaration(nodes, infer_expression_type(nodes, value.node.id, functions, bindings, references))
    if !record.found { return empty_type_shape() } else {}
    for field in nodes {
      if field.parentId == record.node.id && field.kind == "field_declaration" && field.text == found.node.text {
        let fieldType = child_at(nodes, field.id, "type", 0)
        if fieldType.found { return type_shape_at(nodes, fieldType.node.id) } else { return empty_type_shape() }
      } else {}
    }
  } else {}
  if found.node.kind == "list" {
    var elementShape = empty_type_shape()
    for element in nodes {
      if element.parentId == found.node.id && element.role == "element" && element.kind != "hole" && elementShape.kind == "" {
        elementShape = expression_type_shape(nodes, element.id, functions, bindings, references)
        if elementShape.kind != "" { return with_one_more_list(elementShape) } else {}
      } else {}
    }
    return with_one_more_list(elementShape)
  } else {}
  return empty_type_shape()
}
fn without_one_list(shape: PepTypeShape) -> PepTypeShape {
  if shape.listDepth == 0 { return empty_type_shape() } else {}
  return PepTypeShape { kind: shape.kind, name: shape.name, listDepth: shape.listDepth - 1 }
}
fn has_extra_list_depth(actual: PepTypeShape, expected: PepTypeShape) -> Bool {
  if expected.listDepth == 0 { return actual.listDepth != 0 } else {}
  if actual.listDepth == 0 { return false } else {}
  return has_extra_list_depth(without_one_list(actual), without_one_list(expected))
}
fn list_mismatch_node(nodes: List[FlatAstNode], expressionId: Int, expected: PepTypeShape, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> NodeLookup {
  let expression = lookup_node(nodes, expressionId)
  if !expression.found { return NodeLookup { found: false, node: empty_node() } } else {}
  if expression.node.kind == "list" && expected.listDepth != 0 {
    let expectedElement = without_one_list(expected)
    for element in nodes {
      if element.parentId == expressionId && element.role == "element" && element.kind != "hole" {
        if expectedElement.listDepth != 0 && element.kind == "list" {
          let nested = list_mismatch_node(nodes, element.id, expectedElement, functions, bindings, references)
          if nested.found { return nested } else {}
        } else {
          let actualElement = expression_type_shape(nodes, element.id, functions, bindings, references)
          if actualElement.kind != "" && !same_type_shape(expectedElement, actualElement) {
            return NodeLookup { found: true, node: element }
          } else {}
        }
      } else {}
    }
    return NodeLookup { found: false, node: empty_node() }
  } else {}
  let actual = expression_type_shape(nodes, expressionId, functions, bindings, references)
  if actual.kind != "" && !same_type_shape(expected, actual) { return expression } else {}
  return NodeLookup { found: false, node: empty_node() }
}
fn list_type_name(elementType: Str) -> Str {
  if elementType == "Int" { return "List[Int]" } else {}
  if elementType == "Bool" { return "List[Bool]" } else {}
  if elementType == "Str" { return "List[Str]" } else {}
  if elementType == "Unit" { return "List[Unit]" } else {}
  if elementType == "SourceBytes" { return "List[SourceBytes]" } else {}
  if elementType == "List[Int]" { return "List[List[Int]]" } else {}
  if elementType == "List[Bool]" { return "List[List[Bool]]" } else {}
  if elementType == "List[Str]" { return "List[List[Str]]" } else {}
  if elementType == "List[Unit]" { return "List[List[Unit]]" } else {}
  if elementType == "List[SourceBytes]" { return "List[List[SourceBytes]]" } else {}
  return ""
}
fn legacy_type_name(shape: PepTypeShape) -> Str {
  if shape.kind == "" { return "" } else {}
  if shape.listDepth == 0 { return shape.name } else {}
  if shape.listDepth == 1 { return list_type_name(shape.name) } else {}
  if shape.listDepth == 2 { return list_type_name(list_type_name(shape.name)) } else {}
  return ""
}
fn list_element_type(typeName: Str) -> Str {
  if typeName == "List[Int]" { return "Int" } else {}
  if typeName == "List[Bool]" { return "Bool" } else {}
  if typeName == "List[Str]" { return "Str" } else {}
  if typeName == "List[Unit]" { return "Unit" } else {}
  if typeName == "List[SourceBytes]" { return "SourceBytes" } else {}
  if typeName == "List[List[Int]]" { return "List[Int]" } else {}
  if typeName == "List[List[Bool]]" { return "List[Bool]" } else {}
  if typeName == "List[List[Str]]" { return "List[Str]" } else {}
  if typeName == "List[List[Unit]]" { return "List[Unit]" } else {}
  if typeName == "List[List[SourceBytes]]" { return "List[SourceBytes]" } else {}
  return ""
}
fn contextual_expected_type(nodes: List[FlatAstNode], node: FlatAstNode, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> Str {
  let parent = lookup_node(nodes, node.parentId)
  if !parent.found { return "" } else {}
  if parent.node.kind == "record_field" && node.role == "value" {
    let record = lookup_node(nodes, parent.node.parentId)
    if record.found && record.node.kind == "record" { return record_field_type(nodes, record.node.text, parent.node.text) } else { return "" }
  } else {}
  if parent.node.kind == "assignment" && node.role == "value" {
    let target = find_reference(references, parent.node.id)
    if target.found {
      let binding = find_binding(bindings, target.reference.bindingId)
      if binding.found {
        if binding.binding.typeName != "" { return binding.binding.typeName } else { return legacy_type_name(binding.binding.typeShape) }
      } else { return "" }
    } else { return "" }
  } else {}
  if (parent.node.kind == "let" || parent.node.kind == "var") && node.role == "value" {
    let annotation = child_at(nodes, parent.node.id, "annotation", 0)
    if annotation.found { return type_name_at(nodes, annotation.node.id) } else { return "" }
  } else {}
  if parent.node.kind == "return" && node.role == "value" {
    let owner = owner_function(nodes, node, functions)
    if owner.found { return owner.function.returnType } else { return "" }
  } else {}
  if parent.node.kind == "call" && node.role == "argument" {
    let target = find_function(functions, parent.node.text)
    if target.found { return function_parameter_type(nodes, target.function.syntaxId, node.childIndex) } else {}
    if is_constructor(nodes, parent.node.text) { return variant_payload_type(nodes, parent.node.text, node.childIndex) } else {}
    if (parent.node.text == "append" || parent.node.text == "prepend") && node.childIndex == 0 {
      let enclosingExpected = contextual_expected_type(nodes, parent.node, functions, bindings, references)
      if list_element_type(enclosingExpected) != "" { return enclosingExpected } else {}
      let collection = child_at(nodes, parent.node.id, "argument", 0)
      if collection.found && collection.node.kind == "list" && count_children(nodes, collection.node.id, "element") == 0 {
        let value = child_at(nodes, parent.node.id, "argument", 1)
        if value.found { return list_type_name(infer_expression_type(nodes, value.node.id, functions, bindings, references)) } else { return "" }
      } else { return "" }
    } else {}
    if (parent.node.text == "append" || parent.node.text == "prepend") && node.childIndex == 1 {
      let enclosingExpected = contextual_expected_type(nodes, parent.node, functions, bindings, references)
      if list_element_type(enclosingExpected) != "" { return list_element_type(enclosingExpected) } else {}
      let collection = child_at(nodes, parent.node.id, "argument", 0)
      if collection.found && !(collection.node.kind == "list" && count_children(nodes, collection.node.id, "element") == 0) {
        return list_element_type(infer_expression_type(nodes, collection.node.id, functions, bindings, references))
      } else { return "" }
    } else {}
    return ""
  } else {}
  if parent.node.kind == "if_expression" && (node.role == "then" || node.role == "else") {
    let enclosingExpected = contextual_expected_type(nodes, parent.node, functions, bindings, references)
    if enclosingExpected != "" { return enclosingExpected } else {}
    let siblingRole = if node.role == "then" { "else" } else { "then" }
    let siblingIndex = if node.role == "then" { 2 } else { 1 }
    let sibling = child_at(nodes, parent.node.id, siblingRole, siblingIndex)
    if sibling.found { return infer_expression_type(nodes, sibling.node.id, functions, bindings, references) } else { return "" }
  } else {}
  if parent.node.kind == "list" && node.role == "element" {
    let expectedList = contextual_expected_type(nodes, parent.node, functions, bindings, references)
    return list_element_type(expectedList)
  } else {}
  return ""
}
fn pattern_binding_type(nodes: List[FlatAstNode], pattern: FlatAstNode, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> Str {
  let parent = lookup_node(nodes, pattern.parentId)
  if !parent.found { return "" } else {}
  if parent.node.kind == "constructor_pattern" {
    return variant_payload_type(nodes, parent.node.text, pattern.childIndex)
  } else {}
  if parent.node.kind == "match_arm" {
    let expression = lookup_node(nodes, parent.node.parentId)
    if expression.found {
      let subject = child_at(nodes, expression.node.id, "value", 0)
      if subject.found { return infer_expression_type(nodes, subject.node.id, functions, bindings, references) } else { return "" }
    } else { return "" }
  } else {}
  return ""
}
fn pattern_binding_shape(nodes: List[FlatAstNode], pattern: FlatAstNode, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> PepTypeShape {
  let parent = lookup_node(nodes, pattern.parentId)
  if !parent.found { return empty_type_shape() } else {}
  if parent.node.kind == "constructor_pattern" {
    let variant = variant_declaration(nodes, parent.node.text)
    if !variant.found { return empty_type_shape() } else {}
    let payload = child_at(nodes, variant.node.id, "field_type", pattern.childIndex)
    if payload.found { return type_shape_at(nodes, payload.node.id) } else { return empty_type_shape() }
  } else {}
  if parent.node.kind == "match_arm" {
    let expression = lookup_node(nodes, parent.node.parentId)
    if expression.found {
      let subject = child_at(nodes, expression.node.id, "value", 0)
      if subject.found { return expression_type_shape(nodes, subject.node.id, functions, bindings, references) } else { return empty_type_shape() }
    } else { return empty_type_shape() }
  } else {}
  return empty_type_shape()
}
fn union_variant_count(nodes: List[FlatAstNode], unionName: Str) -> Int {
  let union = union_declaration(nodes, unionName)
  if !union.found { return 0 } else {}
  var count = 0
  for variant in nodes {
    if variant.parentId == union.node.id && variant.kind == "variant_declaration" { count = count + 1 } else {}
  }
  return count
}
fn validate_nested_pattern(nodes: List[FlatAstNode], pattern: FlatAstNode, expectedType: Str) -> PatternValidation {
  if pattern.kind == "binding_pattern" || pattern.kind == "wildcard_pattern" {
    return PatternValidation { valid: true, covers: true, code: "", node: empty_node() }
  } else {}
  if pattern.kind != "constructor_pattern" {
    return PatternValidation { valid: false, covers: false, code: "PEP_PATTERN_UNSUPPORTED", node: pattern }
  } else {}
  if !is_constructor(nodes, pattern.text) {
    return PatternValidation { valid: false, covers: false, code: "PEP_UNKNOWN_CONSTRUCTOR", node: pattern }
  } else {}
  let actualUnion = constructor_union_type(nodes, pattern.text)
  if expectedType == "" || actualUnion != expectedType {
    return PatternValidation { valid: false, covers: false, code: "PEP_PATTERN_TYPE_MISMATCH", node: pattern }
  } else {}
  let variant = variant_declaration(nodes, pattern.text)
  let expectedArity = if variant.found { count_children(nodes, variant.node.id, "field_type") } else { -1 }
  if expectedArity != count_children(nodes, pattern.id, "argument") {
    return PatternValidation { valid: false, covers: false, code: "PEP_PATTERN_ARITY", node: pattern }
  } else {}
  var covers = union_variant_count(nodes, expectedType) == 1
  for payload in nodes {
    if payload.parentId == pattern.id && payload.role == "argument" {
      let payloadType = variant_payload_type(nodes, pattern.text, payload.childIndex)
      let nested = validate_nested_pattern(nodes, payload, payloadType)
      if !nested.valid { return nested } else {}
      if !nested.covers { covers = false } else {}
    } else {}
  }
  return PatternValidation { valid: true, covers: covers, code: "", node: empty_node() }
}
fn pattern_covers_payload(nodes: List[FlatAstNode], pattern: FlatAstNode, expectedType: Str) -> Bool {
  let checked = validate_nested_pattern(nodes, pattern, expectedType)
  return checked.valid && checked.covers
}
fn pattern_key_nested_parts(nodes: List[FlatAstNode], pattern: FlatAstNode) -> List[PatternKeyNestedPart] {
  var reversed: List[PatternKeyNestedPart] = []
  for payload in nodes {
    if payload.parentId == pattern.id && payload.role == "argument" {
      let kind = if payload.kind == "constructor_pattern" { "constructor" } else { if payload.kind == "binding_pattern" || payload.kind == "wildcard_pattern" { "irrefutable" } else { "unsupported" } }
      let constructor = if payload.kind == "constructor_pattern" { payload.text } else { "" }
      let payloadArity = if payload.kind == "constructor_pattern" { count_children(nodes, payload.id, "argument") } else { 0 }
      reversed = prepend(reversed, PatternKeyNestedPart { position: payload.childIndex, kind: kind, constructor: constructor, payloadArity: payloadArity })
    } else {}
  }
  return reverse(reversed)
}
fn pattern_has_unkeyed_constructor(nodes: List[FlatAstNode], rootId: Int) -> Bool {
  for top in nodes {
    if top.parentId == rootId && top.role == "argument" && top.kind == "constructor_pattern" {
      for nested in nodes {
        if nested.parentId == top.id && nested.role == "argument" && nested.kind == "constructor_pattern" {
          for deeper in nodes {
            if deeper.parentId == nested.id && deeper.role == "argument" && deeper.kind == "constructor_pattern" { return true } else {}
          }
        } else {}
      }
    } else {}
  }
  return false
}
fn same_pattern_structure(nodes: List[FlatAstNode], leftId: Int, rightId: Int) -> Bool {
  let left = lookup_node(nodes, leftId)
  let right = lookup_node(nodes, rightId)
  if !left.found || !right.found { return false } else {}
  if left.node.kind == "binding_pattern" || left.node.kind == "wildcard_pattern" {
    return right.node.kind == "binding_pattern" || right.node.kind == "wildcard_pattern"
  } else {}
  if left.node.kind != "constructor_pattern" || right.node.kind != "constructor_pattern" { return false } else {}
  if left.node.text != right.node.text { return false } else {}
  let leftCount = count_children(nodes, leftId, "argument")
  let rightCount = count_children(nodes, rightId, "argument")
  if leftCount != rightCount { return false } else {}
  var index = 0
  while index <= leftCount - 1 {
    let leftArgument = child_at(nodes, leftId, "argument", index)
    let rightArgument = child_at(nodes, rightId, "argument", index)
    if !leftArgument.found || !rightArgument.found { return false } else {}
    if !same_pattern_structure(nodes, leftArgument.node.id, rightArgument.node.id) { return false } else {}
    index = index + 1
  }
  return true
}
fn same_nested_pattern_parts(left: List[PatternKeyNestedPart], right: List[PatternKeyNestedPart]) -> Bool {
  if length(left) != length(right) { return false } else {}
  for leftPart in left {
    var found = false
    for rightPart in right {
      if leftPart.position == rightPart.position && leftPart.kind == rightPart.kind && leftPart.constructor == rightPart.constructor && leftPart.payloadArity == rightPart.payloadArity { found = true } else {}
    }
    if !found { return false } else {}
  }
  return true
}
fn same_pattern_key_parts(left: List[PatternKeyPart], right: List[PatternKeyPart]) -> Bool {
  if length(left) != length(right) { return false } else {}
  for leftPart in left {
    var found = false
    for rightPart in right {
      if leftPart.position == rightPart.position && leftPart.kind == rightPart.kind && leftPart.constructor == rightPart.constructor && leftPart.payloadArity == rightPart.payloadArity && same_nested_pattern_parts(leftPart.nestedParts, rightPart.nestedParts) { found = true } else {}
    }
    if !found { return false } else {}
  }
  return true
}
fn same_constructor_pattern_key(nodes: List[FlatAstNode], left: ConstructorPatternKey, right: ConstructorPatternKey) -> Bool {
  if left.name != right.name || left.argumentCount != right.argumentCount { return false } else {}
  if pattern_has_unkeyed_constructor(nodes, left.syntaxId) || pattern_has_unkeyed_constructor(nodes, right.syntaxId) {
    return same_pattern_structure(nodes, left.syntaxId, right.syntaxId)
  } else {}
  return same_pattern_key_parts(left.argumentPatterns, right.argumentPatterns)
}
fn infer_binding_types(nodes: List[FlatAstNode], functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> List[BindingFact] {
  var typed: List[BindingFact] = []
  for binding in bindings {
    var typeName = binding.typeName
    let declaration = lookup_node(nodes, binding.syntaxId)
    var typeShape = binding.typeShape
    if typeName == "" && declaration.found {
      if declaration.node.kind == "for_in" {
        let iterable = child_at(nodes, declaration.node.id, "iterable", 0)
        if iterable.found {
          let iterableShape = expression_type_shape(nodes, iterable.node.id, functions, typed, references)
          if iterableShape.listDepth != 0 {
            typeShape = without_one_list(iterableShape)
            typeName = legacy_type_name(typeShape)
          } else {
            let iterableType = infer_expression_type(nodes, iterable.node.id, functions, typed, references)
            typeName = list_element_type(iterableType)
            if typeName != "" { typeShape = legacy_type_shape(nodes, typeName) } else {}
          }
        } else {}
      } else {
        if declaration.node.kind == "binding_pattern" {
          if typeShape.kind == "" { typeShape = pattern_binding_shape(nodes, declaration.node, functions, typed, references) } else {}
          if typeShape.kind != "" { typeName = legacy_type_name(typeShape) } else {
            typeName = pattern_binding_type(nodes, declaration.node, functions, typed, references)
          }
        } else {
          let value = child_at(nodes, declaration.node.id, "value", 0)
          if value.found { typeName = infer_expression_type(nodes, value.node.id, functions, typed, references) } else {}
        }
      }
    } else {}
    if typeShape.kind == "" && typeName != "" { typeShape = legacy_type_shape(nodes, typeName) } else {}
    if typeShape.kind == "" && typeName == "" && declaration.found && declaration.node.kind != "binding_pattern" {
      let value = child_at(nodes, declaration.node.id, "value", 0)
      if value.found { typeShape = expression_type_shape(nodes, value.node.id, functions, typed, references) } else {}
    } else {}
    typed = prepend(typed, BindingFact { semanticId: binding.semanticId, syntaxId: binding.syntaxId, name: binding.name, ownerFunctionId: binding.ownerFunctionId, scopeId: binding.scopeId, visibleFrom: binding.visibleFrom, mutable: binding.mutable, typeName: typeName, typeShape: typeShape })
  }
  return reverse(typed)
}
fn is_first_type_declaration(nodes: List[FlatAstNode], name: Str, nodeId: Int) -> Bool {
  var earlierMatches = 0
  for node in nodes {
    if node.parentId == -1 && (node.kind == "record_declaration" || node.kind == "union_declaration") && node.text == name && node.id + 1 <= nodeId { earlierMatches = earlierMatches + 1 } else {}
  }
  return earlierMatches == 0
}
fn is_first_duplicate_type_declaration(nodes: List[FlatAstNode], name: Str, nodeId: Int) -> Bool {
  var earlierMatches = 0
  for node in nodes {
    if node.parentId == -1 && (node.kind == "record_declaration" || node.kind == "union_declaration") && node.text == name && node.id + 1 <= nodeId {
      earlierMatches = earlierMatches + 1
    } else {}
  }
  return earlierMatches == 1
}
fn is_first_duplicate_occurrence(nodes: List[FlatAstNode], parentId: Int, kind: Str, name: Str, nodeId: Int) -> Bool {
  var earlierMatches = 0
  for node in nodes {
    if node.parentId == parentId && node.kind == kind && node.text == name && node.id + 1 <= nodeId {
      earlierMatches = earlierMatches + 1
    } else {}
  }
  return earlierMatches == 1
}
fn is_first_duplicate_constructor(nodes: List[FlatAstNode], name: Str, nodeId: Int) -> Bool {
  var earlierMatches = 0
  for node in nodes {
    if node.kind == "variant_declaration" && node.text == name && node.id + 1 <= nodeId {
      earlierMatches = earlierMatches + 1
    } else {}
  }
  return earlierMatches == 1
}
fn supported_primitive_type(typeName: Str) -> Bool {
  return typeName == "Int" || typeName == "Bool" || typeName == "Str" || typeName == "Unit" || typeName == "SourceBytes" || list_element_type(typeName) != ""
}
fn supported_type(nodes: List[FlatAstNode], typeName: Str) -> Bool {
  return supported_primitive_type(typeName) || record_declaration(nodes, typeName).found || union_declaration(nodes, typeName).found
}
fn supported_type_at(nodes: List[FlatAstNode], id: Int, knownName: Str) -> Bool {
  if supported_type(nodes, knownName) { return true } else {}
  let shape = type_shape_at(nodes, id)
  if shape.kind == "" { return false } else {}
  return supported_type(nodes, shape.name)
}
fn unsupported_type_code(nodes: List[FlatAstNode], id: Int, knownName: Str) -> Str {
  if supported_type_at(nodes, id, knownName) { return "" } else {}
  let shape = type_shape_at(nodes, id)
  if shape.kind == "nominal" && !record_declaration(nodes, shape.name).found && !union_declaration(nodes, shape.name).found { return "PEP_UNKNOWN_TYPE" } else {}
  return "PEP_A13_TYPE_UNSUPPORTED"
}
fn equality_supported_type(typeName: Str) -> Bool {
  return typeName == "Int" || typeName == "Bool" || typeName == "Str" || typeName == "Unit"
}
fn expected_hole_type(nodes: List[FlatAstNode], hole: FlatAstNode, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> Str {
  let parent = lookup_node(nodes, hole.parentId)
  if !parent.found { return "" } else {}
  if parent.node.kind == "return" && hole.role == "value" {
    let owner = owner_function(nodes, hole, functions)
    if owner.found { return owner.function.returnType } else { return "" }
  } else {}
  if parent.node.kind == "assignment" && hole.role == "value" {
    return contextual_expected_type(nodes, hole, functions, bindings, references)
  } else {}
  if parent.node.kind == "if_expression" && (hole.role == "then" || hole.role == "else") {
    let expected = contextual_expected_type(nodes, parent.node, functions, bindings, references)
    if expected != "" { return expected } else {}
    let siblingRole = if hole.role == "then" { "else" } else { "then" }
    let siblingIndex = if hole.role == "then" { 2 } else { 1 }
    let sibling = child_at(nodes, parent.node.id, siblingRole, siblingIndex)
    if sibling.found { return infer_expression_type(nodes, sibling.node.id, functions, bindings, references) } else { return "" }
  } else {}
  if parent.node.kind == "match_arm" && hole.role == "result" {
    let expression = lookup_node(nodes, parent.node.parentId)
    if expression.found {
      let expected = contextual_expected_type(nodes, expression.node, functions, bindings, references)
      if expected != "" { return expected } else {}
      for arm in nodes {
        if arm.parentId == expression.node.id && arm.kind == "match_arm" && arm.id != parent.node.id {
          let sibling = child_at(nodes, arm.id, "result", 1)
          if sibling.found {
            let actual = infer_expression_type(nodes, sibling.node.id, functions, bindings, references)
            if actual != "" { return actual } else {}
          } else {}
        } else {}
      }
    } else {}
  } else {}
  if parent.node.kind == "call" && hole.role == "argument" {
    let target = find_function(functions, parent.node.text)
    if target.found { return function_parameter_type(nodes, target.function.syntaxId, hole.childIndex) } else {}
    if is_constructor(nodes, parent.node.text) { return variant_payload_type(nodes, parent.node.text, hole.childIndex) } else {}
    if (parent.node.text == "append" || parent.node.text == "prepend" || parent.node.text == "contains") && hole.childIndex == 1 {
      let collection = child_at(nodes, parent.node.id, "argument", 0)
      if collection.found { return list_element_type(infer_expression_type(nodes, collection.node.id, functions, bindings, references)) } else { return "" }
    } else {}
    if (parent.node.text == "append" || parent.node.text == "prepend") && hole.childIndex == 0 {
      return contextual_expected_type(nodes, parent.node, functions, bindings, references)
    } else {}
    return ""
  } else {}
  if (parent.node.kind == "let" || parent.node.kind == "var") && hole.role == "value" {
    let annotation = child_at(nodes, parent.node.id, "annotation", 0)
    if annotation.found { return type_name_at(nodes, annotation.node.id) } else { return "" }
  } else {}
  if parent.node.kind == "binary" {
    if parent.node.text == "&&" || parent.node.text == "||" { return "Bool" } else {}
    if parent.node.text == "+" || parent.node.text == "-" || parent.node.text == "*" || parent.node.text == "/" || parent.node.text == "%" || parent.node.text == "<" || parent.node.text == "<=" || parent.node.text == ">" || parent.node.text == ">=" { return "Int" } else {}
    let siblingRole = if hole.role == "left" { "right" } else { "left" }
    let siblingIndex = if hole.role == "left" { 1 } else { 0 }
    let sibling = child_at(nodes, parent.node.id, siblingRole, siblingIndex)
    if sibling.found { return infer_expression_type(nodes, sibling.node.id, functions, bindings, references) } else { return "" }
  } else {}
  if parent.node.kind == "unary" && hole.role == "operand" {
    if parent.node.text == "!" { return "Bool" } else { return "Int" }
  } else {}
  if parent.node.kind == "list" && hole.role == "element" {
    return list_element_type(contextual_expected_type(nodes, parent.node, functions, bindings, references))
  } else {}
  if parent.node.kind == "record_field" && hole.role == "value" {
    let record = lookup_node(nodes, parent.node.parentId)
    if record.found { return record_field_type(nodes, record.node.text, parent.node.text) } else { return "" }
  } else {}
  if (parent.node.kind == "if_expression" || parent.node.kind == "if_statement" || parent.node.kind == "while") && hole.role == "condition" { return "Bool" } else {}
  return ""
}
fn hole_facts(nodes: List[FlatAstNode], functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> List[HoleFact] {
  var facts: List[HoleFact] = []
  var ordinal = 0
  for node in nodes {
    if node.kind == "hole" {
      let owner = owner_function(nodes, node, functions)
      let scopes = if owner.found { scope_chain(nodes, node, owner.function.syntaxId, owner.function.semanticId) } else { [] }
      let scope = first_scope(scopes, 0)
      let expected = expected_hole_type(nodes, node, functions, bindings, references)
      var visible: List[Int] = []
      var candidates: List[Int] = []
      var visibleNames: List[Str] = []
      for scopeId in scopes {
        for binding in bindings {
          if owner.found && binding.ownerFunctionId == owner.function.semanticId && binding.scopeId == scopeId && binding.visibleFrom <= node.startByte && !contains(visibleNames, binding.name) {
            visibleNames = append(visibleNames, binding.name)
            visible = append(visible, binding.semanticId)
            if expected != "" && binding.typeName == expected { candidates = append(candidates, binding.semanticId) } else {}
          } else {}
        }
      }
      facts = append(facts, HoleFact { semanticId: 3000000 + ordinal, syntaxId: node.id, name: node.text, expectedType: expected, scopeId: scope, visibleBindingIds: visible, candidateBindingIds: candidates, startByte: node.startByte, endByte: node.endByte })
      ordinal = ordinal + 1
    } else {}
  }
  return facts
}
fn fixed_builtin_arity(name: Str) -> Int {
  if name == "say" || name == "int_text" || name == "byte_length" || name == "length" || name == "reverse" { return 1 } else {}
  if name == "append" || name == "prepend" || name == "contains" { return 2 } else {}
  if name == "byte_at" { return 2 } else {}
  if name == "byte_slice" || name == "utf8_slice" { return 3 } else {}
  if name == "source_bytes" { return 0 } else {}
  return -1
}
fn fixed_builtin_parameter_type(name: Str, index: Int) -> Str {
  if name == "say" && index == 0 { return "Str" } else {}
  if name == "int_text" && index == 0 { return "Int" } else {}
  if name == "byte_length" && index == 0 { return "SourceBytes" } else {}
  if name == "byte_at" && index == 0 { return "SourceBytes" } else {}
  if (name == "byte_slice" || name == "utf8_slice") && index == 0 { return "SourceBytes" } else {}
  if name == "byte_at" && index == 1 { return "Int" } else {}
  if (name == "byte_slice" || name == "utf8_slice") && (index == 1 || index == 2) { return "Int" } else {}
  return ""
}
fn branch_always_returns(nodes: List[FlatAstNode], parentId: Int, role: Str) -> Bool {
  var covered = false
  for statement in nodes {
    if statement.parentId == parentId && statement.role == role && statement_always_returns(nodes, statement) { covered = true } else {}
  }
  return covered
}
fn statement_always_returns(nodes: List[FlatAstNode], statement: FlatAstNode) -> Bool {
  if statement.kind == "return" { return true } else {}
  if statement.kind == "block" { return branch_always_returns(nodes, statement.id, "statement") } else {}
  if statement.kind == "if_statement" {
    if count_children(nodes, statement.id, "else") == 0 { return false } else {}
    return branch_always_returns(nodes, statement.id, "then") && branch_always_returns(nodes, statement.id, "else")
  } else {}
  return false
}
fn if_expression_branch_mismatch(nodes: List[FlatAstNode], id: Int, expectedType: Str, expectedShape: PepTypeShape, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> Bool {
  let expression = lookup_node(nodes, id)
  if !expression.found || expression.node.kind != "if_expression" { return false } else {}
  let thenValue = child_at(nodes, id, "then", 1)
  let elseValue = child_at(nodes, id, "else", 2)
  if !thenValue.found || !elseValue.found { return false } else {}
  let thenType = infer_expression_type(nodes, thenValue.node.id, functions, bindings, references)
  let elseType = infer_expression_type(nodes, elseValue.node.id, functions, bindings, references)
  if expectedType != "" && ((thenType != "" && thenType != expectedType) || (elseType != "" && elseType != expectedType)) { return true } else {}
  let thenShape = expression_type_shape(nodes, thenValue.node.id, functions, bindings, references)
  let elseShape = expression_type_shape(nodes, elseValue.node.id, functions, bindings, references)
  if expectedShape.kind != "" && ((thenShape.kind != "" && !same_type_shape(expectedShape, thenShape)) || (elseShape.kind != "" && !same_type_shape(expectedShape, elseShape))) { return true } else {}
  if (thenType == "" || elseType == "") && thenShape.kind != "" && elseShape.kind != "" && !same_type_shape(thenShape, elseShape) { return true } else {}
  return false
}

fn type_analysis(nodes: List[FlatAstNode], functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> TypeAnalysis {
  var reversedFacts: List[ExpressionTypeFact] = []
  let sequentialFunctionOwner = length(functions) != 1
  var activeFunctionFound = false
  var activeFunction = CheckedFunction { semanticId: -1, syntaxId: -1, name: "", arity: 0, returnType: "", returnShape: empty_type_shape(), startByte: 0, endByte: 0 }
  var reversedDiagnostics: List[CheckDiagnostic] = []
  var unreachable = UnreachableLookup { found: false, node: empty_node() }
  for node in nodes {
    if !unreachable.found && (node.kind == "return" || node.kind == "block" || node.kind == "if_statement") && statement_always_returns(nodes, node) {
      let nextStatement = child_at(nodes, node.parentId, node.role, node.childIndex + 1)
      if nextStatement.found { unreachable = UnreachableLookup { found: true, node: nextStatement.node } } else {}
    } else {}
    if sequentialFunctionOwner && node.parentId == -1 && node.kind == "function" {
      let activeLookup = find_function_by_syntax(functions, node.id)
      activeFunction = activeLookup.function
      activeFunctionFound = activeLookup.found
    } else {}
    if node.kind == "function" {
      let returnType = child_at(nodes, node.id, "return_type", 0)
      if !returnType.found || !supported_type_at(nodes, returnType.node.id, declared_return_type(nodes, node.id)) {
        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(unsupported_type_code(nodes, returnType.node.id, declared_return_type(nodes, node.id)), "Function result type is outside the implemented primitive checker subset", node))
      } else {}
      if (known_builtin(node.text) || is_constructor(nodes, node.text)) && is_first_function_declaration(functions, node.text, node.id) {
        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_RESERVED_FUNCTION", "Function name is reserved for a builtin or constructor", node))
      } else {}
      for parameter in nodes {
        if parameter.parentId == node.id && parameter.kind == "parameter" {
          let parameterType = child_at(nodes, parameter.id, "type", 0)
          if !parameterType.found || !supported_type_at(nodes, parameterType.node.id, declared_binding_type(nodes, parameter)) {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(unsupported_type_code(nodes, parameterType.node.id, declared_binding_type(nodes, parameter)), "Parameter type is outside the implemented primitive checker subset", parameter))
          } else {}
        } else {}
      }
      if declared_return_type(nodes, node.id) != "Unit" {
        var returnsOnAllPaths = false
        for statement in nodes {
          if statement.parentId == node.id && statement.role == "statement" && statement_always_returns(nodes, statement) { returnsOnAllPaths = true } else {}
        }
        if !returnsOnAllPaths {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_MISSING_RETURN", "Non-Unit function does not return a value on every path", node))
        } else {}
      } else {}
    } else {}
    if (node.kind == "let" || node.kind == "var") {
      let annotation = child_at(nodes, node.id, "annotation", 0)
      if annotation.found && !supported_type_at(nodes, annotation.node.id, type_name_at(nodes, annotation.node.id)) {
        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(unsupported_type_code(nodes, annotation.node.id, type_name_at(nodes, annotation.node.id)), "Binding annotation is outside the implemented primitive checker subset", node))
      } else {}
    } else {}
    if node.kind == "record_declaration" {
      if is_first_duplicate_type_declaration(nodes, node.text, node.id) && !supported_primitive_type(node.text) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_TYPE", "Type name is declared more than once", node)) } else {}
      if supported_primitive_type(node.text) && is_first_type_declaration(nodes, node.text, node.id) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_TYPE", "Type name is already reserved by a built-in type", node)) } else {}
      for field in nodes {
        if field.parentId == node.id && field.kind == "field_declaration" {
          if is_first_duplicate_occurrence(nodes, node.id, "field_declaration", field.text, field.id) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_FIELD", "Record field is declared more than once", field)) } else {}
          let fieldType = child_at(nodes, field.id, "type", 0)
          if fieldType.found && !supported_type_at(nodes, fieldType.node.id, type_name_at(nodes, fieldType.node.id)) {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(unsupported_type_code(nodes, fieldType.node.id, type_name_at(nodes, fieldType.node.id)), "Record field type is outside the implemented checker subset", field))
          } else {}
        } else {}
      }
    } else {}
    if node.kind == "union_declaration" {
      if is_first_duplicate_type_declaration(nodes, node.text, node.id) && !supported_primitive_type(node.text) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_TYPE", "Type name is declared more than once", node)) } else {}
      if supported_primitive_type(node.text) && is_first_type_declaration(nodes, node.text, node.id) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_TYPE", "Type name is already reserved by a built-in type", node)) } else {}
      for variant in nodes {
        if variant.parentId == node.id && variant.kind == "variant_declaration" {
          if is_first_duplicate_constructor(nodes, variant.text, variant.id) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_CONSTRUCTOR", "Constructor name is declared more than once", variant)) } else {}
          for payload in nodes {
            if payload.parentId == variant.id && payload.role == "field_type" && !supported_type_at(nodes, payload.id, type_name_at(nodes, payload.id)) {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(unsupported_type_code(nodes, payload.id, type_name_at(nodes, payload.id)), "Union constructor payload type is outside the implemented checker subset", payload))
            } else {}
          }
        } else {}
      }
    } else {}
    if node.kind == "for_in" {
      let iterable = child_at(nodes, node.id, "iterable", 0)
      if iterable.found {
        let iterableType = infer_expression_type(nodes, iterable.node.id, functions, bindings, references)
        let iterableShape = expression_type_shape(nodes, iterable.node.id, functions, bindings, references)
        let isList = iterableShape.listDepth != 0 || list_element_type(iterableType) != ""
        if !isList && (iterableType != "" || iterableShape.kind != "") {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_FOR_REQUIRES_LIST", "for-in requires a list value", iterable.node))
        } else {}
      } else {}
    } else {}
    if node.kind == "assignment" {
      let target = find_reference(references, node.id)
      if target.found {
        let binding = find_binding(bindings, target.reference.bindingId)
        if binding.found {
          if !binding.binding.mutable {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_ASSIGN_IMMUTABLE", "Cannot assign to an immutable binding", node))
          } else {
            let value = child_at(nodes, node.id, "value", 0)
            if value.found {
              let expectedName = binding.binding.typeName
              let expectedShape = if binding.binding.typeShape.kind != "" { binding.binding.typeShape } else { legacy_type_shape(nodes, expectedName) }
              let actualName = infer_expression_type(nodes, value.node.id, functions, bindings, references)
              let actualShape = expression_type_shape(nodes, value.node.id, functions, bindings, references)
              let nameMismatch = expectedName != "" && actualName != "" && expectedName != actualName
              let shapeMismatch = expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
              if expectedName == "" && expectedShape.kind == "" {
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "Assignment target has no supported concrete type", node))
              } else {}
              if nameMismatch || shapeMismatch {
                let mismatch = if expectedShape.listDepth != 0 { list_mismatch_node(nodes, value.node.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
                let mismatchNode = if mismatch.found { mismatch.node } else { value.node }
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Assigned value type does not match the target binding", mismatchNode))
              } else {}
            } else {}
          }
        } else {}
      } else {}
    } else {}
    if is_expression_kind(node.kind) {
      let actual = infer_expression_type(nodes, node.id, functions, bindings, references)
      if actual == "" {
        let shape = expression_type_shape(nodes, node.id, functions, bindings, references)
        if shape.kind != "" { reversedFacts = prepend(reversedFacts, ExpressionTypeFact { syntaxId: node.id, typeName: "", typeShape: shape, startByte: node.startByte, endByte: node.endByte }) } else {}
        if node.kind == "hole" { } else {
        if node.kind == "call" {
          if known_builtin(node.text) && shape.kind == "" { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "This built-in call has no type rule in the current checker slice", node)) } else {}
          if is_constructor(nodes, node.text) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "Constructor payload and nominal identity checks are not implemented", node)) } else {}
        } else {
          if node.kind == "list" && count_children(nodes, node.id, "element") == 0 {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_EMPTY_LIST_NEEDS_TYPE", "An empty list needs a concrete list type from context", node))
          } else {
            if node.kind != "name" && shape.kind == "" { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "This expression form has no type rule in the current checker slice", node)) } else {}
          }
        }
        }
      } else {
        reversedFacts = prepend(reversedFacts, ExpressionTypeFact { syntaxId: node.id, typeName: actual, typeShape: legacy_type_shape(nodes, actual), startByte: node.startByte, endByte: node.endByte })
      }
      if node.kind == "record" {
        let declaration = record_declaration(nodes, node.text)
        if declaration.found {
          var duplicateFound = false
          var duplicateNode = empty_node()
          var fieldDiagnosticFound = false
          var fieldDiagnosticCode = ""
          var fieldDiagnosticNode = empty_node()
          for field in nodes {
            if field.parentId == node.id && field.kind == "record_field" {
              if !duplicateFound && is_first_duplicate_occurrence(nodes, node.id, "record_field", field.text, field.id) {
                duplicateFound = true
                duplicateNode = field
              } else {}
              if !fieldDiagnosticFound {
                let expected = record_field_type(nodes, node.text, field.text)
                let expectedShape = record_field_shape(nodes, node.text, field.text)
                let value = child_at(nodes, field.id, "value", 0)
                let actual = if value.found { infer_expression_type(nodes, value.node.id, functions, bindings, references) } else { "" }
                let actualShape = if value.found { expression_type_shape(nodes, value.node.id, functions, bindings, references) } else { empty_type_shape() }
                let shapeMismatch = expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
                if expected == "" && expectedShape.kind == "" {
                  fieldDiagnosticFound = true
                  fieldDiagnosticCode = "PEP_UNKNOWN_FIELD"
                  fieldDiagnosticNode = field
                } else {
                  if expected != "" && actual != "" && actual != expected {
                    fieldDiagnosticFound = true
                    fieldDiagnosticCode = "PEP_TYPE_MISMATCH"
                    fieldDiagnosticNode = value.node
                  } else {
                    let listMismatch = if expectedShape.listDepth != 0 { list_mismatch_node(nodes, value.node.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
                    if ((expected == "" || actual == "") && shapeMismatch) || (expected == actual && expectedShape.listDepth != 0 && expectedShape.listDepth != 1 && listMismatch.found) {
                      let mismatch = listMismatch
                      fieldDiagnosticFound = true
                      fieldDiagnosticCode = "PEP_TYPE_MISMATCH"
                      fieldDiagnosticNode = if mismatch.found { mismatch.node } else { value.node }
                    } else {}
                  }
                }
              } else {}
            } else {}
          }
          var missingFound = false
          var missingNode = empty_node()
          for declared in nodes {
            if !missingFound && declared.parentId == declaration.node.id && declared.kind == "field_declaration" {
              var supplied = false
              for field in nodes {
                if field.parentId == node.id && field.kind == "record_field" && field.text == declared.text { supplied = true } else {}
              }
              if !supplied {
                missingFound = true
                missingNode = declared
              } else {}
            } else {}
          }
          if duplicateFound {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_FIELD", "Record literal supplies a field more than once", duplicateNode))
          } else {
            if missingFound {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_MISSING_FIELD", "Record literal omits a declared field", missingNode))
            } else {
              if fieldDiagnosticFound {
                let fieldDiagnosticMessage = if fieldDiagnosticCode == "PEP_UNKNOWN_FIELD" { "Record literal names a field absent from its declaration" } else { "Record field value type does not match its declaration" }
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(fieldDiagnosticCode, fieldDiagnosticMessage, fieldDiagnosticNode))
              } else {}
            }
          }
        } else {}
      } else {}
      if node.kind == "list" && contextual_expected_type(nodes, node, functions, bindings, references) == "" {
        let expectedElement = list_element_type(infer_expression_type(nodes, node.id, functions, bindings, references))
        var mismatchReported = false
        for element in nodes {
          if element.parentId == node.id && element.role == "element" && element.kind != "hole" {
            let actualElement = infer_expression_type(nodes, element.id, functions, bindings, references)
            if !mismatchReported && expectedElement != "" && actualElement != "" && expectedElement != actualElement {
              var mismatchNode = element
              let nestedExpectedElement = list_element_type(expectedElement)
              if element.kind == "list" && nestedExpectedElement != "" {
                var nestedMismatchReported = false
                for nested in nodes {
                  if !nestedMismatchReported && nested.parentId == element.id && nested.role == "element" && nested.kind != "hole" && infer_expression_type(nodes, nested.id, functions, bindings, references) != nestedExpectedElement {
                    mismatchNode = nested
                    nestedMismatchReported = true
                  } else {}
                }
              } else {}
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "List element type does not match the inferred element type", mismatchNode))
              mismatchReported = true
            } else {}
          } else {}
        }
      } else {}
      if node.kind == "field_access" {
        let value = child_at(nodes, node.id, "value", 0)
        if value.found && infer_expression_type(nodes, node.id, functions, bindings, references) == "" && expression_type_shape(nodes, node.id, functions, bindings, references).kind == "" {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNKNOWN_FIELD", "Field selection does not name a declared field of the record", node))
        } else {}
      } else {}
      if node.kind == "match" {
        let subject = child_at(nodes, node.id, "value", 0)
        let subjectType = if subject.found { infer_expression_type(nodes, subject.node.id, functions, bindings, references) } else { "" }
        let union = union_declaration(nodes, subjectType)
        if !union.found {
          let code = if subjectType == "" { "PEP_MATCH_UNTYPED" } else { "PEP_MATCH_NON_UNION" }
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(code, "Match subject must have a supported tagged-union type", node))
        } else {}
        var catchAll = false
        var invalidPattern = false
        var seenConstructors: List[Str] = []
        var seenConstructorPatterns: List[ConstructorPatternKey] = []
        let expectedResultType = contextual_expected_type(nodes, node, functions, bindings, references)
        var resultType = ""
        var contextualMismatchReported = false
        for arm in nodes {
          if arm.parentId == node.id && arm.kind == "match_arm" {
            let pattern = child_at(nodes, arm.id, "pattern", 0)
            let result = child_at(nodes, arm.id, "result", 1)
            var unreachable = catchAll
            if unreachable {
              invalidPattern = true
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNREACHABLE_MATCH_ARM", "Match arm follows an irrefutable pattern", arm))
            } else {}
            if pattern.found && !unreachable {
              if pattern.node.kind == "wildcard_pattern" || pattern.node.kind == "binding_pattern" { catchAll = true } else {}
              if pattern.node.kind == "constructor_pattern" {
                let patternUnion = constructor_union_type(nodes, pattern.node.text)
                var duplicatePatternEligible = true
                let patternErrorCode = if patternUnion == "" { "PEP_UNKNOWN_CONSTRUCTOR" } else { "PEP_PATTERN_TYPE_MISMATCH" }
                if union.found && (patternUnion == "" || patternUnion != subjectType) {
                  duplicatePatternEligible = false
                  invalidPattern = true
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(patternErrorCode, "Unknown constructor or constructor from another union", pattern.node))
                } else {}
                var coversVariant = true
                var patternArgumentCount = 0
                var reversedArgumentPatterns: List[PatternKeyPart] = []
                let variant = variant_declaration(nodes, pattern.node.text)
                let expectedArity = if variant.found { count_children(nodes, variant.node.id, "field_type") } else { -1 }
                for payload in nodes {
                  if payload.parentId == pattern.node.id && payload.role == "argument" {
                    patternArgumentCount = patternArgumentCount + 1
                    let partKind = if payload.kind == "constructor_pattern" { "constructor" } else { if payload.kind == "binding_pattern" || payload.kind == "wildcard_pattern" { "irrefutable" } else { "unsupported" } }
                    let partConstructor = if payload.kind == "constructor_pattern" { payload.text } else { "" }
                    let partArity = if payload.kind == "constructor_pattern" { count_children(nodes, payload.id, "argument") } else { 0 }
                    reversedArgumentPatterns = prepend(reversedArgumentPatterns, PatternKeyPart { position: payload.childIndex, kind: partKind, constructor: partConstructor, payloadArity: partArity, nestedParts: pattern_key_nested_parts(nodes, payload) })
                    if payload.kind == "constructor_pattern" {
                      let expectedType = variant_payload_type(nodes, pattern.node.text, payload.childIndex)
                      let nested = validate_nested_pattern(nodes, payload, expectedType)
                      if !nested.valid {
                        coversVariant = false
                        duplicatePatternEligible = false
                        invalidPattern = true
                        let message = if nested.code == "PEP_PATTERN_ARITY" { "Nested constructor pattern payload count does not match its variant" } else { if nested.code == "PEP_PATTERN_TYPE_MISMATCH" { "Nested constructor pattern does not match its payload type" } else { if nested.code == "PEP_UNKNOWN_CONSTRUCTOR" { "Unknown constructor in nested pattern" } else { "Pattern form is outside the implemented checker subset" } } }
                        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(nested.code, message, nested.node))
                      } else {
                        if !nested.covers { coversVariant = false } else {}
                      }
                    } else {
                      if payload.kind != "binding_pattern" && payload.kind != "wildcard_pattern" {
                        coversVariant = false
                        duplicatePatternEligible = false
                        invalidPattern = true
                        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_PATTERN_UNSUPPORTED", "Pattern form is outside the implemented checker subset", payload))
                      } else {}
                    }
                  } else {}
                }
                if variant.found && expectedArity != patternArgumentCount {
                  coversVariant = false
                  duplicatePatternEligible = false
                  invalidPattern = true
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_PATTERN_ARITY", "Constructor pattern payload count does not match its variant", pattern.node))
                } else {}
                let currentPatternKey = ConstructorPatternKey { name: pattern.node.text, syntaxId: pattern.node.id, argumentCount: patternArgumentCount, argumentPatterns: reverse(reversedArgumentPatterns) }
                if union.found && patternUnion == subjectType && duplicatePatternEligible {
                  var samePattern = false
                  for previousPatternKey in seenConstructorPatterns {
                    if same_constructor_pattern_key(nodes, previousPatternKey, currentPatternKey) { samePattern = true } else {}
                  }
                  if samePattern {
                    invalidPattern = true
                    reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_MATCH_ARM", "Match constructor pattern is repeated", arm))
                  } else {
                    if contains(seenConstructors, pattern.node.text) {
                      invalidPattern = true
                      unreachable = true
                      reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNREACHABLE_MATCH_ARM", "Constructor pattern follows a fully covered variant", arm))
                    } else {
                      seenConstructorPatterns = prepend(seenConstructorPatterns, currentPatternKey)
                      if coversVariant { seenConstructors = prepend(seenConstructors, pattern.node.text) } else {}
                    }
                  }
                } else {}
              } else {}
              if pattern.node.kind != "wildcard_pattern" && pattern.node.kind != "binding_pattern" && pattern.node.kind != "constructor_pattern" {
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_PATTERN_UNSUPPORTED", "Pattern form is outside the implemented checker subset", pattern.node))
              } else {}
            } else {}
            if result.found && !unreachable {
              let actualResult = infer_expression_type(nodes, result.node.id, functions, bindings, references)
              if resultType == "" && actualResult != "" { resultType = actualResult } else {}
              if expectedResultType != "" {
                if result.node.kind == "list" {
                  let expectedResultShape = legacy_type_shape(nodes, expectedResultType)
                  let listMismatch = if expectedResultShape.listDepth != 0 && !contextualMismatchReported { list_mismatch_node(nodes, result.node.id, expectedResultShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
                  if (actualResult != "" && actualResult != expectedResultType || listMismatch.found) && !contextualMismatchReported {
                    let mismatchNode = if listMismatch.found { listMismatch.node } else { result.node }
                    reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_MATCH_ARM_TYPE_MISMATCH", "Match arm result type does not match the other arms", mismatchNode))
                    contextualMismatchReported = true
                  } else {}
                } else {
                  if actualResult != "" && actualResult != expectedResultType && !contextualMismatchReported {
                    reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_MATCH_ARM_TYPE_MISMATCH", "Match arm result type does not match the other arms", result.node))
                    contextualMismatchReported = true
                  } else {}
                }
              } else {
                if resultType != "" && actualResult != "" && resultType != actualResult {
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_MATCH_ARM_TYPE_MISMATCH", "Match arm result type does not match the other arms", result.node))
                } else {}
              }
            } else {}
          } else {}
        }
        if union.found && !catchAll && !invalidPattern {
          for variant in nodes {
            if variant.parentId == union.node.id && variant.kind == "variant_declaration" && !contains(seenConstructors, variant.text) {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_NON_EXHAUSTIVE_MATCH", "Match does not cover every constructor", node))
            } else {}
          }
        } else {}
      } else {}
      if node.kind == "binary" {
        let left = child_at(nodes, node.id, "left", 0)
        let right = child_at(nodes, node.id, "right", 1)
        let leftType = if left.found { infer_expression_type(nodes, left.node.id, functions, bindings, references) } else { "" }
        let rightType = if right.found { infer_expression_type(nodes, right.node.id, functions, bindings, references) } else { "" }
        let expected = if node.text == "&&" || node.text == "||" { "Bool" } else { if node.text == "==" || node.text == "!=" { leftType } else { "Int" } }
        if (node.text == "==" || node.text == "!=") && leftType != "" && !equality_supported_type(leftType) && left.found {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_EQUALITY_UNSUPPORTED", "Equality is not defined for this value type", left.node))
        } else {}
        if expected != "" && leftType != "" && leftType != expected && left.found { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Binary operator operand has an incompatible type", left.node)) } else {}
        if expected != "" && rightType != "" && rightType != expected && right.found { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Binary operator operand has an incompatible type", right.node)) } else {}
      } else {}
      if node.kind == "unary" {
        let operand = child_at(nodes, node.id, "operand", 0)
        let expected = if node.text == "!" { "Bool" } else { "Int" }
        if operand.found && operand.node.kind != "hole" && infer_expression_type(nodes, operand.node.id, functions, bindings, references) != expected { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Unary operator operand has an incompatible type", operand.node)) } else {}
      } else {}
      if node.kind == "call" {
        let target = find_function(functions, node.text)
        if target.found {
          var index = 0
          var argumentMismatchFound = false
          for argument in nodes {
            if argument.parentId == node.id && argument.role == "argument" {
              if !argumentMismatchFound {
                let expected = function_parameter_type(nodes, target.function.syntaxId, index)
                let actualArgument = infer_expression_type(nodes, argument.id, functions, bindings, references)
                let needsExpectedShape = expected == "" || actualArgument == "" || argument.kind == "list"
                let expectedShape = if needsExpectedShape { function_parameter_shape(nodes, target.function.syntaxId, index) } else { empty_type_shape() }
                let needsStructuralCheck = expected == "" || actualArgument == ""
                let actualShape = if needsStructuralCheck { expression_type_shape(nodes, argument.id, functions, bindings, references) } else { empty_type_shape() }
                let shapeMismatch = needsStructuralCheck && expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
                let needsNestedListCheck = expectedShape.listDepth != 0 && (expected == "" || actualArgument == "" || expected != actualArgument || argument.kind == "list")
                let listMismatch = if needsNestedListCheck { list_mismatch_node(nodes, argument.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
                if expected != "" && actualArgument != "" && expected != actualArgument || shapeMismatch || listMismatch.found {
                  let mismatchNode = if listMismatch.found { listMismatch.node } else { argument }
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Function argument type does not match its parameter", mismatchNode))
                  argumentMismatchFound = true
                } else {}
              } else {}
              index = index + 1
            } else {}
          }
        } else {
          let requiredArity = fixed_builtin_arity(node.text)
          if requiredArity != -1 {
            if count_children(nodes, node.id, "argument") != requiredArity {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_ARGUMENT_COUNT", "Built-in call argument count does not match its signature", node))
            } else {}
            var index = 0
            for argument in nodes {
              if argument.parentId == node.id && argument.role == "argument" {
                let expected = fixed_builtin_parameter_type(node.text, index)
                if expected != "" {
                  let actualArgument = infer_expression_type(nodes, argument.id, functions, bindings, references)
                  if actualArgument != "" && expected != actualArgument {
                    reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_ARGUMENT_TYPE", "Built-in argument type does not match its signature", argument))
                  } else {}
                } else {}
                index = index + 1
              } else {}
            }
          if (node.text == "length" || node.text == "reverse" || node.text == "append" || node.text == "prepend" || node.text == "contains") && count_children(nodes, node.id, "argument") == requiredArity {
              let collection = child_at(nodes, node.id, "argument", 0)
              let collectionShape = if collection.found { expression_type_shape(nodes, collection.node.id, functions, bindings, references) } else { empty_type_shape() }
              let elementShape = without_one_list(collectionShape)
              let collectionType = if collection.found && collectionShape.listDepth == 0 { infer_expression_type(nodes, collection.node.id, functions, bindings, references) } else { "" }
              let elementType = if collectionShape.listDepth != 0 { legacy_type_name(elementShape) } else { "" }
              if elementType == "" && collectionShape.listDepth == 0 {
                let emptyCollection = collection.found && collection.node.kind == "list" && count_children(nodes, collection.node.id, "element") == 0
                if !emptyCollection {
                  let code = if collectionType == "" { "PEP_LIST_UNTYPED" } else { "PEP_LIST_EXPECTED" }
                  let atNode = if collection.found { collection.node } else { node }
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(code, "Built-in operation requires a list with a supported element type", atNode))
                } else {}
              } else {}
              if node.text == "append" || node.text == "prepend" || node.text == "contains" {
                let value = child_at(nodes, node.id, "argument", 1)
                if value.found && value.node.kind != "hole" {
                  let actualValue = infer_expression_type(nodes, value.node.id, functions, bindings, references)
                  let actualValueShape = expression_type_shape(nodes, value.node.id, functions, bindings, references)
                  let expectedElementShape = elementShape
                  let contextualExtraList = node.text == "append" && value.node.kind == "list" && actualValue == elementType && has_extra_list_depth(actualValueShape, expectedElementShape)
                  let structuralMismatch = expectedElementShape.kind != "" && actualValueShape.kind != "" && !same_type_shape(expectedElementShape, actualValueShape) && !contextualExtraList
                  if elementType != "" && actualValue != "" && actualValue != elementType || structuralMismatch {
                    let mismatch = if expectedElementShape.listDepth != 0 { list_mismatch_node(nodes, value.node.id, expectedElementShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
                    let mismatchNode = if mismatch.found { mismatch.node } else { value.node }
                    reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Expected list element type does not match", mismatchNode))
                  } else {}
                } else {}
                let elementShape = without_one_list(collectionShape)
                let elementName = legacy_type_name(elementShape)
                if node.text == "contains" && collectionShape.listDepth != 0 && !equality_supported_type(elementName) {
                  let atNode = if collection.found { collection.node } else { node }
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_MEMBERSHIP_UNSUPPORTED", "Membership is not defined for this list element type", atNode))
                } else {}
              } else {}
            } else {}
          } else {}
        }
      } else {}
      if node.kind == "call" && is_constructor(nodes, node.text) {
        let variant = variant_declaration(nodes, node.text)
        let expectedArity = if variant.found { count_children(nodes, variant.node.id, "field_type") } else { -1 }
        if expectedArity != count_children(nodes, node.id, "argument") {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_ARGUMENT_COUNT", "Constructor payload count does not match its declared variant", node))
        } else {}
        var payloadIndex = 0
        for argument in nodes {
          if argument.parentId == node.id && argument.role == "argument" {
            let expected = variant_payload_type(nodes, node.text, payloadIndex)
            let actual = infer_expression_type(nodes, argument.id, functions, bindings, references)
            let expectedShape = variant_payload_shape(nodes, node.text, payloadIndex)
            let actualShape = expression_type_shape(nodes, argument.id, functions, bindings, references)
            let shapeMismatch = expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
            let nestedMismatch = if argument.kind == "list" && expectedShape.listDepth != 0 { list_mismatch_node(nodes, argument.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
            if nestedMismatch.found {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Constructor payload type does not match its declaration", nestedMismatch.node))
            } else {
              if shapeMismatch || expected != "" && actual != "" && expected != actual {
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Constructor payload type does not match its declaration", argument))
              } else {}
            }
            payloadIndex = payloadIndex + 1
          } else {}
        }
      } else {}
      if node.kind == "if_expression" {
        let condition = child_at(nodes, node.id, "condition", 0)
        let thenValue = child_at(nodes, node.id, "then", 1)
        let elseValue = child_at(nodes, node.id, "else", 2)
        let expectedResult = contextual_expected_type(nodes, node, functions, bindings, references)
        let expectedShape = if expectedResult != "" { legacy_type_shape(nodes, expectedResult) } else { empty_type_shape() }
        if condition.found && condition.node.kind != "hole" && infer_expression_type(nodes, condition.node.id, functions, bindings, references) != "Bool" {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If condition must have type Bool", condition.node))
        } else {}
        if thenValue.found && elseValue.found {
          let thenType = infer_expression_type(nodes, thenValue.node.id, functions, bindings, references)
          let elseType = infer_expression_type(nodes, elseValue.node.id, functions, bindings, references)
          let needsStructuralCheck = thenType == "" || elseType == ""
          let thenShape = if needsStructuralCheck { expression_type_shape(nodes, thenValue.node.id, functions, bindings, references) } else { empty_type_shape() }
          let elseShape = if needsStructuralCheck { expression_type_shape(nodes, elseValue.node.id, functions, bindings, references) } else { empty_type_shape() }
          let structuralMismatch = needsStructuralCheck && thenShape.kind != "" && elseShape.kind != "" && !same_type_shape(thenShape, elseShape)
          if structuralMismatch {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If branch does not match the other branch type", elseValue.node))
          } else {}
          if expectedResult != "" {
            var mismatchReported = false
            let thenMismatch = if expectedShape.listDepth != 0 && thenValue.node.kind == "list" { list_mismatch_node(nodes, thenValue.node.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
            if thenMismatch.found {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If branch does not match its contextual result type", thenMismatch.node))
              mismatchReported = true
            } else {}
            if !mismatchReported && thenType != "" && thenType != expectedResult {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If branch does not match its contextual result type", thenValue.node))
              mismatchReported = true
            } else {}
            let elseMismatch = if !mismatchReported && expectedShape.listDepth != 0 && elseValue.node.kind == "list" { list_mismatch_node(nodes, elseValue.node.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
            if !mismatchReported && elseMismatch.found {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If branch does not match its contextual result type", elseMismatch.node))
              mismatchReported = true
            } else {}
            if !mismatchReported && elseType != "" && elseType != expectedResult {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If branch does not match its contextual result type", elseValue.node))
            } else {}
          } else {
            if thenType != "" && elseType != "" && thenType != elseType {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If branch does not match the other branch type", elseValue.node))
            } else {}
          }
        } else {}
      } else {}
    } else {}
    if node.kind == "if_statement" || node.kind == "while" {
      let condition = child_at(nodes, node.id, "condition", 0)
      if condition.found && condition.node.kind != "hole" && infer_expression_type(nodes, condition.node.id, functions, bindings, references) != "Bool" {
        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Control-flow condition must have type Bool", condition.node))
      } else {}
    } else {}
    if node.kind == "return" {
      let owner = if sequentialFunctionOwner {
        FunctionLookup { found: activeFunctionFound && activeFunction.startByte <= node.startByte && node.endByte <= activeFunction.endByte, function: activeFunction }
      } else { owner_function(nodes, node, functions) }
      let returned = child_at(nodes, node.id, "value", 0)
      if owner.found && returned.found {
        let actualReturn = infer_expression_type(nodes, returned.node.id, functions, bindings, references)
        let actualShape = expression_type_shape(nodes, returned.node.id, functions, bindings, references)
        let expectedShape = if owner.function.returnShape.kind != "" { owner.function.returnShape } else { legacy_type_shape(nodes, owner.function.returnType) }
        let shapeMismatch = expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
        let listMismatch = if expectedShape.listDepth != 0 { list_mismatch_node(nodes, returned.node.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
        let conditionalMismatchHandled = if returned.node.kind == "if_expression" { if_expression_branch_mismatch(nodes, returned.node.id, owner.function.returnType, expectedShape, functions, bindings, references) } else { false }
        if (owner.function.returnType != "" && actualReturn != "" && owner.function.returnType != actualReturn || shapeMismatch || listMismatch.found) && !conditionalMismatchHandled {
          let code = "PEP_TYPE_MISMATCH"
          let mismatchNode = if listMismatch.found { listMismatch.node } else { returned.node }
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(code, "Return expression type does not match the function result type", mismatchNode))
        } else {}
      } else {}
    } else {}
    if (node.kind == "let" || node.kind == "var") {
      let annotation = child_at(nodes, node.id, "annotation", 0)
      let value = child_at(nodes, node.id, "value", 0)
      if annotation.found && value.found {
        let expected = type_name_at(nodes, annotation.node.id)
        let expectedShape = type_shape_at(nodes, annotation.node.id)
        let actualInitializer = infer_expression_type(nodes, value.node.id, functions, bindings, references)
        let actualShape = expression_type_shape(nodes, value.node.id, functions, bindings, references)
        let shapeMismatch = expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
        let listMismatch = if expectedShape.listDepth != 0 { list_mismatch_node(nodes, value.node.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
        if expected == "" || actualInitializer == "" || listMismatch.found {
          if shapeMismatch || listMismatch.found {
            let mismatchNode = if listMismatch.found { listMismatch.node } else { value.node }
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Initialiser type does not match the declared binding type", mismatchNode))
          } else {}
        } else {
          if expected != actualInitializer {
            let expectedElement = list_element_type(expected)
            let actualElement = list_element_type(actualInitializer)
            if value.node.kind == "list" && expectedElement != "" {
              for element in nodes {
                if element.parentId == value.node.id && element.role == "element" && element.kind != "hole" {
                  let actual = infer_expression_type(nodes, element.id, functions, bindings, references)
                  if actual != "" && actual != expectedElement {
                    reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "List element type does not match the annotation", element))
                  } else {}
                } else {}
              }
            } else {
              let code = "PEP_TYPE_MISMATCH"
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(code, "Initialiser type does not match the declared binding type", value.node))
            }
          } else {}
        }
      } else {}
    } else {}
  }
  let orderedDiagnostics = reverse(reversedDiagnostics)
  var selectedMismatch: CheckDiagnostic = CheckDiagnostic { code: "", message: "", syntaxId: -1, startByte: 0, endByte: 0 }
  var firstMismatchFound = false
  for candidate in orderedDiagnostics {
    if candidate.code == "PEP_TYPE_MISMATCH" || candidate.code == "PEP_MATCH_ARM_TYPE_MISMATCH" {
      var hasMoreSpecificMismatch = false
      for other in orderedDiagnostics {
        if (other.code == "PEP_TYPE_MISMATCH" || other.code == "PEP_MATCH_ARM_TYPE_MISMATCH") && other.syntaxId != candidate.syntaxId && candidate.startByte <= other.startByte && other.endByte <= candidate.endByte && (candidate.startByte != other.startByte || other.endByte != candidate.endByte) {
          hasMoreSpecificMismatch = true
        } else {}
      }
      let earlierMismatch = candidate.startByte + 1 <= selectedMismatch.startByte || candidate.startByte == selectedMismatch.startByte && (candidate.endByte + 1 <= selectedMismatch.endByte || candidate.endByte == selectedMismatch.endByte && candidate.code == "PEP_MATCH_ARM_TYPE_MISMATCH" && selectedMismatch.code != "PEP_MATCH_ARM_TYPE_MISMATCH")
      if !hasMoreSpecificMismatch && (!firstMismatchFound || earlierMismatch) {
        selectedMismatch = candidate
        firstMismatchFound = true
      } else {}
    } else {}
  }
  var selectedDiagnosticsReversed: List[CheckDiagnostic] = []
  for candidate in orderedDiagnostics {
    let isTypeMismatch = candidate.code == "PEP_TYPE_MISMATCH" || candidate.code == "PEP_MATCH_ARM_TYPE_MISMATCH"
    if !isTypeMismatch || firstMismatchFound && candidate.code == selectedMismatch.code && candidate.syntaxId == selectedMismatch.syntaxId && candidate.startByte == selectedMismatch.startByte && candidate.endByte == selectedMismatch.endByte {
      selectedDiagnosticsReversed = prepend(selectedDiagnosticsReversed, candidate)
    } else {}
  }
  return TypeAnalysis { expressionTypes: reverse(reversedFacts), diagnostics: reverse(selectedDiagnosticsReversed), unreachable: unreachable }
}
fn diagnostic(code: Str, message: Str, node: FlatAstNode) -> CheckDiagnostic {
  return CheckDiagnostic { code: code, message: message, syntaxId: node.id, startByte: node.startByte, endByte: node.endByte }
}
fn invalid_report(document: Str, revision: Str, count: Int, code: Str, message: Str, node: FlatAstNode) -> CheckerReport {
  return CheckerReport { document: document, revision: revision, status: "invalid", syntaxNodeCount: count, functions: [], bindings: [], references: [], calls: [], expressionTypes: [], holes: [], diagnostics: [diagnostic(code, message, node)] }
}
fn analyze() -> CheckerReport {
  let authority = semantic_snapshot()
  var cursor = parser_start()
  var nodesReversed: List[FlatAstNode] = []
  var complete = false
  var parseStatus = "continuing"
  var errorCode = ""
  var errorMessage = ""
  var errorNode = empty_node()
  var attempts = 0
  let sourceLength = byte_length(source_bytes())
  while !complete && attempts <= sourceLength + 1 {
    let chunk = parser_step(cursor)
    if chunk.document != authority.document || chunk.revision != authority.revision {
      return invalid_report(authority.document, authority.revision, 0, "A13_PARSER_REVISION", "Parser result changed the authorised target identity", empty_node())
    } else {}
    if !chunk.done && chunk.cursor.nextNodeId == cursor.nextNodeId && chunk.cursor.stream.lexCursor.offset == cursor.stream.lexCursor.offset && chunk.cursor.stream.lexCursor.stage == cursor.stream.lexCursor.stage && chunk.cursor.functionActive == cursor.functionActive && chunk.cursor.functionChildIndex == cursor.functionChildIndex && chunk.cursor.topLevelChildIndex == cursor.topLevelChildIndex && length(chunk.cursor.frames) == length(cursor.frames) && length(chunk.cursor.stream.bufferedTokens) == length(cursor.stream.bufferedTokens) && chunk.cursor.stream.lexCursor.line == cursor.stream.lexCursor.line && chunk.cursor.stream.lexCursor.column == cursor.stream.lexCursor.column {
      return invalid_report(authority.document, authority.revision, 0, "A13_PARSER_NO_PROGRESS", "Parser continuation did not advance", empty_node())
    } else {}
    for node in chunk.nodes { nodesReversed = prepend(nodesReversed, node) }
    cursor = chunk.cursor
    complete = chunk.done
    parseStatus = chunk.status
    errorCode = chunk.errorCode
    errorMessage = chunk.message
    errorNode = FlatAstNode { id: -1, parentId: -1, childIndex: -1, role: "", kind: "", text: "", integerValue: 0, booleanValue: false, stringParts: [], startByte: chunk.errorStart, endByte: chunk.errorEnd, line: chunk.errorLine, column: chunk.errorColumn }
    attempts = attempts + 1
  }
  if !complete { return invalid_report(authority.document, authority.revision, 0, "A13_PARSER_BUDGET", "Parser continuation did not finish within the source-bounded call envelope", empty_node()) } else {}
  if parseStatus != "complete" { return invalid_report(authority.document, authority.revision, 0, errorCode, errorMessage, errorNode) } else {}
  let parsed = ParserProgress { document: authority.document, revision: authority.revision, status: parseStatus, nodes: reverse(nodesReversed), done: complete, errorCode: errorCode, message: errorMessage, errorStart: errorNode.startByte, errorEnd: errorNode.endByte, errorLine: errorNode.line, errorColumn: errorNode.column }
  return analyze_parsed(parsed)
}
fn is_first_function_declaration(functions: List[CheckedFunction], name: Str, syntaxId: Int) -> Bool {
  var earlierMatches = 0
  for prior in functions {
    if prior.name == name && prior.syntaxId + 1 <= syntaxId { earlierMatches = earlierMatches + 1 } else {}
  }
  return earlierMatches == 0
}
fn is_first_duplicate_function(functions: List[CheckedFunction], name: Str, syntaxId: Int) -> Bool {
  var earlierMatches = 0
  for prior in functions {
    if prior.name == name && prior.syntaxId + 1 <= syntaxId { earlierMatches = earlierMatches + 1 } else {}
  }
  return earlierMatches == 1
}
fn analyze_parsed(parsed: ParserProgress) -> CheckerReport {
  let authority = semantic_snapshot()
  if parsed.document != authority.document || parsed.revision != authority.revision {
    return invalid_report(authority.document, authority.revision, 0, "A13_PARSER_REVISION", "Parser result changed the authorised target identity", empty_node())
  } else {}
  if !parsed.done { return invalid_report(authority.document, authority.revision, 0, "A13_PARSER_BUDGET", "Parser continuation did not finish within the source-bounded call envelope", empty_node()) } else {}
  if parsed.status != "complete" {
    let errorNode = FlatAstNode { id: -1, parentId: -1, childIndex: -1, role: "", kind: "", text: "", integerValue: 0, booleanValue: false, stringParts: [], startByte: parsed.errorStart, endByte: parsed.errorEnd, line: parsed.errorLine, column: parsed.errorColumn }
    return invalid_report(authority.document, authority.revision, 0, parsed.errorCode, parsed.message, errorNode)
  } else {}
  let sourceLength = byte_length(source_bytes())
  let nodes = sort_nodes(parsed.nodes)
  if !tree_is_valid(nodes, sourceLength) { return invalid_report(authority.document, authority.revision, length(nodes), "A13_INVALID_SYNTAX_TREE", "Completed parser output failed node identity, parent, child-order, or source-span validation", empty_node()) } else {}
  let functions = collect_functions(nodes)
  let bindingResult = collect_bindings(nodes, functions)
  let nameResult = resolve_names(nodes, functions, bindingResult.bindings)
  let typedBindings = infer_binding_types(nodes, functions, bindingResult.bindings, nameResult.references)
  let typeResult = type_analysis(nodes, functions, typedBindings, nameResult.references)
  let holes = hole_facts(nodes, functions, typedBindings, nameResult.references)
  var reversedCalls: List[ResolvedCall] = []
  var reversedDiagnostics: List[CheckDiagnostic] = []
  for item in bindingResult.diagnostics { reversedDiagnostics = prepend(reversedDiagnostics, item) }
  for item in nameResult.diagnostics { reversedDiagnostics = prepend(reversedDiagnostics, item) }
  for item in typeResult.diagnostics { reversedDiagnostics = prepend(reversedDiagnostics, item) }
  if length(functions) <= 1 {
    for function in functions {
      for node in nodes {
        if node.kind == "call" && inside_function(node, function) {
          let target = find_function(functions, node.text)
          if target.found {
            if count_children(nodes, node.id, "argument") == target.function.arity {
              reversedCalls = prepend(reversedCalls, ResolvedCall { callerId: function.semanticId, calleeId: target.function.semanticId, syntaxId: node.id, startByte: node.startByte, endByte: node.endByte })
            } else { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_ARGUMENT_COUNT", "Function call argument count does not match the resolved declaration", node)) }
          } else { if is_constructor(nodes, node.text) || known_builtin(node.text) { } else {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNKNOWN_FUNCTION", "No function or declared constructor has this name", node))
          } }
        } else {}
      }
    }
  } else {
    var currentCallerId = -1
    var currentCallerSyntaxId = -1
    var currentCallerStartByte = -1
    var currentCallerEndByte = -1
    var nextCallerId = 100000
    for node in nodes {
      if node.parentId == -1 && node.kind == "function" {
        currentCallerId = nextCallerId
        currentCallerSyntaxId = node.id
        currentCallerStartByte = node.startByte
        currentCallerEndByte = node.endByte
        nextCallerId = nextCallerId + 1
      } else {}
      if node.kind == "call" && currentCallerId != -1 && node.id != currentCallerSyntaxId && currentCallerStartByte <= node.startByte && node.endByte <= currentCallerEndByte {
        let target = find_function(functions, node.text)
        if target.found {
          if count_children(nodes, node.id, "argument") == target.function.arity {
            reversedCalls = prepend(reversedCalls, ResolvedCall { callerId: currentCallerId, calleeId: target.function.semanticId, syntaxId: node.id, startByte: node.startByte, endByte: node.endByte })
          } else { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_ARGUMENT_COUNT", "Function call argument count does not match the resolved declaration", node)) }
        } else { if is_constructor(nodes, node.text) || known_builtin(node.text) { } else {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNKNOWN_FUNCTION", "No function or declared constructor has this name", node))
        } }
      } else {}
    }
  }
  for function in functions {
    if is_first_duplicate_function(functions, function.name, function.syntaxId) && !known_builtin(function.name) && !is_constructor(nodes, function.name) {
      let declaration = lookup_node(nodes, function.syntaxId)
      if declaration.found { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_FUNCTION", "Function name is declared more than once", declaration.node)) } else {}
    } else {}
  }
  let calls = reverse(reversedCalls)
  let collectedDiagnostics = reverse(reversedDiagnostics)
  var diagnostics = collectedDiagnostics
  if typeResult.unreachable.found {
    var earlierFound = false
    var earlier = CheckDiagnostic { code: "", message: "", syntaxId: -1, startByte: 0, endByte: 0 }
    for candidate in collectedDiagnostics {
      if candidate.code != "PEP_MISSING_RETURN" && candidate.startByte + 1 <= typeResult.unreachable.node.startByte && (!earlierFound || candidate.startByte + 1 <= earlier.startByte) {
        earlierFound = true
        earlier = candidate
      } else {}
    }
    if earlierFound {
      diagnostics = [earlier]
    } else {
      diagnostics = [diagnostic("PEP_UNREACHABLE", "Statement follows an unconditional return", typeResult.unreachable.node)]
    }
  } else {
    if length(collectedDiagnostics) <= 1 {
    } else {
      var firstFound = false
      var unknownTypeFound = false
      var candidateCount = 0
      var first = CheckDiagnostic { code: "", message: "", syntaxId: -1, startByte: 0, endByte: 0 }
      var firstOrderByte = 0
      var unknownType = CheckDiagnostic { code: "", message: "", syntaxId: -1, startByte: 0, endByte: 0 }
      for candidate in collectedDiagnostics {
        let orderByte = diagnostic_order_byte(nodes, candidate)
        if candidate.code == "PEP_TYPE_MISMATCH" || candidate.code == "PEP_MATCH_ARM_TYPE_MISMATCH" ||
            candidate.code == "PEP_UNKNOWN_VARIABLE" || candidate.code == "PEP_UNKNOWN_FUNCTION" ||
            candidate.code == "PEP_ARGUMENT_COUNT" || candidate.code == "PEP_UNKNOWN_TYPE" {
          candidateCount = candidateCount + 1
        } else {}
        if candidate.code == "PEP_UNKNOWN_TYPE" {
          if !unknownTypeFound || candidate.startByte + 1 <= unknownType.startByte {
            unknownTypeFound = true
            unknownType = candidate
          } else {}
        } else {
          if candidate.code != "PEP_A13_TYPE_UNSUPPORTED" {
            if !firstFound || orderByte + 1 <= firstOrderByte ||
                (orderByte == firstOrderByte && candidate.startByte == first.startByte && candidate.endByte == first.endByte &&
                 candidate.code == "PEP_MATCH_ARM_TYPE_MISMATCH" && first.code == "PEP_TYPE_MISMATCH") {
              firstFound = true
              first = candidate
              firstOrderByte = orderByte
            } else {}
          } else {}
        }
      }
      if candidateCount == 0 {
      } else {
        if unknownTypeFound { diagnostics = [unknownType] } else { if firstFound { diagnostics = [first] } else {} }
      }
    }
  }
  let status = if length(diagnostics) != 0 { "invalid" } else { if length(holes) != 0 { "incomplete" } else { "valid" } }
  return CheckerReport { document: authority.document, revision: authority.revision, status: status, syntaxNodeCount: length(nodes), functions: functions, bindings: typedBindings, references: nameResult.references, calls: calls, expressionTypes: typeResult.expressionTypes, holes: holes, diagnostics: diagnostics }
}