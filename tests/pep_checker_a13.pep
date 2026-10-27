type CheckedFunction { semanticId: Int, syntaxId: Int, name: Str, arity: Int, startByte: Int, endByte: Int }
type ResolvedCall { callerId: Int, calleeId: Int, syntaxId: Int, startByte: Int, endByte: Int }
type CheckDiagnostic { code: Str, message: Str, syntaxId: Int, startByte: Int, endByte: Int }
type BindingFact { semanticId: Int, syntaxId: Int, name: Str, ownerFunctionId: Int, scopeId: Int, visibleFrom: Int, mutable: Bool }
type ResolvedName { syntaxId: Int, bindingId: Int, name: Str, startByte: Int, endByte: Int }
type BindingCollection { bindings: List[BindingFact], diagnostics: List[CheckDiagnostic] }
type NameResolution { references: List[ResolvedName], diagnostics: List[CheckDiagnostic] }
type CheckerReport { document: Str, revision: Str, status: Str, syntaxNodeCount: Int, functions: List[CheckedFunction], bindings: List[BindingFact], references: List[ResolvedName], calls: List[ResolvedCall], diagnostics: List[CheckDiagnostic] }
type NodeLookup { found: Bool, node: FlatAstNode }
type FunctionLookup { found: Bool, function: CheckedFunction }

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
  var answer = FunctionLookup { found: false, function: CheckedFunction { semanticId: -1, syntaxId: -1, name: "", arity: 0, startByte: 0, endByte: 0 } }
  for function in functions { if function.name == name { answer = FunctionLookup { found: true, function: function } } else {} }
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
      var expectedChild = 0
      for earlier in nodes { if earlier.id + 1 <= node.id && earlier.parentId == node.parentId && earlier.role == node.role { expectedChild = expectedChild + 1 } else {} }
      if node.childIndex != expectedChild { valid = false } else {}
    }
    expectedId = expectedId + 1
  }
  return valid
}
fn collect_functions(nodes: List[FlatAstNode]) -> List[CheckedFunction] {
  var reversed: List[CheckedFunction] = []
  var ordinal = 0
  for node in nodes {
    if node.parentId == -1 && node.kind == "function" {
      reversed = prepend(reversed, CheckedFunction { semanticId: 100000 + ordinal, syntaxId: node.id, name: node.text, arity: count_children(nodes, node.id, "parameter"), startByte: node.startByte, endByte: node.endByte })
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
        let binding = BindingFact { semanticId: 2000000 + ordinal, syntaxId: node.id, name: node.text, ownerFunctionId: function.semanticId, scopeId: scope, visibleFrom: visible, mutable: node.kind == "var" }
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
fn diagnostic(code: Str, message: Str, node: FlatAstNode) -> CheckDiagnostic {
  return CheckDiagnostic { code: code, message: message, syntaxId: node.id, startByte: node.startByte, endByte: node.endByte }
}
fn invalid_report(document: Str, revision: Str, count: Int, code: Str, message: Str, node: FlatAstNode) -> CheckerReport {
  return CheckerReport { document: document, revision: revision, status: "invalid", syntaxNodeCount: count, functions: [], bindings: [], references: [], calls: [], diagnostics: [diagnostic(code, message, node)] }
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
  var reversedCalls: List[ResolvedCall] = []
  var reversedDiagnostics: List[CheckDiagnostic] = []
  for item in bindingResult.diagnostics { reversedDiagnostics = prepend(reversedDiagnostics, item) }
  for item in nameResult.diagnostics { reversedDiagnostics = prepend(reversedDiagnostics, item) }
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
  return CheckerReport { document: authority.document, revision: authority.revision, status: if length(diagnostics) == 0 { "valid" } else { "invalid" }, syntaxNodeCount: length(nodes), functions: functions, bindings: bindingResult.bindings, references: nameResult.references, calls: calls, diagnostics: diagnostics }
}