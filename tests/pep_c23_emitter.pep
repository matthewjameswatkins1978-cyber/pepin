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

// Accept checked zero-argument Int functions with pure integer literals, checked arithmetic and bounded calls.
// Checked C23 helpers preserve Pep overflow and division-by-zero errors; unsupported syntax fails closed.
fn pep_c23_function(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == -1 && node.kind == "function" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_expression_may_fail(nodes: List[FlatAstNode], node: FlatAstNode) -> Bool {
  if node.kind == "integer" { return false } else {}
  if node.kind == "call" { return true } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    if !left.found || !right.found { return true } else {}
    if node.text == "neg" {
      if right.node.kind == "integer" { return false } else { return true }
    } else {}
    if node.text == "<=" {
      return pep_c23_expression_may_fail(nodes, left.node) || pep_c23_expression_may_fail(nodes, right.node)
    } else {}
    return true
  } else {}
  return true
}
fn pep_c23_call_free_expression(nodes: List[FlatAstNode], node: FlatAstNode) -> Bool {
  if node.kind == "integer" { return true } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    return left.found && right.found &&
      pep_c23_call_free_expression(nodes, left.node) &&
      pep_c23_call_free_expression(nodes, right.node)
  } else {}
  if node.kind == "unary" {
    let operand = pep_c23_child(nodes, node.id, "operand", 0)
    return operand.found && pep_c23_call_free_expression(nodes, operand.node)
  } else {}
  return false
}
fn pep_c23_expression(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> PepC23Emission {
  if node.kind == "integer" {
    return PepC23Emission { status: "emitted", sourceParts: [int_text(node.integerValue)], diagnostic: "" }
  } else {}
  if node.kind == "name" {
    var localFound = false
    var localId = -1
    for candidate in nodes {
      if candidate.parentId == function.id && candidate.role == "statement" && candidate.kind == "let" && candidate.text == node.text {
        localFound = true
        localId = candidate.id
      } else {}
    }
    if !localFound { return pep_c23_unsupported("Pep C23 name lowering requires a direct immutable local let") } else {}
    return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(localId)], diagnostic: "" }
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
    if !targetStatement.found || targetStatement.node.kind != "return" || !targetValue.found ||
       !pep_c23_call_free_expression(nodes, targetValue.node) {
      return pep_c23_unsupported("Pep C23 calls require a zero-argument Int target with a call-free integer expression; recursive calls are unsupported")
    } else {}
    return PepC23Emission { status: "emitted", sourceParts: ["pep_fn_", int_text(target.node.id), "()"], diagnostic: "" }
  } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    if !left.found || !right.found {
      return pep_c23_unsupported("Pep C23 binary expression is missing an operand")
    } else {}
    if pep_c23_expression_may_fail(nodes, left.node) && pep_c23_expression_may_fail(nodes, right.node) {
      return pep_c23_unsupported("Pep C23 rejects two fallible operands because C operand evaluation order is unspecified")
    } else {}
    if node.text == "neg" {
      let lowered = pep_c23_expression(nodes, function, right.node)
      if lowered.status != "emitted" { return lowered } else {}
      var parts: List[Str] = ["pep_neg("]
      for part in lowered.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
    let loweredLeft = pep_c23_expression(nodes, function, left.node)
    let loweredRight = pep_c23_expression(nodes, function, right.node)
    if loweredLeft.status != "emitted" { return loweredLeft } else {}
    if loweredRight.status != "emitted" { return loweredRight } else {}
    let helper = if node.text == "+" { "pep_add" } else {
      if node.text == "-" { "pep_sub" } else {
        if node.text == "*" { "pep_mul" } else {
          if node.text == "/" { "pep_div" } else { "" }
        }
      }
    }
    if helper != "" {
      var parts: List[Str] = [helper, "("]
      for part in loweredLeft.sourceParts { parts = append(parts, part) }
      parts = append(parts, ", ")
      for part in loweredRight.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
    if node.text == "<=" {
      var parts: List[Str] = ["("]
      for part in loweredLeft.sourceParts { parts = append(parts, part) }
      parts = append(parts, " <= ")
      for part in loweredRight.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
    return pep_c23_unsupported("Pep C23 binary operator is unsupported")
  } else {}
  if node.kind == "unary" && node.text == "-" {
    let operand = pep_c23_child(nodes, node.id, "operand", 0)
    if !operand.found { return pep_c23_unsupported("Pep C23 unary expression has no operand") } else {}
    let lowered = pep_c23_expression(nodes, function, operand.node)
    if lowered.status != "emitted" { return lowered } else {}
    var parts: List[Str] = ["pep_neg("]
    for part in lowered.sourceParts { parts = append(parts, part) }
    parts = append(parts, ")")
    return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
  } else {}
  return pep_c23_unsupported("Pep C23 expression lowering does not support this expression")
}
fn pep_c23_function_expression(nodes: List[FlatAstNode], function: FlatAstNode) -> PepC23Emission {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let result = pep_c23_child(nodes, function.id, "return_type", 0)
  let statement = pep_c23_child(nodes, function.id, "statement", 0)
  let second = pep_c23_child(nodes, function.id, "statement", 1)
  let third = pep_c23_child(nodes, function.id, "statement", 2)
  let hasLocal = statement.found && statement.node.kind == "let"
  let returnStatement = if hasLocal { second } else { statement }
  if parameter.found || !result.found || result.node.kind != "type_scalar" || result.node.text != "Int" ||
     !statement.found || third.found || !returnStatement.found || returnStatement.node.kind != "return" ||
     (hasLocal && !second.found) {
    return pep_c23_unsupported("Pep C23 functions require zero parameters, Int results, and one return with an optional direct let")
  } else {}
  if hasLocal {
    let initialValue = pep_c23_child(nodes, statement.node.id, "value", 0)
    if !initialValue.found { return pep_c23_unsupported("Pep C23 local let has no value") } else {}
    let initial = pep_c23_expression(nodes, function, initialValue.node)
    if initial.status != "emitted" { return initial } else {}
  } else {}
  let value = pep_c23_child(nodes, returnStatement.node.id, "value", 0)
  if !value.found { return pep_c23_unsupported("Pep C23 return statement has no value") } else {}
  return pep_c23_expression(nodes, function, value.node)
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
  reversed = prepend(reversed, "#include <stdlib.h>\n")
  reversed = prepend(reversed, "int64_t pep_add(int64_t a, int64_t b) {\n  if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a + b;\n}\nint64_t pep_sub(int64_t a, int64_t b) {\n  if ((b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a - b;\n}\nint64_t pep_mul(int64_t a, int64_t b) {\n  if (a > 0) { if ((b > 0 && a > INT64_MAX / b) || (b < 0 && b < INT64_MIN / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  else if (a < 0) { if ((b > 0 && a < INT64_MIN / b) || (b < 0 && b < INT64_MAX / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  return a * b;\n}\nint64_t pep_div(int64_t a, int64_t b) {\n  if (b == 0) { fputs(\"PEP_RUNTIME_DIVISION_BY_ZERO\\n\", stderr); exit(1); }\n  if (a == INT64_MIN && b == -1) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a / b;\n}\nint64_t pep_neg(int64_t a) {\n  if (a == INT64_MIN) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return -a;\n}\n")
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
      if lowered.status != "emitted" { return lowered } else {}
      var bodyParts: List[Str] = []
      let statement = pep_c23_child(parsed.nodes, node.id, "statement", 0)
      if statement.found && statement.node.kind == "let" {
        let initialValue = pep_c23_child(parsed.nodes, statement.node.id, "value", 0)
        if !initialValue.found { return pep_c23_unsupported("Pep C23 local let has no value") } else {}
        let initial = pep_c23_expression(parsed.nodes, node, initialValue.node)
        for part in ["  int64_t pep_local_", int_text(statement.node.id), " = "] { bodyParts = append(bodyParts, part) }
        for part in initial.sourceParts { bodyParts = append(bodyParts, part) }
        bodyParts = append(bodyParts, ";\n")
      } else {}
      bodyParts = append(bodyParts, "  return ")
      for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
      bodyParts = append(bodyParts, ";\n")
      reversed = prepend(reversed, "int64_t pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      reversed = prepend(reversed, " (void) {\n")
      for part in bodyParts { reversed = prepend(reversed, part) }
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
