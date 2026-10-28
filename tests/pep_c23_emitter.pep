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
    if binding.parentId == function.id && binding.role == "statement" && (binding.kind == "let" || binding.kind == "var") && binding.text == value.text {
      matches = matches + 1
      let initial = pep_c23_child(nodes, binding.id, "value", 0)
      if initial.found && initial.node.kind == "list" { list = initial } else { return PepC23NodeLookup { found: false, node: empty_node() } }
    } else {}
  }
  if matches != 1 { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
  return list
}
fn pep_c23_mutable_list_binding(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for binding in nodes {
    if binding.parentId == function.id && binding.role == "statement" && binding.kind == "var" && binding.text == name {
      let initial = pep_c23_child(nodes, binding.id, "value", 0)
      if initial.found && initial.node.kind == "list" {
        return PepC23NodeLookup { found: true, node: binding }
      } else {}
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_mutable_list_element_kind(nodes: List[FlatAstNode], binding: FlatAstNode) -> Str {
  let declared = pep_c23_child(nodes, binding.id, "annotation", 0)
  if declared.found && declared.node.kind == "type_list" {
    let elementType = pep_c23_child(nodes, declared.node.id, "element_type", 0)
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Int" { return "integer" } else {}
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Bool" { return "boolean" } else {}
  } else {}
  let initial = pep_c23_child(nodes, binding.id, "value", 0)
  let first = if initial.found { pep_c23_child(nodes, initial.node.id, "element", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  if first.found && (first.node.kind == "integer" || first.node.kind == "boolean") { return first.node.kind } else {}
  return ""
}
fn pep_c23_int_list_argument(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> PepC23Emission {
  if node.kind == "name" {
    let parameter = pep_c23_int_list_parameter(nodes, function, node.text)
    if parameter.found {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(parameter.node.id)], diagnostic: "" }
    } else {}
    let binding = pep_c23_mutable_list_binding(nodes, function, node.text)
    if binding.found {
      if pep_c23_mutable_list_element_kind(nodes, binding.node) != "integer" {
        return pep_c23_unsupported("Pep C23 List[Int] forwarding requires an Int list binding")
      } else {}
      return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(binding.node.id)], diagnostic: "" }
    } else {}
    return pep_c23_unsupported("Pep C23 List[Int] forwarding currently requires a direct List[Int] parameter or mutable Int list binding")
  } else {}
  if node.kind != "list" { return pep_c23_unsupported("Pep C23 List[Int] parameters currently require a direct integer list literal argument or direct parameter forwarding") } else {}
  var parts: List[Str] = ["(pep_list_int){ .data = "]
  let elementCount = count_children(nodes, node.id, "element")
  if elementCount == 0 {
    parts = append(parts, "NULL")
  } else {
    parts = append(parts, "(const int64_t[]){")
    var count = 0
    for element in nodes {
      if element.parentId == node.id && element.role == "element" {
        if element.kind != "integer" { return pep_c23_unsupported("Pep C23 List[Int] parameter arguments currently require integer elements") } else {}
        if count != 0 { parts = append(parts, ", ") } else {}
        parts = append(parts, int_text(element.integerValue))
        count = count + 1
      } else {}
    }
    parts = append(parts, "}")
  }
  parts = append(parts, ", .length = ")
  parts = append(parts, int_text(elementCount))
  parts = append(parts, " }")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_int_list_parameter(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
  if parameter.found && parameter.node.text == name {
    let parameterType = pep_c23_child(nodes, parameter.node.id, "type", 0)
    if parameterType.found && pep_c23_c_parameter_type(nodes, parameterType.node) == "pep_list_int" {
      return parameter
    } else {}
  } else {}
  if secondParameter.found && secondParameter.node.text == name {
    let parameterType = pep_c23_child(nodes, secondParameter.node.id, "type", 0)
    if parameterType.found && pep_c23_c_parameter_type(nodes, parameterType.node) == "pep_list_int" {
      return secondParameter
    } else {}
  } else {}
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_bool_list_parameter(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
  if parameter.found && parameter.node.text == name {
    let parameterType = pep_c23_child(nodes, parameter.node.id, "type", 0)
    if parameterType.found && pep_c23_c_parameter_type(nodes, parameterType.node) == "pep_list_bool" { return parameter } else {}
  } else {}
  if secondParameter.found && secondParameter.node.text == name {
    let parameterType = pep_c23_child(nodes, secondParameter.node.id, "type", 0)
    if parameterType.found && pep_c23_c_parameter_type(nodes, parameterType.node) == "pep_list_bool" { return secondParameter } else {}
  } else {}
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_bool_list_argument(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> PepC23Emission {
  if node.kind == "name" {
    let parameter = pep_c23_bool_list_parameter(nodes, function, node.text)
    if parameter.found { return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(parameter.node.id)], diagnostic: "" } } else {}
    let binding = pep_c23_mutable_list_binding(nodes, function, node.text)
    if binding.found {
      if pep_c23_mutable_list_element_kind(nodes, binding.node) != "boolean" {
        return pep_c23_unsupported("Pep C23 List[Bool] forwarding requires a Bool list binding")
      } else {}
      return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(binding.node.id)], diagnostic: "" }
    } else {}
    return pep_c23_unsupported("Pep C23 List[Bool] forwarding requires a direct List[Bool] parameter or mutable Bool list binding")
  } else {}
  if node.kind != "list" { return pep_c23_unsupported("Pep C23 List[Bool] parameters require a Bool list literal or direct parameter forwarding") } else {}
  var parts: List[Str] = ["(pep_list_bool){ .data = "]
  let elementCount = count_children(nodes, node.id, "element")
  if elementCount == 0 { parts = append(parts, "NULL") } else {
    parts = append(parts, "(const _Bool[]){")
    var count = 0
    for element in nodes {
      if element.parentId == node.id && element.role == "element" {
        if element.kind != "boolean" { return pep_c23_unsupported("Pep C23 List[Bool] parameter arguments require Bool elements") } else {}
        if count != 0 { parts = append(parts, ", ") } else {}
        parts = append(parts, if element.booleanValue { "1" } else { "0" })
        count = count + 1
      } else {}
    }
    parts = append(parts, "}")
  }
  parts = append(parts, ", .length = ")
  parts = append(parts, int_text(elementCount))
  parts = append(parts, " }")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_call_argument(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode, parameterType: PepC23NodeLookup) -> PepC23Emission {
  if !parameterType.found { return pep_c23_expression(nodes, function, node) } else {}
  let cType = pep_c23_c_parameter_type(nodes, parameterType.node)
  if cType == "pep_list_int" { return pep_c23_int_list_argument(nodes, function, node) } else {}
  if cType == "pep_list_bool" { return pep_c23_bool_list_argument(nodes, function, node) } else {}
  return pep_c23_expression(nodes, function, node)
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
fn pep_c23_c_parameter_type(nodes: List[FlatAstNode], node: FlatAstNode) -> Str {
  if node.kind == "type_scalar" { return pep_c23_c_scalar_type(node) } else {}
  if node.kind == "type_list" {
    let elementType = pep_c23_child(nodes, node.id, "element_type", 0)
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Int" {
      return "pep_list_int"
    } else {}
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Bool" {
      return "pep_list_bool"
    } else {}
  } else {}
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
  if node.kind == "call" && node.text == "length" {
    let argument = pep_c23_child(nodes, node.id, "argument", 0)
    let extraArgument = pep_c23_child(nodes, node.id, "argument", 1)
    return argument.found && !extraArgument.found && argument.node.kind == "name" &&
      (argument.node.text == parameterName || argument.node.text == secondParameterName)
  } else {}
  if node.kind == "call" && node.text == "contains" {
    let argument = pep_c23_child(nodes, node.id, "argument", 0)
    let secondArgument = pep_c23_child(nodes, node.id, "argument", 1)
    let extraArgument = pep_c23_child(nodes, node.id, "argument", 2)
    return argument.found && secondArgument.found && !extraArgument.found &&
      argument.node.kind == "name" && argument.node.text == parameterName &&
      secondArgument.node.kind == "name" && secondArgument.node.text == secondParameterName
  } else {}
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
fn pep_c23_direct_local(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> Bool {
  for candidate in nodes {
    if candidate.parentId == function.id && candidate.role == "statement" &&
       (candidate.kind == "let" || candidate.kind == "var") && candidate.text == name {
      return true
    } else {}
  }
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
    if node.text == "contains" {
      if !argument.found || !secondArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 contains lowering requires a list and an Int value")
      } else {}
      let listParameter = if argument.node.kind == "name" {
        pep_c23_int_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
      if listParameter.found {
        if secondArgument.node.kind != "integer" && secondArgument.node.kind != "name" {
          return pep_c23_unsupported("Pep C23 runtime List[Int] contains requires an integer literal or local needle")
        } else {}
        let value = pep_c23_expression(nodes, function, secondArgument.node)
        if value.status != "emitted" { return value } else {}
        var parts: List[Str] = ["pep_contains_int(pep_arg_", int_text(listParameter.node.id), ", "]
        for part in value.sourceParts { parts = append(parts, part) }
        parts = append(parts, ")")
        return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
      } else {}
      let boolListParameter = if argument.node.kind == "name" {
        pep_c23_bool_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
      if boolListParameter.found {
        if secondArgument.node.kind != "boolean" && secondArgument.node.kind != "name" {
          return pep_c23_unsupported("Pep C23 runtime List[Bool] contains requires a Bool literal or local value")
        } else {}
        let value = pep_c23_expression(nodes, function, secondArgument.node)
        if value.status != "emitted" { return value } else {}
        var parts: List[Str] = ["pep_contains_bool(pep_arg_", int_text(boolListParameter.node.id), ", "]
        for part in value.sourceParts { parts = append(parts, part) }
        parts = append(parts, ")")
        return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
      } else {}
      let mutableList = if argument.node.kind == "name" {
        pep_c23_mutable_list_binding(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
      if mutableList.found {
        let elementKind = pep_c23_mutable_list_element_kind(nodes, mutableList.node)
        if elementKind != "integer" && elementKind != "boolean" {
          return pep_c23_unsupported("Pep C23 mutable contains requires a typed Int or Bool list binding")
        } else {}
        if secondArgument.node.kind != "integer" && secondArgument.node.kind != "boolean" && secondArgument.node.kind != "name" {
          return pep_c23_unsupported("Pep C23 mutable contains requires a scalar literal or local value")
        } else {}
        let value = pep_c23_expression(nodes, function, secondArgument.node)
        if value.status != "emitted" { return value } else {}
        var parts: List[Str] = [if elementKind == "boolean" { "pep_contains_bool(" } else { "pep_contains_int(" }, "pep_local_", int_text(mutableList.node.id), ", "]
        for part in value.sourceParts { parts = append(parts, part) }
        parts = append(parts, ")")
        return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
      } else {}
      let list = pep_c23_list_literal(nodes, function, argument.node)
      if !list.found { return pep_c23_unsupported("Pep C23 contains lowering requires a direct integer list literal or immutable list binding") } else {}
      if secondArgument.node.kind != "integer" && secondArgument.node.kind != "boolean" && secondArgument.node.kind != "name" {
        return pep_c23_unsupported("Pep C23 contains lowering requires an integer literal or local value")
      } else {}
      let value = pep_c23_expression(nodes, function, secondArgument.node)
      if value.status != "emitted" { return value } else {}
      var parts: List[Str] = ["("]
      var count = 0
      for element in nodes {
        if element.parentId == list.node.id && element.role == "element" {
          if element.kind != "integer" && element.kind != "boolean" { return pep_c23_unsupported("Pep C23 contains list literals currently require integer or Bool elements") } else {}
          if count != 0 { parts = append(parts, " || ") } else {}
          parts = append(parts, "(")
          for part in value.sourceParts { parts = append(parts, part) }
          parts = append(parts, " == ")
          let elementText = if element.kind == "boolean" { if element.booleanValue { "1" } else { "0" } } else { int_text(element.integerValue) }
          parts = append(parts, elementText)
          parts = append(parts, ")")
          count = count + 1
        } else {}
      }
      if count == 0 { parts = append(parts, "0") } else {}
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
    if node.text == "length" {
      if !argument.found || secondArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 length lowering requires one supported list value")
      } else {}
      let listParameter = if argument.node.kind == "name" {
        pep_c23_int_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
      if listParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(listParameter.node.id), ".length"], diagnostic: "" }
      } else {}
      let boolListParameter = if argument.node.kind == "name" {
        pep_c23_bool_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
      if boolListParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(boolListParameter.node.id), ".length"], diagnostic: "" }
      } else {}
      for binding in nodes {
        if binding.parentId == function.id && binding.role == "statement" && binding.kind == "var" && binding.text == argument.node.text {
          let initial = pep_c23_child(nodes, binding.id, "value", 0)
          if initial.found && initial.node.kind == "list" {
            return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(binding.id), ".length"], diagnostic: "" }
          } else {}
        } else {}
      }
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
    let directLocalTarget = targetStatement.found && targetStatement.node.kind == "return" &&
      targetValue.found && targetValue.node.kind == "name" &&
      pep_c23_direct_local(nodes, target.node, targetValue.node.text)
    let nestedReturnTarget = if targetValue.found && targetValue.node.kind == "call" {
      pep_c23_function(nodes, targetValue.node.text)
    } else { PepC23NodeLookup { found: false, node: empty_node() } }
    let directCallTarget = targetStatement.found && targetStatement.node.kind == "return" &&
      targetValue.found && targetValue.node.kind == "call" &&
      nestedReturnTarget.found && nestedReturnTarget.node.id != target.node.id
    let conditionalTarget = (targetStatement.found && targetStatement.node.kind == "if_statement") ||
      (targetStatement.found && targetStatement.node.kind == "return" && targetValue.found && targetValue.node.kind == "if_expression") ||
      directLocalTarget ||
      directCallTarget
    if !targetStatement.found || (targetStatement.node.kind != "return" && !conditionalTarget) || (!conditionalTarget && !targetValue.found) {
      return pep_c23_unsupported("Pep C23 calls require a direct-return or supported conditional-return target")
    } else {}
    if parameter.found {
      let parameterType = pep_c23_child(nodes, parameter.node.id, "type", 0)
      if secondParameter.found {
        let secondParameterType = pep_c23_child(nodes, secondParameter.node.id, "type", 0)
        if !argument.found || !secondArgument.found || (!conditionalTarget && !pep_c23_parameter_expression(nodes, parameter.node.text, secondParameter.node.text, targetValue.node)) {
          return pep_c23_unsupported("Pep C23 two-parameter calls require two arguments and a call-free result expression")
        } else {}
        if pep_c23_expression_may_fail(nodes, argument.node) && pep_c23_expression_may_fail(nodes, secondArgument.node) {
          return pep_c23_unsupported("Pep C23 rejects two fallible call arguments because C argument evaluation order is unspecified")
        } else {}
        let loweredArgument = pep_c23_call_argument(nodes, function, argument.node, parameterType)
        let loweredSecondArgument = pep_c23_call_argument(nodes, function, secondArgument.node, secondParameterType)
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
        let loweredArgument = pep_c23_call_argument(nodes, function, argument.node, parameterType)
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

fn pep_c23_while_body(nodes: List[FlatAstNode], function: FlatAstNode, loop: FlatAstNode) -> PepC23Emission {
  let condition = pep_c23_child(nodes, loop.id, "condition", 0)
  if !condition.found || count_children(nodes, loop.id, "body") == 0 {
    return pep_c23_unsupported("Pep C23 while lowering requires a condition and a non-empty assignment body")
  } else {}
  let loweredCondition = pep_c23_expression(nodes, function, condition.node)
  if loweredCondition.status != "emitted" { return loweredCondition } else {}
  var parts: List[Str] = ["  while ("]
  for part in loweredCondition.sourceParts { parts = append(parts, part) }
  parts = append(parts, ") {\n")
  for statement in nodes {
    if statement.parentId == loop.id && statement.role == "body" {
      if statement.kind != "assignment" { return pep_c23_unsupported("Pep C23 while bodies currently require assignments to mutable locals") } else {}
      let value = pep_c23_child(nodes, statement.id, "value", 0)
      if !value.found { return pep_c23_unsupported("Pep C23 while assignment has no value") } else {}
      let loweredValue = pep_c23_expression(nodes, function, value.node)
      if loweredValue.status != "emitted" { return loweredValue } else {}
      var targetId = -1
      var targetFound = false
      for local in nodes {
        if local.parentId == function.id && local.role == "statement" && local.kind == "var" && local.text == statement.text {
          targetId = local.id
          targetFound = true
        } else {}
      }
      if !targetFound { return pep_c23_unsupported("Pep C23 while assignments must target direct mutable locals") } else {}
      let targetList = pep_c23_mutable_list_binding(nodes, function, statement.text)
      if targetList.found {
        let targetKind = pep_c23_mutable_list_element_kind(nodes, targetList.node)
        var sourceKind = ""
        if value.node.kind == "name" {
          let sourceList = pep_c23_mutable_list_binding(nodes, function, value.node.text)
          let sourceIntParameter = pep_c23_int_list_parameter(nodes, function, value.node.text)
          let sourceBoolParameter = pep_c23_bool_list_parameter(nodes, function, value.node.text)
          if sourceList.found { sourceKind = pep_c23_mutable_list_element_kind(nodes, sourceList.node) } else {}
          if sourceIntParameter.found { sourceKind = "integer" } else {}
          if sourceBoolParameter.found { sourceKind = "boolean" } else {}
        } else {}
        if sourceKind != targetKind || (sourceKind != "integer" && sourceKind != "boolean") {
          return pep_c23_unsupported("Pep C23 mutable list reassignment requires a matching typed list binding or parameter")
        } else {}
      } else {}
      for part in ["    pep_local_", int_text(targetId), " = "] { parts = append(parts, part) }
      for part in loweredValue.sourceParts { parts = append(parts, part) }
      parts = append(parts, ";\n")
    } else {}
  }
  parts = append(parts, "  }\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_function_expression(nodes: List[FlatAstNode], function: FlatAstNode) -> PepC23Emission {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
  let extraParameter = pep_c23_child(nodes, function.id, "parameter", 2)
  let parameterType = if parameter.found { pep_c23_child(nodes, parameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let secondParameterType = if secondParameter.found { pep_c23_child(nodes, secondParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let result = pep_c23_child(nodes, function.id, "return_type", 0)
  let parameterCType = if parameterType.found { pep_c23_c_parameter_type(nodes, parameterType.node) } else { "" }
  let secondParameterCType = if secondParameterType.found { pep_c23_c_parameter_type(nodes, secondParameterType.node) } else { "" }
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
        if initialValue.node.kind == "list" && (statement.kind == "let" || statement.kind == "var") {
          for item in nodes {
            if item.parentId == initialValue.node.id && item.role == "element" && item.kind != "integer" && item.kind != "boolean" {
              return pep_c23_unsupported("Pep C23 immutable collection bindings currently require integer or Bool list literals")
            } else {}
          }
          // List descriptors have value semantics, so reassignment copies the descriptor.
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
          let iterableLocal = if iterable.found && iterable.node.kind == "name" { pep_c23_mutable_list_binding(nodes, function, iterable.node.text) } else { PepC23NodeLookup { found: false, node: empty_node() } }
          let iterableIntegerParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_int_list_parameter(nodes, function, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: empty_node() } }
          let iterableBooleanParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_bool_list_parameter(nodes, function, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: empty_node() } }
          let iterableParameter = if iterableIntegerParameter.found { iterableIntegerParameter } else { iterableBooleanParameter }
          if !iterable.found || (!iterableList.found && !iterableParameter.found && !iterableLocal.found) || count_children(nodes, statement.id, "body") == 0 {
            return pep_c23_unsupported("Pep C23 for-in lowering requires an integer or Bool list literal or immutable literal binding, or a List[Int] or List[Bool] parameter, and a non-empty assignment body")
          } else {}
          if iterableList.found {
            for item in nodes {
              if item.parentId == iterableList.node.id && item.role == "element" && item.kind != "integer" && item.kind != "boolean" {
                return pep_c23_unsupported("Pep C23 for-in list literals currently require integer or Bool elements")
              } else {}
            }
          } else {}
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
          if statement.kind == "while" && !returned {
            let loweredWhile = pep_c23_while_body(nodes, function, statement)
            if loweredWhile.status != "emitted" { return loweredWhile } else {}
          } else {
            if statement.kind == "return" && !returned {
              returned = true
              returnStatement = PepC23NodeLookup { found: true, node: statement }
            } else {
              return pep_c23_unsupported("Pep C23 functions require local bindings and supported loops followed by one return")
            }
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
  reversed = prepend(reversed, "typedef struct { const int64_t *data; size_t length; } pep_list_int;\n_Bool pep_contains_int(pep_list_int values, int64_t needle) {\n  if (values.length != 0 && values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t i = 0; i < values.length; ++i) { if (values.data[i] == needle) { return 1; } }\n  return 0;\n}\n")
  reversed = prepend(reversed, "typedef struct { const _Bool *data; size_t length; } pep_list_bool;\n_Bool pep_contains_bool(pep_list_bool values, _Bool needle) {\n  if (values.length != 0 && values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t i = 0; i < values.length; ++i) { if (values.data[i] == needle) { return 1; } }\n  return 0;\n}\n")
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
        reversed = prepend(reversed, pep_c23_c_parameter_type(parsed.nodes, parameterType.node))
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameter.node.id))
        if secondParameter.found {
          let secondParameterType = pep_c23_child(parsed.nodes, secondParameter.node.id, "type", 0)
          reversed = prepend(reversed, ", ")
          reversed = prepend(reversed, pep_c23_c_parameter_type(parsed.nodes, secondParameterType.node))
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
            if initialValue.node.kind == "list" && statement.kind == "var" {
              let elementCount = count_children(parsed.nodes, initialValue.node.id, "element")
              var elementKind = ""
              for element in parsed.nodes {
                if element.parentId == initialValue.node.id && element.role == "element" { elementKind = element.kind } else {}
              }
              if elementCount == 0 {
                elementKind = pep_c23_mutable_list_element_kind(parsed.nodes, statement)
              } else {}
              if elementKind != "boolean" && elementKind != "integer" {
                return pep_c23_unsupported("Pep C23 mutable collection bindings require a typed Int or Bool list")
              } else {}
              let initial = if elementKind == "boolean" {
                pep_c23_bool_list_argument(parsed.nodes, node, initialValue.node)
              } else { pep_c23_int_list_argument(parsed.nodes, node, initialValue.node) }
              if initial.status != "emitted" { return initial } else {}
              let cType = if elementKind == "boolean" { "pep_list_bool" } else { "pep_list_int" }
              for part in ["  ", cType, " pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
              for part in initial.sourceParts { bodyParts = append(bodyParts, part) }
              bodyParts = append(bodyParts, ";\n")
            } else {
              let initial = pep_c23_expression(parsed.nodes, node, initialValue.node)
              for part in ["  int64_t pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
              for part in initial.sourceParts { bodyParts = append(bodyParts, part) }
              bodyParts = append(bodyParts, ";\n")
            }
          }
        } else {
          if statement.parentId == node.id && statement.role == "statement" && statement.kind == "for_in" {
            let iterable = pep_c23_child(parsed.nodes, statement.id, "iterable", 0)
            let iterableList = if iterable.found { pep_c23_list_literal(parsed.nodes, node, iterable.node) } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableLocal = if iterable.found && iterable.node.kind == "name" { pep_c23_mutable_list_binding(parsed.nodes, node, iterable.node.text) } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableIntegerParameter = if iterable.found && iterable.node.kind == "name" {
              pep_c23_int_list_parameter(parsed.nodes, node, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableBooleanParameter = if iterable.found && iterable.node.kind == "name" {
              pep_c23_bool_list_parameter(parsed.nodes, node, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableParameter = if iterableIntegerParameter.found { iterableIntegerParameter } else { iterableBooleanParameter }
            if !iterable.found || (!iterableList.found && !iterableParameter.found && !iterableLocal.found) {
              return pep_c23_unsupported("Pep C23 for-in lowering requires a list literal, immutable literal binding, or List[Int]/List[Bool] parameter")
            } else {}
            var elementCount = 0
            if iterableList.found {
              for element in parsed.nodes {
                if element.parentId == iterableList.node.id && element.role == "element" {
                  if element.kind != "integer" && element.kind != "boolean" { return pep_c23_unsupported("Pep C23 for-in list literals currently require integer or Bool elements") } else {}
                  elementCount = elementCount + 1
                } else {}
              }
            } else {}
            var arrayDeclaration: List[Str] = []
            if iterableParameter.found {
              for part in ["  if (pep_arg_", int_text(iterableParameter.node.id), ".length != 0 && pep_arg_", int_text(iterableParameter.node.id), ".data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t pep_index_", int_text(statement.id), " = 0; pep_index_", int_text(statement.id), " < pep_arg_", int_text(iterableParameter.node.id), ".length; ++pep_index_", int_text(statement.id), ") {\n    int64_t pep_local_", int_text(statement.id), " = pep_arg_", int_text(iterableParameter.node.id), ".data[pep_index_", int_text(statement.id), "];\n"] {
                arrayDeclaration = append(arrayDeclaration, part)
              }
            } else {
              if iterableLocal.found {
                let localList = pep_c23_child(parsed.nodes, iterableLocal.node.id, "value", 0)
                if !localList.found || localList.node.kind != "list" {
                  return pep_c23_unsupported("Pep C23 runtime list iteration requires a mutable list literal binding")
                } else {}
                for part in ["  if (pep_local_", int_text(iterableLocal.node.id), ".length != 0 && pep_local_", int_text(iterableLocal.node.id), ".data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t pep_index_", int_text(statement.id), " = 0; pep_index_", int_text(statement.id), " < pep_local_", int_text(iterableLocal.node.id), ".length; ++pep_index_", int_text(statement.id), ") {\n    int64_t pep_local_", int_text(statement.id), " = (int64_t)pep_local_", int_text(iterableLocal.node.id), ".data[pep_index_", int_text(statement.id), "];\n"] {
                  arrayDeclaration = append(arrayDeclaration, part)
                }
              } else {
                if elementCount == 0 {
                  for part in ["  if (0) {\n    int64_t pep_local_", int_text(statement.id), " = 0;\n"] {
                    arrayDeclaration = append(arrayDeclaration, part)
                  }
                } else {
                  arrayDeclaration = ["  int64_t pep_iter_", int_text(statement.id), "[] = {"]
                  for element in parsed.nodes {
                    if element.parentId == iterableList.node.id && element.role == "element" {
                      let elementText = if element.kind == "boolean" { if element.booleanValue { "1" } else { "0" } } else { int_text(element.integerValue) }
                      arrayDeclaration = append(arrayDeclaration, elementText)
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
                }
              }
            }
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
          } else {
            if statement.parentId == node.id && statement.role == "statement" && statement.kind == "while" {
              let loweredWhile = pep_c23_while_body(parsed.nodes, node, statement)
              if loweredWhile.status != "emitted" { return loweredWhile } else {}
              for part in loweredWhile.sourceParts { bodyParts = append(bodyParts, part) }
            } else {}
          }
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
        reversed = prepend(reversed, pep_c23_c_parameter_type(parsed.nodes, parameterType.node))
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameter.node.id))
        if secondParameter.found {
          let secondParameterType = pep_c23_child(parsed.nodes, secondParameter.node.id, "type", 0)
          reversed = prepend(reversed, ", ")
          reversed = prepend(reversed, pep_c23_c_parameter_type(parsed.nodes, secondParameterType.node))
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
