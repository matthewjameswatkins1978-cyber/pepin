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
type TypeAnalysis { expressionTypes: List[ExpressionTypeFact], diagnostics: List[CheckDiagnostic] }
type CheckerReport { document: Str, revision: Str, status: Str, syntaxNodeCount: Int, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName], calls: List[ResolvedCall], expressionTypes: List[ExpressionTypeFact], holes: List[HoleFact], diagnostics: List[CheckDiagnostic] }
type NodeLookup { found: Bool, node: FlatAstNode }
type FunctionLookup { found: Bool, function: CheckedFunction }
type BindingLookup { found: Bool, binding: BindingFact }
type ReferenceLookup { found: Bool, reference: ResolvedName }

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
  var pivotId = -1
  for node in nodes {
    if position == pivotIndex { pivotId = node.id } else {}
    position = position + 1
  }
  let pivot = lookup_node(nodes, pivotId)
  if !pivot.found { return nodes } else {}
  var less: List[FlatAstNode] = []
  var greater: List[FlatAstNode] = []
  for node in nodes {
    if node.id + 1 <= pivotId { less = prepend(less, node) } else {}
    if pivotId + 1 <= node.id { greater = prepend(greater, node) } else {}
  }
  let sortedLess = quick_sort_nodes(less)
  let sortedGreater = quick_sort_nodes(greater)
  var reversed: List[FlatAstNode] = []
  for node in sortedLess { reversed = prepend(reversed, node) }
  reversed = prepend(reversed, pivot.node)
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
fn tree_is_valid(nodes: List[FlatAstNode], sourceLength: Int) -> Bool {
  var expectedId = 0
  var nextRoot = 0
  var valid = true
  for node in nodes {
    if node.id != expectedId || node.startByte <= -1 || node.endByte <= node.startByte && node.endByte != node.startByte || sourceLength <= node.endByte && node.endByte != sourceLength || node.line <= 0 || node.column <= 0 { valid = false } else {}
    if node.parentId == -1 {
      if node.role != "top_level" || node.childIndex != nextRoot { valid = false } else {}
      nextRoot = nextRoot + 1
    } else {
      let parent = lookup_node(nodes, node.parentId)
      if !parent.found || node.id <= node.parentId || node.childIndex <= -1 { valid = false } else {}
      let fixedIndex = if parent.found { fixed_child_index(parent.node.kind, node.role) } else { -1 }
      if fixedIndex != -1 {
        if node.childIndex != fixedIndex { valid = false } else {}
      } else {
        var expectedChild = 0
        for earlier in nodes { if earlier.id + 1 <= node.id && earlier.parentId == node.parentId && earlier.role == node.role { expectedChild = expectedChild + 1 } else {} }
        if node.childIndex != expectedChild { valid = false } else {}
      }
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
      reversed = prepend(reversed, CheckedFunction { semanticId: 100000 + ordinal, syntaxId: node.id, name: node.text, arity: count_children(nodes, node.id, "parameter"), returnType: declared_return_type(nodes, node.id), returnShape: declared_return_shape(nodes, node.id), startByte: node.startByte, endByte: node.endByte })
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
  for function in functions {
    for node in nodes {
      if node.kind == "name" && inside_function(node, function) {
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
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNKNOWN_BINDING", "No visible local binding has this name", node))
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
fn infer_binding_types(nodes: List[FlatAstNode], functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> List[BindingFact] {
  var typed: List[BindingFact] = []
  for binding in bindings {
    var typeName = binding.typeName
    let declaration = lookup_node(nodes, binding.syntaxId)
    var typeShape = binding.typeShape
    if typeName == "" && declaration.found {
      if declaration.node.kind == "binding_pattern" {
        if typeShape.kind == "" { typeShape = pattern_binding_shape(nodes, declaration.node, functions, typed, references) } else {}
        if typeShape.kind != "" { typeName = legacy_type_name(typeShape) } else {
          typeName = pattern_binding_type(nodes, declaration.node, functions, typed, references)
        }
      } else {
        let value = child_at(nodes, declaration.node.id, "value", 0)
        if value.found { typeName = infer_expression_type(nodes, value.node.id, functions, typed, references) } else {}
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
fn named_type_declaration_count(nodes: List[FlatAstNode], name: Str) -> Int {
  var count = 0
  for node in nodes { if node.parentId == -1 && (node.kind == "record_declaration" || node.kind == "union_declaration") && node.text == name { count = count + 1 } else {} }
  return count
}
fn record_field_declaration_count(nodes: List[FlatAstNode], parentId: Int, name: Str) -> Int {
  var count = 0
  for node in nodes { if node.parentId == parentId && node.kind == "field_declaration" && node.text == name { count = count + 1 } else {} }
  return count
}
fn constructor_declaration_count(nodes: List[FlatAstNode], name: Str) -> Int {
  var count = 0
  for node in nodes { if node.kind == "variant_declaration" && node.text == name { count = count + 1 } else {} }
  return count
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
  var reversedDiagnostics: List[CheckDiagnostic] = []
  for node in nodes {
    if node.kind == "function" {
      let returnType = child_at(nodes, node.id, "return_type", 0)
      if !returnType.found || !supported_type_at(nodes, returnType.node.id, declared_return_type(nodes, node.id)) {
        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(unsupported_type_code(nodes, returnType.node.id, declared_return_type(nodes, node.id)), "Function result type is outside the implemented primitive checker subset", node))
      } else {}
      if known_builtin(node.text) || is_constructor(nodes, node.text) {
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
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_CONTROL_FLOW_UNSUPPORTED", "Non-Unit function return completeness is not established", node))
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
      if named_type_declaration_count(nodes, node.text) != 1 { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_TYPE", "Type name is declared more than once", node)) } else {}
      if supported_primitive_type(node.text) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_TYPE", "Type name is already reserved by a built-in type", node)) } else {}
      for field in nodes {
        if field.parentId == node.id && field.kind == "field_declaration" {
          if record_field_declaration_count(nodes, node.id, field.text) != 1 { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_FIELD", "Record field is declared more than once", field)) } else {}
          let fieldType = child_at(nodes, field.id, "type", 0)
          if fieldType.found && !supported_type_at(nodes, fieldType.node.id, type_name_at(nodes, fieldType.node.id)) {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(unsupported_type_code(nodes, fieldType.node.id, type_name_at(nodes, fieldType.node.id)), "Record field type is outside the implemented checker subset", field))
          } else {}
        } else {}
      }
    } else {}
    if node.kind == "union_declaration" {
      if named_type_declaration_count(nodes, node.text) != 1 { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_TYPE", "Type name is declared more than once", node)) } else {}
      if supported_primitive_type(node.text) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_TYPE", "Type name is already reserved by a built-in type", node)) } else {}
      for variant in nodes {
        if variant.parentId == node.id && variant.kind == "variant_declaration" {
          if constructor_declaration_count(nodes, variant.text) != 1 { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_CONSTRUCTOR", "Constructor name is declared more than once", variant)) } else {}
          for payload in nodes {
            if payload.parentId == variant.id && payload.role == "field_type" && !supported_type_at(nodes, payload.id, type_name_at(nodes, payload.id)) {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(unsupported_type_code(nodes, payload.id, type_name_at(nodes, payload.id)), "Union constructor payload type is outside the implemented checker subset", payload))
            } else {}
          }
        } else {}
      }
    } else {}
    if node.kind == "assignment" || node.kind == "for_in" {
      reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_CONTROL_FLOW_UNSUPPORTED", "Assignment and for-in semantics are outside the implemented checker subset", node))
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
          for field in nodes {
            if field.parentId == node.id && field.kind == "record_field" {
              let expected = record_field_type(nodes, node.text, field.text)
              let expectedShape = record_field_shape(nodes, node.text, field.text)
              let value = child_at(nodes, field.id, "value", 0)
              let actual = if value.found { infer_expression_type(nodes, value.node.id, functions, bindings, references) } else { "" }
              let actualShape = if value.found { expression_type_shape(nodes, value.node.id, functions, bindings, references) } else { empty_type_shape() }
              let shapeMismatch = expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
              let listMismatch = if expectedShape.listDepth != 0 { list_mismatch_node(nodes, value.node.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
              if expected == "" && expectedShape.kind == "" { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNKNOWN_FIELD", "Record literal names a field absent from its declaration", field)) } else {}
              if expected != "" && actual != "" && actual != expected { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Record field value type does not match its declaration", value.node)) } else {}
              if ((expected == "" || actual == "") && shapeMismatch) || (expected == actual && expectedShape.listDepth != 0 && expectedShape.listDepth != 1 && listMismatch.found) {
                let mismatch = listMismatch
                let mismatchNode = if mismatch.found { mismatch.node } else { value.node }
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Record field value type does not match its declaration", mismatchNode))
              } else {}
              var repeated = false
              for prior in nodes { if prior.parentId == node.id && prior.kind == "record_field" && prior.text == field.text && prior.id != field.id { repeated = true } else {} }
              if repeated { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_FIELD", "Record literal supplies a field more than once", field)) } else {}
            } else {}
          }
          for declared in nodes {
            if declared.parentId == declaration.node.id && declared.kind == "field_declaration" {
              var supplied = false
              for field in nodes { if field.parentId == node.id && field.kind == "record_field" && field.text == declared.text { supplied = true } else {} }
              if !supplied { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_MISSING_FIELD", "Record literal omits a declared field", node)) } else {}
            } else {}
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
        let expectedResultType = contextual_expected_type(nodes, node, functions, bindings, references)
        var resultType = ""
        var contextualMismatchReported = false
        for arm in nodes {
          if arm.parentId == node.id && arm.kind == "match_arm" {
            let pattern = child_at(nodes, arm.id, "pattern", 0)
            let result = child_at(nodes, arm.id, "result", 1)
            let unreachable = catchAll
            if unreachable {
              invalidPattern = true
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_UNREACHABLE_MATCH_ARM", "Match arm follows an irrefutable pattern", arm))
            } else {}
            if pattern.found && !unreachable {
              if pattern.node.kind == "wildcard_pattern" || pattern.node.kind == "binding_pattern" { catchAll = true } else {}
              if pattern.node.kind == "constructor_pattern" {
                let patternUnion = constructor_union_type(nodes, pattern.node.text)
                if union.found && (patternUnion == "" || patternUnion != subjectType) {
                  invalidPattern = true
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_PATTERN_TYPE_MISMATCH", "Constructor pattern does not belong to the match subject type", pattern.node))
                } else {}
                if union.found && patternUnion == subjectType {
                  if contains(seenConstructors, pattern.node.text) {
                    invalidPattern = true
                    reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_MATCH_ARM", "Match constructor pattern is repeated", pattern.node))
                  } else { seenConstructors = prepend(seenConstructors, pattern.node.text) }
                } else {}
                let variant = variant_declaration(nodes, pattern.node.text)
                let expectedArity = if variant.found { count_children(nodes, variant.node.id, "field_type") } else { -1 }
                if expectedArity != count_children(nodes, pattern.node.id, "argument") {
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_PATTERN_ARITY", "Constructor pattern payload count does not match its variant", pattern.node))
                } else {}
                for payload in nodes {
                  if payload.parentId == pattern.node.id && payload.role == "argument" && payload.kind != "binding_pattern" && payload.kind != "wildcard_pattern" {
                    reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_PATTERN_UNSUPPORTED", "Nested constructor patterns are outside the scalar-payload checker subset", payload))
                  } else {}
                }
              } else {}
              if pattern.node.kind != "wildcard_pattern" && pattern.node.kind != "binding_pattern" && pattern.node.kind != "constructor_pattern" {
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_PATTERN_UNSUPPORTED", "Pattern form is outside the implemented checker subset", pattern.node))
              } else {}
            } else {}
            if result.found && !unreachable {
              let actualResult = infer_expression_type(nodes, result.node.id, functions, bindings, references)
              if resultType == "" && actualResult != "" { resultType = actualResult } else {}
              if expectedResultType != "" {
                if actualResult != "" && actualResult != expectedResultType && !contextualMismatchReported {
                  reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_MATCH_ARM_TYPE_MISMATCH", "Match arm result type does not match the other arms", result.node))
                  contextualMismatchReported = true
                } else {}
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
          for argument in nodes {
            if argument.parentId == node.id && argument.role == "argument" {
              let expected = function_parameter_type(nodes, target.function.syntaxId, index)
              let expectedShape = function_parameter_shape(nodes, target.function.syntaxId, index)
              let actualArgument = infer_expression_type(nodes, argument.id, functions, bindings, references)
              let actualShape = expression_type_shape(nodes, argument.id, functions, bindings, references)
              let shapeMismatch = expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
              let listMismatch = if expectedShape.listDepth != 0 { list_mismatch_node(nodes, argument.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
              if expected != "" && actualArgument != "" && expected != actualArgument || shapeMismatch || listMismatch.found {
                let code = if expectedShape.listDepth != 0 && expectedShape.listDepth != 1 && listMismatch.found || expected == "" || actualArgument == "" { "PEP_TYPE_MISMATCH" } else { "PEP_ARGUMENT_TYPE" }
                let mismatchNode = if expectedShape.listDepth != 0 && expectedShape.listDepth != 1 && listMismatch.found { listMismatch.node } else { argument }
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(code, "Function argument type does not match its parameter", mismatchNode))
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
                  let structuralMismatch = expectedElementShape.kind != "" && actualValueShape.kind != "" && !same_type_shape(expectedElementShape, actualValueShape)
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
            if expected != "" && actual != "" && expected != actual {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Constructor payload type does not match its declaration", argument))
            } else {}
            payloadIndex = payloadIndex + 1
          } else {}
        }
      } else {}
      if node.kind == "if_expression" {
        let condition = child_at(nodes, node.id, "condition", 0)
        let thenValue = child_at(nodes, node.id, "then", 1)
        let elseValue = child_at(nodes, node.id, "else", 2)
        let expectedResult = contextual_expected_type(nodes, node, functions, bindings, references)
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
            if thenType != "" && thenType != expectedResult {
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If branch does not match its contextual result type", thenValue.node))
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
    if node.kind == "return" && inside_any_function(nodes, node, functions) {
      let owner = owner_function(nodes, node, functions)
      let returned = child_at(nodes, node.id, "value", 0)
      if owner.found && returned.found {
        let actualReturn = infer_expression_type(nodes, returned.node.id, functions, bindings, references)
        let actualShape = expression_type_shape(nodes, returned.node.id, functions, bindings, references)
        let expectedShape = if owner.function.returnShape.kind != "" { owner.function.returnShape } else { legacy_type_shape(nodes, owner.function.returnType) }
        let shapeMismatch = expectedShape.kind != "" && actualShape.kind != "" && !same_type_shape(expectedShape, actualShape)
        let listMismatch = if expectedShape.listDepth != 0 { list_mismatch_node(nodes, returned.node.id, expectedShape, functions, bindings, references) } else { NodeLookup { found: false, node: empty_node() } }
        let conditionalMismatchHandled = if returned.node.kind == "if_expression" { if_expression_branch_mismatch(nodes, returned.node.id, owner.function.returnType, expectedShape, functions, bindings, references) } else { false }
        if (owner.function.returnType != "" && actualReturn != "" && owner.function.returnType != actualReturn || shapeMismatch || listMismatch.found) && !conditionalMismatchHandled {
          let code = if (expectedShape.listDepth != 0 && expectedShape.listDepth != 1 && (listMismatch.found || shapeMismatch)) || (listMismatch.found && !shapeMismatch) || owner.function.returnType == "" || actualReturn == "" { "PEP_TYPE_MISMATCH" } else { "PEP_RETURN_TYPE" }
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
              let code = if expectedElement != "" && actualElement != "" { "PEP_TYPE_MISMATCH" } else { "PEP_BINDING_TYPE" }
              reversedDiagnostics = prepend(reversedDiagnostics, diagnostic(code, "Initialiser type does not match the declared binding type", value.node))
            }
          } else {}
        }
      } else {}
    } else {}
  }
  return TypeAnalysis { expressionTypes: reverse(reversedFacts), diagnostics: reverse(reversedDiagnostics) }
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
  var seenNames: List[Str] = []
  for function in functions {
    if contains(seenNames, function.name) {
      let declaration = lookup_node(nodes, function.syntaxId)
      if declaration.found { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_DUPLICATE_FUNCTION", "Function name is declared more than once", declaration.node)) } else {}
    } else { seenNames = prepend(seenNames, function.name) }
  }
  let calls = reverse(reversedCalls)
  let diagnostics = reverse(reversedDiagnostics)
  let status = if length(diagnostics) != 0 { "invalid" } else { if length(holes) != 0 { "incomplete" } else { "valid" } }
  return CheckerReport { document: authority.document, revision: authority.revision, status: status, syntaxNodeCount: length(nodes), functions: functions, bindings: typedBindings, references: nameResult.references, calls: calls, expressionTypes: typeResult.expressionTypes, holes: holes, diagnostics: diagnostics }
}