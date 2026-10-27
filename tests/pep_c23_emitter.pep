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

// This slice accepts one checked main returning a non-negative Int literal.
// Unsupported syntax is rejected until its lowering has matching evidence.
fn emit_c23() -> PepC23Emission {
  let parsed = parser_parse_program()
  if parsed.status != "complete" {
    return pep_c23_unsupported("Pep C23 emission requires a complete program")
  } else {}
  let checked = analyze()
  if checked.status != "valid" {
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
  if functionCount != 1 || !mainFound {
    return pep_c23_unsupported("Pep C23 emission currently requires exactly one function named main")
  } else {}
  let resultType = pep_c23_child(parsed.nodes, mainId, "return_type", 0)
  if !resultType.found || resultType.node.kind != "type_scalar" || resultType.node.text != "Int" {
    return pep_c23_unsupported("Pep C23 emission currently requires main to return Int")
  } else {}
  let statement = pep_c23_child(parsed.nodes, mainId, "statement", 0)
  if !statement.found || statement.node.kind != "return" {
    return pep_c23_unsupported("Pep C23 emission currently requires main to contain one return statement")
  } else {}
  let value = pep_c23_child(parsed.nodes, statement.node.id, "value", 0)
  if !value.found || value.node.kind != "integer" {
    return pep_c23_unsupported("Pep C23 emission currently supports non-negative integer literal returns only")
  } else {}
  let sourceParts: List[Str] = [
    "#include <stdio.h>\n",
    "int main(void) {\n",
    "  (void)printf(\"%lld\\n\", (long long)(",
    int_text(value.node.integerValue), "));\n", "  return 0;\n", "}\n"
  ]
  return PepC23Emission { status: "emitted", sourceParts: sourceParts, diagnostic: "" }
}
