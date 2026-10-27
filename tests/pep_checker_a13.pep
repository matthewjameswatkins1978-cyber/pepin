type CheckedFunction { semanticId: Int, syntaxId: Int, name: Str, arity: Int, returnType: Str, startByte: Int, endByte: Int }
type ResolvedCall { callerId: Int, calleeId: Int, syntaxId: Int, startByte: Int, endByte: Int }
type CheckDiagnostic { code: Str, message: Str, syntaxId: Int, startByte: Int, endByte: Int }
type BindingFact { semanticId: Int, syntaxId: Int, name: Str, ownerFunctionId: Int, scopeId: Int, visibleFrom: Int, mutable: Bool, typeName: Str }
type ResolvedName { syntaxId: Int, bindingId: Int, name: Str, startByte: Int, endByte: Int }
type ExpressionTypeFact { syntaxId: Int, typeName: Str, startByte: Int, endByte: Int }
type BindingCollection { bindings: List[BindingFact], diagnostics: List[CheckDiagnostic] }
type NameResolution { references: List[ResolvedName], diagnostics: List[CheckDiagnostic] }
type TypeAnalysis { expressionTypes: List[ExpressionTypeFact], diagnostics: List[CheckDiagnostic] }
type CheckerReport { document: Str, revision: Str, status: Str, syntaxNodeCount: Int, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName], calls: List[ResolvedCall], expressionTypes: List[ExpressionTypeFact], diagnostics: List[CheckDiagnostic] }
type NodeLookup { found: Bool, node: FlatAstNode }
type FunctionLookup { found: Bool, function: CheckedFunction }
type BindingLookup { found: Bool, binding: BindingFact }
type ReferenceLookup { found: Bool, reference: ResolvedName }

fn empty_node() -> FlatAstNode {
  return FlatAstNode { id: -1, parentId: -1, childIndex: -1, role: "", kind: "", text: "", integerValue: 0, booleanValue: false, stringParts: [], startByte: 0, endByte: 0, line: 1, column: 1 }
}
fn lookup_node(nodes: List[FlatAstNode], id: Int) -> NodeLookup {
  var answer = NodeLookup { found: false, node: empty_node() }
  for node in nodes { if node.id == id { answer = NodeLookup { found: true, node: node } } else {} }
  return answer
}
fn count_children(nodes: List[FlatAstNode], parent: Int, role: Str) -> Int {
  var count = 0
  for node in nodes { if node.parentId == parent && node.role == role { count = count + 1 } else {} }
  return count
}
fn child_at(nodes: List[FlatAstNode], parent: Int, role: Str, index: Int) -> NodeLookup {
  var answer = NodeLookup { found: false, node: empty_node() }
  for node in nodes {
    if node.parentId == parent && node.role == role && node.childIndex == index {
      answer = NodeLookup { found: true, node: node }
    } else {}
  }
  return answer
}
fn type_name_at(nodes: List[FlatAstNode], id: Int) -> Str {
  let found = lookup_node(nodes, id)
  if !found.found { return "" } else {}
  if found.node.kind == "type_scalar" || found.node.kind == "type_named" { return found.node.text } else {}
  if found.node.kind == "type_list" {
    let element = child_at(nodes, id, "element_type", 0)
    if element.found { return "" } else { return "" }
  } else {}
  return ""
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
fn sort_nodes(nodes: List[FlatAstNode]) -> List[FlatAstNode] {
  var sorted: List[FlatAstNode] = []
  for node in nodes { sorted = insert_sorted(sorted, node) }
  return sorted
}
fn known_builtin(name: Str) -> Bool {
  return name == "say" || name == "int_text" || name == "length" || name == "append" || name == "prepend" || name == "reverse" || name == "source_bytes" || name == "byte_length" || name == "byte_at" || name == "byte_slice" || name == "utf8_slice" || name == "contains"
}
fn is_constructor(nodes: List[FlatAstNode], name: Str) -> Bool {
  for node in nodes { if node.kind == "variant_declaration" && node.text == name { return true } else {} }
  return false
}
fn find_function(functions: List[CheckedFunction], name: Str) -> FunctionLookup {
  var answer = FunctionLookup { found: false, function: CheckedFunction { semanticId: -1, syntaxId: -1, name: "", arity: 0, returnType: "", startByte: 0, endByte: 0 } }
  for function in functions { if function.name == name { answer = FunctionLookup { found: true, function: function } } else {} }
  return answer
}
fn find_binding(bindings: List[BindingFact], semanticId: Int) -> BindingLookup {
  var answer = BindingLookup { found: false, binding: BindingFact { semanticId: -1, syntaxId: -1, name: "", ownerFunctionId: -1, scopeId: -1, visibleFrom: 0, mutable: false, typeName: "" } }
  for binding in bindings { if binding.semanticId == semanticId { answer = BindingLookup { found: true, binding: binding } } else {} }
  return answer
}
fn find_reference(references: List[ResolvedName], syntaxId: Int) -> ReferenceLookup {
  var answer = ReferenceLookup { found: false, reference: ResolvedName { syntaxId: -1, bindingId: -1, name: "", startByte: 0, endByte: 0 } }
  for reference in references { if reference.syntaxId == syntaxId { answer = ReferenceLookup { found: true, reference: reference } } else {} }
  return answer
}
fn inside_function(nodes: List[FlatAstNode], node: FlatAstNode, functionId: Int) -> Bool {
  var parentId = node.parentId
  var steps = 0
  var found = false
  while parentId != -1 && !found && steps <= length(nodes) {
    if parentId == functionId { found = true } else {
      let parent = lookup_node(nodes, parentId)
      if parent.found { parentId = parent.node.parentId } else { parentId = -1 }
    }
    steps = steps + 1
  }
  return found
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
fn collect_functions(nodes: List[FlatAstNode]) -> List[CheckedFunction] {
  var reversed: List[CheckedFunction] = []
  var ordinal = 0
  for node in nodes {
    if node.parentId == -1 && node.kind == "function" {
      reversed = prepend(reversed, CheckedFunction { semanticId: 100000 + ordinal, syntaxId: node.id, name: node.text, arity: count_children(nodes, node.id, "parameter"), returnType: declared_return_type(nodes, node.id), startByte: node.startByte, endByte: node.endByte })
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
fn collect_bindings(nodes: List[FlatAstNode], functions: List[CheckedFunction]) -> BindingCollection {
  var reversed: List[BindingFact] = []
  var reversedDiagnostics: List[CheckDiagnostic] = []
  var ordinal = 0
  for function in functions {
    for node in nodes {
      let parameter = node.kind == "parameter" && node.parentId == function.syntaxId
      let local = (node.kind == "let" || node.kind == "var" || node.kind == "for_in") && inside_function(nodes, node, function.syntaxId)
      if parameter || local {
        let scopes = scope_chain(nodes, node, function.syntaxId, function.semanticId)
        let scope = if parameter { function.semanticId } else { if node.kind == "for_in" { scope_key(node, "body") } else { first_scope(scopes, function.semanticId) } }
        let visible = if parameter { node.startByte } else { if node.kind == "for_in" { node.startByte } else { node.endByte } }
        var duplicate = false
        for prior in reversed { if prior.ownerFunctionId == function.semanticId && prior.scopeId == scope && prior.name == node.text { duplicate = true } else {} }
        let binding = BindingFact { semanticId: 2000000 + ordinal, syntaxId: node.id, name: node.text, ownerFunctionId: function.semanticId, scopeId: scope, visibleFrom: visible, mutable: node.kind == "var", typeName: declared_binding_type(nodes, node) }
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
      if node.kind == "name" && inside_function(nodes, node, function.syntaxId) {
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
  var answer = FunctionLookup { found: false, function: CheckedFunction { semanticId: -1, syntaxId: -1, name: "", arity: 0, returnType: "", startByte: 0, endByte: 0 } }
  for function in functions { if inside_function(nodes, node, function.syntaxId) { answer = FunctionLookup { found: true, function: function } } else {} }
  return answer
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
    if node.text == "int_text" || node.text == "utf8_slice" { return "Str" } else {}
    if node.text == "say" { return "Unit" } else {}
    if node.text == "length" || node.text == "byte_length" || node.text == "byte_at" { return "Int" } else {}
    if node.text == "byte_slice" { return "SourceBytes" } else {}
    if node.text == "contains" { return "Bool" } else {}
    if is_constructor(nodes, node.text) {
      for variant in nodes {
        if variant.kind == "variant_declaration" && variant.text == node.text {
          let owner = lookup_node(nodes, variant.parentId)
          if owner.found { return owner.node.text } else {}
        } else {}
      }
    } else {}
    return ""
  } else {}
  if node.kind == "binary" {
    if node.text == "&&" || node.text == "||" || node.text == "==" || node.text == "!=" || node.text == "<" || node.text == "<=" || node.text == ">" || node.text == ">=" { return "Bool" } else {}
    return "Int"
  } else {}
  if node.kind == "unary" { if node.text == "!" { return "Bool" } else { return "Int" } } else {}
  if node.kind == "list" { return "" } else {}
  if node.kind == "if_expression" {
    let thenValue = child_at(nodes, node.id, "then", 1)
    if thenValue.found { return infer_expression_type(nodes, thenValue.node.id, functions, bindings, references) } else { return "" }
  } else {}
  if node.kind == "record" { return node.text } else {}
  return ""
}
fn infer_binding_types(nodes: List[FlatAstNode], functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> List[BindingFact] {
  var typed: List[BindingFact] = []
  for binding in bindings {
    var typeName = binding.typeName
    if typeName == "" {
      let declaration = lookup_node(nodes, binding.syntaxId)
      if declaration.found {
        let value = child_at(nodes, declaration.node.id, "value", 0)
        if value.found { typeName = infer_expression_type(nodes, value.node.id, functions, typed, references) } else {}
      } else {}
    } else {}
    typed = append(typed, BindingFact { semanticId: binding.semanticId, syntaxId: binding.syntaxId, name: binding.name, ownerFunctionId: binding.ownerFunctionId, scopeId: binding.scopeId, visibleFrom: binding.visibleFrom, mutable: binding.mutable, typeName: typeName })
  }
  return typed
}
fn supported_primitive_type(typeName: Str) -> Bool {
  return typeName == "Int" || typeName == "Bool" || typeName == "Str" || typeName == "Unit" || typeName == "SourceBytes"
}
fn type_analysis(nodes: List[FlatAstNode], functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName]) -> TypeAnalysis {
  var reversedFacts: List[ExpressionTypeFact] = []
  var reversedDiagnostics: List[CheckDiagnostic] = []
  for node in nodes {
    if node.kind == "function" {
      if !supported_primitive_type(declared_return_type(nodes, node.id)) {
        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "Function result type is outside the implemented primitive checker subset", node))
      } else {}
      for parameter in nodes {
        if parameter.parentId == node.id && parameter.kind == "parameter" && !supported_primitive_type(declared_binding_type(nodes, parameter)) {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "Parameter type is outside the implemented primitive checker subset", parameter))
        } else {}
      }
    } else {}
    if (node.kind == "let" || node.kind == "var") {
      let annotation = child_at(nodes, node.id, "annotation", 0)
      if annotation.found && !supported_primitive_type(type_name_at(nodes, annotation.node.id)) {
        reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "Binding annotation is outside the implemented primitive checker subset", node))
      } else {}
    } else {}
    if is_expression_kind(node.kind) {
      let actual = infer_expression_type(nodes, node.id, functions, bindings, references)
      if actual == "" {
        if node.kind == "call" {
          if known_builtin(node.text) { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "This built-in call has no type rule in the current checker slice", node)) } else {}
        } else {
          if node.kind != "name" { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_A13_TYPE_UNSUPPORTED", "This expression form has no type rule in the current checker slice", node)) } else {}
        }
      } else {
        reversedFacts = prepend(reversedFacts, ExpressionTypeFact { syntaxId: node.id, typeName: actual, startByte: node.startByte, endByte: node.endByte })
      }
      if node.kind == "binary" {
        let left = child_at(nodes, node.id, "left", 0)
        let right = child_at(nodes, node.id, "right", 1)
        let leftType = if left.found { infer_expression_type(nodes, left.node.id, functions, bindings, references) } else { "" }
        let rightType = if right.found { infer_expression_type(nodes, right.node.id, functions, bindings, references) } else { "" }
        let expected = if node.text == "&&" || node.text == "||" { "Bool" } else { if node.text == "==" || node.text == "!=" { leftType } else { "Int" } }
        if expected != "" && leftType != "" && leftType != expected && left.found { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Binary operator operand has an incompatible type", left.node)) } else {}
        if expected != "" && rightType != "" && rightType != expected && right.found { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Binary operator operand has an incompatible type", right.node)) } else {}
      } else {}
      if node.kind == "unary" {
        let operand = child_at(nodes, node.id, "operand", 0)
        let expected = if node.text == "!" { "Bool" } else { "Int" }
        if operand.found && infer_expression_type(nodes, operand.node.id, functions, bindings, references) != expected { reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "Unary operator operand has an incompatible type", operand.node)) } else {}
      } else {}
      if node.kind == "call" {
        let target = find_function(functions, node.text)
        if target.found {
          var index = 0
          for argument in nodes {
            if argument.parentId == node.id && argument.role == "argument" {
              let expected = function_parameter_type(nodes, target.function.syntaxId, index)
              let actualArgument = infer_expression_type(nodes, argument.id, functions, bindings, references)
              if expected != "" && actualArgument != "" && expected != actualArgument {
                reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_ARGUMENT_TYPE", "Function argument type does not match its parameter", argument))
              } else {}
              index = index + 1
            } else {}
          }
        } else {}
      } else {}
      if node.kind == "if_expression" {
        let condition = child_at(nodes, node.id, "condition", 0)
        let thenValue = child_at(nodes, node.id, "then", 1)
        let elseValue = child_at(nodes, node.id, "else", 2)
        if condition.found && infer_expression_type(nodes, condition.node.id, functions, bindings, references) != "Bool" {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If condition must have type Bool", condition.node))
        } else {}
        if thenValue.found && elseValue.found {
          let thenType = infer_expression_type(nodes, thenValue.node.id, functions, bindings, references)
          let elseType = infer_expression_type(nodes, elseValue.node.id, functions, bindings, references)
          if thenType != "" && elseType != "" && thenType != elseType {
            reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_TYPE_MISMATCH", "If branches must have the same type", node))
          } else {}
        } else {}
      } else {}
    } else {}
    if node.kind == "return" && inside_any_function(nodes, node, functions) {
      let owner = owner_function(nodes, node, functions)
      let returned = child_at(nodes, node.id, "value", 0)
      if owner.found && returned.found {
        let actualReturn = infer_expression_type(nodes, returned.node.id, functions, bindings, references)
        if owner.function.returnType != "" && actualReturn != "" && owner.function.returnType != actualReturn {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_RETURN_TYPE", "Return expression type does not match the function result type", returned.node))
        } else {}
      } else {}
    } else {}
    if (node.kind == "let" || node.kind == "var") {
      let annotation = child_at(nodes, node.id, "annotation", 0)
      let value = child_at(nodes, node.id, "value", 0)
      if annotation.found && value.found {
        let expected = type_name_at(nodes, annotation.node.id)
        let actualInitializer = infer_expression_type(nodes, value.node.id, functions, bindings, references)
        if expected != "" && actualInitializer != "" && expected != actualInitializer {
          reversedDiagnostics = prepend(reversedDiagnostics, diagnostic("PEP_BINDING_TYPE", "Initialiser type does not match the declared binding type", value.node))
        } else {}
      } else {}
    } else {}
  }
  return TypeAnalysis { expressionTypes: reverse(reversedFacts), diagnostics: reverse(reversedDiagnostics) }
}
fn diagnostic(code: Str, message: Str, node: FlatAstNode) -> CheckDiagnostic {
  return CheckDiagnostic { code: code, message: message, syntaxId: node.id, startByte: node.startByte, endByte: node.endByte }
}
fn invalid_report(document: Str, revision: Str, count: Int, code: Str, message: Str, node: FlatAstNode) -> CheckerReport {
  return CheckerReport { document: document, revision: revision, status: "invalid", syntaxNodeCount: count, functions: [], bindings: [], references: [], calls: [], expressionTypes: [], diagnostics: [diagnostic(code, message, node)] }
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
  let nodes = sort_nodes(reverse(nodesReversed))
  if !tree_is_valid(nodes, sourceLength) { return invalid_report(authority.document, authority.revision, length(nodes), "A13_INVALID_SYNTAX_TREE", "Completed parser output failed node identity, parent, child-order, or source-span validation", empty_node()) } else {}
  let functions = collect_functions(nodes)
  let bindingResult = collect_bindings(nodes, functions)
  let nameResult = resolve_names(nodes, functions, bindingResult.bindings)
  let typedBindings = infer_binding_types(nodes, functions, bindingResult.bindings, nameResult.references)
  let typeResult = type_analysis(nodes, functions, typedBindings, nameResult.references)
  var reversedCalls: List[ResolvedCall] = []
  var reversedDiagnostics: List[CheckDiagnostic] = []
  for item in bindingResult.diagnostics { reversedDiagnostics = prepend(reversedDiagnostics, item) }
  for item in nameResult.diagnostics { reversedDiagnostics = prepend(reversedDiagnostics, item) }
  for item in typeResult.diagnostics { reversedDiagnostics = prepend(reversedDiagnostics, item) }
  for function in functions {
    for node in nodes {
      if node.kind == "call" && inside_function(nodes, node, function.syntaxId) {
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
  return CheckerReport { document: authority.document, revision: authority.revision, status: if length(diagnostics) == 0 { "valid" } else { "invalid" }, syntaxNodeCount: length(nodes), functions: functions, bindings: typedBindings, references: nameResult.references, calls: calls, expressionTypes: typeResult.expressionTypes, diagnostics: diagnostics }
}