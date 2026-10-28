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
fn pep_c23_list_literal(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "list" { return PepC23NodeLookup { found: true, node: value } } else {}
  if value.kind != "name" { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
  var matches = 0
  var list = PepC23NodeLookup { found: false, node: empty_node() }
  for binding in nodes {
    if binding.parentId == function.id && binding.role == "statement" && binding.kind == "let" && binding.text == value.text {
      matches = matches + 1
      let initial = pep_c23_child(nodes, binding.id, "value", 0)
      if initial.found && initial.node.kind == "list" { list = initial } else { return PepC23NodeLookup { found: false, node: empty_node() } }
    } else {}
  }
  if matches != 1 { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
  return list
}
fn pep_c23_unsupported(message: Str) -> PepC23Emission {
  return PepC23Emission { status: "unsupported", sourceParts: [], diagnostic: message }
}
fn pep_c23_c_scalar_type(node: FlatAstNode) -> Str {
  if node.kind != "type_scalar" { return "" } else {}
  if node.text == "Int" { return "int64_t" } else {}
  if node.text == "Bool" { return "_Bool" } else {}
  return ""
}

// Accept checked Int functions with zero, one or two Int parameters and pure arithmetic expressions.
// Checked C23 helpers preserve Pep overflow and division-by-zero errors; unsupported syntax fails closed.
fn pep_c23_function(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == -1 && node.kind == "function" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_last_statement(nodes: List[FlatAstNode], function: FlatAstNode) -> PepC23NodeLookup {
  var lastStatement = PepC23NodeLookup { found: false, node: empty_node() }
  for candidate in nodes {
    if candidate.parentId == function.id && candidate.role == "statement" {
      lastStatement = PepC23NodeLookup { found: true, node: candidate }
    } else {}
  }
  return lastStatement
}
fn pep_c23_expression_may_fail(nodes: List[FlatAstNode], node: FlatAstNode) -> Bool {
  if node.kind == "integer" || node.kind == "boolean" || node.kind == "name" { return false } else {}
  if node.kind == "call" { return true } else {}
  if node.kind == "unary" && node.text == "!" {
    let operand = pep_c23_child(nodes, node.id, "operand", 0)
    return !operand.found || pep_c23_expression_may_fail(nodes, operand.node)
  } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    if !left.found || !right.found { return true } else {}
    if node.text == "neg" {
      if right.node.kind == "integer" { return false } else { return true }
    } else {}
    if node.text == "==" || node.text == "!=" || node.text == "<" || node.text == "<=" || node.text == ">" || node.text == ">=" || node.text == "&&" || node.text == "||" {
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
fn pep_c23_parameter_expression(nodes: List[FlatAstNode], parameterName: Str, secondParameterName: Str, node: FlatAstNode) -> Bool {
  if node.kind == "integer" { return true } else {}
  if node.kind == "name" { return node.text == parameterName || node.text == secondParameterName } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    return left.found && right.found &&
      pep_c23_parameter_expression(nodes, parameterName, secondParameterName, left.node) &&
      pep_c23_parameter_expression(nodes, parameterName, secondParameterName, right.node)
  } else {}
  if node.kind == "unary" {
    let operand = pep_c23_child(nodes, node.id, "operand", 0)
    return operand.found && pep_c23_parameter_expression(nodes, parameterName, secondParameterName, operand.node)
  } else {}
  return false
}
fn pep_c23_expression(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> PepC23Emission {
  if node.kind == "integer" {
    return PepC23Emission { status: "emitted", sourceParts: [int_text(node.integerValue)], diagnostic: "" }
  } else {}
  if node.kind == "boolean" {
    let value = if node.booleanValue { "1" } else { "0" }
    return PepC23Emission { status: "emitted", sourceParts: [value], diagnostic: "" }
  } else {}
  if node.kind == "name" {
    var localFound = false
    var localId = -1
    for candidate in nodes {
      if candidate.parentId == function.id && candidate.role == "statement" && (candidate.kind == "let" || candidate.kind == "var") && candidate.text == node.text {
        localFound = true
        localId = candidate.id
      } else {}
    }
    if localFound { return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(localId)], diagnostic: "" } } else {}
    for candidate in nodes {
      if candidate.parentId == function.id && candidate.role == "statement" && candidate.kind == "for_in" && candidate.text == node.text {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(candidate.id)], diagnostic: "" }
      } else {}
    }
    let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
    let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
    if parameter.found && parameter.node.text == node.text {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(parameter.node.id)], diagnostic: "" }
    } else {}
    if secondParameter.found && secondParameter.node.text == node.text {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(secondParameter.node.id)], diagnostic: "" }
    } else {}
    return pep_c23_unsupported("Pep C23 name lowering requires a direct immutable local let or Int parameter")
  } else {}
  if node.kind == "call" {
    let argument = pep_c23_child(nodes, node.id, "argument", 0)
    let secondArgument = pep_c23_child(nodes, node.id, "argument", 1)
    let extraArgument = pep_c23_child(nodes, node.id, "argument", 2)
    let target = pep_c23_function(nodes, node.text)
    if node.text == "length" {
      if !argument.found || secondArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 length lowering requires one supported list value")
      } else {}
      let list = pep_c23_list_literal(nodes, function, argument.node)
      if !list.found { return pep_c23_unsupported("Pep C23 length lowering requires a direct integer list literal or immutable list binding") } else {}
      return PepC23Emission { status: "emitted", sourceParts: [int_text(count_children(nodes, list.node.id, "element"))], diagnostic: "" }
    } else {}
    if !target.found || extraArgument.found {
      return pep_c23_unsupported("Pep C23 calls require a known target and at most two arguments")
    } else {}
    let parameter = pep_c23_child(nodes, target.node.id, "parameter", 0)
    let secondParameter = pep_c23_child(nodes, target.node.id, "parameter", 1)
    let extraParameter = pep_c23_child(nodes, target.node.id, "parameter", 2)
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    if extraParameter.found || !result.found || pep_c23_c_scalar_type(result.node) == "" {
      return pep_c23_unsupported("Pep C23 calls require a known target with a supported scalar result")
    } else {}
    let targetStatement = pep_c23_last_statement(nodes, target.node)
    let targetValue = if targetStatement.found {
      pep_c23_child(nodes, targetStatement.node.id, "value", 0)
    } else { PepC23NodeLookup { found: false, node: empty_node() } }
    let conditionalTarget = targetStatement.found && targetStatement.node.kind == "if_statement"
    if !targetStatement.found || (targetStatement.node.kind != "return" && !conditionalTarget) || (!conditionalTarget && !targetValue.found) {
      return pep_c23_unsupported("Pep C23 calls require a direct-return or supported conditional-return target")
    } else {}
    if parameter.found {
      if secondParameter.found {
        if !argument.found || !secondArgument.found || (!conditionalTarget && !pep_c23_parameter_expression(nodes, parameter.node.text, secondParameter.node.text, targetValue.node)) {
          return pep_c23_unsupported("Pep C23 two-parameter calls require two arguments and a call-free result expression")
        } else {}
        if pep_c23_expression_may_fail(nodes, argument.node) && pep_c23_expression_may_fail(nodes, secondArgument.node) {
          return pep_c23_unsupported("Pep C23 rejects two fallible call arguments because C argument evaluation order is unspecified")
        } else {}
        let loweredArgument = pep_c23_expression(nodes, function, argument.node)
        let loweredSecondArgument = pep_c23_expression(nodes, function, secondArgument.node)
        if loweredArgument.status != "emitted" { return loweredArgument } else {}
        if loweredSecondArgument.status != "emitted" { return loweredSecondArgument } else {}
        var parts: List[Str] = ["pep_fn_", int_text(target.node.id), "("]
        for part in loweredArgument.sourceParts { parts = append(parts, part) }
        parts = append(parts, ", ")
        for part in loweredSecondArgument.sourceParts { parts = append(parts, part) }
        parts = append(parts, ")")
        return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
      } else {
        if !argument.found || secondArgument.found || (!conditionalTarget && !pep_c23_parameter_expression(nodes, parameter.node.text, "", targetValue.node)) {
          return pep_c23_unsupported("Pep C23 one-parameter calls require one argument and a call-free target expression")
        } else {}
        let loweredArgument = pep_c23_expression(nodes, function, argument.node)
        if loweredArgument.status != "emitted" { return loweredArgument } else {}
        var parts: List[Str] = ["pep_fn_", int_text(target.node.id), "("]
        for part in loweredArgument.sourceParts { parts = append(parts, part) }
        parts = append(parts, ")")
        return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
      }
    } else {
      if argument.found || secondArgument.found || (!conditionalTarget && !pep_c23_call_free_expression(nodes, targetValue.node)) {
        return pep_c23_unsupported("Pep C23 zero-argument calls require a call-free integer result; recursive calls are unsupported")
      } else {}
      return PepC23Emission { status: "emitted", sourceParts: ["pep_fn_", int_text(target.node.id), "()"], diagnostic: "" }
    }
  } else {}
  if node.kind == "if_expression" {
    let condition = pep_c23_child(nodes, node.id, "condition", 0)
    let thenValue = pep_c23_child(nodes, node.id, "then", 1)
    let elseValue = pep_c23_child(nodes, node.id, "else", 2)
    if !condition.found || !thenValue.found || !elseValue.found {
      return pep_c23_unsupported("Pep C23 conditional expression requires a condition and both branches")
    } else {}
    let loweredCondition = pep_c23_expression(nodes, function, condition.node)
    let loweredThen = pep_c23_expression(nodes, function, thenValue.node)
    let loweredElse = pep_c23_expression(nodes, function, elseValue.node)
    if loweredCondition.status != "emitted" { return loweredCondition } else {}
    if loweredThen.status != "emitted" { return loweredThen } else {}
    if loweredElse.status != "emitted" { return loweredElse } else {}
    var parts: List[Str] = ["("]
    for part in loweredCondition.sourceParts { parts = append(parts, part) }
    parts = append(parts, " ? ")
    for part in loweredThen.sourceParts { parts = append(parts, part) }
    parts = append(parts, " : ")
    for part in loweredElse.sourceParts { parts = append(parts, part) }
    parts = append(parts, ")")
    return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
  } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    if !left.found || !right.found {
      return pep_c23_unsupported("Pep C23 binary expression is missing an operand")
    } else {}
    if node.text != "&&" && node.text != "||" && pep_c23_expression_may_fail(nodes, left.node) && pep_c23_expression_may_fail(nodes, right.node) {
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
    if node.text == "==" || node.text == "!=" || node.text == "<" || node.text == "<=" || node.text == ">" || node.text == ">=" || node.text == "&&" || node.text == "||" {
      var parts: List[Str] = ["("]
      for part in loweredLeft.sourceParts { parts = append(parts, part) }
      parts = append(parts, " ")
      parts = append(parts, node.text)
      parts = append(parts, " ")
      for part in loweredRight.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
    return pep_c23_unsupported("Pep C23 binary operator is unsupported")
  } else {}
  if node.kind == "unary" && node.text == "!" {
    let operand = pep_c23_child(nodes, node.id, "operand", 0)
    if !operand.found { return pep_c23_unsupported("Pep C23 unary expression has no operand") } else {}
    let lowered = pep_c23_expression(nodes, function, operand.node)
    if lowered.status != "emitted" { return lowered } else {}
    var parts: List[Str] = ["(!"]
    for part in lowered.sourceParts { parts = append(parts, part) }
    parts = append(parts, ")")
    return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
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
fn pep_c23_if_return_body(nodes: List[FlatAstNode], function: FlatAstNode) -> PepC23Emission {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
  let extraParameter = pep_c23_child(nodes, function.id, "parameter", 2)
  let parameterType = if parameter.found { pep_c23_child(nodes, parameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let secondParameterType = if secondParameter.found { pep_c23_child(nodes, secondParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let result = pep_c23_child(nodes, function.id, "return_type", 0)
  if extraParameter.found || (secondParameter.found && !parameter.found) || (function.text == "main" && (parameter.found || secondParameter.found)) || (parameter.found && (!parameterType.found || parameterType.node.kind != "type_scalar" || (parameterType.node.text != "Int" && parameterType.node.text != "Bool"))) || (secondParameter.found && (!secondParameterType.found || secondParameterType.node.kind != "type_scalar" || (secondParameterType.node.text != "Int" && secondParameterType.node.text != "Bool"))) || !result.found || result.node.kind != "type_scalar" || (result.node.text != "Int" && result.node.text != "Bool") || (function.text == "main" && result.node.text != "Int") {
    return pep_c23_unsupported("Pep C23 conditional-return functions require supported scalar parameters and results")
  } else {}
  var statementCount = 0
  var conditionalCount = 0
  var prefixValid = true
  var lastStatement = PepC23NodeLookup { found: false, node: empty_node() }
  for candidate in nodes {
    if candidate.parentId == function.id && candidate.role == "statement" {
      statementCount = statementCount + 1
      lastStatement = PepC23NodeLookup { found: true, node: candidate }
      if candidate.kind == "if_statement" { conditionalCount = conditionalCount + 1 } else {
        if candidate.kind != "let" { prefixValid = false } else {}
      }
    } else {}
  }
  if statementCount == 0 || conditionalCount != 1 || !lastStatement.found || lastStatement.node.kind != "if_statement" || !prefixValid {
    return pep_c23_unsupported("Pep C23 conditional-return lowering requires direct immutable lets followed by one final if statement")
  } else {}
  let statement = lastStatement
  let condition = pep_c23_child(nodes, statement.node.id, "condition", 0)
  if !condition.found || count_children(nodes, statement.node.id, "then") != 1 || count_children(nodes, statement.node.id, "else") != 1 {
    return pep_c23_unsupported("Pep C23 conditional return requires one condition and one statement in each branch")
  } else {}
  let thenReturn = pep_c23_child(nodes, statement.node.id, "then", 0)
  let elseReturn = pep_c23_child(nodes, statement.node.id, "else", 0)
  if !thenReturn.found || !elseReturn.found || thenReturn.node.kind != "return" || elseReturn.node.kind != "return" {
    return pep_c23_unsupported("Pep C23 conditional branches must each contain one direct return")
  } else {}
  let thenValue = pep_c23_child(nodes, thenReturn.node.id, "value", 0)
  let elseValue = pep_c23_child(nodes, elseReturn.node.id, "value", 0)
  if !thenValue.found || !elseValue.found {
    return pep_c23_unsupported("Pep C23 conditional return is missing a result expression")
  } else {}
  let loweredCondition = pep_c23_expression(nodes, function, condition.node)
  let loweredThen = pep_c23_expression(nodes, function, thenValue.node)
  let loweredElse = pep_c23_expression(nodes, function, elseValue.node)
  if loweredCondition.status != "emitted" { return loweredCondition } else {}
  if loweredThen.status != "emitted" { return loweredThen } else {}
  if loweredElse.status != "emitted" { return loweredElse } else {}
  var parts: List[Str] = ["if ("]
  for part in loweredCondition.sourceParts { parts = append(parts, part) }
  parts = append(parts, ") {\n  int64_t pep_result = ")
  for part in loweredThen.sourceParts { parts = append(parts, part) }
  parts = append(parts, ";\n  pep_leave();\n  return pep_result;\n} else {\n  int64_t pep_result = ")
  for part in loweredElse.sourceParts { parts = append(parts, part) }
  parts = append(parts, ";\n  pep_leave();\n  return pep_result;\n}\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}

fn pep_c23_function_expression(nodes: List[FlatAstNode], function: FlatAstNode) -> PepC23Emission {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
  let extraParameter = pep_c23_child(nodes, function.id, "parameter", 2)
  let parameterType = if parameter.found { pep_c23_child(nodes, parameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let secondParameterType = if secondParameter.found { pep_c23_child(nodes, secondParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let result = pep_c23_child(nodes, function.id, "return_type", 0)
  let parameterCType = if parameterType.found { pep_c23_c_scalar_type(parameterType.node) } else { "" }
  let secondParameterCType = if secondParameterType.found { pep_c23_c_scalar_type(secondParameterType.node) } else { "" }
  let resultCType = if result.found { pep_c23_c_scalar_type(result.node) } else { "" }
  if extraParameter.found || (secondParameter.found && !parameter.found) || (function.text == "main" && (parameter.found || secondParameter.found)) || (parameter.found && parameterCType == "") || (secondParameter.found && secondParameterCType == "") || resultCType == "" || (function.text == "main" && result.node.text != "Int") {
    return pep_c23_unsupported("Pep C23 functions require supported scalar parameters and results")
  } else {}
  var returned = false
  var statementCount = 0
  var returnStatement = PepC23NodeLookup { found: false, node: empty_node() }
  for statement in nodes {
    if statement.parentId == function.id && statement.role == "statement" {
      statementCount = statementCount + 1
      if (statement.kind == "let" || statement.kind == "var") && !returned {
        let initialValue = pep_c23_child(nodes, statement.id, "value", 0)
        if !initialValue.found { return pep_c23_unsupported("Pep C23 local binding has no value") } else {}
        if initialValue.node.kind == "list" && statement.kind == "let" {
          for item in nodes {
            if item.parentId == initialValue.node.id && item.role == "element" && item.kind != "integer" {
              return pep_c23_unsupported("Pep C23 immutable collection bindings currently require integer list literals")
            } else {}
          }
        } else {
          let initial = pep_c23_expression(nodes, function, initialValue.node)
          if initial.status != "emitted" { return initial } else {}
        }
      } else {
        if statement.kind == "for_in" && !returned {
          for local in nodes {
            if local.parentId == function.id && local.role == "statement" && local.id != statement.id && (local.kind == "let" || local.kind == "var" || local.kind == "for_in") && local.text == statement.text {
              return pep_c23_unsupported("Pep C23 for-in bindings cannot shadow function locals or other loop bindings")
            } else {}
          }
          let firstParameter = pep_c23_child(nodes, function.id, "parameter", 0)
          let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
          if (firstParameter.found && firstParameter.node.text == statement.text) || (secondParameter.found && secondParameter.node.text == statement.text) {
            return pep_c23_unsupported("Pep C23 for-in bindings cannot shadow function parameters")
          } else {}
          let iterable = pep_c23_child(nodes, statement.id, "iterable", 0)
          let iterableList = if iterable.found { pep_c23_list_literal(nodes, function, iterable.node) } else { PepC23NodeLookup { found: false, node: empty_node() } }
          if !iterable.found || !iterableList.found || count_children(nodes, iterableList.node.id, "element") == 0 || count_children(nodes, statement.id, "body") == 0 {
            return pep_c23_unsupported("Pep C23 for-in lowering requires a non-empty integer list literal or immutable list binding")
          } else {}
          for item in nodes {
            if item.parentId == iterableList.node.id && item.role == "element" && item.kind != "integer" {
              return pep_c23_unsupported("Pep C23 for-in list literals currently require integer elements")
            } else {}
          }
          for bodyStatement in nodes {
            if bodyStatement.parentId == statement.id && bodyStatement.role == "body" {
              if bodyStatement.kind != "assignment" { return pep_c23_unsupported("Pep C23 for-in bodies currently require assignments to mutable integer locals") } else {}
              var mutableTargetFound = false
              for local in nodes {
                if local.parentId == function.id && local.role == "statement" && local.kind == "var" && local.text == bodyStatement.text { mutableTargetFound = true } else {}
              }
              let assignedValue = pep_c23_child(nodes, bodyStatement.id, "value", 0)
              if !mutableTargetFound || !assignedValue.found { return pep_c23_unsupported("Pep C23 for-in assignments must target a direct mutable local") } else {}
              let assigned = pep_c23_expression(nodes, function, assignedValue.node)
              if assigned.status != "emitted" { return assigned } else {}
            } else {}
          }
        } else {
          if statement.kind == "return" && !returned {
            returned = true
            returnStatement = PepC23NodeLookup { found: true, node: statement }
          } else {
            return pep_c23_unsupported("Pep C23 functions require local bindings and supported loops followed by one return")
          }
        }
      }
    } else {}
  }
  if statementCount == 0 || !returned { return pep_c23_unsupported("Pep C23 functions require a return statement") } else {}
  let value = pep_c23_child(nodes, returnStatement.node.id, "value", 0)
  if !value.found { return pep_c23_unsupported("Pep C23 return statement has no value") } else {}
  return pep_c23_expression(nodes, function, value.node)
}
fn emit_c23() -> PepC23Emission {
  let parsed = parser_parse_program()
  if parsed.status != "complete" {
    return pep_c23_unsupported("Pep C23 emission requires a complete program")
  } else {}
  let checked = analyze_parsed(parsed)
  return emit_c23_checked(parsed, checked)
}
fn emit_c23_checked(parsed: ParserProgress, checked: CheckerReport) -> PepC23Emission {
  let authority = semantic_snapshot()
  if parsed.document != authority.document || parsed.revision != authority.revision ||
     checked.document != authority.document || checked.revision != authority.revision ||
     checked.syntaxNodeCount != length(parsed.nodes) {
    return pep_c23_unsupported("Pep C23 emission inputs do not match the authorised source revision")
  } else {}
  if parsed.status != "complete" || checked.status != "valid" {
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
  reversed = prepend(reversed, "#include <stddef.h>\n")
  reversed = prepend(reversed, "#include <stdio.h>\n")
  reversed = prepend(reversed, "#include <stdint.h>\n")
  reversed = prepend(reversed, "#include <stdlib.h>\n")
  reversed = prepend(reversed, "int64_t pep_add(int64_t a, int64_t b) {\n  if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a + b;\n}\nint64_t pep_sub(int64_t a, int64_t b) {\n  if ((b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a - b;\n}\nint64_t pep_mul(int64_t a, int64_t b) {\n  if (a > 0) { if ((b > 0 && a > INT64_MAX / b) || (b < 0 && b < INT64_MIN / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  else if (a < 0) { if ((b > 0 && a < INT64_MIN / b) || (b < 0 && b < INT64_MAX / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  return a * b;\n}\nint64_t pep_div(int64_t a, int64_t b) {\n  if (b == 0) { fputs(\"PEP_RUNTIME_DIVISION_BY_ZERO\\n\", stderr); exit(1); }\n  if (a == INT64_MIN && b == -1) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a / b;\n}\nint64_t pep_neg(int64_t a) {\n  if (a == INT64_MIN) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return -a;\n}\nstatic int pep_call_depth = 0;\nstatic void pep_enter(void) { if (pep_call_depth >= 512) { fputs(\"PEP_RUNTIME_CALL_DEPTH\\n\", stderr); exit(1); } pep_call_depth += 1; }\nstatic void pep_leave(void) { pep_call_depth -= 1; }\n")
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      let parameter = pep_c23_child(parsed.nodes, node.id, "parameter", 0)
      let secondParameter = pep_c23_child(parsed.nodes, node.id, "parameter", 1)
      let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
      reversed = prepend(reversed, pep_c23_c_scalar_type(result.node))
      reversed = prepend(reversed, " pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      if parameter.found {
        let parameterType = pep_c23_child(parsed.nodes, parameter.node.id, "type", 0)
        reversed = prepend(reversed, "(")
        reversed = prepend(reversed, pep_c23_c_scalar_type(parameterType.node))
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameter.node.id))
        if secondParameter.found {
          let secondParameterType = pep_c23_child(parsed.nodes, secondParameter.node.id, "type", 0)
          reversed = prepend(reversed, ", ")
          reversed = prepend(reversed, pep_c23_c_scalar_type(secondParameterType.node))
          reversed = prepend(reversed, " pep_arg_")
          reversed = prepend(reversed, int_text(secondParameter.node.id))
        } else {}
        reversed = prepend(reversed, ");\n")
      } else { reversed = prepend(reversed, "(void);\n") }
    } else {}
  }
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      let conditionalBody = pep_c23_if_return_body(parsed.nodes, node)
      let hasConditionalBody = conditionalBody.status == "emitted"
      let lowered = if hasConditionalBody { conditionalBody } else { pep_c23_function_expression(parsed.nodes, node) }
      if lowered.status != "emitted" { return lowered } else {}
      let parameter = pep_c23_child(parsed.nodes, node.id, "parameter", 0)
      let secondParameter = pep_c23_child(parsed.nodes, node.id, "parameter", 1)
      var bodyParts: List[Str] = ["  pep_enter();\n"]
      if parameter.found {
        bodyParts = append(bodyParts, "  (void)pep_arg_")
        bodyParts = append(bodyParts, int_text(parameter.node.id))
        bodyParts = append(bodyParts, ";\n")
      } else {}
      if secondParameter.found {
        bodyParts = append(bodyParts, "  (void)pep_arg_")
        bodyParts = append(bodyParts, int_text(secondParameter.node.id))
        bodyParts = append(bodyParts, ";\n")
      } else {}
      for statement in parsed.nodes {
        if statement.parentId == node.id && statement.role == "statement" && (statement.kind == "let" || statement.kind == "var") {
          let initialValue = pep_c23_child(parsed.nodes, statement.id, "value", 0)
          if !initialValue.found { return pep_c23_unsupported("Pep C23 local binding has no value") } else {}
          if initialValue.node.kind == "list" && statement.kind == "let" {
            // Immutable list literals are lowered at their direct length/for-in use sites.
          } else {
            let initial = pep_c23_expression(parsed.nodes, node, initialValue.node)
            for part in ["  int64_t pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
            for part in initial.sourceParts { bodyParts = append(bodyParts, part) }
            bodyParts = append(bodyParts, ";\n")
          }
        } else {
          if statement.parentId == node.id && statement.role == "statement" && statement.kind == "for_in" {
            let iterable = pep_c23_child(parsed.nodes, statement.id, "iterable", 0)
            let iterableList = if iterable.found { pep_c23_list_literal(parsed.nodes, node, iterable.node) } else { PepC23NodeLookup { found: false, node: empty_node() } }
            if !iterable.found || !iterableList.found { return pep_c23_unsupported("Pep C23 for-in lowering requires a list literal or immutable list binding") } else {}
            var elementCount = 0
            for element in parsed.nodes {
              if element.parentId == iterableList.node.id && element.role == "element" {
                if element.kind != "integer" { return pep_c23_unsupported("Pep C23 for-in list literals currently require integer elements") } else {}
                elementCount = elementCount + 1
              } else {}
            }
            if elementCount == 0 { return pep_c23_unsupported("Pep C23 for-in lowering requires a non-empty list literal") } else {}
            var arrayDeclaration: List[Str] = ["  int64_t pep_iter_", int_text(statement.id), "[] = {"]
            for element in parsed.nodes {
              if element.parentId == iterableList.node.id && element.role == "element" {
                arrayDeclaration = append(arrayDeclaration, int_text(element.integerValue))
                arrayDeclaration = append(arrayDeclaration, ", ")
              } else {}
            }
            arrayDeclaration = append(arrayDeclaration, "};\n  for (size_t pep_index_")
            arrayDeclaration = append(arrayDeclaration, int_text(statement.id))
            arrayDeclaration = append(arrayDeclaration, " = 0; pep_index_")
            arrayDeclaration = append(arrayDeclaration, int_text(statement.id))
            arrayDeclaration = append(arrayDeclaration, " < ")
            arrayDeclaration = append(arrayDeclaration, int_text(elementCount))
            arrayDeclaration = append(arrayDeclaration, "; ++pep_index_")
            arrayDeclaration = append(arrayDeclaration, int_text(statement.id))
            arrayDeclaration = append(arrayDeclaration, ") {\n    int64_t pep_local_")
            arrayDeclaration = append(arrayDeclaration, int_text(statement.id))
            arrayDeclaration = append(arrayDeclaration, " = pep_iter_")
            arrayDeclaration = append(arrayDeclaration, int_text(statement.id))
            arrayDeclaration = append(arrayDeclaration, "[pep_index_")
            arrayDeclaration = append(arrayDeclaration, int_text(statement.id))
            arrayDeclaration = append(arrayDeclaration, "];\n")
            for part in arrayDeclaration { bodyParts = append(bodyParts, part) }
            for loopStatement in parsed.nodes {
              if loopStatement.parentId == statement.id && loopStatement.role == "body" {
                if loopStatement.kind != "assignment" { return pep_c23_unsupported("Pep C23 for-in bodies currently require mutable local assignments") } else {}
                let assignedValue = pep_c23_child(parsed.nodes, loopStatement.id, "value", 0)
                if !assignedValue.found { return pep_c23_unsupported("Pep C23 assignment has no value") } else {}
                let assigned = pep_c23_expression(parsed.nodes, node, assignedValue.node)
                if assigned.status != "emitted" { return assigned } else {}
                var targetId = -1
                var targetFound = false
                for local in parsed.nodes {
                  if local.parentId == node.id && local.role == "statement" && local.kind == "var" && local.text == loopStatement.text {
                    targetId = local.id
                    targetFound = true
                  } else {}
                }
                if !targetFound { return pep_c23_unsupported("Pep C23 assignment target must be a direct mutable local") } else {}
                for part in ["    pep_local_", int_text(targetId), " = "] { bodyParts = append(bodyParts, part) }
                for part in assigned.sourceParts { bodyParts = append(bodyParts, part) }
                bodyParts = append(bodyParts, ";\n")
              } else {}
            }
            bodyParts = append(bodyParts, "  }\n")
          } else {}
        }
      }

      if hasConditionalBody {
        for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
      } else {
        bodyParts = append(bodyParts, "  int64_t pep_result = ")
        for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
        bodyParts = append(bodyParts, ";\n  pep_leave();\n  return pep_result;\n")
      }
      let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
      reversed = prepend(reversed, pep_c23_c_scalar_type(result.node))
      reversed = prepend(reversed, " pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      if parameter.found {
        let parameterType = pep_c23_child(parsed.nodes, parameter.node.id, "type", 0)
        reversed = prepend(reversed, "(")
        reversed = prepend(reversed, pep_c23_c_scalar_type(parameterType.node))
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameter.node.id))
        if secondParameter.found {
          let secondParameterType = pep_c23_child(parsed.nodes, secondParameter.node.id, "type", 0)
          reversed = prepend(reversed, ", ")
          reversed = prepend(reversed, pep_c23_c_scalar_type(secondParameterType.node))
          reversed = prepend(reversed, " pep_arg_")
          reversed = prepend(reversed, int_text(secondParameter.node.id))
        } else {}
        reversed = prepend(reversed, ") {\n")
      } else { reversed = prepend(reversed, " (void) {\n") }
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
