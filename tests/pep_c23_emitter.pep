type PepC23NodeLookup { found: Bool, node: FlatAstNode }
type PepC23Emission { status: Str, sourceParts: List[Str], diagnostic: Str }

fn pep_c23_child(nodes: List[FlatAstNode], parentId: Int, role: Str, wantedIndex: Int) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == parentId && node.role == role && node.childIndex == wantedIndex {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_unsupported(message: Str) -> PepC23Emission {
  return PepC23Emission { status: "unsupported", sourceParts: [], diagnostic: message }
}

// Accept checked zero-argument Int functions with one returned non-negative integer or a call to a literal-returning function.
// Unsupported syntax and recursive calls are rejected before C is emitted.
fn pep_c23_function(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == -1 && node.kind == "function" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_expression(nodes: List[FlatAstNode], node: FlatAstNode) -> PepC23Emission {
  if node.kind == "integer" {
    return PepC23Emission { status: "emitted", sourceParts: [int_text(node.integerValue)], diagnostic: "" }
  } else {}
  if node.kind == "call" {
    let argument = pep_c23_child(nodes, node.id, "argument", 0)
    let target = pep_c23_function(nodes, node.text)
    if argument.found || !target.found {
      return pep_c23_unsupported("Pep C23 call lowering requires a known zero-argument Pep function")
    } else {}
    let parameter = pep_c23_child(nodes, target.node.id, "parameter", 0)
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    if parameter.found || !result.found || result.node.kind != "type_scalar" || result.node.text != "Int" {
      return pep_c23_unsupported("Pep C23 calls currently require zero-argument Int-returning functions")
    } else {}
    let targetStatement = pep_c23_child(nodes, target.node.id, "statement", 0)
    let targetValue = if targetStatement.found {
      pep_c23_child(nodes, targetStatement.node.id, "value", 0)
    } else { PepC23NodeLookup { found: false, node: empty_node() } }
    if !targetStatement.found || !targetValue.found || targetValue.node.kind != "integer" {
      return pep_c23_unsupported("Pep C23 calls currently require a literal-returning target; recursive calls are unsupported")
    } else {}
    return PepC23Emission { status: "emitted", sourceParts: ["pep_fn_", int_text(target.node.id), "()"], diagnostic: "" }
  } else {}
  return pep_c23_unsupported("Pep C23 expression lowering does not support this expression")
}
fn pep_c23_function_expression(nodes: List[FlatAstNode], function: FlatAstNode) -> PepC23Emission {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let result = pep_c23_child(nodes, function.id, "return_type", 0)
  let statement = pep_c23_child(nodes, function.id, "statement", 0)
  let second = pep_c23_child(nodes, function.id, "statement", 1)
  if parameter.found || !result.found || result.node.kind != "type_scalar" || result.node.text != "Int" ||
     !statement.found || second.found || statement.node.kind != "return" {
    return pep_c23_unsupported("Pep C23 functions require zero parameters, Int results, and one return statement")
  } else {}
  let value = pep_c23_child(nodes, statement.node.id, "value", 0)
  if !value.found { return pep_c23_unsupported("Pep C23 return statement has no value") } else {}
  return pep_c23_expression(nodes, value.node)
}
fn emit_c23() -> PepC23Emission {
  let parsed = parser_parse_program()
  if parsed.status != "complete" {
    return pep_c23_unsupported("Pep C23 emission requires a complete program")
  } else {}
  if analyze().status != "valid" {
    return pep_c23_unsupported("Pep C23 emission requires a valid Pep checker report")
  } else {}
  var mainFound = false
  var mainId = -1
  var functionCount = 0
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      functionCount = functionCount + 1
      if node.text == "main" { mainFound = true; mainId = node.id } else {}
    } else {}
  }
  if functionCount == 0 || !mainFound {
    return pep_c23_unsupported("Pep C23 emission requires a top-level function named main")
  } else {}
  let mainType = pep_c23_child(parsed.nodes, mainId, "return_type", 0)
  if !mainType.found || mainType.node.kind != "type_scalar" || mainType.node.text != "Int" {
    return pep_c23_unsupported("Pep C23 main function must return Int")
  } else {}
  var reversed: List[Str] = []
  reversed = prepend(reversed, "#include <stdio.h>\n")
  reversed = prepend(reversed, "#include <stdint.h>\n")
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      let lowered = pep_c23_function_expression(parsed.nodes, node)
      if lowered.status != "emitted" { return lowered } else {}
      reversed = prepend(reversed, "int64_t pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      reversed = prepend(reversed, "(void);\n")
    } else {}
  }
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      let lowered = pep_c23_function_expression(parsed.nodes, node)
      reversed = prepend(reversed, "int64_t pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      reversed = prepend(reversed, " (void) {\n")
      reversed = prepend(reversed, "  return ")
      for part in lowered.sourceParts { reversed = prepend(reversed, part) }
      reversed = prepend(reversed, ";\n")
      reversed = prepend(reversed, "}\n")
    } else {}
  }
  reversed = prepend(reversed, "int main(void) {\n")
  reversed = prepend(reversed, "  (void)printf(\"%lld\\n\", (long long)(pep_fn_")
  reversed = prepend(reversed, int_text(mainId))
  reversed = prepend(reversed, "()));\n")
  reversed = prepend(reversed, "  return 0;\n")
  reversed = prepend(reversed, "}\n")
  return PepC23Emission { status: "emitted", sourceParts: reverse(reversed), diagnostic: "" }
}
