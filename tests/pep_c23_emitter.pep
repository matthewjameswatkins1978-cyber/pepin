type PepC23NodeLookup { found: Bool, node: FlatAstNode }
type PepC23Emission { status: Str, sourceParts: List[Str], diagnostic: Str }
type PepC23UnitPrerequisites { status: Str, diagnostic: Str, kinds: List[Str], nodeIds: List[Int] }
type PepC23IdList { status: Str, diagnostic: Str, ids: List[Int] }
type PepC23DeclarationCheck { status: Str, diagnostic: Str }
type PepC23BoundedUnit { status: Str, diagnostic: Str, sourceParts: List[Str], prerequisiteKinds: List[Str], prerequisiteIds: List[Int], requiresArena: Bool }

fn pep_c23_empty_ast_node() -> FlatAstNode {
  return FlatAstNode {
    id: -1, parentId: -1, childIndex: -1, role: "", kind: "", text: "",
    integerValue: 0, booleanValue: false, stringParts: [],
    startByte: 0, endByte: 0, line: 0, column: 0
  }
}

fn pep_c23_count_children(nodes: List[FlatAstNode], parent: Int, role: Str) -> Int {
  var count = 0
  for node in nodes {
    if node.parentId == parent && node.role == role { count = count + 1 } else {}
  }
  return count
}

fn pep_c23_child(nodes: List[FlatAstNode], parentId: Int, role: Str, wantedIndex: Int) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == parentId && node.role == role && node.childIndex == wantedIndex {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
// Parameter and argument lists are collected in declared order, so arity is not baked into a fixed
// number of slots. Ordering uses childIndex, never node arrival order.
fn pep_c23_ordered_children(nodes: List[FlatAstNode], parentId: Int, role: Str) -> List[FlatAstNode] {
  // Single pass in the common case: nodes arrive in ascending childIndex order. This runs for
  // every function twice (prototype and definition), so a count-plus-indexed-lookup loop here
  // measurably inflates emitter step cost on large programs.
  var collected: List[FlatAstNode] = []
  var inorder = true
  var previous = -1
  for node in nodes {
    if node.parentId == parentId && node.role == role {
      if !(previous <= node.childIndex) { inorder = false } else {}
      previous = node.childIndex
      collected = append(collected, node)
    } else {}
  }
  if inorder { return collected } else {}
  var ordered: List[FlatAstNode] = []
  var wanted = 0
  while !(length(collected) <= wanted) {
    let child = pep_c23_child(nodes, parentId, role, wanted)
    if child.found { ordered = append(ordered, child.node) } else {}
    wanted = wanted + 1
  }
  return ordered
}
fn pep_c23_parameters(nodes: List[FlatAstNode], function: FlatAstNode) -> List[FlatAstNode] {
  return pep_c23_ordered_children(nodes, function.id, "parameter")
}
fn pep_c23_is_negative_int_literal(nodes: List[FlatAstNode], value: FlatAstNode) -> Bool {
  if value.kind != "binary" || value.text != "neg" { return false } else {}
  let zero = pep_c23_child(nodes, value.id, "left", 0)
  let operand = pep_c23_child(nodes, value.id, "right", 1)
  return zero.found && zero.node.kind == "integer" && zero.node.integerValue == 0 && operand.found && operand.node.kind == "integer"
}
fn pep_c23_list_literal(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "list" { return PepC23NodeLookup { found: true, node: value } } else {}
  if value.kind != "name" { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  var matches = 0
  var list = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  for binding in nodes {
    if binding.parentId == function.id && binding.role == "statement" && (binding.kind == "let" || binding.kind == "var") && binding.text == value.text {
      matches = matches + 1
      let initial = pep_c23_child(nodes, binding.id, "value", 0)
      if initial.found && initial.node.kind == "list" { list = initial } else { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    } else {}
  }
  if matches != 1 { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
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
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_mutable_list_element_kind(nodes: List[FlatAstNode], binding: FlatAstNode) -> Str {
  let declared = pep_c23_child(nodes, binding.id, "annotation", 0)
  if declared.found && declared.node.kind == "type_list" {
    let elementType = pep_c23_child(nodes, declared.node.id, "element_type", 0)
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Int" { return "integer" } else {}
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Bool" { return "boolean" } else {}
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Str" { return "string" } else {}
    if elementType.found && elementType.node.kind == "type_named" &&
       pep_c23_record_declaration(nodes, elementType.node.text).found { return "record" } else {}
  } else {}
  let initial = pep_c23_child(nodes, binding.id, "value", 0)
  let first = if initial.found { pep_c23_child(nodes, initial.node.id, "element", 0) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  if first.found && (first.node.kind == "integer" || first.node.kind == "boolean") { return first.node.kind } else {}
  if first.found && first.node.kind == "binary" && first.node.text == "neg" {
    let zero = pep_c23_child(nodes, first.node.id, "left", 0)
    let operand = pep_c23_child(nodes, first.node.id, "right", 1)
    if zero.found && zero.node.kind == "integer" && zero.node.integerValue == 0 && operand.found && operand.node.kind == "integer" {
      return "integer"
    } else {}
  } else {}
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
  let elementCount = pep_c23_count_children(nodes, node.id, "element")
  if elementCount == 0 {
    parts = append(parts, "NULL")
  } else {
    parts = append(parts, "(const int64_t[]){")
    var count = 0
    for element in nodes {
      if element.parentId == node.id && element.role == "element" {
        if count != 0 { parts = append(parts, ", ") } else {}
        if element.kind == "integer" {
          parts = append(parts, int_text(element.integerValue))
        } else {
          let zero = if element.kind == "binary" && element.text == "neg" {
            pep_c23_child(nodes, element.id, "left", 0)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let operand = if zero.found && zero.node.kind == "integer" && zero.node.integerValue == 0 {
            pep_c23_child(nodes, element.id, "right", 1)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          if !operand.found || operand.node.kind != "integer" {
            return pep_c23_unsupported("Pep C23 List[Int] parameter arguments currently require integer or negative integer literal elements")
          } else {}
          let lowered = pep_c23_expression(nodes, function, element)
          if lowered.status != "emitted" { return lowered } else {}
          for part in lowered.sourceParts { parts = append(parts, part) }
        }
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
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
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
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_record_list_parameter(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
  if parameter.found && parameter.node.text == name {
    let parameterType = pep_c23_child(nodes, parameter.node.id, "type", 0)
    if parameterType.found && pep_c23_record_list_declaration(nodes, parameterType.node).found { return parameter } else {}
  } else {}
  if secondParameter.found && secondParameter.node.text == name {
    let parameterType = pep_c23_child(nodes, secondParameter.node.id, "type", 0)
    if parameterType.found && pep_c23_record_list_declaration(nodes, parameterType.node).found { return secondParameter } else {}
  } else {}
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_union_list_parameter(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for parameter in nodes {
    if parameter.parentId == function.id && parameter.role == "parameter" &&
       parameter.kind == "parameter" && parameter.text == name {
      let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
      if parameterType.found && pep_c23_union_list_declaration(nodes, parameterType.node).found {
        return PepC23NodeLookup { found: true, node: parameter }
      } else {}
      return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_str_parameter(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for parameter in nodes {
    if parameter.parentId == function.id && parameter.role == "parameter" &&
       parameter.kind == "parameter" && parameter.text == name {
      let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
      if parameterType.found && parameterType.node.kind == "type_scalar" &&
         parameterType.node.text == "Str" {
        return PepC23NodeLookup { found: true, node: parameter }
      } else {}
      return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
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
  let elementCount = pep_c23_count_children(nodes, node.id, "element")
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
fn pep_c23_str_list_parameter(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for parameter in nodes {
    if parameter.parentId == function.id && parameter.role == "parameter" &&
       parameter.kind == "parameter" && parameter.text == name {
      let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
      if parameterType.found && parameterType.node.kind == "type_list" {
        let elementType = pep_c23_child(nodes, parameterType.node.id, "element_type", 0)
        if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Str" {
          return PepC23NodeLookup { found: true, node: parameter }
        } else {}
      } else {}
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_str_list_argument(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> PepC23Emission {
  if node.kind == "name" {
    let parameter = pep_c23_str_list_parameter(nodes, function, node.text)
    if parameter.found {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(parameter.node.id)], diagnostic: "" }
    } else {}
    return pep_c23_unsupported("Pep C23 List[Str] arguments currently require a list literal or a direct List[Str] parameter")
  } else {}
  if node.kind != "list" {
    return pep_c23_unsupported("Pep C23 List[Str] arguments currently require a list literal or a direct List[Str] parameter")
  } else {}
  var parts: List[Str] = ["(pep_list_str){ .data = "]
  let elementCount = pep_c23_count_children(nodes, node.id, "element")
  if elementCount == 0 {
    parts = append(parts, "NULL")
  } else {
    parts = append(parts, "(const pep_str[]){")
    var count = 0
    for element in nodes {
      if element.parentId == node.id && element.role == "element" {
        if element.kind != "string" {
          return pep_c23_unsupported("Pep C23 List[Str] arguments currently require string literal elements")
        } else {}
        if count != 0 { parts = append(parts, ", ") } else {}
        let lowered = pep_c23_string_literal(nodes, element)
        if lowered.status != "emitted" { return lowered } else {}
        for part in lowered.sourceParts { parts = append(parts, part) }
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
fn pep_c23_record_list_argument(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode, parameterType: PepC23NodeLookup) -> PepC23Emission {
  let declaration = pep_c23_record_list_declaration(nodes, parameterType.node)
  if !declaration.found { return pep_c23_unsupported("Pep C23 List[Record] argument has no supported record element type") } else {}
  if node.kind == "name" {
    let parameter = pep_c23_record_list_parameter(nodes, function, node.text)
    if parameter.found {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(parameter.node.id)], diagnostic: "" }
    } else {}
    let list = pep_c23_list_literal(nodes, function, node)
    if list.found {
      let actualDeclaration = pep_c23_record_list_declaration(nodes, list.node)
      if !actualDeclaration.found || actualDeclaration.node.id != declaration.node.id {
        return pep_c23_unsupported("Pep C23 List[Record] binding must match the parameter record type")
      } else {}
      return pep_c23_record_list_argument(nodes, function, list.node, parameterType)
    } else {}
    return pep_c23_unsupported("Pep C23 List[Record] forwarding requires a direct List[Record] parameter or immutable literal binding")
  } else {}
  if node.kind != "list" {
    return pep_c23_unsupported("Pep C23 List[Record] arguments currently require a record list literal or direct parameter forwarding")
  } else {}
  var parts: List[Str] = ["(pep_list_record_", int_text(declaration.node.id), "){ .data = "]
  let elementCount = pep_c23_count_children(nodes, node.id, "element")
  if elementCount == 0 { parts = append(parts, "NULL") } else {
    parts = append(parts, "(const pep_record_")
    parts = append(parts, int_text(declaration.node.id))
    parts = append(parts, "[]){")
    var count = 0
    for element in nodes {
      if element.parentId == node.id && element.role == "element" {
        if element.kind != "record" { return pep_c23_unsupported("Pep C23 List[Record] literal arguments currently require record values") } else {}
        if count != 0 { parts = append(parts, ", ") } else {}
        let lowered = pep_c23_expression(nodes, function, element)
        if lowered.status != "emitted" { return lowered } else {}
        for part in lowered.sourceParts { parts = append(parts, part) }
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
fn pep_c23_union_list_element_supported(nodes: List[FlatAstNode], declaration: FlatAstNode,
  element: FlatAstNode) -> Bool {
  if element.kind != "call" { return false } else {}
  var variant = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  for candidate in nodes {
    if candidate.parentId == declaration.id && candidate.role == "variant" &&
       candidate.kind == "variant_declaration" && candidate.text == element.text && !variant.found {
      variant = PepC23NodeLookup { found: true, node: candidate }
    } else {}
  }
  if !variant.found ||
     pep_c23_count_children(nodes, element.id, "argument") != pep_c23_count_children(nodes, variant.node.id, "field_type") {
    return false
  } else {}
  for payload in nodes {
    if payload.parentId == variant.node.id && payload.role == "field_type" {
      let argument = pep_c23_child(nodes, element.id, "argument", payload.childIndex)
      if !argument.found { return false } else {}
      if payload.kind == "type_list" {
        let elementType = pep_c23_child(nodes, payload.id, "element_type", 0)
        if !elementType.found || elementType.node.kind != "type_named" ||
           elementType.node.text != declaration.text || argument.node.kind != "list" {
          return false
        } else {}
      } else {
        if payload.kind == "type_scalar" && payload.text == "Int" &&
           argument.node.kind == "integer" {
        } else {
          if payload.kind == "type_scalar" && payload.text == "Bool" &&
             argument.node.kind == "boolean" {
          } else { return false }
        }
      }
    } else {}
  }
  return true
}
fn pep_c23_union_list_match_argument(nodes: List[FlatAstNode], function: FlatAstNode,
  node: FlatAstNode, declaration: FlatAstNode) -> PepC23Emission {
  if node.kind != "name" {
    return pep_c23_unsupported("Pep C23 recursive union list arguments require a direct list literal or a matched payload binding")
  } else {}
  var call = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  for candidate in nodes {
    if candidate.id == node.parentId && candidate.kind == "call" {
      call = PepC23NodeLookup { found: true, node: candidate }
    } else {}
  }
  var arm = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  var callArgument = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  for candidate in nodes {
    if call.found && candidate.id == call.node.parentId &&
       candidate.kind == "match_arm" && candidate.role == "arm" {
      arm = PepC23NodeLookup { found: true, node: candidate }
    } else {}
    if call.found && candidate.id == node.id &&
       candidate.parentId == call.node.id && candidate.role == "argument" &&
       candidate.childIndex == node.childIndex {
      callArgument = PepC23NodeLookup { found: true, node: candidate }
    } else {}
  }
  if node.role != "argument" || !call.found || call.node.role != "result" ||
     !callArgument.found || callArgument.node.id != node.id {
    return pep_c23_unsupported("Pep C23 recursive union list binding must be passed by a direct call in its match arm")
  } else {}
  if !arm.found {
    return pep_c23_unsupported("Pep C23 recursive union list binding must come from the enclosing match arm")
  } else {}
  var matched = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  var armResult = false
  for candidate in nodes {
    if candidate.id == arm.node.parentId && candidate.kind == "match" {
      matched = PepC23NodeLookup { found: true, node: candidate }
    } else {}
    if candidate.parentId == arm.node.id && candidate.role == "result" &&
       candidate.id == call.node.id {
      armResult = true
    } else {}
  }
  if !matched.found { return pep_c23_unsupported("Pep C23 recursive union list payload has no enclosing match") } else {}
  if !armResult {
    return pep_c23_unsupported("Pep C23 recursive union list binding must be the direct match-arm call argument")
  } else {}
  let pattern = pep_c23_child(nodes, arm.node.id, "pattern", 0)
  let variant = if pattern.found && pattern.node.kind == "constructor_pattern" {
    pep_c23_union_variant(nodes, pattern.node.text)
  } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  var binding = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  var extraBinding = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  var payload0 = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  var payload1 = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  var payloadCount = 0
  var patternArgumentCount = 0
  var indicesValid = true
  for candidate in nodes {
    if variant.found && candidate.parentId == variant.node.id &&
       candidate.role == "field_type" {
      payloadCount = payloadCount + 1
      if candidate.childIndex == 0 {
        if payload0.found { indicesValid = false } else {
          payload0 = PepC23NodeLookup { found: true, node: candidate }
        }
      } else {
        if candidate.childIndex == 1 {
          if payload1.found { indicesValid = false } else {
            payload1 = PepC23NodeLookup { found: true, node: candidate }
          }
        } else { indicesValid = false }
      }
    } else {}
    if pattern.found && candidate.parentId == pattern.node.id &&
       candidate.role == "argument" {
      patternArgumentCount = patternArgumentCount + 1
      if candidate.childIndex == 0 {
        if binding.found { indicesValid = false } else {
          binding = PepC23NodeLookup { found: true, node: candidate }
        }
      } else {
        if candidate.childIndex == 1 {
          if extraBinding.found { indicesValid = false } else {
            extraBinding = PepC23NodeLookup { found: true, node: candidate }
          }
        } else { indicesValid = false }
      }
    } else {}
  }
  let binding0Valid = binding.found &&
    (binding.node.kind == "binding_pattern" || binding.node.kind == "wildcard_pattern")
  let binding1Valid = extraBinding.found &&
    (extraBinding.node.kind == "binding_pattern" || extraBinding.node.kind == "wildcard_pattern")
  if !variant.found || (payloadCount != 1 && payloadCount != 2) ||
     patternArgumentCount != payloadCount || !indicesValid || !payload0.found ||
     (payloadCount == 2 && (!binding1Valid || !payload1.found)) ||
     !binding0Valid {
    return pep_c23_unsupported("Pep C23 recursive union list call requires a supported one- or two-field constructor pattern")
  } else {}
  var listBinding = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  if binding.node.kind == "binding_pattern" && binding.node.text == node.text {
    listBinding = binding
  } else {}
  if extraBinding.found && extraBinding.node.kind == "binding_pattern" &&
     extraBinding.node.text == node.text {
    listBinding = extraBinding
  } else {}
  if !listBinding.found {
    return pep_c23_unsupported("Pep C23 recursive union list call requires its List[Self] field to be a named pattern binding")
  } else {}
  let owner = pep_c23_union_of_variant(nodes, variant.node)
  let payload = if listBinding.node.childIndex == 0 { payload0 } else { payload1 }
  let listType = if payload.found { pep_c23_union_list_declaration(nodes, payload.node) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  if !owner.found || owner.node.id != declaration.id || !payload.found ||
     !listType.found || listType.node.id != declaration.id {
    return pep_c23_unsupported("Pep C23 recursive union list match payload must be a List[Self] field")
  } else {}
  let subject = pep_c23_child(nodes, matched.node.id, "value", 0)
  let subjectUnion = if subject.found { pep_c23_union_value_type(nodes, function, subject.node) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  if !subject.found || !subjectUnion.found || subjectUnion.node.id != declaration.id {
    return pep_c23_unsupported("Pep C23 recursive union list match subject has an incompatible union type")
  } else {}
  let loweredSubject = pep_c23_expression(nodes, function, subject.node)
  if loweredSubject.status != "emitted" { return loweredSubject } else {}
  var parts: List[Str] = []
  for part in loweredSubject.sourceParts { parts = append(parts, part) }
  parts = append(parts, ".payload.payload_")
  parts = append(parts, int_text(variant.node.childIndex))
  parts = append(parts, ".field_")
  parts = append(parts, int_text(listBinding.node.childIndex))
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_union_list_argument(nodes: List[FlatAstNode], function: FlatAstNode,
  node: FlatAstNode, declaration: FlatAstNode) -> PepC23Emission {
  if node.kind == "name" {
    return pep_c23_union_list_match_argument(nodes, function, node, declaration)
  } else {}
  if node.kind != "list" {
    return pep_c23_unsupported("Pep C23 recursive union lists currently require a direct list literal")
  } else {}
  let elementCount = pep_c23_count_children(nodes, node.id, "element")
  var parts: List[Str] = ["(pep_list_union_", int_text(declaration.id), "){ .data = "]
  if elementCount == 0 {
    parts = append(parts, "NULL")
  } else {
    parts = append(parts, "(const pep_union_")
    parts = append(parts, int_text(declaration.id))
    parts = append(parts, "[]){")
    var count = 0
    for element in nodes {
      if element.parentId == node.id && element.role == "element" {
        let actual = pep_c23_union_value_type(nodes, function, element)
        if !actual.found || actual.node.id != declaration.id ||
           !pep_c23_union_list_element_supported(nodes, declaration, element) {
          return pep_c23_unsupported("Pep C23 recursive union list literals require matching constructors with scalar literal payloads")
        } else {}
        let lowered = pep_c23_expression(nodes, function, element)
        if lowered.status != "emitted" { return lowered } else {}
        if count != 0 { parts = append(parts, ", ") } else {}
        for part in lowered.sourceParts { parts = append(parts, part) }
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
  if cType == "pep_list_record" { return pep_c23_record_list_argument(nodes, function, node, parameterType) } else {}
  if cType == "pep_list_int" { return pep_c23_int_list_argument(nodes, function, node) } else {}
  if cType == "pep_list_bool" { return pep_c23_bool_list_argument(nodes, function, node) } else {}
  if cType == "pep_list_str" { return pep_c23_str_list_argument(nodes, function, node) } else {}
  if cType == "pep_list_union" {
    let elementType = pep_c23_child(nodes, parameterType.node.id, "element_type", 0)
    if elementType.found {
      let declaration = pep_c23_union_declaration(nodes, elementType.node.text)
      if declaration.found { return pep_c23_union_list_argument(nodes, function, node, declaration.node) } else {}
    } else {}
    return pep_c23_unsupported("Pep C23 recursive union list parameter type is unresolved")
  } else {}
  return pep_c23_expression(nodes, function, node)
}
fn pep_c23_unsupported(message: Str) -> PepC23Emission {
  return PepC23Emission { status: "unsupported", sourceParts: [], diagnostic: message }
}
// Lower one direct-function-body `say(...)` statement to the inlined runtime print helper. The
// argument must classify as a Str value position through pep_c23_str_expression -- string literal,
// Str parameter, immutable Str local, or Str field -- and is then lowered through the ordinary
// expression path; those classified shapes have no side effects, so emitting the value twice for
// `.data` and `.length` cannot observe an evaluation difference. Anything else refuses with its
// shape named: wrong arity, a non-Str position such as int_text(...), or a non-say expression
// statement. Say inside loop/conditional bodies stays with those bodies' own statement whitelists.
fn pep_c23_say_statement(nodes: List[FlatAstNode], function: FlatAstNode, statement: FlatAstNode) -> PepC23Emission {
  let value = pep_c23_child(nodes, statement.id, "value", 0)
  if !value.found || value.node.kind != "call" || value.node.text != "say" {
    return pep_c23_unsupported("Pep C23 expression statements currently support only say(...)")
  } else {}
  var argumentCount = 0
  var argumentNode = pep_c23_empty_ast_node()
  for candidate in nodes {
    if candidate.parentId == value.node.id && candidate.role == "argument" {
      argumentCount = argumentCount + 1
      if candidate.childIndex == 0 { argumentNode = candidate } else {}
    } else {}
  }
  if argumentCount != 1 {
    return pep_c23_unsupported("Pep C23 say requires exactly one argument")
  } else {}
  if !pep_c23_str_expression(nodes, function, argumentNode).found {
    return pep_c23_unsupported("Pep C23 say lowers only string literals, Str parameters, Str locals and Str fields")
  } else {}
  let lowered = pep_c23_expression(nodes, function, argumentNode)
  if lowered.status != "emitted" { return lowered } else {}
  var parts: List[Str] = ["  pep_say("]
  for part in lowered.sourceParts { parts = append(parts, part) }
  parts = append(parts, ".data, ")
  for part in lowered.sourceParts { parts = append(parts, part) }
  parts = append(parts, ".length);\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
// ---- Cross-chunk call lowering (PEP-WB-A2-20261104-B slice A2-1).
// The one- to four-parameter paths above resolve the callee from the SAME parsed nodes and then
// validate its body shape. When the callee lives in another checked chunk those nodes do not
// exist here, so this path resolves the target ONLY through the checked facts already in the
// report: ResolvedCall.syntaxId identifies this call node, ResolvedCall.calleeId names exactly
// one CheckedFunction (the checker resolved it against the supplied external signatures), and
// that entry carries the authenticated name -- the name-based C symbol -- plus arity and result
// type/shape. No textual name lookup happens here: missing, duplicate or disagreeing facts
// refuse with their own diagnostic instead of guessing a target. Argument TYPE soundness is the
// checker's (report status valid means types/arity were verified against external signatures);
// this path re-checks arity against its own node count as fail-closed defence of forged or
// mismatched reports, and the emit entry's document/revision identity check rejects stale facts
// before any body is lowered.
fn pep_c23_cross_chunk_call(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode,
                             checked: CheckerReport) -> PepC23Emission {
  var callMatches = 0
  var calleeSemanticId = -1
  for callFact in checked.calls {
    if callFact.syntaxId == node.id {
      callMatches = callMatches + 1
      calleeSemanticId = callFact.calleeId
    } else {}
  }
  if callMatches == 0 {
    return pep_c23_unsupported("Pep C23 cross-chunk call has no resolved call fact")
  } else {}
  if !(callMatches <= 1) {
    return pep_c23_unsupported("Pep C23 cross-chunk call has ambiguous resolved call facts")
  } else {}
  var targetMatches = 0
  var calleeName = ""
  var calleeArity = 0
  var calleeReturn = ""
  var calleeShapeKind = ""
  for fnFact in checked.functions {
    if fnFact.semanticId == calleeSemanticId {
      targetMatches = targetMatches + 1
      calleeName = fnFact.name
      calleeArity = fnFact.arity
      calleeReturn = fnFact.returnType
      calleeShapeKind = fnFact.returnShape.kind
    } else {}
  }
  if targetMatches == 0 {
    return pep_c23_unsupported("Pep C23 cross-chunk call target is missing from the checked functions")
  } else {}
  if !(targetMatches <= 1) {
    return pep_c23_unsupported("Pep C23 cross-chunk call target is ambiguous in the checked functions")
  } else {}
  let argumentCount = pep_c23_count_children(nodes, node.id, "argument")
  if argumentCount != calleeArity {
    return pep_c23_unsupported("Pep C23 cross-chunk call argument count disagrees with the checked arity")
  } else {}
  // Result support: Int and Bool always; a nominal record only when its declaration is visible
  // in THIS chunk (the struct type must exist where the value is consumed -- the declaration
  // chunk's header supplies it). Str, tagged unions and unknown results refuse: the callee-side
  // unit refuses them too, and a call must not reference a symbol the assembly never emits.
  if !(calleeReturn == "Int" || calleeReturn == "Bool") {
    if !(calleeShapeKind == "nominal" && pep_c23_record_declaration(nodes, calleeReturn).found) {
      return pep_c23_unsupported("Pep C23 cross-chunk calls support Int, Bool, and locally declared record results")
    } else {}
  } else {}
  // Same fallible-argument rule as the ordered path, mirrored exactly: C leaves argument
  // evaluation order unspecified, so more than one fallible argument refuses.
  var fallibleArguments = 0
  var arguments: List[FlatAstNode] = []
  var wanted = 0
  while !(argumentCount <= wanted) {
    let argument = pep_c23_child(nodes, node.id, "argument", wanted)
    if !argument.found {
      return pep_c23_unsupported("Pep C23 call argument list has a gap")
    } else {}
    if pep_c23_infallible_value(nodes, argument.node) {
      fallibleArguments = fallibleArguments + 1
    } else {}
    arguments = append(arguments, argument.node)
    wanted = wanted + 1
  }
  if !(fallibleArguments <= 1) {
    return pep_c23_unsupported("Pep C23 rejects multiple fallible call arguments because C argument evaluation order is unspecified")
  } else {}
  // Name-based symbol from the authenticated fact: the callee unit emits pep_fn_<name> too, so
  // chunk-local id remapping can never split a call from its definition.
  var parts: List[Str] = ["pep_fn_", calleeName, "("]
  var emitted = 0
  for argument in arguments {
    let lowered = pep_c23_call_argument(nodes, function, argument,
      PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() })
    if lowered.status != "emitted" { return lowered } else {}
    if emitted != 0 { parts = append(parts, ", ") } else {}
    for part in lowered.sourceParts { parts = append(parts, part) }
    emitted = emitted + 1
  }
  parts = pep_c23_close_generated_call(nodes, parts, argumentCount)
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
// Checked-aware expression entry. The plain path runs FIRST, so every success and every refusal
// except the missing-target one is byte-for-byte identical to today (one-shot and same-chunk
// behaviour preserved by construction); "calls require a known target" is exactly where a
// cross-chunk callee appears, and there the checked-fact path takes over. Supported statement
// forms in this slice: let initialisers and direct return values -- the two sites threaded with
// the real report. Nested calls inside arguments resolve same-chunk or refuse; conditional-return
// bodies keep the plain path (documented boundary).
fn pep_c23_expression_checked(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode,
                              checked: CheckerReport) -> PepC23Emission {
  let plain = pep_c23_expression(nodes, function, node)
  if plain.status == "emitted" { return plain } else {}
  if plain.diagnostic != "Pep C23 calls require a known target" { return plain } else {}
  if node.kind == "call" { return pep_c23_cross_chunk_call(nodes, function, node, checked) } else {}
  return plain
}
fn pep_c23_close_generated_call(nodes: List[FlatAstNode], parts: List[Str], argumentCount: Int) -> List[Str] {
  var closedParts = parts
  if pep_c23_requires_arena(nodes) {
    if argumentCount == 0 { closedParts = append(closedParts, "pep_arena") } else { closedParts = append(closedParts, ", pep_arena") }
  } else {}
  closedParts = append(closedParts, ")")
  return closedParts
}
fn pep_c23_c_scalar_type(node: FlatAstNode) -> Str {
  if node.kind != "type_scalar" { return "" } else {}
  if node.text == "Int" { return "int64_t" } else {}
  if node.text == "Bool" { return "_Bool" } else {}
  return ""
}
fn pep_c23_source_bytes_parameter(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for parameter in nodes {
    if parameter.parentId == function.id && parameter.role == "parameter" &&
       parameter.kind == "parameter" && parameter.text == name {
      let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
      if parameterType.found && parameterType.node.kind == "type_scalar" &&
         parameterType.node.text == "SourceBytes" {
        return PepC23NodeLookup { found: true, node: parameter }
      } else {}
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}

fn pep_c23_c_list_field_type_parts(nodes: List[FlatAstNode], owner: FlatAstNode, node: FlatAstNode) -> List[Str] {
  let elementType = pep_c23_child(nodes, node.id, "element_type", 0)
  if !elementType.found { return [] } else {}
  if elementType.node.kind == "type_scalar" {
    if elementType.node.text == "Int" { return ["pep_list_int"] } else {}
    if elementType.node.text == "Bool" { return ["pep_list_bool"] } else {}
    if elementType.node.text == "Str" { return ["pep_list_str"] } else {}
    return []
  } else {}
  if elementType.node.kind == "type_named" {
    let nested = pep_c23_record_declaration(nodes, elementType.node.text)
    if !nested.found || !(nested.node.id + 1 <= owner.id) { return [] } else {}
    return ["pep_list_record_", int_text(nested.node.id)]
  } else {}
  return []
}
fn pep_c23_c_record_field_type(nodes: List[FlatAstNode], owner: FlatAstNode, node: FlatAstNode) -> Str {
  if node.kind == "type_list" {
    if length(pep_c23_c_list_field_type_parts(nodes, owner, node)) == 0 { return "" } else {}
    return "list"
  } else {}
  let scalar = pep_c23_c_scalar_type(node)
  if scalar != "" { return scalar } else {}
  if node.kind == "type_scalar" && node.text == "Str" { return "pep_str" } else {}
  if node.kind != "type_named" { return "" } else {}
  let nested = pep_c23_record_declaration(nodes, node.text)
  if !nested.found || !(nested.node.id + 1 <= owner.id) { return "" } else {}
  return "record"
}
fn pep_c23_record_declaration(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == -1 && node.kind == "record_declaration" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_union_declaration(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == -1 && node.kind == "union_declaration" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_union_variant(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for declaration in nodes {
    if declaration.parentId == -1 && declaration.kind == "union_declaration" {
      for variant in nodes {
        if variant.parentId == declaration.id && variant.role == "variant" &&
           variant.kind == "variant_declaration" && variant.text == name {
          return PepC23NodeLookup { found: true, node: variant }
        } else {}
      }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_union_of_variant(nodes: List[FlatAstNode], variant: FlatAstNode) -> PepC23NodeLookup {
  for declaration in nodes {
    if declaration.parentId == -1 && declaration.kind == "union_declaration" &&
       variant.parentId == declaration.id && variant.role == "variant" {
      return PepC23NodeLookup { found: true, node: declaration }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_union_payload_type_supported(nodes: List[FlatAstNode], payload: FlatAstNode) -> Bool {
  if payload.kind == "type_scalar" {
    return payload.text == "Int" || payload.text == "Bool"
  } else {}
  if payload.kind == "type_named" {
    return pep_c23_record_declaration(nodes, payload.text).found
  } else {}
  return false
}
fn pep_c23_union_payload_is_recursive(nodes: List[FlatAstNode], declaration: FlatAstNode,
  payload: FlatAstNode) -> Bool {
  if payload.kind == "type_named" && payload.text == declaration.text { return true } else {}
  if payload.kind == "type_list" {
    let elementType = pep_c23_child(nodes, payload.id, "element_type", 0)
    return elementType.found && elementType.node.kind == "type_named" &&
      elementType.node.text == declaration.text
  } else {}
  return false
}
fn pep_c23_union_payload_type_supported_for(nodes: List[FlatAstNode], declaration: FlatAstNode,
  payload: FlatAstNode) -> Bool {
  if pep_c23_union_payload_is_recursive(nodes, declaration, payload) { return true } else {}
  return pep_c23_union_payload_type_supported(nodes, payload)
}
fn pep_c23_union_has_recursive_payload(nodes: List[FlatAstNode], declaration: FlatAstNode,
  variant: FlatAstNode) -> Bool {
  for payload in nodes {
    if payload.parentId == variant.id && payload.role == "field_type" &&
       pep_c23_union_payload_is_recursive(nodes, declaration, payload) {
      return true
    } else {}
  }
  return false
}
fn pep_c23_union_has_recursive_list_payload(nodes: List[FlatAstNode], declaration: FlatAstNode) -> Bool {
  for variant in nodes {
    if variant.parentId == declaration.id && variant.role == "variant" &&
       variant.kind == "variant_declaration" {
      for payload in nodes {
        if payload.parentId == variant.id && payload.role == "field_type" &&
           payload.kind == "type_list" &&
           pep_c23_union_payload_is_recursive(nodes, declaration, payload) {
          return true
        } else {}
      }
    } else {}
  }
  return false
}
fn pep_c23_union_is_recursive(nodes: List[FlatAstNode], declaration: FlatAstNode) -> Bool {
  for variant in nodes {
    if variant.parentId == declaration.id && variant.role == "variant" &&
       variant.kind == "variant_declaration" &&
       pep_c23_union_has_recursive_payload(nodes, declaration, variant) {
      return true
    } else {}
  }
  return false
}
fn pep_c23_node_by_id(nodes: List[FlatAstNode], wantedId: Int) -> PepC23NodeLookup {
  for node in nodes {
    if node.id == wantedId { return PepC23NodeLookup { found: true, node: node } } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_while_local_binding(nodes: List[FlatAstNode], ownerId: Int,
  beforeId: Int, name: Str) -> PepC23NodeLookup {
  var best = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  var bestId = -1
  for candidate in nodes {
    if candidate.parentId == ownerId && candidate.role == "body" &&
       candidate.kind == "let" && candidate.text == name &&
       !(beforeId <= candidate.id) && bestId <= candidate.id {
      best = PepC23NodeLookup { found: true, node: candidate }
      bestId = candidate.id
    } else {}
  }
  return best
}
fn pep_c23_enclosing_while_binding(nodes: List[FlatAstNode], function: FlatAstNode,
  node: FlatAstNode, name: Str) -> PepC23NodeLookup {
  var ancestorId = node.parentId
  var depth = 0
  while ancestorId != function.id && 0 <= ancestorId && !(32 <= depth) {
    let ancestor = pep_c23_node_by_id(nodes, ancestorId)
    if ancestor.found {
      if ancestor.node.kind == "while" {
        let local = pep_c23_while_local_binding(nodes, ancestor.node.id, node.id, name)
        if local.found { return local } else {}
      } else {}
      ancestorId = ancestor.node.parentId
      depth = depth + 1
    } else { ancestorId = -1 }
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_requires_arena(nodes: List[FlatAstNode]) -> Bool {
  // Arena-backed list updates allocate a fresh array per call, so the arena must exist whenever
  // one is present in the source.
  for node in nodes {
    if node.kind == "call" && (node.text == "prepend" || node.text == "reverse") { return true } else {}
  }
  for payload in nodes {
    if payload.role == "field_type" {
      let variant = pep_c23_node_by_id(nodes, payload.parentId)
      if variant.found && variant.node.kind == "variant_declaration" {
        let declaration = pep_c23_node_by_id(nodes, variant.node.parentId)
        if declaration.found && declaration.node.kind == "union_declaration" &&
           pep_c23_union_payload_is_recursive(nodes, declaration.node, payload) {
          return true
        } else {}
      } else {}
    } else {}
  }
  return false
}
fn pep_c23_union_supported_layout(nodes: List[FlatAstNode], declaration: FlatAstNode) -> Bool {
  var variantCount = 0
  var hasPayload = false
  for variant in nodes {
    if variant.parentId == declaration.id && variant.role == "variant" &&
       variant.kind == "variant_declaration" {
      variantCount = variantCount + 1
      var payloadCount = 0
      for payload in nodes {
        if payload.parentId == variant.id && payload.role == "field_type" {
          payloadCount = payloadCount + 1
          if payloadCount == 3 || !pep_c23_union_payload_type_supported_for(nodes, declaration, payload) {
            return false
          } else {}
        } else {}
      }
      if payloadCount != 0 { hasPayload = true } else {}
    } else {}
  }
  return !(variantCount <= 1) && hasPayload
}
fn pep_c23_record_list_declaration(nodes: List[FlatAstNode], node: FlatAstNode) -> PepC23NodeLookup {
  if node.kind == "list" {
    for element in nodes {
      if element.parentId == node.id && element.role == "element" && element.kind == "record" {
        return pep_c23_record_declaration(nodes, element.text)
      } else {}
    }
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  if node.kind != "type_list" { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  let elementType = pep_c23_child(nodes, node.id, "element_type", 0)
  if !elementType.found || elementType.node.kind != "type_named" {
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  return pep_c23_record_declaration(nodes, elementType.node.text)
}
fn pep_c23_union_list_declaration(nodes: List[FlatAstNode], node: FlatAstNode) -> PepC23NodeLookup {
  if node.kind != "type_list" { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  let elementType = pep_c23_child(nodes, node.id, "element_type", 0)
  if !elementType.found || elementType.node.kind != "type_named" {
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  let declaration = pep_c23_union_declaration(nodes, elementType.node.text)
  if declaration.found && pep_c23_union_has_recursive_list_payload(nodes, declaration.node) {
    return declaration
  } else {}
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_union_list_local_declaration(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for binding in nodes {
    if binding.parentId == function.id && binding.role == "statement" &&
       binding.kind == "let" && binding.text == name {
      let annotation = pep_c23_child(nodes, binding.id, "annotation", 0)
      if annotation.found { return pep_c23_union_list_declaration(nodes, annotation.node) } else {}
      return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_local_recursive_union_list_is_iterated(nodes: List[FlatAstNode],
  function: FlatAstNode, name: Str) -> Bool {
  for statement in nodes {
    if statement.parentId == function.id && statement.role == "statement" &&
       statement.kind == "for_in" {
      let iterable = pep_c23_child(nodes, statement.id, "iterable", 0)
      if iterable.found && iterable.node.kind == "name" && iterable.node.text == name {
        return true
      } else {}
    } else {}
  }
  return false
}
fn pep_c23_record_field_declaration(nodes: List[FlatAstNode], record: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == record.id && node.role == "field" && node.kind == "field_declaration" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_record_value_type(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "record" { return pep_c23_record_declaration(nodes, value.text) } else {}
  if value.kind == "call" {
    let target = pep_c23_function(nodes, value.text)
    if !target.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    if result.found && result.node.kind == "type_named" {
      return pep_c23_record_declaration(nodes, result.node.text)
    } else {}
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  if value.kind == "field_access" {
    let base = pep_c23_child(nodes, value.id, "value", 0)
    if !base.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
    let parent = pep_c23_record_value_type(nodes, function, base.node)
    if !parent.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
    let field = pep_c23_record_field_declaration(nodes, parent.node, value.text)
    if !field.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
    let fieldType = pep_c23_child(nodes, field.node.id, "type", 0)
    if !fieldType.found || fieldType.node.kind != "type_named" {
      return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
    } else {}
    return pep_c23_record_declaration(nodes, fieldType.node.text)
  } else {}
  if value.kind == "name" {
    for parameter in nodes {
      if parameter.parentId == function.id && parameter.role == "parameter" && parameter.kind == "parameter" && parameter.text == value.text {
        let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
        if parameterType.found && parameterType.node.kind == "type_named" {
          return pep_c23_record_declaration(nodes, parameterType.node.text)
        } else {}
        return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
      } else {}
    }
    for binding in nodes {
      if binding.parentId == function.id && binding.role == "statement" &&
         (binding.kind == "let" || binding.kind == "var") && binding.text == value.text {
        let initial = pep_c23_child(nodes, binding.id, "value", 0)
        if initial.found && (initial.node.kind == "record" || initial.node.kind == "call") {
          return pep_c23_record_value_type(nodes, function, initial.node)
        } else {}
        let annotation = pep_c23_child(nodes, binding.id, "annotation", 0)
        if annotation.found && annotation.node.kind == "type_named" {
          return pep_c23_record_declaration(nodes, annotation.node.text)
        } else {}
        return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
      } else {}
    }
  } else {}
  for loop in nodes {
    if loop.parentId == function.id && loop.role == "statement" && loop.kind == "for_in" && loop.text == value.text {
      let iterable = pep_c23_child(nodes, loop.id, "iterable", 0)
      if iterable.found && iterable.node.kind == "list" {
        return pep_c23_record_list_declaration(nodes, iterable.node)
      } else {}
      if iterable.found && iterable.node.kind == "name" {
        let literal = pep_c23_list_literal(nodes, function, iterable.node)
        if literal.found { return pep_c23_record_list_declaration(nodes, literal.node) } else {}
        let parameter = pep_c23_record_list_parameter(nodes, function, iterable.node.text)
        if parameter.found {
          let parameterType = pep_c23_child(nodes, parameter.node.id, "type", 0)
          if parameterType.found { return pep_c23_record_list_declaration(nodes, parameterType.node) } else {}
        } else {}
      } else {}
      return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
// A call to a zero-argument function whose DECLARED result is Str is a Str value position.
// Only the declaration is consulted here (the call path separately validates target, arity and
// body), and only `let` initialisers and name classifications use this -- say still refuses a
// direct say(<call>) so its documented double-lowering of the argument can never re-emit a
// callee body (a callee containing say would otherwise print twice).
fn pep_c23_str_result_call(nodes: List[FlatAstNode], value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind != "call" {
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  // str_concat is a BUILTIN (A1 844c8b0; seed @2ad750b): no top-level function node
  // exists for pep_c23_function to find, and it returns Str -- classify it directly so
  // let-inits and say() accept its results (Campaign G G-A2-7, source demand = the staged
  // checker's own nested diagnostic composition).
  if value.text == "str_concat" {
    return PepC23NodeLookup { found: true, node: value }
  } else {}
  let callee = pep_c23_function(nodes, value.text)
  if !callee.found {
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  let calleeResult = pep_c23_child(nodes, callee.node.id, "return_type", 0)
  if calleeResult.found && calleeResult.node.kind == "type_scalar" &&
     calleeResult.node.text == "Str" {
    return PepC23NodeLookup { found: true, node: value }
  } else {}
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
// Local-declaration hot-path variant: the CHECKER already recorded this call expression's
// type in `expressionTypes`, so the declaration lookup is unnecessary here. Measured during
// Campaign F F3: the per-call-initialiser `pep_c23_function` node scan tipped a near-ceiling
// recursive-union fixture over the fixed 100,000-step emitter budget (ablated back to passing,
// then this fact lookup restored it green). Early-exits on the syntaxId match. A missing fact
// classifies as not-Str and falls to the int64_t default, which the C compiler then refuses --
// fail-closed at the native build rather than silently wrong.
fn pep_c23_str_typed_call(checked: CheckerReport, callNode: FlatAstNode) -> PepC23NodeLookup {
  for fact in checked.expressionTypes {
    if fact.syntaxId == callNode.id {
      if fact.typeName == "Str" {
        return PepC23NodeLookup { found: true, node: callNode }
      } else {}
      return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_str_expression(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "string" { return PepC23NodeLookup { found: true, node: value } } else {}
  if value.kind == "name" {
    let parameter = pep_c23_str_parameter(nodes, function, value.text)
    if parameter.found { return parameter } else {}
    var matches = 0
    for binding in nodes {
      if binding.parentId == function.id && binding.role == "statement" &&
         binding.kind == "let" && binding.text == value.text {
        let initial = pep_c23_child(nodes, binding.id, "value", 0)
        if initial.found && initial.node.kind == "string" {
          matches = matches + 1
        } else {
          if initial.found && initial.node.kind == "field_access" &&
             pep_c23_str_expression(nodes, function, initial.node).found {
            matches = matches + 1
          } else {
            if initial.found && initial.node.kind == "name" &&
               pep_c23_str_parameter(nodes, function, initial.node.text).found {
              matches = matches + 1
            } else {
              // Str local initialised by a Str-returning call (Campaign F F3): the call was
              // emitted once at the let; say only re-emits the local NAME, so the side-effect
              // argument for double-lowering still holds.
              if initial.found && pep_c23_str_result_call(nodes, initial.node).found {
                matches = matches + 1
              } else {}
            }
          }
        }
      } else {}
    }
    if matches == 1 { return PepC23NodeLookup { found: true, node: value } } else {}
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  // Direct str_concat CALLS classify too (G-A2-7): the two-arg dispatch validates its
  // arguments through this function, and only the bump-pool builtin is added -- Str-returning
  // user FUNCTIONS stay refused here, which is exactly the pinned say(<Str call>) boundary
  // from F3 (a callee body could contain say, and say re-lowers its argument twice).
  if value.kind == "call" && value.text == "str_concat" {
    return PepC23NodeLookup { found: true, node: value }
  } else {}
  if value.kind == "field_access" {
    let owner = pep_c23_child(nodes, value.id, "value", 0)
    if !owner.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
    let record = pep_c23_record_value_type(nodes, function, owner.node)
    if !record.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
    let field = pep_c23_record_field_declaration(nodes, record.node, value.text)
    if !field.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
    let fieldType = pep_c23_child(nodes, field.node.id, "type", 0)
    if fieldType.found && fieldType.node.kind == "type_scalar" && fieldType.node.text == "Str" {
      return PepC23NodeLookup { found: true, node: value }
    } else {}
  } else {}
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_string_literal(nodes: List[FlatAstNode], node: FlatAstNode) -> PepC23Emission {
  let source = source_bytes()
  let sourceLength = byte_length(source)
  if node.startByte <= -1 || node.endByte <= 0 ||
     node.endByte - node.startByte <= 1 || sourceLength <= node.endByte - 1 {
    return pep_c23_unsupported("Pep C23 string literal span is outside the authorized source")
  } else {}
  if byte_at(source, node.startByte) != 34 || byte_at(source, node.endByte - 1) != 34 {
    return pep_c23_unsupported("Pep C23 string literal span does not include matching quotes")
  } else {}
  let contentEnd = node.endByte - 1
  // Fast path: a literal that contains no backslash and no quote can be emitted verbatim as one C
  // string literal, which costs a constant number of list operations instead of two per byte.
  // The slow path below stays for literals that need escape decoding.
  let contentStart = node.startByte + 1
  var verbatim = true
  var scan = contentStart
  while !(contentEnd <= scan) {
    let scanned = byte_at(source, scan)
    if scanned == 92 || scanned == 34 { verbatim = false } else {}
    scan = scan + 1
  }
  if verbatim {
    let content = utf8_slice(source, contentStart, contentEnd)
    // Pointer cast to the STRING LITERAL itself: a string literal has static storage duration,
    // so a pep_str carrying it stays valid after the creating function returns. The previous
    // block-scope compound-literal array died at the closing brace -- measured during Campaign
    // F F3: a Str-result function returning one printed garbage under clang and GCC refused
    // -Wdangling-pointer under -Werror. Same bytes, same explicit .length.
    return PepC23Emission { status: "emitted",
      sourceParts: ["(pep_str){ .data = (const unsigned char *)\"", content,
                    "\", .length = ", int_text(contentEnd - contentStart), " }"],
      diagnostic: "" }
  } else {}
  var offset = node.startByte + 1
  var byteCount = 0
  // Build the byte list with prepend only. A singly linked list makes prepend cheap and append
  // O(n), so emitting one append per byte was quadratic in literal length, and a long literal
  // exhausted the emitter's step budget. One reverse at the end restores the order.
  var reversedValues: List[Str] = []
  while !(contentEnd <= offset) {
    var value = byte_at(source, offset)
    if value == 92 {
      offset = offset + 1
      if contentEnd <= offset {
        return pep_c23_unsupported("Pep C23 string literal ends with an incomplete escape")
      } else {}
      let escaped = byte_at(source, offset)
      if escaped == 110 { value = 10 } else {
        if escaped == 114 { value = 13 } else {
          if escaped == 116 { value = 9 } else {
            if escaped == 48 { value = 0 } else {
              if escaped == 92 { value = 92 } else {
                if escaped == 34 { value = 34 } else {
                  return pep_c23_unsupported("Pep C23 string literal uses an unsupported escape")
                }
              }
            }
          }
        }
      }
    } else {}
    // Three-digit octal instead of decimal: fixed width makes each escape unambiguous and
    // covers every byte value including NUL and quote. The group is prepended backslash, high,
    // mid, low so the tail's single reversal emits `\ H M L` forward. The result is a STRING
    // LITERAL (static storage), required so a pep_str returned from a function outlives the
    // callee frame -- the measured dangling-pointer failure of the compound-array form.
    // Only / * - are used; the emitter never relies on an operator this file has not used.
    let highDigit = value / 64
    let midDigit = (value - (highDigit * 64)) / 8
    let lowDigit = value - ((value / 8) * 8)
    reversedValues = prepend(reversedValues, "\\")
    reversedValues = prepend(reversedValues, int_text(highDigit))
    reversedValues = prepend(reversedValues, int_text(midDigit))
    reversedValues = prepend(reversedValues, int_text(lowDigit))
    byteCount = byteCount + 1
    offset = offset + 1
  }
  var reversed: List[Str] = [" }"]
  reversed = prepend(reversed, int_text(byteCount))
  reversed = prepend(reversed, "\", .length = ")
  if byteCount == 0 {
    // The header already emitted the opening quote; one closing quote makes an empty literal.
    reversed = prepend(reversed, "\"")
  } else {
    for part in reversedValues { reversed = prepend(reversed, part) }
  }
  reversed = prepend(reversed, "(pep_str){ .data = (const unsigned char *)\"")
  // The list is already in forward order: prepend builds it back to front from the tail, and each
  // prepend of a stored value restores that value's position. Reversing here would emit the bytes
  // backwards, which compiles but produces wrong string contents.
  return PepC23Emission { status: "emitted", sourceParts: reversed, diagnostic: "" }
}
fn pep_c23_union_value_type(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "call" {
    let variant = pep_c23_union_variant(nodes, value.text)
    if variant.found { return pep_c23_union_of_variant(nodes, variant.node) } else {}
    let target = pep_c23_function(nodes, value.text)
    if !target.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    if result.found && result.node.kind == "type_named" {
      return pep_c23_union_declaration(nodes, result.node.text)
    } else {}
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  if value.kind == "name" {
    for parameter in nodes {
      if parameter.parentId == function.id && parameter.role == "parameter" &&
         parameter.kind == "parameter" && parameter.text == value.text {
        let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
        if parameterType.found && parameterType.node.kind == "type_named" {
          return pep_c23_union_declaration(nodes, parameterType.node.text)
        } else {}
        return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
      } else {}
    }
    for binding in nodes {
      if binding.parentId == function.id && binding.role == "statement" &&
         (binding.kind == "let" || binding.kind == "var") && binding.text == value.text {
        let initial = pep_c23_child(nodes, binding.id, "value", 0)
        if initial.found && initial.node.kind == "call" {
          let inferred = pep_c23_union_value_type(nodes, function, initial.node)
          if inferred.found { return inferred } else {}
        } else {}
        let annotation = pep_c23_child(nodes, binding.id, "annotation", 0)
        if annotation.found && annotation.node.kind == "type_named" {
          return pep_c23_union_declaration(nodes, annotation.node.text)
        } else {}
        return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
      } else {}
    }
    for loop in nodes {
      if loop.parentId == function.id && loop.role == "statement" &&
         loop.kind == "for_in" && loop.text == value.text {
        let iterable = pep_c23_child(nodes, loop.id, "iterable", 0)
        if iterable.found && iterable.node.kind == "name" {
          let parameter = pep_c23_union_list_parameter(nodes, function, iterable.node.text)
          if parameter.found {
            let parameterType = pep_c23_child(nodes, parameter.node.id, "type", 0)
            if parameterType.found {
              return pep_c23_union_list_declaration(nodes, parameterType.node)
            } else {}
          } else {
            let local = pep_c23_union_list_local_declaration(nodes, function, iterable.node.text)
            if local.found { return local } else {}
          }
        } else {}
        return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
      } else {}
    }
  } else {}
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_c_parameter_type(nodes: List[FlatAstNode], node: FlatAstNode) -> Str {
  if node.kind == "type_scalar" {
    if node.text == "Str" { return "pep_str" } else {}
    if node.text == "SourceBytes" { return "pep_source_bytes" } else {}
    return pep_c23_c_scalar_type(node)
  } else {}
  if node.kind == "type_named" {
    let declaration = pep_c23_record_declaration(nodes, node.text)
    if declaration.found { return "pep_record" } else {}
    let unionType = pep_c23_union_declaration(nodes, node.text)
    if unionType.found { return "pep_union" } else {}
  } else {}
  if node.kind == "type_list" {
    let elementType = pep_c23_child(nodes, node.id, "element_type", 0)
    if elementType.found && elementType.node.kind == "type_named" &&
       pep_c23_record_declaration(nodes, elementType.node.text).found {
      return "pep_list_record"
    } else {}
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Int" {
      return "pep_list_int"
    } else {}
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Bool" {
      return "pep_list_bool"
    } else {}
    if elementType.found && elementType.node.kind == "type_scalar" && elementType.node.text == "Str" {
      return "pep_list_str"
    } else {}
    if elementType.found && elementType.node.kind == "type_named" {
      let unionType = pep_c23_union_declaration(nodes, elementType.node.text)
      if unionType.found && pep_c23_union_is_recursive(nodes, unionType.node) {
        return "pep_list_union"
      } else {}
    } else {}
  } else {}
  return ""
}
fn pep_c23_c_parameter_type_parts(nodes: List[FlatAstNode], node: FlatAstNode) -> List[Str] {
  if node.kind == "type_list" {
    let declaration = pep_c23_record_list_declaration(nodes, node)
    if declaration.found { return ["pep_list_record_", int_text(declaration.node.id)] } else {}
    let elementType = pep_c23_child(nodes, node.id, "element_type", 0)
    if elementType.found && elementType.node.kind == "type_named" {
      let unionType = pep_c23_union_declaration(nodes, elementType.node.text)
      if unionType.found && pep_c23_union_is_recursive(nodes, unionType.node) {
        return ["pep_list_union_", int_text(unionType.node.id)]
      } else {}
    } else {}
  } else {}
  if node.kind == "type_named" {
    let declaration = pep_c23_record_declaration(nodes, node.text)
    if declaration.found { return ["pep_record_", int_text(declaration.node.id)] } else {}
    let unionType = pep_c23_union_declaration(nodes, node.text)
    if unionType.found { return ["pep_union_", int_text(unionType.node.id)] } else {}
  } else {}
  let cType = pep_c23_c_parameter_type(nodes, node)
  if cType == "" { return [] } else { return [cType] }
}

// Accept checked Int functions with zero, one or two Int parameters and pure arithmetic expressions.
// Checked C23 helpers preserve Pep overflow and division-by-zero errors; unsupported syntax fails closed.
fn pep_c23_function(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == -1 && node.kind == "function" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
fn pep_c23_last_statement(nodes: List[FlatAstNode], function: FlatAstNode) -> PepC23NodeLookup {
  var lastStatement = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  for candidate in nodes {
    if candidate.parentId == function.id && candidate.role == "statement" {
      lastStatement = PepC23NodeLookup { found: true, node: candidate }
    } else {}
  }
  return lastStatement
}
// A list record field accepts a list literal, or a same-typed list parameter forwarded by value.
// Forwarding copies the descriptor only, so the caller keeps ownership of the element storage.
fn pep_c23_list_parameter_of_type(nodes: List[FlatAstNode], function: FlatAstNode, name: Str,
  declaredType: FlatAstNode) -> PepC23NodeLookup {
  let wantedElement = pep_c23_child(nodes, declaredType.id, "element_type", 0)
  if !wantedElement.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  for parameter in nodes {
    if parameter.parentId == function.id && parameter.role == "parameter" &&
       parameter.kind == "parameter" && parameter.text == name {
      let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
      if !parameterType.found || parameterType.node.kind != "type_list" {
        return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
      } else {}
      let actualElement = pep_c23_child(nodes, parameterType.node.id, "element_type", 0)
      if !actualElement.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
      if actualElement.node.kind == wantedElement.node.kind && actualElement.node.text == wantedElement.node.text {
        return PepC23NodeLookup { found: true, node: parameter }
      } else {}
      return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
// True when a value cannot fail at runtime. A string literal lowers to static bytes, and a list
// literal can only fail through its elements, so neither constrains C's unspecified evaluation
// order for record fields or call arguments. Used only by record construction and the
// three-or-more-argument call path, so programs that use neither pay no extra execution steps.
fn pep_c23_infallible_value(nodes: List[FlatAstNode], node: FlatAstNode) -> Bool {
  if node.kind == "string" { return false } else {}
  // A record constructor is infallible when every supplied field value is, which is what makes a
  // zero-argument constructor returning a record with literal list fields safe to call.
  if node.kind == "record" {
    for supplied in nodes {
      if supplied.parentId == node.id && supplied.role == "field" && supplied.kind == "record_field" {
        let suppliedValue = pep_c23_child(nodes, supplied.id, "value", 0)
        if !suppliedValue.found { return true } else {}
        if pep_c23_infallible_value(nodes, suppliedValue.node) { return true } else {}
      } else {}
    }
    return false
  } else {}
  if node.kind == "list" {
    for element in nodes {
      if element.parentId == node.id && element.role == "element" {
        if pep_c23_infallible_value(nodes, element) { return true } else {}
      } else {}
    }
    return false
  } else {}
  return pep_c23_expression_may_fail(nodes, node)
}
fn pep_c23_expression_may_fail(nodes: List[FlatAstNode], node: FlatAstNode) -> Bool {
  if node.kind == "integer" || node.kind == "boolean" || node.kind == "name" { return false } else {}
  if node.kind == "field_access" {
    let value = pep_c23_child(nodes, node.id, "value", 0)
    return !value.found || pep_c23_expression_may_fail(nodes, value.node)
  } else {}
  if node.kind == "record" {
    for field in nodes {
      if field.parentId == node.id && field.role == "field" {
        let value = pep_c23_child(nodes, field.id, "value", 0)
        if !value.found || pep_c23_expression_may_fail(nodes, value.node) { return true } else {}
      } else {}
    }
    return false
  } else {}
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
// A call ARGUMENT that is a pure function of the caller's parameters and literals:
// parameter names, literals, and binary/unary combinations of those. Deliberately
// EXCLUDES nested calls -- two fallible calls in one expression have unspecified C
// evaluation order, which is the same rule the multi-argument paths already enforce.
// This is what lets a callee body such as `return f(n - 1) + 1` pass the call-result
// purity gate: the argument is computed, but it is still a pure function of `n`.
fn pep_c23_parameter_value_expression(nodes: List[FlatAstNode], function: FlatAstNode, parameterName: Str, secondParameterName: Str, node: FlatAstNode) -> Bool {
  if node.kind == "integer" { return true } else {}
  if node.kind == "string" { return true } else {}
  if node.kind == "boolean" { return true } else {}
  if node.kind == "name" {
    return node.text == parameterName || (secondParameterName != "" && node.text == secondParameterName)
  } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    return left.found && right.found &&
      pep_c23_parameter_value_expression(nodes, function, parameterName, secondParameterName, left.node) &&
      pep_c23_parameter_value_expression(nodes, function, parameterName, secondParameterName, right.node)
  } else {}
  if node.kind == "unary" {
    let operand = pep_c23_child(nodes, node.id, "operand", 0)
    return operand.found && pep_c23_parameter_value_expression(nodes, function, parameterName, secondParameterName, operand.node)
  } else {}
  return false
}
fn pep_c23_parameter_expression(nodes: List[FlatAstNode], function: FlatAstNode, parameterName: Str, secondParameterName: Str, node: FlatAstNode) -> Bool {
  if node.kind == "match" {
    let subject = pep_c23_child(nodes, node.id, "value", 0)
    return subject.found && subject.node.kind == "name" &&
      (subject.node.text == parameterName || subject.node.text == secondParameterName)
  } else {}
  if node.kind == "integer" { return true } else {}
  // A literal constant references nothing and cannot fail, so it keeps a callee's result
  // parameter-dependent in the only sense this gate cares about. Without this, a constructor
  // whose record has a literal field could not be called with a parameter at all.
  if node.kind == "string" { return true } else {}
  if node.kind == "boolean" { return true } else {}
  if node.kind == "name" { return node.text == parameterName || node.text == secondParameterName } else {}
  if node.kind == "field_access" {
    let value = pep_c23_child(nodes, node.id, "value", 0)
    let parentRecord = if value.found {
      pep_c23_record_value_type(nodes, function, value.node)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    let field = if parentRecord.found {
      pep_c23_record_field_declaration(nodes, parentRecord.node, node.text)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    return value.found &&
      pep_c23_parameter_expression(nodes, function, parameterName, secondParameterName, value.node) &&
      parentRecord.found && field.found
  } else {}
  if node.kind == "record" {
    let declaration = pep_c23_record_declaration(nodes, node.text)
    if !declaration.found { return false } else {}
    var fieldCount = 0
    for supplied in nodes {
      if supplied.parentId == node.id && supplied.role == "field" && supplied.kind == "record_field" {
        let declared = pep_c23_record_field_declaration(nodes, declaration.node, supplied.text)
        let fieldType = if declared.found {
          pep_c23_child(nodes, declared.node.id, "type", 0)
        } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
        let value = pep_c23_child(nodes, supplied.id, "value", 0)
        if !declared.found || !fieldType.found ||
           pep_c23_c_record_field_type(nodes, declaration.node, fieldType.node) == "" ||
           !value.found ||
           !pep_c23_parameter_expression(nodes, function, parameterName, secondParameterName, value.node) {
          return false
        } else {}
        fieldCount = fieldCount + 1
      } else {}
    }
    return !(fieldCount <= 0)
  } else {}
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
    let firstParameter = pep_c23_child(nodes, function.id, "parameter", 0)
    let firstParameterType = if firstParameter.found { pep_c23_child(nodes, firstParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    let firstParameterIsBoolList = firstParameter.found && firstParameter.node.text == parameterName && firstParameterType.found &&
      pep_c23_c_parameter_type(nodes, firstParameterType.node) == "pep_list_bool"
    let secondArgumentMatches = (secondParameterName != "" && secondArgument.found &&
      secondArgument.node.kind == "name" && secondArgument.node.text == secondParameterName) ||
      (secondParameterName == "" && firstParameterIsBoolList && secondArgument.found && secondArgument.node.kind == "boolean")
    return argument.found && secondArgumentMatches && !extraArgument.found &&
      argument.node.kind == "name" && argument.node.text == parameterName
  } else {}
  if node.kind == "call" {
    let argument = pep_c23_child(nodes, node.id, "argument", 0)
    let extraArgument = pep_c23_child(nodes, node.id, "argument", 1)
    // The argument may be a bare parameter name (the original shape) OR a computed
    // value over parameters and literals. Both are pure functions of the parameters,
    // which is all this gate claims. Nested calls stay refused: two fallible calls in
    // one expression have unspecified C evaluation order.
    return argument.found && !extraArgument.found &&
      pep_c23_parameter_value_expression(nodes, function, parameterName, secondParameterName, argument.node)
  } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    return left.found && right.found &&
      pep_c23_parameter_expression(nodes, function, parameterName, secondParameterName, left.node) &&
      pep_c23_parameter_expression(nodes, function, parameterName, secondParameterName, right.node)
  } else {}
  if node.kind == "unary" {
    let operand = pep_c23_child(nodes, node.id, "operand", 0)
    return operand.found && pep_c23_parameter_expression(nodes, function, parameterName, secondParameterName, operand.node)
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
fn pep_c23_union_constructor(nodes: List[FlatAstNode], function: FlatAstNode,
  node: FlatAstNode, variant: FlatAstNode) -> PepC23Emission {
  let declaration = pep_c23_union_of_variant(nodes, variant)
  if !declaration.found || !pep_c23_union_supported_layout(nodes, declaration.node) {
    return pep_c23_unsupported("Pep C23 tagged union has an unsupported layout")
  } else {}
  let payloadCount = pep_c23_count_children(nodes, variant.id, "field_type")
  let argumentCount = pep_c23_count_children(nodes, node.id, "argument")
  if payloadCount != argumentCount {
    return pep_c23_unsupported("Pep C23 payload constructor argument count must match the variant")
  } else {}
  if pep_c23_union_has_recursive_payload(nodes, declaration.node, variant) {
    if !pep_c23_requires_arena(nodes) {
      return pep_c23_unsupported("Pep C23 recursive union construction requires an arena")
    } else {}
    var recursiveParts: List[Str] = ["pep_make_union_", int_text(declaration.node.id), "_", int_text(variant.childIndex), "("]
    var recursiveArgumentCount = 0
    var recursiveFallibleCount = 0
    for payloadType in nodes {
      if payloadType.parentId == variant.id && payloadType.role == "field_type" {
        let argument = pep_c23_child(nodes, node.id, "argument", payloadType.childIndex)
        if !argument.found { return pep_c23_unsupported("Pep C23 recursive constructor payload argument is missing") } else {}
        if pep_c23_expression_may_fail(nodes, argument.node) {
          recursiveFallibleCount = recursiveFallibleCount + 1
        } else {}
        if recursiveFallibleCount == 2 {
          return pep_c23_unsupported("Pep C23 rejects multiple fallible recursive constructor arguments because C evaluation order is unspecified")
        } else {}
        let value = pep_c23_call_argument(nodes, function, argument.node,
          PepC23NodeLookup { found: true, node: payloadType })
        if value.status != "emitted" { return value } else {}
        if recursiveArgumentCount != 0 { recursiveParts = append(recursiveParts, ", ") } else {}
        for part in value.sourceParts { recursiveParts = append(recursiveParts, part) }
        recursiveArgumentCount = recursiveArgumentCount + 1
      } else {}
    }
    if recursiveArgumentCount != 0 { recursiveParts = append(recursiveParts, ", ") } else {}
    recursiveParts = append(recursiveParts, "pep_arena)")
    return PepC23Emission { status: "emitted", sourceParts: recursiveParts, diagnostic: "" }
  } else {}
  var parts: List[Str] = ["(pep_union_", int_text(declaration.node.id), "){ .tag = ", int_text(variant.childIndex)]
  if payloadCount != 0 {
    parts = append(parts, ", .payload.payload_")
    parts = append(parts, int_text(variant.childIndex))
    parts = append(parts, " = { ")
    var emittedCount = 0
    var fallibleArgumentCount = 0
    for payloadType in nodes {
      if payloadType.parentId == variant.id && payloadType.role == "field_type" {
        if !pep_c23_union_payload_type_supported_for(nodes, declaration.node, payloadType) {
          return pep_c23_unsupported("Pep C23 constructor payload type is unsupported")
        } else {}
        let argument = pep_c23_child(nodes, node.id, "argument", payloadType.childIndex)
        if !argument.found { return pep_c23_unsupported("Pep C23 constructor payload argument is missing") } else {}
        if pep_c23_expression_may_fail(nodes, argument.node) {
          fallibleArgumentCount = fallibleArgumentCount + 1
        } else {}
        if fallibleArgumentCount == 2 {
          return pep_c23_unsupported("Pep C23 rejects multiple fallible constructor arguments because C evaluation order is unspecified")
        } else {}
        let value = pep_c23_expression(nodes, function, argument.node)
        if value.status != "emitted" { return value } else {}
        if emittedCount != 0 { parts = append(parts, ", ") } else {}
        parts = append(parts, ".field_")
        parts = append(parts, int_text(payloadType.childIndex))
        parts = append(parts, " = ")
        for part in value.sourceParts { parts = append(parts, part) }
        emittedCount = emittedCount + 1
      } else {}
    }
    parts = append(parts, " }")
  } else {}
  parts = append(parts, " }")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_union_constructor_helper_source(nodes: List[FlatAstNode], declaration: FlatAstNode,
  variant: FlatAstNode) -> List[Str] {
  var parts: List[Str] = ["[[maybe_unused]] static pep_union_", int_text(declaration.id), " pep_make_union_",
    int_text(declaration.id), "_", int_text(variant.childIndex), "("]
  var argumentCount = 0
  for payloadType in nodes {
    if payloadType.parentId == variant.id && payloadType.role == "field_type" {
      if argumentCount != 0 { parts = append(parts, ", ") } else {}
      for typePart in pep_c23_c_parameter_type_parts(nodes, payloadType) { parts = append(parts, typePart) }
      parts = append(parts, " pep_ctor_arg_")
      parts = append(parts, int_text(payloadType.childIndex))
      argumentCount = argumentCount + 1
    } else {}
  }
  if argumentCount != 0 { parts = append(parts, ", ") } else {}
  parts = append(parts, "pep_arena_t *pep_arena) {\n")
  for payloadType in nodes {
    if payloadType.parentId == variant.id && payloadType.role == "field_type" &&
       payloadType.kind == "type_named" && payloadType.text == declaration.text {
      parts = append(parts, "  pep_union_")
      parts = append(parts, int_text(declaration.id))
      parts = append(parts, " *pep_recursive_")
      parts = append(parts, int_text(payloadType.childIndex))
      parts = append(parts, " = pep_arena_alloc(pep_arena, sizeof(pep_union_")
      parts = append(parts, int_text(declaration.id))
      parts = append(parts, "), _Alignof(pep_union_")
      parts = append(parts, int_text(declaration.id))
      parts = append(parts, "));\n  if (pep_recursive_")
      parts = append(parts, int_text(payloadType.childIndex))
      parts = append(parts, " == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  *pep_recursive_")
      parts = append(parts, int_text(payloadType.childIndex))
      parts = append(parts, " = pep_ctor_arg_")
      parts = append(parts, int_text(payloadType.childIndex))
      parts = append(parts, ";\n")
    } else {
      if payloadType.parentId == variant.id && payloadType.role == "field_type" &&
         payloadType.kind == "type_list" &&
         pep_c23_union_payload_is_recursive(nodes, declaration, payloadType) {
        let fieldIndex = int_text(payloadType.childIndex)
        let unionId = int_text(declaration.id)
        parts = append(parts, "  pep_union_")
        parts = append(parts, unionId)
        parts = append(parts, " *pep_recursive_list_")
        parts = append(parts, fieldIndex)
        parts = append(parts, " = NULL;\n  if (pep_ctor_arg_")
        parts = append(parts, fieldIndex)
        parts = append(parts, ".length != 0 && pep_ctor_arg_")
        parts = append(parts, fieldIndex)
        parts = append(parts, ".data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_ctor_arg_")
        parts = append(parts, fieldIndex)
        parts = append(parts, ".length > SIZE_MAX / sizeof(pep_union_")
        parts = append(parts, unionId)
        parts = append(parts, ")) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  if (pep_ctor_arg_")
        parts = append(parts, fieldIndex)
        parts = append(parts, ".length != 0) {\n    pep_recursive_list_")
        parts = append(parts, fieldIndex)
        parts = append(parts, " = pep_arena_alloc(pep_arena, pep_ctor_arg_")
        parts = append(parts, fieldIndex)
        parts = append(parts, ".length * sizeof(pep_union_")
        parts = append(parts, unionId)
        parts = append(parts, "), _Alignof(pep_union_")
        parts = append(parts, unionId)
        parts = append(parts, "));\n    if (pep_recursive_list_")
        parts = append(parts, fieldIndex)
        parts = append(parts, " == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n    for (size_t pep_i = 0; pep_i < pep_ctor_arg_")
        parts = append(parts, fieldIndex)
        parts = append(parts, ".length; ++pep_i) { pep_recursive_list_")
        parts = append(parts, fieldIndex)
        parts = append(parts, "[pep_i] = pep_ctor_arg_")
        parts = append(parts, fieldIndex)
        parts = append(parts, ".data[pep_i]; }\n  }\n")
      } else {}
    }
  }
  parts = append(parts, "  return (pep_union_")
  parts = append(parts, int_text(declaration.id))
  parts = append(parts, "){ .tag = ")
  parts = append(parts, int_text(variant.childIndex))
  parts = append(parts, ", .payload.payload_")
  parts = append(parts, int_text(variant.childIndex))
  parts = append(parts, " = { ")
  var fieldCount = 0
  for payloadType in nodes {
    if payloadType.parentId == variant.id && payloadType.role == "field_type" {
      if fieldCount != 0 { parts = append(parts, ", ") } else {}
      parts = append(parts, ".field_")
      parts = append(parts, int_text(payloadType.childIndex))
      parts = append(parts, " = ")
      if payloadType.kind == "type_named" && payloadType.text == declaration.text {
        parts = append(parts, "pep_recursive_")
        parts = append(parts, int_text(payloadType.childIndex))
      } else {
        if payloadType.kind == "type_list" &&
           pep_c23_union_payload_is_recursive(nodes, declaration, payloadType) {
          parts = append(parts, "(pep_list_union_")
          parts = append(parts, int_text(declaration.id))
          parts = append(parts, "){ .data = pep_recursive_list_")
          parts = append(parts, int_text(payloadType.childIndex))
          parts = append(parts, ", .length = pep_ctor_arg_")
          parts = append(parts, int_text(payloadType.childIndex))
          parts = append(parts, ".length }")
        } else {
          parts = append(parts, "pep_ctor_arg_")
          parts = append(parts, int_text(payloadType.childIndex))
        }
      }
      fieldCount = fieldCount + 1
    } else {}
  }
  parts = append(parts, " } };\n}\n")
  return parts
}
fn pep_c23_recursive_union_guard_source(declaration: FlatAstNode) -> List[Str] {
  let id = int_text(declaration.id)
  return ["[[maybe_unused]] static pep_union_", id, " pep_require_union_", id,
    "(const pep_union_", id, " *pep_value) {\n  if (pep_value == NULL) { fputs(\"PEP_RUNTIME_INVALID_UNION\\n\", stderr); exit(1); }\n  return *pep_value;\n}\n"]
}
fn pep_c23_union_payload_parts(subject: List[Str], variant: FlatAstNode,
  payloadCount: Int, payloadIndex: Int, field: PepC23NodeLookup,
  dereference: Bool) -> List[Str] {
  var parts: List[Str] = []
  if dereference {
    parts = append(parts, "pep_require_union_")
    parts = append(parts, int_text(variant.parentId))
    parts = append(parts, "(")
  } else {}
  for part in subject { parts = append(parts, part) }
  parts = append(parts, ".payload.payload_")
  parts = append(parts, int_text(variant.childIndex))
  parts = append(parts, ".field_")
  parts = append(parts, int_text(payloadIndex))
  if field.found {
    parts = append(parts, ".pep_field_")
    parts = append(parts, int_text(field.node.childIndex))
  } else {}
  if dereference { parts = append(parts, ")") } else {}
  return parts
}
fn pep_c23_union_two_payload_operand(nodes: List[FlatAstNode],
  subject: List[Str], declaration: FlatAstNode, variant: FlatAstNode,
  firstPattern: FlatAstNode, secondPattern: FlatAstNode,
  operand: FlatAstNode) -> PepC23Emission {
  var bindingName = ""
  var wantsLength = false
  if operand.kind == "name" {
    bindingName = operand.text
  } else {
    if operand.kind == "call" && operand.text == "length" {
      let lengthArgument = pep_c23_child(nodes, operand.id, "argument", 0)
      let extraArgument = pep_c23_child(nodes, operand.id, "argument", 1)
      if !lengthArgument.found || lengthArgument.node.kind != "name" || extraArgument.found {
        return pep_c23_unsupported("Pep C23 recursive union addition requires a direct child-list length binding")
      } else {}
      bindingName = lengthArgument.node.text
      wantsLength = true
    } else {
      return pep_c23_unsupported("Pep C23 recursive union addition requires a scalar binding or child-list length")
    }
  }
  let firstMatches = firstPattern.kind == "binding_pattern" && firstPattern.text == bindingName
  let secondMatches = secondPattern.kind == "binding_pattern" && secondPattern.text == bindingName
  if firstMatches == secondMatches {
    return pep_c23_unsupported("Pep C23 recursive union addition binding must identify exactly one pattern field")
  } else {}
  let payloadIndex = if firstMatches { 0 } else { 1 }
  let payload = pep_c23_child(nodes, variant.id, "field_type", payloadIndex)
  if !payload.found {
    return pep_c23_unsupported("Pep C23 recursive union addition payload field is missing")
  } else {}
  if wantsLength {
    if payload.node.kind != "type_list" ||
       !pep_c23_union_payload_is_recursive(nodes, declaration, payload.node) {
      return pep_c23_unsupported("Pep C23 recursive union addition length binding must be List[Self]")
    } else {}
  } else {
    if pep_c23_c_scalar_type(payload.node) != "int64_t" {
      return pep_c23_unsupported("Pep C23 recursive union addition scalar binding must be Int")
    } else {}
  }
  var parts = pep_c23_union_payload_parts(subject, variant, 2, payloadIndex,
    PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }, false)
  if wantsLength {
    parts = prepend(parts, "pep_checked_length(")
    parts = append(parts, ".length)")
  } else {}
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_union_payload_record_path_type(nodes: List[FlatAstNode],
  payloadRecord: FlatAstNode, bindingName: Str, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "name" {
    if value.text == bindingName {
      return PepC23NodeLookup { found: true, node: payloadRecord }
    } else {}
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  if value.kind != "field_access" {
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  let base = pep_c23_child(nodes, value.id, "value", 0)
  if !base.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  let parentRecord = pep_c23_union_payload_record_path_type(nodes, payloadRecord,
    bindingName, base.node)
  if !parentRecord.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  let field = pep_c23_record_field_declaration(nodes, parentRecord.node, value.text)
  let fieldType = if field.found {
    pep_c23_child(nodes, field.node.id, "type", 0)
  } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  if !field.found || !fieldType.found || fieldType.node.kind != "type_named" {
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  return pep_c23_record_declaration(nodes, fieldType.node.text)
}
fn pep_c23_union_payload_record_path_parts(nodes: List[FlatAstNode],
  payloadRecord: FlatAstNode, bindingName: Str, value: FlatAstNode) -> List[Str] {
  if value.kind == "name" && value.text == bindingName { return [] } else {}
  if value.kind != "field_access" { return [] } else {}
  let base = pep_c23_child(nodes, value.id, "value", 0)
  if !base.found { return [] } else {}
  let parentRecord = pep_c23_union_payload_record_path_type(nodes, payloadRecord,
    bindingName, base.node)
  if !parentRecord.found { return [] } else {}
  let field = pep_c23_record_field_declaration(nodes, parentRecord.node, value.text)
  if !field.found { return [] } else {}
  var parts = pep_c23_union_payload_record_path_parts(nodes, payloadRecord,
    bindingName, base.node)
  parts = append(parts, ".pep_field_")
  parts = append(parts, int_text(field.node.childIndex))
  return parts
}
fn pep_c23_union_match_expression(nodes: List[FlatAstNode], function: FlatAstNode,
  node: FlatAstNode) -> PepC23Emission {
  let subject = pep_c23_child(nodes, node.id, "value", 0)
  if !subject.found || subject.node.kind != "name" {
    return pep_c23_unsupported("Pep C23 tagged-union match currently requires a named subject")
  } else {}
  let declaration = pep_c23_union_value_type(nodes, function, subject.node)
  if !declaration.found || !pep_c23_union_supported_layout(nodes, declaration.node) {
    return pep_c23_unsupported("Pep C23 tagged-union match requires a supported layout")
  } else {}
  let variantCount = pep_c23_count_children(nodes, declaration.node.id, "variant")
  var armCount = 0
  for candidate in nodes {
    if candidate.parentId == node.id && candidate.role == "arm" && candidate.kind == "match_arm" {
      armCount = armCount + 1
    } else {}
  }
  if armCount != variantCount {
    return pep_c23_unsupported("Pep C23 tagged-union match must cover every constructor exactly once")
  } else {}
  let loweredSubject = pep_c23_expression(nodes, function, subject.node)
  if loweredSubject.status != "emitted" { return loweredSubject } else {}
  var parts: List[Str] = ["("]
  var remaining = variantCount
  var matchedCount = 0
  for variant in nodes {
    if variant.parentId == declaration.node.id && variant.role == "variant" &&
       variant.kind == "variant_declaration" {
      var arm = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
      for candidate in nodes {
        if candidate.parentId == node.id && candidate.role == "arm" && candidate.kind == "match_arm" {
          let pattern = pep_c23_child(nodes, candidate.id, "pattern", 0)
          if !pattern.found || pattern.node.kind != "constructor_pattern" {
            return pep_c23_unsupported("Pep C23 match bare identifiers are bindings, not nullary constructors")
          } else {}
          if pattern.node.text == variant.text {
            if arm.found { return pep_c23_unsupported("Pep C23 match repeats a constructor pattern") } else {}
            arm = PepC23NodeLookup { found: true, node: candidate }
          } else {}
        } else {}
      }
      if !arm.found { return pep_c23_unsupported("Pep C23 tagged-union match must cover each constructor exactly once") } else {}
      let pattern = pep_c23_child(nodes, arm.node.id, "pattern", 0)
      let patternArgument = pep_c23_child(nodes, pattern.node.id, "argument", 0)
      let payloadType = pep_c23_child(nodes, variant.id, "field_type", 0)
      let secondPayloadType = pep_c23_child(nodes, variant.id, "field_type", 1)
      let result = pep_c23_child(nodes, arm.node.id, "result", 1)
      if !result.found { return pep_c23_unsupported("Pep C23 match arm has no result") } else {}
      var resultParts: List[Str] = []
      if payloadType.found {
        if secondPayloadType.found {
          let secondPatternArgument = pep_c23_child(nodes, pattern.node.id, "argument", 1)
          let thirdPatternArgument = pep_c23_child(nodes, pattern.node.id, "argument", 2)
          let thirdPayloadType = pep_c23_child(nodes, variant.id, "field_type", 2)
          if !patternArgument.found || !secondPatternArgument.found ||
             thirdPayloadType.found || thirdPatternArgument.found ||
             (patternArgument.node.kind != "binding_pattern" && patternArgument.node.kind != "wildcard_pattern") ||
             (secondPatternArgument.node.kind != "binding_pattern" && secondPatternArgument.node.kind != "wildcard_pattern") ||
             !pep_c23_union_payload_type_supported_for(nodes, declaration.node, payloadType.node) ||
             !pep_c23_union_payload_type_supported_for(nodes, declaration.node, secondPayloadType.node) {
            return pep_c23_unsupported("Pep C23 payload patterns require bindings or wildcards matching a supported constructor layout")
          } else {}
          var bindingIndex = -1
          var bindingIsLength = false
          if result.node.kind == "name" && result.node.text == patternArgument.node.text {
            bindingIndex = 0
          } else {}
          if result.node.kind == "name" && result.node.text == secondPatternArgument.node.text {
            bindingIndex = 1
          } else {}
          if result.node.kind == "call" && result.node.text == "length" {
            let lengthArgument = pep_c23_child(nodes, result.node.id, "argument", 0)
            let extraLengthArgument = pep_c23_child(nodes, result.node.id, "argument", 1)
            if lengthArgument.found && !extraLengthArgument.found && lengthArgument.node.kind == "name" {
              if patternArgument.node.kind == "binding_pattern" &&
                 lengthArgument.node.text == patternArgument.node.text &&
                 payloadType.node.kind == "type_list" &&
                 pep_c23_union_payload_is_recursive(nodes, declaration.node, payloadType.node) {
                bindingIndex = 0
                bindingIsLength = true
              } else {}
              if bindingIndex == -1 && secondPatternArgument.node.kind == "binding_pattern" &&
                 lengthArgument.node.text == secondPatternArgument.node.text &&
                 secondPayloadType.node.kind == "type_list" &&
                 pep_c23_union_payload_is_recursive(nodes, declaration.node, secondPayloadType.node) {
                bindingIndex = 1
                bindingIsLength = true
              } else {}
            } else {}
          } else {}
          if bindingIndex != -1 {
            let bindingType = if bindingIndex == 0 { payloadType.node } else { secondPayloadType.node }
            let recursiveBinding = bindingType.kind == "type_named" && bindingType.text == declaration.node.text
            resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts,
              variant, 2, bindingIndex,
              PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }, recursiveBinding)
            if bindingIsLength {
              resultParts = prepend(resultParts, "pep_checked_length(")
              resultParts = append(resultParts, ".length)")
            } else {}
          } else {
            let base = pep_c23_child(nodes, result.node.id, "value", 0)
            let firstRecord = if payloadType.node.kind == "type_named" {
              pep_c23_record_declaration(nodes, payloadType.node.text)
            } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
            let firstParentRecord = if result.node.kind == "field_access" && base.found && firstRecord.found {
              pep_c23_union_payload_record_path_type(nodes, firstRecord.node,
                patternArgument.node.text, base.node)
            } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
            let secondRecord = if secondPayloadType.node.kind == "type_named" {
              pep_c23_record_declaration(nodes, secondPayloadType.node.text)
            } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
            let secondParentRecord = if result.node.kind == "field_access" && base.found && secondRecord.found {
              pep_c23_union_payload_record_path_type(nodes, secondRecord.node,
                secondPatternArgument.node.text, base.node)
            } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
            var projectionIndex = -1
            var projectionBindingName = ""
            var projectionRecord = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
            var parentRecord = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
            if firstParentRecord.found {
              projectionIndex = 0
              projectionBindingName = patternArgument.node.text
              projectionRecord = firstRecord
              parentRecord = firstParentRecord
            } else {}
            if secondParentRecord.found {
              projectionIndex = 1
              projectionBindingName = secondPatternArgument.node.text
              projectionRecord = secondRecord
              parentRecord = secondParentRecord
            } else {}
            if projectionIndex != -1 {
              let field = pep_c23_record_field_declaration(nodes, parentRecord.node, result.node.text)
              let fieldType = if field.found {
                pep_c23_child(nodes, field.node.id, "type", 0)
              } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
              if !field.found || !fieldType.found {
                return pep_c23_unsupported("Pep C23 record payload projection does not resolve a declared field")
              } else {}
              if base.node.kind == "name" {
                resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts,
                  variant, 2, projectionIndex, field, false)
              } else {
                if pep_c23_c_scalar_type(fieldType.node) == "" {
                  return pep_c23_unsupported("Pep C23 nested record payload projection requires a scalar terminal field")
                } else {}
                resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts,
                  variant, 2, projectionIndex,
                  PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }, false)
                for pathPart in pep_c23_union_payload_record_path_parts(nodes,
                  projectionRecord.node, projectionBindingName, base.node) {
                  resultParts = append(resultParts, pathPart)
                }
                resultParts = append(resultParts, ".pep_field_")
                resultParts = append(resultParts, int_text(field.node.childIndex))
              }
            } else {
              if result.node.kind == "binary" && result.node.text == "+" {
                let left = pep_c23_child(nodes, result.node.id, "left", 0)
                let right = pep_c23_child(nodes, result.node.id, "right", 1)
                if !left.found || !right.found {
                  return pep_c23_unsupported("Pep C23 recursive union addition requires two operands")
                } else {}
                let loweredLeft = pep_c23_union_two_payload_operand(nodes,
                  loweredSubject.sourceParts, declaration.node, variant,
                  patternArgument.node, secondPatternArgument.node, left.node)
                let loweredRight = pep_c23_union_two_payload_operand(nodes,
                  loweredSubject.sourceParts, declaration.node, variant,
                  patternArgument.node, secondPatternArgument.node, right.node)
                if loweredLeft.status != "emitted" { return loweredLeft } else {}
                if loweredRight.status != "emitted" { return loweredRight } else {}
                resultParts = ["pep_add("]
                for part in loweredLeft.sourceParts { resultParts = append(resultParts, part) }
                resultParts = append(resultParts, ", ")
                for part in loweredRight.sourceParts { resultParts = append(resultParts, part) }
                resultParts = append(resultParts, ")")
              } else {
                let loweredResult = pep_c23_expression(nodes, function, result.node)
                if loweredResult.status != "emitted" { return loweredResult } else {}
                resultParts = loweredResult.sourceParts
              }
            }
          }
        } else {
          let extraPatternArgument = pep_c23_child(nodes, pattern.node.id, "argument", 1)
          if !patternArgument.found || extraPatternArgument.found ||
             patternArgument.node.kind != "binding_pattern" && patternArgument.node.kind != "wildcard_pattern" {
            return pep_c23_unsupported("Pep C23 payload patterns require one binding or wildcard")
          } else {}
          if result.node.kind == "call" && result.node.text == "length" {
            let lengthArgument = pep_c23_child(nodes, result.node.id, "argument", 0)
            let extraLengthArgument = pep_c23_child(nodes, result.node.id, "argument", 1)
            if payloadType.node.kind != "type_list" ||
               !pep_c23_union_payload_is_recursive(nodes, declaration.node, payloadType.node) ||
               patternArgument.node.kind != "binding_pattern" ||
               !lengthArgument.found || lengthArgument.node.kind != "name" ||
               lengthArgument.node.text != patternArgument.node.text || extraLengthArgument.found {
              return pep_c23_unsupported("Pep C23 match length extraction requires its recursive list payload binding")
            } else {}
            resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts, variant, 1, 0,
              PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }, false)
            resultParts = prepend(resultParts, "pep_checked_length(")
            resultParts = append(resultParts, ".length)")
          } else {
            if result.node.kind == "name" && result.node.text == patternArgument.node.text {
              let recursiveBinding = payloadType.node.kind == "type_named" && payloadType.node.text == declaration.node.text
              resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts, variant, 1, 0,
                PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }, recursiveBinding)
            } else {
              if result.node.kind == "field_access" && payloadType.node.kind == "type_named" {
                let base = pep_c23_child(nodes, result.node.id, "value", 0)
                if base.found && base.node.kind == "name" && base.node.text == patternArgument.node.text {
                  let record = pep_c23_record_declaration(nodes, payloadType.node.text)
                  let field = if record.found {
                    pep_c23_record_field_declaration(nodes, record.node, result.node.text)
                  } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
                  if !record.found || !field.found {
                    return pep_c23_unsupported("Pep C23 record payload projection does not resolve a declared field")
                  } else {}
                  resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts, variant,
                    1, 0, field, false)
                } else {
                  if base.found && base.node.kind == "field_access" {
                    let record = pep_c23_record_declaration(nodes, payloadType.node.text)
                    let parentRecord = if record.found {
                      pep_c23_union_payload_record_path_type(nodes, record.node,
                        patternArgument.node.text, base.node)
                    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
                    let field = if parentRecord.found {
                      pep_c23_record_field_declaration(nodes, parentRecord.node, result.node.text)
                    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
                    let fieldType = if field.found {
                      pep_c23_child(nodes, field.node.id, "type", 0)
                    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
                    if !record.found || !parentRecord.found || !field.found ||
                       !fieldType.found || pep_c23_c_scalar_type(fieldType.node) == "" {
                      return pep_c23_unsupported("Pep C23 nested record payload projection requires a scalar terminal field")
                    } else {}
                    resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts,
                      variant, 1, 0, PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }, false)
                    for pathPart in pep_c23_union_payload_record_path_parts(nodes,
                      record.node, patternArgument.node.text, base.node) {
                      resultParts = append(resultParts, pathPart)
                    }
                    resultParts = append(resultParts, ".pep_field_")
                    resultParts = append(resultParts, int_text(field.node.childIndex))
                  } else {
                    let loweredResult = pep_c23_expression(nodes, function, result.node)
                    if loweredResult.status != "emitted" { return loweredResult } else {}
                    resultParts = loweredResult.sourceParts
                  }
                }
              } else {
                let loweredResult = pep_c23_expression(nodes, function, result.node)
                if loweredResult.status != "emitted" { return loweredResult } else {}
                resultParts = loweredResult.sourceParts
              }
            }
          }
        }
      } else {
        let secondPatternArgument = pep_c23_child(nodes, pattern.node.id, "argument", 1)
        if patternArgument.found || secondPatternArgument.found {
          return pep_c23_unsupported("Pep C23 nullary constructor pattern requires zero arguments")
        } else {}
        let loweredResult = pep_c23_expression(nodes, function, result.node)
        if loweredResult.status != "emitted" { return loweredResult } else {}
        resultParts = loweredResult.sourceParts
      }
      for part in loweredSubject.sourceParts { parts = append(parts, part) }
      parts = append(parts, ".tag == ")
      parts = append(parts, int_text(variant.childIndex))
      parts = append(parts, " ? ")
      for part in resultParts { parts = append(parts, part) }
      remaining = remaining - 1
      if remaining == 0 {
        parts = append(parts, " : (pep_invalid_union_tag(), ")
        for part in resultParts { parts = append(parts, part) }
        parts = append(parts, ")")
      } else {
        parts = append(parts, " : ")
      }
      matchedCount = matchedCount + 1
    } else {}
  }
  if matchedCount != variantCount { return pep_c23_unsupported("Pep C23 tagged-union match does not cover its declared constructors") } else {}
  parts = append(parts, ")")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_list_field_element(nodes: List[FlatAstNode], function: FlatAstNode, elementKind: Str,
  element: FlatAstNode) -> PepC23Emission {
  if elementKind == "string" {
    if element.kind != "string" {
      return pep_c23_unsupported("Pep C23 List[Str] record field values currently require string literal elements")
    } else {}
    return pep_c23_string_literal(nodes, element)
  } else {}
  if elementKind == "record" {
    if element.kind != "record" {
      return pep_c23_unsupported("Pep C23 List[Record] record field values currently require record constructor elements")
    } else {}
    return pep_c23_expression(nodes, function, element)
  } else {}
  if elementKind == "integer" {
    if element.kind == "integer" {
      return PepC23Emission { status: "emitted", sourceParts: [int_text(element.integerValue)], diagnostic: "" }
    } else {}
    if pep_c23_is_negative_int_literal(nodes, element) {
      return pep_c23_expression(nodes, function, element)
    } else {}
    return pep_c23_unsupported("Pep C23 List[Int] record field values currently require integer literal elements")
  } else {}
  if element.kind != "boolean" {
    return pep_c23_unsupported("Pep C23 List[Bool] record field values currently require Bool literal elements")
  } else {}
  let lowered = if element.booleanValue { "1" } else { "0" }
  return PepC23Emission { status: "emitted", sourceParts: [lowered], diagnostic: "" }
}
// List-valued record fields reuse the existing by-value list structs. Element storage is a
// compound literal with the lifetime of the enclosing block, matching list parameter arguments.
fn pep_c23_list_field_value(nodes: List[FlatAstNode], function: FlatAstNode, owner: FlatAstNode,
  declaredType: FlatAstNode, value: FlatAstNode) -> PepC23Emission {
  let listTypeParts = pep_c23_c_list_field_type_parts(nodes, owner, declaredType)
  if length(listTypeParts) == 0 {
    return pep_c23_unsupported("Pep C23 list record field type is unsupported")
  } else {}
  if value.kind == "name" {
    let parameter = pep_c23_list_parameter_of_type(nodes, function, value.text, declaredType)
    if !parameter.found {
      return pep_c23_unsupported("Pep C23 list record field values currently require a list literal or a matching list parameter")
    } else {}
    return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(parameter.node.id)], diagnostic: "" }
  } else {}
  if value.kind != "list" {
    return pep_c23_unsupported("Pep C23 list record field values currently require a list literal or a matching list parameter")
  } else {}
  let elementType = pep_c23_child(nodes, declaredType.id, "element_type", 0)
  if !elementType.found { return pep_c23_unsupported("Pep C23 list record field has no element type") } else {}
  var cElement: List[Str] = []
  var elementKind = ""
  if elementType.node.kind == "type_scalar" {
    if elementType.node.text == "Str" { cElement = ["pep_str"]; elementKind = "string" } else {}
    if elementType.node.text == "Int" { cElement = ["int64_t"]; elementKind = "integer" } else {}
    if elementType.node.text == "Bool" { cElement = ["_Bool"]; elementKind = "boolean" } else {}
  } else {}
  if elementType.node.kind == "type_named" {
    let nested = pep_c23_record_declaration(nodes, elementType.node.text)
    if !nested.found {
      return pep_c23_unsupported("Pep C23 list record field has no declared element record")
    } else {}
    cElement = ["pep_record_", int_text(nested.node.id)]
    elementKind = "record"
  } else {}
  if elementKind == "" {
    return pep_c23_unsupported("Pep C23 list record field element type is unsupported")
  } else {}
  let elementCount = pep_c23_count_children(nodes, value.id, "element")
  var parts: List[Str] = ["("]
  for listTypePart in listTypeParts { parts = append(parts, listTypePart) }
  parts = append(parts, "){ .data = ")
  if elementCount == 0 {
    parts = append(parts, "NULL")
  } else {
    parts = append(parts, "(const ")
    for cElementPart in cElement { parts = append(parts, cElementPart) }
    parts = append(parts, "[]){")
    var count = 0
    for element in nodes {
      if element.parentId == value.id && element.role == "element" {
        if count != 0 { parts = append(parts, ", ") } else {}
        let lowered = pep_c23_list_field_element(nodes, function, elementKind, element)
        if lowered.status != "emitted" { return lowered } else {}
        for part in lowered.sourceParts { parts = append(parts, part) }
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
fn pep_c23_field_access_list_type(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> PepC23NodeLookup {
  let owner = pep_c23_child(nodes, node.id, "value", 0)
  if !owner.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  let record = pep_c23_record_value_type(nodes, function, owner.node)
  if !record.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  let field = pep_c23_record_field_declaration(nodes, record.node, node.text)
  if !field.found { return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } } else {}
  let fieldType = pep_c23_child(nodes, field.node.id, "type", 0)
  if !fieldType.found || fieldType.node.kind != "type_list" {
    return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  } else {}
  return fieldType
}
// Structural gate for the result expression of a callee with more than three parameters. It keeps
// that path to shapes the expression lowering already handles; anything unexpected refuses.
fn pep_c23_parameterised_expression(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> Bool {
  if node.kind == "integer" || node.kind == "boolean" || node.kind == "name" || node.kind == "string" {
    return true
  } else {}
  if node.kind == "unary" {
    let operand = pep_c23_child(nodes, node.id, "operand", 0)
    return operand.found && pep_c23_parameterised_expression(nodes, function, operand.node)
  } else {}
  if node.kind == "binary" {
    let left = pep_c23_child(nodes, node.id, "left", 0)
    let right = pep_c23_child(nodes, node.id, "right", 1)
    return left.found && right.found &&
      pep_c23_parameterised_expression(nodes, function, left.node) &&
      pep_c23_parameterised_expression(nodes, function, right.node)
  } else {}
  if node.kind == "field_access" {
    let value = pep_c23_child(nodes, node.id, "value", 0)
    if !value.found { return false } else {}
    let record = pep_c23_record_value_type(nodes, function, value.node)
    if !record.found { return false } else {}
    return pep_c23_record_field_declaration(nodes, record.node, node.text).found
  } else {}
  if node.kind == "record" {
    if !pep_c23_record_declaration(nodes, node.text).found { return false } else {}
    for supplied in nodes {
      if supplied.parentId == node.id && supplied.role == "field" && supplied.kind == "record_field" {
        let value = pep_c23_child(nodes, supplied.id, "value", 0)
        if !value.found || !pep_c23_parameterised_expression(nodes, function, value.node) {
          return false
        } else {}
      } else {}
    }
    return true
  } else {}
  if node.kind == "if_expression" {
    let condition = pep_c23_child(nodes, node.id, "condition", 0)
    let thenValue = pep_c23_child(nodes, node.id, "then", 1)
    let elseValue = pep_c23_child(nodes, node.id, "else", 2)
    return condition.found && thenValue.found && elseValue.found &&
      pep_c23_parameterised_expression(nodes, function, condition.node) &&
      pep_c23_parameterised_expression(nodes, function, thenValue.node) &&
      pep_c23_parameterised_expression(nodes, function, elseValue.node)
  } else {}
  return false
}
// Four or more parameters: general ordered lowering. The safety rules match the one- to
// three-parameter paths: the callee must be a direct return of a parameter-only result, or an
// if-statement body, and at most one argument may fail at runtime because C leaves argument
// evaluation order unspecified.
fn pep_c23_many_argument_call(nodes: List[FlatAstNode], function: FlatAstNode, call: FlatAstNode,
  target: FlatAstNode, conditionalTarget: Bool, directLocalTarget: Bool) -> PepC23Emission {
  let parameters = pep_c23_parameters(nodes, target)
  let argumentCount = pep_c23_count_children(nodes, call.id, "argument")
  if length(parameters) != argumentCount {
    return pep_c23_unsupported("Pep C23 calls require exactly one argument per declared parameter")
  } else {}
  let result = pep_c23_child(nodes, target.id, "return_type", 0)
  if !result.found || length(pep_c23_c_parameter_type_parts(nodes, result.node)) == 0 {
    return pep_c23_unsupported("Pep C23 calls require a target with a supported result type")
  } else {}
  let targetStatement = pep_c23_last_statement(nodes, target)
  if !targetStatement.found {
    return pep_c23_unsupported("Pep C23 calls require a target with a body")
  } else {}
  let targetValue = pep_c23_child(nodes, targetStatement.node.id, "value", 0)
  let directParameterReturn = targetStatement.node.kind == "return" && targetValue.found &&
    pep_c23_parameterised_expression(nodes, target, targetValue.node)
  if !conditionalTarget && !directLocalTarget && !directParameterReturn {
    return pep_c23_unsupported("Pep C23 calls require a direct parameter-only return or a conditional-return target")
  } else {}
  var fallibleArguments = 0
  var arguments: List[FlatAstNode] = []
  var wanted = 0
  while !(argumentCount <= wanted) {
    let argument = pep_c23_child(nodes, call.id, "argument", wanted)
    if !argument.found {
      return pep_c23_unsupported("Pep C23 call argument list has a gap")
    } else {}
    if pep_c23_infallible_value(nodes, argument.node) {
      fallibleArguments = fallibleArguments + 1
    } else {}
    arguments = append(arguments, argument.node)
    wanted = wanted + 1
  }
  if !(fallibleArguments <= 1) {
    return pep_c23_unsupported("Pep C23 rejects multiple fallible call arguments because C argument evaluation order is unspecified")
  } else {}
  // Symbols are name-based: function names are unique per document (the checker refuses
  // PEP_DUPLICATE_FUNCTION), so `pep_fn_<name>` is stable ACROSS chunk-local id remapping --
  // chunked assembly would otherwise emit duplicate pep_fn_<id> symbols (measured collision:
  // two chunks both remapping a function to id 18).
  var parts: List[Str] = ["pep_fn_", target.text, "("]
  var emitted = 0
  for parameter in parameters {
    let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
    let argument = pep_c23_child(nodes, call.id, "argument", emitted)
    if !parameterType.found || !argument.found {
      return pep_c23_unsupported("Pep C23 call arguments must match the declared parameter types")
    } else {}
    let lowered = pep_c23_call_argument(nodes, function, argument.node, parameterType)
    if lowered.status != "emitted" { return lowered } else {}
    if emitted != 0 { parts = append(parts, ", ") } else {}
    for part in lowered.sourceParts { parts = append(parts, part) }
    emitted = emitted + 1
  }
  parts = pep_c23_close_generated_call(nodes, parts, emitted)
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_expression(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> PepC23Emission {
  if node.kind == "match" { return pep_c23_union_match_expression(nodes, function, node) } else {}
  if node.kind == "string" { return pep_c23_string_literal(nodes, node) } else {}
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
    var loopFound = false
    var loopId = -1
    var parameterFound = false
    var parameterNode = pep_c23_empty_ast_node()
    var whileLocalCandidate = false
    for candidate in nodes {
      if candidate.kind == "let" && candidate.role == "body" &&
         candidate.text == node.text && !(node.id <= candidate.id) {
        whileLocalCandidate = true
      } else {}
      if candidate.parentId == function.id {
        if candidate.role == "statement" && (candidate.kind == "let" || candidate.kind == "var") && candidate.text == node.text {
          localFound = true
          localId = candidate.id
        } else {}
        if candidate.role == "statement" && candidate.kind == "for_in" && candidate.text == node.text && !loopFound {
          loopFound = true
          loopId = candidate.id
        } else {}
        if candidate.role == "parameter" && candidate.kind == "parameter" && candidate.text == node.text {
          if !parameterFound || !(parameterNode.childIndex <= candidate.childIndex) {
            parameterFound = true
            parameterNode = candidate
          } else {}
        } else {}
      } else {}
    }
    let whileLocal = if whileLocalCandidate {
      pep_c23_enclosing_while_binding(nodes, function, node, node.text)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    if whileLocal.found {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(whileLocal.node.id)], diagnostic: "" }
    } else {}
    if localFound { return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(localId)], diagnostic: "" } } else {}
    if loopFound { return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(loopId)], diagnostic: "" } } else {}
    if parameterFound {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(parameterNode.id)], diagnostic: "" }
    } else {}
    return pep_c23_unsupported("Pep C23 name lowering requires a direct immutable local let or scalar parameter")
  } else {}
  if node.kind == "record" {
    let declaration = pep_c23_record_declaration(nodes, node.text)
    if !declaration.found { return pep_c23_unsupported("Pep C23 record construction requires a declared record type") } else {}
    var parts: List[Str] = []
    parts = ["(pep_record_", int_text(declaration.node.id), "){ "]
    var fieldCount = 0
    var fallibleFieldCount = 0
    for supplied in nodes {
      if supplied.parentId == node.id && supplied.role == "field" && supplied.kind == "record_field" {
        let declared = pep_c23_record_field_declaration(nodes, declaration.node, supplied.text)
        if !declared.found { return pep_c23_unsupported("Pep C23 record construction field does not resolve to a declaration") } else {}
        let fieldType = pep_c23_child(nodes, declared.node.id, "type", 0)
        let fieldKind = if fieldType.found {
          pep_c23_c_record_field_type(nodes, declaration.node, fieldType.node)
        } else { "" }
        if fieldKind == "" {
          return pep_c23_unsupported("Pep C23 record fields require Int, Bool, or a preceding record declaration")
        } else {}
        let value = pep_c23_child(nodes, supplied.id, "value", 0)
        if !value.found { return pep_c23_unsupported("Pep C23 record field has no value") } else {}
        if pep_c23_infallible_value(nodes, value.node) {
          if fallibleFieldCount != 0 {
            return pep_c23_unsupported("Pep C23 record construction rejects multiple fallible field expressions because C field evaluation order is unspecified")
          } else {}
          fallibleFieldCount = fallibleFieldCount + 1
        } else {}
        let lowered = if fieldKind == "list" {
          pep_c23_list_field_value(nodes, function, declaration.node, fieldType.node, value.node)
        } else {
          pep_c23_expression(nodes, function, value.node)
        }
        if lowered.status != "emitted" { return lowered } else {}
        if fieldCount != 0 { parts = append(parts, ", ") } else {}
        parts = append(parts, ".pep_field_")
        parts = append(parts, int_text(declared.node.childIndex))
        parts = append(parts, " = ")
        for part in lowered.sourceParts { parts = append(parts, part) }
        fieldCount = fieldCount + 1
      } else {}
    }
    if fieldCount == 0 { return pep_c23_unsupported("Pep C23 does not lower empty records") } else {}
    parts = append(parts, " }")
    return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
  } else {}
  if node.kind == "field_access" {
    let value = pep_c23_child(nodes, node.id, "value", 0)
    if !value.found { return pep_c23_unsupported("Pep C23 field access has no record value") } else {}
    let record = pep_c23_record_value_type(nodes, function, value.node)
    if !record.found { return pep_c23_unsupported("Pep C23 field access requires a supported record value") } else {}
    let field = pep_c23_record_field_declaration(nodes, record.node, node.text)
    if !field.found { return pep_c23_unsupported("Pep C23 field access does not resolve to a declared field") } else {}
    let loweredValue = pep_c23_expression(nodes, function, value.node)
    if loweredValue.status != "emitted" { return loweredValue } else {}
    var parts: List[Str] = []
    for part in loweredValue.sourceParts { parts = append(parts, part) }
    parts = append(parts, ".pep_field_")
    parts = append(parts, int_text(field.node.childIndex))
    return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
  } else {}
  if node.kind == "call" {
    let variant = pep_c23_union_variant(nodes, node.text)
    if variant.found { return pep_c23_union_constructor(nodes, function, node, variant.node) } else {}
    var argumentFound = false
    var argumentNode = pep_c23_empty_ast_node()
    var secondArgumentFound = false
    var secondArgumentNode = pep_c23_empty_ast_node()
    var thirdArgumentFound = false
    var thirdArgumentNode = pep_c23_empty_ast_node()
    var extraArgumentFound = false
    var extraArgumentNode = pep_c23_empty_ast_node()
    var targetFound = false
    var targetNode = pep_c23_empty_ast_node()
    for candidate in nodes {
      if candidate.parentId == node.id && candidate.role == "argument" {
        if candidate.childIndex == 0 && !argumentFound {
          argumentFound = true
          argumentNode = candidate
        } else {}
        if candidate.childIndex == 1 && !secondArgumentFound {
          secondArgumentFound = true
          secondArgumentNode = candidate
        } else {}
        if candidate.childIndex == 2 && !thirdArgumentFound {
          thirdArgumentFound = true
          thirdArgumentNode = candidate
        } else {}
        if candidate.childIndex == 3 && !extraArgumentFound {
          extraArgumentFound = true
          extraArgumentNode = candidate
        } else {}
      } else {}
      if candidate.parentId == -1 && candidate.kind == "function" &&
         candidate.text == node.text && !targetFound {
        targetFound = true
        targetNode = candidate
      } else {}
    }
    let argument = PepC23NodeLookup { found: argumentFound, node: argumentNode }
    let secondArgument = PepC23NodeLookup { found: secondArgumentFound, node: secondArgumentNode }
    let thirdArgument = PepC23NodeLookup { found: thirdArgumentFound, node: thirdArgumentNode }
    let extraArgument = PepC23NodeLookup { found: extraArgumentFound, node: extraArgumentNode }
    let target = PepC23NodeLookup { found: targetFound, node: targetNode }
    if node.text == "byte_length" {
      if !argument.found || secondArgument.found || thirdArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 byte_length requires one SourceBytes parameter")
      } else {}
      if argument.node.kind != "name" ||
         !pep_c23_source_bytes_parameter(nodes, function, argument.node.text).found {
        return pep_c23_unsupported("Pep C23 byte_length currently requires a direct SourceBytes parameter")
      } else {}
      let source = pep_c23_expression(nodes, function, argument.node)
      if source.status != "emitted" { return source } else {}
      var parts: List[Str] = ["pep_byte_length("]
      for part in source.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
    if node.text == "byte_at" {
      if !argument.found || !secondArgument.found || thirdArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 byte_at requires a SourceBytes parameter and one Int offset")
      } else {}
      if argument.node.kind != "name" ||
         !pep_c23_source_bytes_parameter(nodes, function, argument.node.text).found {
        return pep_c23_unsupported("Pep C23 byte_at currently requires a direct SourceBytes parameter")
      } else {}
      let source = pep_c23_expression(nodes, function, argument.node)
      let offset = pep_c23_expression(nodes, function, secondArgument.node)
      if source.status != "emitted" { return source } else {}
      if offset.status != "emitted" { return offset } else {}
      var parts: List[Str] = ["pep_byte_at("]
      for part in source.sourceParts { parts = append(parts, part) }
      parts = append(parts, ", ")
      for part in offset.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
    if node.text == "str_contains" {
      if !argument.found || !secondArgument.found || thirdArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 str_contains requires exactly two supported Str values")
      } else {}
      let haystack = pep_c23_str_expression(nodes, function, argument.node)
      let needle = pep_c23_str_expression(nodes, function, secondArgument.node)
      if !haystack.found || !needle.found {
        return pep_c23_unsupported("Pep C23 str_contains arguments must resolve to supported Str values")
      } else {}
      let loweredHaystack = pep_c23_expression(nodes, function, argument.node)
      let loweredNeedle = pep_c23_expression(nodes, function, secondArgument.node)
      if loweredHaystack.status != "emitted" { return loweredHaystack } else {}
      if loweredNeedle.status != "emitted" { return loweredNeedle } else {}
      var parts: List[Str] = ["pep_str_contains("]
      for part in loweredHaystack.sourceParts { parts = append(parts, part) }
      parts = append(parts, ", ")
      for part in loweredNeedle.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission {
        status: "emitted",
        sourceParts: parts,
        diagnostic: ""
      }
    } else {}
    // str_concat: same two-supported-Str-values contract as str_contains (Campaign G
    // G-A2-7). Arguments may themselves be str_concat calls (the checker's nested
    // chain) -- classification flows through pep_c23_str_result_call's builtin branch.
    // Bump-pool storage means no aliasing rules are needed on the call side.
    if node.text == "str_concat" {
      if !argument.found || !secondArgument.found || thirdArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 str_concat requires exactly two supported Str values")
      } else {}
      let leftValue = pep_c23_str_expression(nodes, function, argument.node)
      let rightValue = pep_c23_str_expression(nodes, function, secondArgument.node)
      // Side-specific diagnostics (G-A2-7): which argument failed classification is the
      // difference between a five-minute fix and a hunt.
      if !leftValue.found {
        return pep_c23_unsupported("Pep C23 str_concat LEFT argument must resolve to a supported Str value")
      } else {}
      if !rightValue.found {
        return pep_c23_unsupported("Pep C23 str_concat RIGHT argument must resolve to a supported Str value")
      } else {}
      let loweredLeft = pep_c23_expression(nodes, function, argument.node)
      let loweredRight = pep_c23_expression(nodes, function, secondArgument.node)
      if loweredLeft.status != "emitted" { return loweredLeft } else {}
      if loweredRight.status != "emitted" { return loweredRight } else {}
      var parts: List[Str] = ["pep_str_concat("]
      for part in loweredLeft.sourceParts { parts = append(parts, part) }
      parts = append(parts, ", ")
      for part in loweredRight.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission {
        status: "emitted",
        sourceParts: parts,
        diagnostic: ""
      }
    } else {}
    if node.text == "contains" {
      if !argument.found || !secondArgument.found || thirdArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 contains lowering requires a list and an Int value")
      } else {}
      let listParameter = if argument.node.kind == "name" {
        pep_c23_int_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      if listParameter.found {
        if secondArgument.node.kind != "integer" && secondArgument.node.kind != "name" && !pep_c23_is_negative_int_literal(nodes, secondArgument.node) {
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
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
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
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      if mutableList.found {
        let elementKind = pep_c23_mutable_list_element_kind(nodes, mutableList.node)
        if elementKind != "integer" && elementKind != "boolean" {
          return pep_c23_unsupported("Pep C23 mutable contains requires a typed Int or Bool list binding")
        } else {}
        if secondArgument.node.kind != "integer" && secondArgument.node.kind != "boolean" && secondArgument.node.kind != "name" && !pep_c23_is_negative_int_literal(nodes, secondArgument.node) {
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
      if secondArgument.node.kind != "integer" && secondArgument.node.kind != "boolean" && secondArgument.node.kind != "name" && !pep_c23_is_negative_int_literal(nodes, secondArgument.node) {
        return pep_c23_unsupported("Pep C23 contains lowering requires an integer literal or local value")
      } else {}
      let value = pep_c23_expression(nodes, function, secondArgument.node)
      if value.status != "emitted" { return value } else {}
      var parts: List[Str] = ["("]
      var count = 0
      for element in nodes {
        if element.parentId == list.node.id && element.role == "element" {
          if element.kind != "integer" && element.kind != "boolean" && !pep_c23_is_negative_int_literal(nodes, element) { return pep_c23_unsupported("Pep C23 contains list literals currently require integer or Bool elements") } else {}
          if count != 0 { parts = append(parts, " || ") } else {}
          parts = append(parts, "(")
          for part in value.sourceParts { parts = append(parts, part) }
          parts = append(parts, " == ")
          if element.kind == "boolean" {
            parts = append(parts, if element.booleanValue { "1" } else { "0" })
          } else {
            let elementValue = pep_c23_expression(nodes, function, element)
            if elementValue.status != "emitted" { return elementValue } else {}
            for part in elementValue.sourceParts { parts = append(parts, part) }
          }
          parts = append(parts, ")")
          count = count + 1
        } else {}
      }
      if count == 0 { parts = append(parts, "0") } else {}
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
    if node.text == "length" {
      if !argument.found || secondArgument.found || thirdArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 length lowering requires one supported list value")
      } else {}
      let listParameter = if argument.node.kind == "name" {
        pep_c23_int_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      if listParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_arg_", int_text(listParameter.node.id), ".length)"], diagnostic: "" }
      } else {}
      let boolListParameter = if argument.node.kind == "name" {
        pep_c23_bool_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      if boolListParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_arg_", int_text(boolListParameter.node.id), ".length)"], diagnostic: "" }
      } else {}
      let strListParameter = if argument.node.kind == "name" {
        pep_c23_str_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      if strListParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_arg_", int_text(strListParameter.node.id), ".length)"], diagnostic: "" }
      } else {}
      let recordListParameter = if argument.node.kind == "name" {
        pep_c23_record_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      if recordListParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_arg_", int_text(recordListParameter.node.id), ".length)"], diagnostic: "" }
      } else {}
      let unionListParameter = if argument.node.kind == "name" {
        pep_c23_union_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      if unionListParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_arg_", int_text(unionListParameter.node.id), ".length)"], diagnostic: "" }
      } else {}
      for binding in nodes {
        if binding.parentId == function.id && binding.role == "statement" && binding.kind == "var" && binding.text == argument.node.text {
          let initial = pep_c23_child(nodes, binding.id, "value", 0)
          if initial.found && initial.node.kind == "list" {
            return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_local_", int_text(binding.id), ".length)"], diagnostic: "" }
          } else {}
        } else {}
      }
      if argument.node.kind == "field_access" {
        let fieldType = pep_c23_field_access_list_type(nodes, function, argument.node)
        if fieldType.found {
          let projection = pep_c23_expression(nodes, function, argument.node)
          if projection.status == "emitted" {
            var lengthParts: List[Str] = ["pep_checked_length("]
            for part in projection.sourceParts { lengthParts = append(lengthParts, part) }
            lengthParts = append(lengthParts, ".length)")
            return PepC23Emission { status: "emitted", sourceParts: lengthParts, diagnostic: "" }
          } else {}
        } else {}
      } else {}
      let list = pep_c23_list_literal(nodes, function, argument.node)
      if !list.found { return pep_c23_unsupported("Pep C23 length lowering requires a direct integer list literal or immutable list binding") } else {}
      return PepC23Emission { status: "emitted", sourceParts: [int_text(pep_c23_count_children(nodes, list.node.id, "element"))], diagnostic: "" }
    } else {}
    if !target.found {
      return pep_c23_unsupported("Pep C23 calls require a known target")
    } else {}
    let parameter = pep_c23_child(nodes, target.node.id, "parameter", 0)
    let secondParameter = pep_c23_child(nodes, target.node.id, "parameter", 1)
    let thirdParameter = pep_c23_child(nodes, target.node.id, "parameter", 2)
    let extraParameter = pep_c23_child(nodes, target.node.id, "parameter", 3)
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    let recordResult = result.found && result.node.kind == "type_named" && pep_c23_record_declaration(nodes, result.node.text).found
    let unionResult = result.found && result.node.kind == "type_named" && pep_c23_union_declaration(nodes, result.node.text).found
    // Str results join this gate with the function gate (Campaign F F3): the callee body
    // lowers through the same Str value positions say already exercises, and the call value
    // flows into say-eligible locals/arguments as pep_str.
    let stringResult = result.found && result.node.kind == "type_scalar" && result.node.text == "Str"
    // Arity itself is not checked here: three or more parameters are routed to the general
    // ordered path below, which enforces one argument per declared parameter.
    if !result.found || (pep_c23_c_scalar_type(result.node) == "" && !recordResult && !unionResult && !stringResult) {
      return pep_c23_unsupported("Pep C23 calls require a known target with a supported scalar, Str, record, or tagged-union result")
    } else {}
    let targetStatement = pep_c23_last_statement(nodes, target.node)
    let targetValue = if targetStatement.found {
      pep_c23_child(nodes, targetStatement.node.id, "value", 0)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    let directLocalTarget = targetStatement.found && targetStatement.node.kind == "return" &&
      targetValue.found && targetValue.node.kind == "name" &&
      pep_c23_direct_local(nodes, target.node, targetValue.node.text)
    let nestedReturnTarget = if targetValue.found && targetValue.node.kind == "call" {
      pep_c23_function(nodes, targetValue.node.text)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    let directCallTarget = targetStatement.found && targetStatement.node.kind == "return" &&
      targetValue.found && targetValue.node.kind == "call" &&
      nestedReturnTarget.found && nestedReturnTarget.node.id != target.node.id
    let directStrContainsTarget = targetStatement.found && targetStatement.node.kind == "return" &&
      targetValue.found && targetValue.node.kind == "call" && targetValue.node.text == "str_contains"
    let booleanCallTarget = targetStatement.found && targetStatement.node.kind == "return" && targetValue.found &&
      targetValue.node.kind == "binary" && (targetValue.node.text == "&&" || targetValue.node.text == "||")
    let conditionalTarget = (targetStatement.found && targetStatement.node.kind == "if_statement") ||
      (targetStatement.found && targetStatement.node.kind == "return" && targetValue.found && targetValue.node.kind == "if_expression") ||
      directLocalTarget ||
      directCallTarget ||
      directStrContainsTarget ||
      booleanCallTarget
    if !targetStatement.found || (targetStatement.node.kind != "return" && !conditionalTarget) || (!conditionalTarget && !targetValue.found) {
      return pep_c23_unsupported("Pep C23 calls require a direct-return or supported conditional-return target")
    } else {}
    // Clang rejects a direct self-call that passes its own parameter through unchanged
    // (-Winfinite-recursion under -Werror), so emitting it would break the emit-or-refuse
    // contract. This is a compilability check on the call shape only. It makes no claim about
    // termination: a call that passes a changed argument is still just as capable of looping.
    if target.node.id == function.id && parameter.found && !secondParameter.found &&
       !thirdParameter.found && argument.found && !secondArgument.found &&
       argument.node.kind == "name" && argument.node.text == parameter.node.text {
      return pep_c23_unsupported("Pep C23 cannot lower a direct self-call that passes its own parameter unchanged")
    } else {}
    // Only four or more parameters or arguments use the general ordered path, detected through the
    // already-computed lookups so no extra traversal runs. Calls with one to three arguments keep
    // the fixed-slot paths and their exact previous behaviour and step cost: routing them here was
    // measured to push unrelated collection programs over the emitter's 100k step budget.
    if extraParameter.found || extraArgument.found {
      return pep_c23_many_argument_call(nodes, function, node, target.node,
        conditionalTarget, directLocalTarget)
    } else {}
    if parameter.found {
      let parameterType = pep_c23_child(nodes, parameter.node.id, "type", 0)
      if secondParameter.found {
        let secondParameterType = pep_c23_child(nodes, secondParameter.node.id, "type", 0)
        if thirdParameter.found {
          let thirdParameterType = pep_c23_child(nodes, thirdParameter.node.id, "type", 0)
          if !argument.found || !secondArgument.found || !thirdArgument.found || (!conditionalTarget && !directLocalTarget && !pep_c23_call_free_expression(nodes, targetValue.node)) {
            return pep_c23_unsupported("Pep C23 three-parameter calls require three arguments and a call-free result")
          } else {}
          if (pep_c23_expression_may_fail(nodes, argument.node) && pep_c23_expression_may_fail(nodes, secondArgument.node)) ||
             (pep_c23_expression_may_fail(nodes, argument.node) && pep_c23_expression_may_fail(nodes, thirdArgument.node)) ||
             (pep_c23_expression_may_fail(nodes, secondArgument.node) && pep_c23_expression_may_fail(nodes, thirdArgument.node)) {
            return pep_c23_unsupported("Pep C23 rejects multiple fallible call arguments because C argument evaluation order is unspecified")
          } else {}
          let loweredArgument = pep_c23_call_argument(nodes, function, argument.node, parameterType)
          let loweredSecondArgument = pep_c23_call_argument(nodes, function, secondArgument.node, secondParameterType)
          let loweredThirdArgument = pep_c23_call_argument(nodes, function, thirdArgument.node, thirdParameterType)
          if loweredArgument.status != "emitted" { return loweredArgument } else {}
          if loweredSecondArgument.status != "emitted" { return loweredSecondArgument } else {}
          if loweredThirdArgument.status != "emitted" { return loweredThirdArgument } else {}
          var parts: List[Str] = ["pep_fn_", target.node.text, "("]
          for part in loweredArgument.sourceParts { parts = append(parts, part) }
          parts = append(parts, ", ")
          for part in loweredSecondArgument.sourceParts { parts = append(parts, part) }
          parts = append(parts, ", ")
          for part in loweredThirdArgument.sourceParts { parts = append(parts, part) }
          parts = pep_c23_close_generated_call(nodes, parts, 3)
          return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
        } else {}
        if !argument.found || !secondArgument.found || thirdArgument.found || (!conditionalTarget && !pep_c23_parameter_expression(nodes, target.node, parameter.node.text, secondParameter.node.text, targetValue.node)) {
          return pep_c23_unsupported("Pep C23 two-parameter calls require two arguments and a call-free result expression")
        } else {}
        if pep_c23_expression_may_fail(nodes, argument.node) && pep_c23_expression_may_fail(nodes, secondArgument.node) {
          return pep_c23_unsupported("Pep C23 rejects two fallible call arguments because C argument evaluation order is unspecified")
        } else {}
        let loweredArgument = pep_c23_call_argument(nodes, function, argument.node, parameterType)
        let loweredSecondArgument = pep_c23_call_argument(nodes, function, secondArgument.node, secondParameterType)
        if loweredArgument.status != "emitted" { return loweredArgument } else {}
        if loweredSecondArgument.status != "emitted" { return loweredSecondArgument } else {}
        var parts: List[Str] = ["pep_fn_", target.node.text, "("]
        for part in loweredArgument.sourceParts { parts = append(parts, part) }
        parts = append(parts, ", ")
        for part in loweredSecondArgument.sourceParts { parts = append(parts, part) }
        parts = pep_c23_close_generated_call(nodes, parts, 2)
        return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
      } else {
        if !argument.found || secondArgument.found || thirdArgument.found || (!conditionalTarget && !pep_c23_parameter_expression(nodes, target.node, parameter.node.text, "", targetValue.node)) {
          return pep_c23_unsupported("Pep C23 one-parameter calls require one argument and a call-free target expression")
        } else {}
        let loweredArgument = pep_c23_call_argument(nodes, function, argument.node, parameterType)
        if loweredArgument.status != "emitted" { return loweredArgument } else {}
        var parts: List[Str] = ["pep_fn_", target.node.text, "("]
        for part in loweredArgument.sourceParts { parts = append(parts, part) }
        parts = pep_c23_close_generated_call(nodes, parts, 1)
        return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
      }
    } else {
      let returnedUnion = if unionResult {
        pep_c23_union_declaration(nodes, result.node.text)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      let constructorVariant = if targetValue.found && targetValue.node.kind == "call" {
        pep_c23_union_variant(nodes, targetValue.node.text)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      let constructorUnion = if constructorVariant.found {
        pep_c23_union_of_variant(nodes, constructorVariant.node)
      } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
      let safeRecursiveUnionConstruction = returnedUnion.found && constructorUnion.found &&
        returnedUnion.node.id == constructorUnion.node.id &&
        pep_c23_union_is_recursive(nodes, returnedUnion.node)
      // A zero-argument function that calls itself has no base case and no progress argument, so
      // name it explicitly instead of letting it fall into the generic result-shape refusal.
      if targetValue.found && targetValue.node.kind == "call" &&
         targetValue.node.text == target.node.text {
        return pep_c23_unsupported("Pep C23 recursive calls are unsupported for zero-argument targets")
      } else {}
      if argument.found || secondArgument.found || thirdArgument.found ||
         (!conditionalTarget && !pep_c23_call_free_expression(nodes, targetValue.node) &&
          !(recordResult && targetValue.found && targetValue.node.kind == "record" &&
            !pep_c23_infallible_value(nodes, targetValue.node)) &&
          !(stringResult && targetValue.found && targetValue.node.kind == "string") &&
          !safeRecursiveUnionConstruction) {
        return pep_c23_unsupported("Pep C23 zero-argument calls require a call-free scalar result, safe record construction, or direct recursive-union constructor result")
      } else {}
      var parts: List[Str] = ["pep_fn_", target.node.text, "("]
      parts = pep_c23_close_generated_call(nodes, parts, 0)
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
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
    // Str only participates in == and !=, and a string *literal* is always a Str. Probing for Str
    // on every arithmetic operand costs a full node-list scan per operand, which is a large share of
    // the emitter's per-statement step budget, so gate the probe on what can actually be a Str.
    let checkLeftStr = node.text == "==" || node.text == "!=" || left.node.kind == "string"
    let checkRightStr = node.text == "==" || node.text == "!=" || right.node.kind == "string"
    let leftStringValue = if checkLeftStr {
      pep_c23_str_expression(nodes, function, left.node)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    let rightStringValue = if checkRightStr {
      pep_c23_str_expression(nodes, function, right.node)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    if leftStringValue.found || rightStringValue.found {
      if !leftStringValue.found || !rightStringValue.found ||
         (node.text != "==" && node.text != "!=") {
        return pep_c23_unsupported("Pep C23 Str operands currently support only equality and inequality against another Str")
      } else {}
      // String literals have no runtime failure path, so comparing two literals is safe; this uses
      // the same precise predicate as record construction and many-argument calls.
      if pep_c23_infallible_value(nodes, left.node) &&
         pep_c23_infallible_value(nodes, right.node) {
        return pep_c23_unsupported("Pep C23 rejects two fallible Str comparison operands because C operand evaluation order is unspecified")
      } else {}
      let loweredLeftString = pep_c23_expression(nodes, function, left.node)
      let loweredRightString = pep_c23_expression(nodes, function, right.node)
      if loweredLeftString.status != "emitted" { return loweredLeftString } else {}
      if loweredRightString.status != "emitted" { return loweredRightString } else {}
      var stringParts: List[Str] = if node.text == "!=" { ["(!pep_str_equal("] } else { ["pep_str_equal("] }
      for part in loweredLeftString.sourceParts { stringParts = append(stringParts, part) }
      stringParts = append(stringParts, ", ")
      for part in loweredRightString.sourceParts { stringParts = append(stringParts, part) }
      if node.text == "!=" { stringParts = append(stringParts, "))") } else {
        stringParts = append(stringParts, ")")
      }
      return PepC23Emission { status: "emitted", sourceParts: stringParts, diagnostic: "" }
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
  for statement in nodes {
    if statement.parentId == function.id && statement.role == "statement" &&
       (statement.kind == "for_in" || statement.kind == "while") {
      return pep_c23_unsupported("Pep C23 conditional-return specialization does not lower loops")
    } else {}
  }
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
  let thirdParameter = pep_c23_child(nodes, function.id, "parameter", 2)
  let extraParameter = pep_c23_child(nodes, function.id, "parameter", 3)
  let parameterType = if parameter.found { pep_c23_child(nodes, parameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  let secondParameterType = if secondParameter.found { pep_c23_child(nodes, secondParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  let thirdParameterType = if thirdParameter.found { pep_c23_child(nodes, thirdParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  let parameterIsScalar = parameterType.found && parameterType.node.kind == "type_scalar" &&
    (parameterType.node.text == "Int" || parameterType.node.text == "Bool")
  let secondParameterIsScalar = secondParameterType.found && secondParameterType.node.kind == "type_scalar" &&
    (secondParameterType.node.text == "Int" || secondParameterType.node.text == "Bool")
  let thirdParameterIsScalar = thirdParameterType.found && thirdParameterType.node.kind == "type_scalar" &&
    (thirdParameterType.node.text == "Int" || thirdParameterType.node.text == "Bool")
  let parameterIsRecord = if parameterType.found && parameterType.node.kind == "type_named" {
    pep_c23_record_declaration(nodes, parameterType.node.text).found
  } else { false }
  let secondParameterIsRecord = if secondParameterType.found && secondParameterType.node.kind == "type_named" {
    pep_c23_record_declaration(nodes, secondParameterType.node.text).found
  } else { false }
  let thirdParameterIsRecord = if thirdParameterType.found && thirdParameterType.node.kind == "type_named" {
    pep_c23_record_declaration(nodes, thirdParameterType.node.text).found
  } else { false }
  let result = pep_c23_child(nodes, function.id, "return_type", 0)
  let scalarResult = result.found && result.node.kind == "type_scalar" &&
    (result.node.text == "Int" || result.node.text == "Bool")
  let recordResult = if result.found && result.node.kind == "type_named" {
    pep_c23_record_declaration(nodes, result.node.text)
  } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
  let supportedResult = scalarResult || recordResult.found
  if extraParameter.found || (secondParameter.found && !parameter.found) || (thirdParameter.found && !secondParameter.found) || (function.text == "main" && (parameter.found || secondParameter.found || thirdParameter.found)) || (parameter.found && !(parameterIsScalar || parameterIsRecord)) || (secondParameter.found && !(secondParameterIsScalar || secondParameterIsRecord)) || (thirdParameter.found && !(thirdParameterIsScalar || thirdParameterIsRecord)) || !supportedResult || (function.text == "main" && (!scalarResult || result.node.text != "Int")) {
    return pep_c23_unsupported("Pep C23 conditional-return functions require supported scalar parameters and scalar or record results")
  } else {}
  let resultTypeParts = pep_c23_c_parameter_type_parts(nodes, result.node)
  var statementCount = 0
  var conditionalCount = 0
  var prefixValid = true
  var lastStatement = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
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
  if !condition.found || pep_c23_count_children(nodes, statement.node.id, "then") != 1 || pep_c23_count_children(nodes, statement.node.id, "else") != 1 {
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
  var parts: List[Str] = ["if (!!("]
  for part in loweredCondition.sourceParts { parts = append(parts, part) }
  parts = append(parts, ")) {\n  ")
  for part in resultTypeParts { parts = append(parts, part) }
  parts = append(parts, " pep_result = ")
  for part in loweredThen.sourceParts { parts = append(parts, part) }
  parts = append(parts, ";\n  pep_leave();\n  return pep_result;\n} else {\n  ")
  for part in resultTypeParts { parts = append(parts, part) }
  parts = append(parts, " pep_result = ")
  for part in loweredElse.sourceParts { parts = append(parts, part) }
  parts = append(parts, ";\n  pep_leave();\n  return pep_result;\n}\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}

fn pep_c23_loop_statement(nodes: List[FlatAstNode], function: FlatAstNode, statement: FlatAstNode, depth: Int, localBindings: List[FlatAstNode], result: PepC23NodeLookup) -> PepC23Emission {
  if depth == 8 { return pep_c23_unsupported("Pep C23 loop condition nesting exceeds the supported depth") } else {}
  let indent = if depth == 0 { "    " } else { "      " }
  if statement.kind == "return" {
    let value = pep_c23_child(nodes, statement.id, "value", 0)
    if !value.found || !result.found { return pep_c23_unsupported("Pep C23 loop return has no value or declared result type") } else {}
    let scalarType = pep_c23_c_scalar_type(result.node)
    let recordType = if result.node.kind == "type_named" {
      pep_c23_record_declaration(nodes, result.node.text)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    var cTypeParts: List[Str] = []
    if scalarType != "" {
      cTypeParts = [scalarType]
    } else {
      if recordType.found {
        cTypeParts = ["pep_record_", int_text(recordType.node.id)]
      } else {
        // Str results join this branch for GUARD-CHAIN returns (Campaign G G-A2-3): the real
        // lexer's stdlib/scan.pep `lex_error_code` returns string literals from statement-level
        // `if ... { return ... } else {}` guards plus a fallthrough return -- checker-valid and
        // the measured blocker since BOOT-A2-20261104-019 item 5. The lowered value is a
        // static-storage pep_str (F3 lifetime repair) so returning it past the frame is safe,
        // and Str equality already lowers through pep_str_equal (measured before this change).
        // Every other unsupported result keeps the exact same refusal.
        if result.node.kind == "type_scalar" && result.node.text == "Str" {
          cTypeParts = ["pep_str"]
        } else {
          return pep_c23_unsupported("Pep C23 conditional return requires a supported scalar or record result")
        }
      }
    }
    let lowered = pep_c23_expression(nodes, function, value.node)
    if lowered.status != "emitted" { return lowered } else {}
    var parts: List[Str] = [indent]
    for part in cTypeParts { parts = append(parts, part) }
    parts = append(parts, " pep_result_")
    parts = append(parts, int_text(statement.id))
    parts = append(parts, " = ")
    for part in lowered.sourceParts { parts = append(parts, part) }
    parts = append(parts, ";\n")
    parts = append(parts, indent)
    parts = append(parts, "pep_leave();\n")
    parts = append(parts, indent)
    parts = append(parts, "return pep_result_")
    parts = append(parts, int_text(statement.id))
    parts = append(parts, ";\n")
    return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
  } else {}
  if statement.kind == "assignment" {
    let value = pep_c23_child(nodes, statement.id, "value", 0)
    if !value.found { return pep_c23_unsupported("Pep C23 loop assignment has no value") } else {}
    let lowered = pep_c23_expression(nodes, function, value.node)
    if lowered.status != "emitted" { return lowered } else {}
    var targetId = -1
    var targetFound = false
    for local in localBindings {
      if local.parentId == function.id && local.role == "statement" && local.kind == "var" && local.text == statement.text {
        targetId = local.id
        targetFound = true
      } else {}
    }
    if !targetFound { return pep_c23_unsupported("Pep C23 loop assignments must target a direct mutable local") } else {}
    var parts: List[Str] = [indent, "pep_local_", int_text(targetId), " = "]
    for part in lowered.sourceParts { parts = append(parts, part) }
    parts = append(parts, ";\n")
    return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
  } else {
    if statement.kind == "if_statement" {
      let condition = pep_c23_child(nodes, statement.id, "condition", 0)
      if !condition.found { return pep_c23_unsupported("Pep C23 loop conditional has no condition") } else {}
      let loweredCondition = pep_c23_expression(nodes, function, condition.node)
      if loweredCondition.status != "emitted" { return loweredCondition } else {}
      var thenParts: List[Str] = []
      var elseParts: List[Str] = []
      var foundThen = false
      var foundElse = false
      for branchStatement in nodes {
        if branchStatement.parentId == statement.id && branchStatement.role == "then" {
          foundThen = true
          let loweredBranch = pep_c23_loop_statement(nodes, function, branchStatement, depth + 1, localBindings, result)
          if loweredBranch.status != "emitted" { return loweredBranch } else {}
          for part in loweredBranch.sourceParts { thenParts = append(thenParts, part) }
        } else {
          if branchStatement.parentId == statement.id && branchStatement.role == "else" {
            foundElse = true
            let loweredBranch = pep_c23_loop_statement(nodes, function, branchStatement, depth + 1, localBindings, result)
            if loweredBranch.status != "emitted" { return loweredBranch } else {}
            for part in loweredBranch.sourceParts { elseParts = append(elseParts, part) }
          } else {}
        }
      }
      if !foundThen { return pep_c23_unsupported("Pep C23 conditional lowering requires a non-empty then branch") } else {}
      var parts: List[Str] = [indent, "if (!!("]
      for part in loweredCondition.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")) {\n")
      for part in thenParts { parts = append(parts, part) }
      parts = append(parts, indent)
      if foundElse {
        parts = append(parts, "} else {\n")
        for part in elseParts { parts = append(parts, part) }
        parts = append(parts, indent)
      } else {}
      parts = append(parts, "}\n")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else { return pep_c23_unsupported("Pep C23 loop bodies support assignments, returns, and conditionals with assignment sequences") }
  }
}
// Arena-backed update of a mutable Int or Bool list binding. Only the binding being assigned may
// be prepended to or reversed, which keeps the source and destination element types identical and
// keeps this path free of any element-type inference.
fn pep_c23_mutable_list_record_declaration(nodes: List[FlatAstNode], binding: FlatAstNode) -> PepC23NodeLookup {
  let declared = pep_c23_child(nodes, binding.id, "annotation", 0)
  if declared.found && declared.node.kind == "type_list" {
    return pep_c23_record_list_declaration(nodes, declared.node)
  } else {}
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
// Arena-backed updates for one declared record list type, emitted beside that record's
// pep_list_record_N typedef so a record list accumulates exactly like the Int, Bool and Str lists.
fn pep_c23_record_list_update_source(record: FlatAstNode) -> List[Str] {
  let id = int_text(record.id)
  return ["[[maybe_unused]] static pep_list_record_", id, " pep_list_record_", id, "_prepend(pep_arena_t *pep_a, pep_list_record_", id, " pep_values, pep_record_", id, " pep_value) {\n  if (pep_values.length != 0 && pep_values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_values.length == SIZE_MAX || pep_values.length + 1 > SIZE_MAX / sizeof(pep_record_", id, ")) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  size_t pep_count = pep_values.length + 1;\n  pep_record_", id, " *pep_out = (pep_record_", id, " *)pep_arena_alloc(pep_a, pep_count * sizeof(pep_record_", id, "), _Alignof(pep_record_", id, "));\n  if (pep_out == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  pep_out[0] = pep_value;\n  for (size_t pep_i = 0; pep_i < pep_values.length; ++pep_i) { pep_out[pep_i + 1] = pep_values.data[pep_i]; }\n  return (pep_list_record_", id, "){ .data = pep_out, .length = pep_count };\n}\n[[maybe_unused]] static pep_list_record_", id, " pep_list_record_", id, "_reverse(pep_arena_t *pep_a, pep_list_record_", id, " pep_values) {\n  if (pep_values.length != 0 && pep_values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_values.length == 0) { return (pep_list_record_", id, "){ .data = NULL, .length = 0 }; }\n  if (pep_values.length > SIZE_MAX / sizeof(pep_record_", id, ")) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  pep_record_", id, " *pep_out = (pep_record_", id, " *)pep_arena_alloc(pep_a, pep_values.length * sizeof(pep_record_", id, "), _Alignof(pep_record_", id, "));\n  if (pep_out == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  for (size_t pep_i = 0; pep_i < pep_values.length; ++pep_i) { pep_out[pep_i] = pep_values.data[pep_values.length - 1 - pep_i]; }\n  return (pep_list_record_", id, "){ .data = pep_out, .length = pep_values.length };\n}\n"]
}
fn pep_c23_mutable_list_update(nodes: List[FlatAstNode], function: FlatAstNode, call: FlatAstNode,
  target: FlatAstNode) -> PepC23Emission {
  let elementKind = pep_c23_mutable_list_element_kind(nodes, target)
  if elementKind != "integer" && elementKind != "boolean" && elementKind != "string" && elementKind != "record" {
    return pep_c23_unsupported("Pep C23 prepend/reverse currently require an Int, Bool, Str, or record list binding")
  } else {}
  var helperPrefix: List[Str] = ["pep_list_int_"]
  if elementKind == "boolean" { helperPrefix = ["pep_list_bool_"] } else {}
  if elementKind == "string" { helperPrefix = ["pep_list_str_"] } else {}
  if elementKind == "record" {
    let recordList = pep_c23_mutable_list_record_declaration(nodes, target)
    if !recordList.found {
      return pep_c23_unsupported("Pep C23 mutable record list binding requires a declared record element type")
    } else {}
    helperPrefix = ["pep_list_record_", int_text(recordList.node.id), "_"]
  } else {}
  let argument = pep_c23_child(nodes, call.id, "argument", 0)
  let secondArgument = pep_c23_child(nodes, call.id, "argument", 1)
  let thirdArgument = pep_c23_child(nodes, call.id, "argument", 2)
  if call.text == "reverse" {
    if !argument.found || secondArgument.found || thirdArgument.found {
      return pep_c23_unsupported("Pep C23 reverse requires exactly one list argument")
    } else {}
    if argument.node.kind != "name" || argument.node.text != target.text {
      return pep_c23_unsupported("Pep C23 reverse is currently limited to the binding being assigned")
    } else {}
    var reverseParts: List[Str] = []
    for part in helperPrefix { reverseParts = append(reverseParts, part) }
    reverseParts = append(reverseParts, "reverse(pep_arena, pep_local_")
    reverseParts = append(reverseParts, int_text(target.id))
    reverseParts = append(reverseParts, ")")
    return PepC23Emission { status: "emitted", sourceParts: reverseParts, diagnostic: "" }
  } else {}
  if call.text != "prepend" {
    return pep_c23_unsupported("Pep C23 mutable list updates support prepend and reverse only")
  } else {}
  if !argument.found || !secondArgument.found || thirdArgument.found {
    return pep_c23_unsupported("Pep C23 prepend requires a list and exactly one value")
  } else {}
  if argument.node.kind != "name" || argument.node.text != target.text {
    return pep_c23_unsupported("Pep C23 prepend is currently limited to the binding being assigned")
  } else {}
  if pep_c23_infallible_value(nodes, secondArgument.node) {
    return pep_c23_unsupported("Pep C23 prepend cannot evaluate a fallible value inside an arena update")
  } else {}
  if elementKind == "string" && pep_c23_str_expression(nodes, function, secondArgument.node).found == false {
    return pep_c23_unsupported("Pep C23 Str list prepend requires a Str literal, parameter, or local")
  } else {}
  let lowered = pep_c23_expression(nodes, function, secondArgument.node)
  if lowered.status != "emitted" { return lowered } else {}
  var parts: List[Str] = []
  for part in helperPrefix { parts = append(parts, part) }
  parts = append(parts, "prepend(pep_arena, pep_local_")
  parts = append(parts, int_text(target.id))
  parts = append(parts, ", ")
  for part in lowered.sourceParts { parts = append(parts, part) }
  parts = append(parts, ")")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_while_body(nodes: List[FlatAstNode], function: FlatAstNode, loop: FlatAstNode, localBindings: List[FlatAstNode], result: PepC23NodeLookup) -> PepC23Emission {
  let condition = pep_c23_child(nodes, loop.id, "condition", 0)
  if !condition.found || pep_c23_count_children(nodes, loop.id, "body") == 0 {
    return pep_c23_unsupported("Pep C23 while lowering requires a condition and a non-empty assignment body")
  } else {}
  let loweredCondition = pep_c23_expression(nodes, function, condition.node)
  if loweredCondition.status != "emitted" { return loweredCondition } else {}
  var parts: List[Str] = ["  while (!!("]
  for part in loweredCondition.sourceParts { parts = append(parts, part) }
  parts = append(parts, ")) {\n")
  for statement in nodes {
    if statement.parentId == loop.id && statement.role == "body" {
      if statement.kind == "if_statement" || statement.kind == "return" || statement.kind == "let" {
        if statement.kind == "let" {
          let initialValue = pep_c23_child(nodes, statement.id, "value", 0)
          if !initialValue.found || initialValue.node.kind != "call" ||
             initialValue.node.text != "byte_at" {
            return pep_c23_unsupported("Pep C23 while-local lets currently require a byte_at initializer")
          } else {}
          let loweredValue = pep_c23_expression(nodes, function, initialValue.node)
          if loweredValue.status != "emitted" { return loweredValue } else {}
          var bindingParts: List[Str] = ["    int64_t pep_local_", int_text(statement.id), " = "]
          for part in loweredValue.sourceParts { bindingParts = append(bindingParts, part) }
          bindingParts = append(bindingParts, ";\n")
          for part in bindingParts { parts = append(parts, part) }
        } else {
          let loweredConditional = pep_c23_loop_statement(nodes, function, statement, 0, localBindings, result)
          if loweredConditional.status != "emitted" { return loweredConditional } else {}
          for part in loweredConditional.sourceParts { parts = append(parts, part) }
        }
      } else {
        if statement.kind != "assignment" { return pep_c23_unsupported("Pep C23 while bodies support byte_at lets, assignments, returns, and conditionals") } else {}
        let value = pep_c23_child(nodes, statement.id, "value", 0)
        if !value.found { return pep_c23_unsupported("Pep C23 while assignment has no value") } else {}
        // Only a list value, a name, or a prepend/reverse call can carry a list update, and this
        // runs for every assignment in every loop body. Scanning the whole node list for the common
        // scalar assignment was pure waste against a fixed step budget.
        let listUpdateCandidate = value.node.kind == "list" || value.node.kind == "name" ||
          (value.node.kind == "call" &&
           (value.node.text == "prepend" || value.node.text == "reverse"))
        let assignmentTargetList = if listUpdateCandidate {
          pep_c23_mutable_list_binding(nodes, function, statement.text)
        } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
        var listUpdateFound = false
        var listUpdate = PepC23Emission { status: "unsupported", sourceParts: [], diagnostic: "" }
        if assignmentTargetList.found && value.node.kind == "call" &&
           (value.node.text == "prepend" || value.node.text == "reverse") {
          listUpdate = pep_c23_mutable_list_update(nodes, function, value.node, assignmentTargetList.node)
          listUpdateFound = true
        } else {}
        let loweredValue = if listUpdateFound { listUpdate } else { pep_c23_expression(nodes, function, value.node) }
        if loweredValue.status != "emitted" { return loweredValue } else {}
        var targetId = -1
        var targetFound = false
        for local in localBindings {
          if local.parentId == function.id && local.role == "statement" && local.kind == "var" && local.text == statement.text {
            targetId = local.id
            targetFound = true
          } else {}
        }
        if !targetFound { return pep_c23_unsupported("Pep C23 while assignments must target direct mutable locals") } else {}
        let targetList = assignmentTargetList
        if targetList.found {
          let targetKind = pep_c23_mutable_list_element_kind(nodes, targetList.node)
          var sourceKind = if listUpdateFound { targetKind } else { "" }
          if sourceKind == "" && value.node.kind == "name" {
            let sourceList = pep_c23_mutable_list_binding(nodes, function, value.node.text)
            let sourceIntParameter = pep_c23_int_list_parameter(nodes, function, value.node.text)
            let sourceBoolParameter = pep_c23_bool_list_parameter(nodes, function, value.node.text)
            if sourceList.found { sourceKind = pep_c23_mutable_list_element_kind(nodes, sourceList.node) } else {}
            if sourceIntParameter.found { sourceKind = "integer" } else {}
            if sourceBoolParameter.found { sourceKind = "boolean" } else {}
          } else {}
          if sourceKind != targetKind || (sourceKind != "integer" && sourceKind != "boolean" && sourceKind != "string" && sourceKind != "record") {
            return pep_c23_unsupported("Pep C23 mutable list reassignment requires a matching typed list binding or parameter")
          } else {}
        } else {}
        for part in ["    pep_local_", int_text(targetId), " = "] { parts = append(parts, part) }
        for part in loweredValue.sourceParts { parts = append(parts, part) }
        parts = append(parts, ";\n")
      }
    } else {}
  }
  parts = append(parts, "  }\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_function_expression(nodes: List[FlatAstNode], function: FlatAstNode, checked: CheckerReport) -> PepC23Emission {
  let parameters = pep_c23_parameters(nodes, function)
  let result = pep_c23_child(nodes, function.id, "return_type", 0)
  let resultCType = if result.found { pep_c23_c_parameter_type(nodes, result.node) } else { "" }
  var parameterProblem = false
  for parameter in parameters {
    let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
    if !parameterType.found || pep_c23_c_parameter_type(nodes, parameterType.node) == "" {
      parameterProblem = true
    } else {}
  }
  // Entry-parameter SourceBytes grant (A1 docs/NATIVE_SOURCE_GRANT_CONTRACT_DRAFT.md
  // @a802290, mode "entry-parameter"): the host's native main wrapper passes the
  // opened target's OWN bytes as the entry's first SourceBytes parameter. This
  // predicate admits exactly that one shape -- `fn main(<one SourceBytes parameter>)`
  // -- and nothing else changes: source_bytes() as a CALL stays refused, no ambient
  // authority is added, and every other parameterised main still refuses below.
  // The bytes are the target's because the host wrapper is their only producer.
  // COST DISCIPLINE: the parameter lookups run ONLY for a one-parameter main. Computing
  // them unconditionally measured OVER the fixed 100k budget on the near-ceiling
  // recursive-depth fixture, because pep_c23_child walks the node list.
  var entrySourceOnly = false
  if function.text == "main" && length(parameters) == 1 {
    let entryParameter = pep_c23_child(nodes, function.id, "parameter", 0)
    let entryParameterType = if entryParameter.found {
      pep_c23_child(nodes, entryParameter.node.id, "type", 0)
    } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
    entrySourceOnly = entryParameterType.found &&
      pep_c23_c_parameter_type(nodes, entryParameterType.node) == "pep_source_bytes"
  } else {}
  if parameterProblem || length(parameters) != pep_c23_count_children(nodes, function.id, "parameter") ||
     (function.text == "main" && length(parameters) != 0 && !entrySourceOnly) ||
     resultCType == "" ||
     (function.text == "main" && result.node.text != "Int") {
    // Str results are the one missing shape the real lexer blocks on: `lex_error_code`
    // passes the checker and then hit this gate (measured, BOOT-A2-20261104-019 item 5).
    // The body path already lowers every Str value position (say proves it) and the wrapper
    // is ctype-generic (`<ctype> pep_result = <expr>`), so admitting Str here is the whole
    // feature: conditional-return and say-classification boundaries stay exactly as pinned.
    return pep_c23_unsupported("Pep C23 functions require supported parameters and Str, scalar or record results")
  } else {}
  var localBindings: List[FlatAstNode] = []
  var localBindingsCollected = false
  var returned = false
  var statementCount = 0
  var returnStatement = PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
  for statement in nodes {
    if statement.parentId == function.id && statement.role == "statement" {
      statementCount = statementCount + 1
      if (statement.kind == "let" || statement.kind == "var") && !returned {
        let initialValue = pep_c23_child(nodes, statement.id, "value", 0)
        if !initialValue.found { return pep_c23_unsupported("Pep C23 local binding has no value") } else {}
        if statement.kind == "var" {
          let stringLocalValue = pep_c23_str_expression(nodes, function, initialValue.node)
          if stringLocalValue.found {
            return pep_c23_unsupported("Pep C23 mutable Str local bindings are not yet lowered")
          } else {}
        } else {}
        if initialValue.node.kind == "list" && (statement.kind == "let" || statement.kind == "var") {
          let recursiveUnionList = if statement.kind == "let" {
            pep_c23_union_list_local_declaration(nodes, function, statement.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          if recursiveUnionList.found {
            if !pep_c23_local_recursive_union_list_is_iterated(nodes, function, statement.text) {
              if pep_c23_count_children(nodes, initialValue.node.id, "element") == 0 {
                return pep_c23_unsupported("Pep C23 recursive union list local requires at least one constructor element")
              } else {}
              for item in nodes {
                if item.parentId == initialValue.node.id && item.role == "element" &&
                   !pep_c23_union_list_element_supported(nodes, recursiveUnionList.node, item) {
                  return pep_c23_unsupported("Pep C23 recursive union list locals require matching constructors with scalar literal payloads")
                } else {}
              }
            } else {}
          } else {
            let recordList = pep_c23_record_list_declaration(nodes, initialValue.node)
            var hasRecordElement = false
            for item in nodes {
              if item.parentId == initialValue.node.id && item.role == "element" && item.kind == "record" { hasRecordElement = true } else {}
              if item.parentId == initialValue.node.id && item.role == "element" && item.kind != "integer" && item.kind != "boolean" && item.kind != "string" && !pep_c23_is_negative_int_literal(nodes, item) && (item.kind != "record" || statement.kind != "let") {
                return pep_c23_unsupported("Pep C23 immutable collection bindings require Int, Bool, or supported record list literals")
              } else {}
            }
            if hasRecordElement && !recordList.found {
              return pep_c23_unsupported("Pep C23 immutable record list binding has no supported declared record type")
            } else {}
          }
          // List descriptors have value semantics, so reassignment copies the descriptor.
        } else {
          let initial = pep_c23_expression_checked(nodes, function, initialValue.node, checked)
          if initial.status != "emitted" { return initial } else {}
        }
      } else {
        if statement.kind == "for_in" && !returned {
          if !localBindingsCollected {
            for local in nodes {
              if local.parentId == function.id && local.role == "statement" && local.kind == "var" {
                localBindings = append(localBindings, local)
              } else {}
            }
            localBindingsCollected = true
          } else {}
          for local in nodes {
            if local.parentId == function.id && local.role == "statement" && local.id != statement.id && (local.kind == "let" || local.kind == "var" || local.kind == "for_in") && local.text == statement.text {
              return pep_c23_unsupported("Pep C23 for-in bindings cannot shadow function locals or other loop bindings")
            } else {}
          }
          var parameterShadow = false
          for parameterNode in pep_c23_parameters(nodes, function) {
            if parameterNode.text == statement.text { parameterShadow = true } else {}
          }
          if parameterShadow {
            return pep_c23_unsupported("Pep C23 for-in bindings cannot shadow function parameters")
          } else {}
          let iterable = pep_c23_child(nodes, statement.id, "iterable", 0)
          let iterableList = if iterable.found { pep_c23_list_literal(nodes, function, iterable.node) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableLocal = if iterable.found && iterable.node.kind == "name" { pep_c23_mutable_list_binding(nodes, function, iterable.node.text) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableIntegerParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_int_list_parameter(nodes, function, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableBooleanParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_bool_list_parameter(nodes, function, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableRecordParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_record_list_parameter(nodes, function, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableUnionParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_union_list_parameter(nodes, function, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableParameter = if iterableIntegerParameter.found { iterableIntegerParameter } else {
            if iterableBooleanParameter.found { iterableBooleanParameter } else {
              if iterableRecordParameter.found { iterableRecordParameter } else { iterableUnionParameter }
            }
          }
          if !iterable.found || (!iterableList.found && !iterableParameter.found && !iterableLocal.found) || pep_c23_count_children(nodes, statement.id, "body") == 0 {
            return pep_c23_unsupported("Pep C23 for-in lowering requires a supported list literal or parameter and a non-empty supported body")
          } else {}
          if iterableList.found {
            let recordLiteral = pep_c23_record_list_declaration(nodes, iterableList.node)
            let recursiveUnionList = if iterableList.found && iterable.found && iterable.node.kind == "name" {
              pep_c23_union_list_local_declaration(nodes, function, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
            if recursiveUnionList.found &&
               pep_c23_count_children(nodes, iterableList.node.id, "element") == 0 {
              return pep_c23_unsupported("Pep C23 recursive union list local requires at least one constructor element")
            } else {}
            if !recursiveUnionList.found {
              for item in nodes {
                if item.parentId == iterableList.node.id && item.role == "element" {
                  if recordLiteral.found {
                    if item.kind != "record" { return pep_c23_unsupported("Pep C23 record list iteration requires record values") } else {}
                  } else {
                    if item.kind != "integer" && item.kind != "boolean" && !pep_c23_is_negative_int_literal(nodes, item) {
                      return pep_c23_unsupported("Pep C23 for-in list literals currently require integer or Bool elements")
                    } else {}
                  }
                } else {}
              }
            } else {}
          } else {}
          for bodyStatement in nodes {
            if bodyStatement.parentId == statement.id && bodyStatement.role == "body" {
              let loweredBody = pep_c23_loop_statement(nodes, function, bodyStatement, 0, localBindings, result)
              if loweredBody.status != "emitted" { return loweredBody } else {}
            } else {}
          }
        } else {
          if (statement.kind == "while" || statement.kind == "if_statement") && !returned {
            if !localBindingsCollected {
              for local in nodes {
                if local.parentId == function.id && local.role == "statement" && local.kind == "var" {
                  localBindings = append(localBindings, local)
                } else {}
              }
              localBindingsCollected = true
            } else {}
            let loweredControl = if statement.kind == "while" {
              pep_c23_while_body(nodes, function, statement, localBindings, result)
            } else { pep_c23_loop_statement(nodes, function, statement, 0, localBindings, result) }
            if loweredControl.status != "emitted" { return loweredControl } else {}
          } else {
            if statement.kind == "return" && !returned {
              returned = true
              returnStatement = PepC23NodeLookup { found: true, node: statement }
            } else {
              if statement.kind == "expression_statement" {
                // Validation gate: accept exactly the say(...) shape the assembly path lowers, so
                // an unsupported expression statement still fails closed before any emission.
                let sayCheck = pep_c23_say_statement(nodes, function, statement)
                if sayCheck.status != "emitted" { return sayCheck } else {}
              } else {
                return pep_c23_unsupported("Pep C23 functions require local bindings and supported loops followed by one return")
              }
            }
          }
        }
      }
    } else {}
  }
  if statementCount == 0 || !returned { return pep_c23_unsupported("Pep C23 functions require a return statement") } else {}
  let value = pep_c23_child(nodes, returnStatement.node.id, "value", 0)
  if !value.found { return pep_c23_unsupported("Pep C23 return statement has no value") } else {}
  return pep_c23_expression_checked(nodes, function, value.node, checked)
}
fn pep_c23_function_at(functions: List[FlatAstNode], wanted: Int) -> PepC23NodeLookup {
  var index = 0
  for function in functions {
    if index == wanted { return PepC23NodeLookup { found: true, node: function } } else {}
    index = index + 1
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}

// Prerequisites are facts, not text: a chunked caller needs to know which declarations a unit
// depends on so it can assemble a compilable translation unit without whole-program emission.
// Attribution uses the flat-AST preorder-contiguity property: a node's descendants occupy
// [node.id, nextTopLevelId). tests/test_c23_bounded_emission.py pins that property, so this is
// one scan plus a range test rather than an ancestor walk per candidate.
fn pep_c23_declared_type(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == -1 &&
       (node.kind == "record_declaration" || node.kind == "union_declaration") &&
       node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}

fn pep_c23_subtree_end(nodes: List[FlatAstNode], functionId: Int) -> Int {
  var boundary = 0
  var boundaryFound = false
  for node in nodes {
    if node.parentId == -1 && !(node.id <= functionId) {
      if !boundaryFound || !(boundary <= node.id) { boundary = node.id; boundaryFound = true } else {}
    } else {}
  }
  if boundaryFound { return boundary } else {}
  return 2147483647
}

fn pep_c23_declaration_by_id(nodes: List[FlatAstNode], wanted: Int) -> PepC23NodeLookup {
  for node in nodes {
    if node.id == wanted { return PepC23NodeLookup { found: true, node: node } } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}

// Direct type references owned by one declaration or function: its own subtree range only.
// `type_named` is the sole form that names another declaration, so this is the whole edge set.
fn pep_c23_owned_type_ids(nodes: List[FlatAstNode], ownerId: Int) -> PepC23IdList {
  let subtreeEnd = pep_c23_subtree_end(nodes, ownerId)
  var ids: List[Int] = []
  for candidate in nodes {
    if ownerId <= candidate.id && !(subtreeEnd <= candidate.id) && candidate.kind == "type_named" {
      let declaration = pep_c23_declared_type(nodes, candidate.text)
      if declaration.found {
        if !contains(ids, declaration.node.id) { ids = append(ids, declaration.node.id) } else {}
      } else {
        return PepC23IdList {
          status: "unsupported",
          diagnostic: "Pep C23 unit references a type that this source does not declare",
          ids: []
        }
      }
    } else {}
  }
  return PepC23IdList { status: "ok", diagnostic: "", ids: ids }
}

// Prerequisite closure: direct references of the function, then each prerequisite's own
// references, until nothing new appears. Recursive and mutually recursive declarations terminate
// because an id already in the set is never enqueued again. A partial answer would be worse than a
// refusal here: the caller would assemble C with a missing typedef and no diagnostic.
fn pep_c23_unit_prerequisites(nodes: List[FlatAstNode], functionId: Int) -> PepC23UnitPrerequisites {
  let direct = pep_c23_owned_type_ids(nodes, functionId)
  if direct.status != "ok" {
    return PepC23UnitPrerequisites {
      status: "unsupported", diagnostic: direct.diagnostic, kinds: [], nodeIds: []
    }
  } else {}
  var ids = direct.ids
  var pending = direct.ids
  var index = 0
  while !(length(pending) <= index) {
    let expanded = pep_c23_owned_type_ids(nodes, pep_c23_list_int_at(pending, index))
    if expanded.status != "ok" {
      return PepC23UnitPrerequisites {
        status: "unsupported", diagnostic: expanded.diagnostic, kinds: [], nodeIds: []
      }
    } else {}
    for id in expanded.ids {
      if !contains(ids, id) {
        ids = append(ids, id)
        pending = append(pending, id)
      } else {}
    }
    index = index + 1
  }
  var kinds: List[Str] = []
  for id in ids {
    let declaration = pep_c23_declaration_by_id(nodes, id)
    if declaration.found { kinds = append(kinds, declaration.node.kind) } else {
      return PepC23UnitPrerequisites {
        status: "unsupported",
        diagnostic: "Pep C23 unit prerequisite has no declaration node",
        kinds: [],
        nodeIds: []
      }
    }
  }
  return PepC23UnitPrerequisites { status: "ok", diagnostic: "", kinds: kinds, nodeIds: ids }
}

// Prerequisite facts say what a unit depends on, not whether those declarations can be lowered.
// Without this, a caller could only learn emittability by running whole-program emission -- the
// cost the bounded contract exists to avoid. These predicates are the emitter's own support rules,
// so the answer agrees with what emission would do rather than approximating it.
fn pep_c23_declaration_check(nodes: List[FlatAstNode], nodeId: Int) -> PepC23DeclarationCheck {
  let declaration = pep_c23_declaration_by_id(nodes, nodeId)
  if !declaration.found {
    return PepC23DeclarationCheck { status: "unsupported", diagnostic: "Pep C23 declaration is missing" }
  } else {}
  if declaration.node.parentId != -1 {
    return PepC23DeclarationCheck { status: "unsupported", diagnostic: "Pep C23 declaration must be top level" }
  } else {}
  if declaration.node.kind == "record_declaration" {
    return pep_c23_record_declaration_check(nodes, declaration.node, 0)
  } else {}
  if declaration.node.kind == "union_declaration" {
    if !pep_c23_union_supported_layout(nodes, declaration.node) {
      return PepC23DeclarationCheck {
        status: "unsupported", diagnostic: "Pep C23 tagged union has an unsupported layout"
      }
    } else {}
    return PepC23DeclarationCheck { status: "ok", diagnostic: "" }
  } else {}
  return PepC23DeclarationCheck {
    status: "unsupported", diagnostic: "Pep C23 declaration kind has no C23 lowering"
  }
}

fn pep_c23_record_declaration_check(nodes: List[FlatAstNode], record: FlatAstNode, depth: Int) -> PepC23DeclarationCheck {
  if 16 <= depth {
    return PepC23DeclarationCheck {
      status: "unsupported", diagnostic: "Pep C23 record nesting is too deep to classify"
    }
  } else {}
  var fields = 0
  for field in nodes {
    if field.parentId == record.id && field.role == "field" && field.kind == "field_declaration" {
      fields = fields + 1
      let fieldType = pep_c23_child(nodes, field.id, "type", 0)
      if !fieldType.found {
        return PepC23DeclarationCheck {
          status: "unsupported", diagnostic: "Pep C23 record field has no type"
        }
      } else {}
      let fieldKind = pep_c23_c_record_field_type(nodes, record, fieldType.node)
      if fieldKind == "" {
        return PepC23DeclarationCheck {
          status: "unsupported",
          diagnostic: "Pep C23 record fields require Int, Bool, or a preceding record declaration"
        }
      } else {}
      if fieldKind == "record" {
        let nested = pep_c23_declared_type(nodes, fieldType.node.text)
        if !nested.found {
          return PepC23DeclarationCheck {
            status: "unsupported", diagnostic: "Pep C23 nested record field has no declaration"
          }
        } else {}
        let inner = pep_c23_record_declaration_check(nodes, nested.node, depth + 1)
        if inner.status != "ok" { return inner } else {}
      } else {}
    } else {}
  }
  if fields == 0 {
    return PepC23DeclarationCheck { status: "unsupported", diagnostic: "Pep C23 does not lower empty records" }
  } else {}
  return PepC23DeclarationCheck { status: "ok", diagnostic: "" }
}

// The caller-facing answer: are every one of this function's prerequisites emittable?
fn pep_c23_unit_declarations_check(nodes: List[FlatAstNode], functionId: Int) -> PepC23DeclarationCheck {
  let prerequisites = pep_c23_unit_prerequisites(nodes, functionId)
  if prerequisites.status != "ok" {
    return PepC23DeclarationCheck { status: prerequisites.status, diagnostic: prerequisites.diagnostic }
  } else {}
  // Traversal order has to match emission, not closure discovery (CR3). Emission lowers every
  // record declaration before any union declaration, each in source order, so the first refusal a
  // caller actually sees is the lowest-id failing record and only then the lowest-id failing union.
  // Walking the closure in discovery order reported the union's layout rule for a source whose real
  // first failure was an empty record: a caller relaying that text would name the wrong rule.
  for node in nodes {
    if node.parentId == -1 && node.kind == "record_declaration" &&
       contains(prerequisites.nodeIds, node.id) {
      let recordCheck = pep_c23_declaration_check(nodes, node.id)
      if recordCheck.status != "ok" { return recordCheck } else {}
    } else {}
  }
  for node in nodes {
    if node.parentId == -1 && node.kind == "union_declaration" &&
       contains(prerequisites.nodeIds, node.id) {
      let unionCheck = pep_c23_declaration_check(nodes, node.id)
      if unionCheck.status != "ok" { return unionCheck } else {}
    } else {}
  }
  return PepC23DeclarationCheck { status: "ok", diagnostic: "" }
}

// The bounded unit entry: the unit text comes from the already-gated bounded path, so its bytes
// are identical to emit_c23_function_unit by construction, and the prerequisite facts are the only
// additional work. Nothing here scans the program for other functions' bodies, typedefs or the
// epilogue.
fn emit_c23_function_unit_bounded(parsed: ParserProgress, checked: CheckerReport, index: Int) -> PepC23BoundedUnit {
  var selected = pep_c23_empty_ast_node()
  var found = false
  var seen = 0
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      if seen == index { selected = node; found = true } else {}
      seen = seen + 1
    } else {}
  }
  if !found {
    return PepC23BoundedUnit {
      status: "unsupported",
      diagnostic: "Pep C23 function unit index is out of range",
      sourceParts: [],
      prerequisiteKinds: [],
      prerequisiteIds: [],
      requiresArena: false
    }
  } else {}
  let prerequisites = pep_c23_unit_prerequisites(parsed.nodes, selected.id)
  if prerequisites.status != "ok" {
    return PepC23BoundedUnit {
      status: "unsupported",
      diagnostic: prerequisites.diagnostic,
      sourceParts: [],
      prerequisiteKinds: [],
      prerequisiteIds: [],
      requiresArena: false
    }
  } else {}
  let emission = emit_c23_function_unit(parsed, checked, index)
  if emission.status != "emitted" {
    return PepC23BoundedUnit {
      status: "unsupported",
      diagnostic: emission.diagnostic,
      sourceParts: [],
      prerequisiteKinds: [],
      prerequisiteIds: [],
      requiresArena: false
    }
  } else {}
  return PepC23BoundedUnit {
    status: "emitted",
    diagnostic: "",
    sourceParts: emission.sourceParts,
    prerequisiteKinds: prerequisites.kinds,
    prerequisiteIds: prerequisites.nodeIds,
    requiresArena: pep_c23_requires_arena(parsed.nodes)
  }
}

fn pep_c23_function_definition(parsed: ParserProgress, node: FlatAstNode, requiresArena: Bool, checked: CheckerReport) -> PepC23Emission {
  var reversed: List[Str] = []
  if node.parentId == -1 && node.kind == "function" {
    let conditionalBody = pep_c23_if_return_body(parsed.nodes, node)
    let hasConditionalBody = conditionalBody.status == "emitted"
    let lowered = if hasConditionalBody { conditionalBody } else { pep_c23_function_expression(parsed.nodes, node, checked) }
    if lowered.status != "emitted" { return lowered } else {}
    let functionParameters = pep_c23_parameters(parsed.nodes, node)
    let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
    var bodyParts: List[Str] = ["  pep_enter();\n"]
    if requiresArena { bodyParts = append(bodyParts, "  (void)pep_arena;\n") } else {}
    for parameterNode in functionParameters {
      bodyParts = append(bodyParts, "  (void)pep_arg_")
      bodyParts = append(bodyParts, int_text(parameterNode.id))
      bodyParts = append(bodyParts, ";\n")
    }
    var localBindings: List[FlatAstNode] = []
    var localBindingsCollected = false
    for statement in parsed.nodes {
      if statement.parentId == node.id && statement.role == "statement" && (statement.kind == "let" || statement.kind == "var") {
        let initialValue = pep_c23_child(parsed.nodes, statement.id, "value", 0)
        if !initialValue.found { return pep_c23_unsupported("Pep C23 local binding has no value") } else {}
        if initialValue.node.kind == "list" && statement.kind == "let" {
          // Immutable list literals are lowered at their direct length/for-in use sites.
        } else {
          if initialValue.node.kind == "list" && statement.kind == "var" {
            let elementKind = pep_c23_mutable_list_element_kind(parsed.nodes, statement)
            if elementKind != "boolean" && elementKind != "integer" && elementKind != "string" && elementKind != "record" {
              return pep_c23_unsupported("Pep C23 mutable collection bindings require a typed Int, Bool, Str, or record list")
            } else {}
            var initial = pep_c23_int_list_argument(parsed.nodes, node, initialValue.node)
            if elementKind == "boolean" {
              initial = pep_c23_bool_list_argument(parsed.nodes, node, initialValue.node)
            } else {}
            if elementKind == "string" {
              initial = pep_c23_str_list_argument(parsed.nodes, node, initialValue.node)
            } else {}
            if elementKind == "record" {
              let annotation = pep_c23_child(parsed.nodes, statement.id, "annotation", 0)
              initial = pep_c23_record_list_argument(parsed.nodes, node, initialValue.node, annotation)
            } else {}
            if initial.status != "emitted" { return initial } else {}
            var cTypeParts: List[Str] = ["pep_list_int"]
            if elementKind == "boolean" { cTypeParts = ["pep_list_bool"] } else {}
            if elementKind == "string" { cTypeParts = ["pep_list_str"] } else {}
            if elementKind == "record" {
              let recordList = pep_c23_mutable_list_record_declaration(parsed.nodes, statement)
              if !recordList.found {
                return pep_c23_unsupported("Pep C23 mutable record list binding requires a declared record element type")
              } else {}
              cTypeParts = ["pep_list_record_", int_text(recordList.node.id)]
            } else {}
            for part in ["  "] { bodyParts = append(bodyParts, part) }
            for part in cTypeParts { bodyParts = append(bodyParts, part) }
            for part in [" pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
            for part in initial.sourceParts { bodyParts = append(bodyParts, part) }
            bodyParts = append(bodyParts, ";\n")
          } else {
            let initial = pep_c23_expression_checked(parsed.nodes, node, initialValue.node, checked)
            // A record or union value type can only be carried by these initialiser shapes, so do
            // not pay two full node-list scans for a scalar literal. This runs for every local
            // binding, and the per-statement step cost is what bounds real compiler bodies.
            let possibleAggregate = initialValue.node.kind == "record" ||
              initialValue.node.kind == "call" || initialValue.node.kind == "field_access" ||
              initialValue.node.kind == "name"
            let localRecord = if possibleAggregate {
              pep_c23_record_value_type(parsed.nodes, node, initialValue.node)
            } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
            let localUnion = if possibleAggregate {
              pep_c23_union_value_type(parsed.nodes, node, initialValue.node)
            } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
            let localString = if initialValue.node.kind == "string" {
              PepC23NodeLookup { found: true, node: initialValue.node }
            } else {
              if initialValue.node.kind == "name" {
                pep_c23_str_parameter(parsed.nodes, node, initialValue.node.text)
              } else {
                if initialValue.node.kind == "field_access" {
                  pep_c23_str_expression(parsed.nodes, node, initialValue.node)
                } else {
                  // Str local from a Str-returning call: without this the ladder fell through
                  // to int64_t and emitted type-wrong C instead of refusing or getting it
                  // right (measured during Campaign F F3).
                  if initialValue.node.kind == "call" {
                    pep_c23_str_typed_call(checked, initialValue.node)
                  } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
                }
              }
            }
            if initialValue.node.kind == "record" && !localRecord.found {
              return pep_c23_unsupported("Pep C23 record local has no declared record type")
            } else {}
            if localString.found {
              for part in ["  ", "pep_str", " pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
            } else {
              if localRecord.found {
                for part in ["  ", "pep_record_", int_text(localRecord.node.id), " pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
              } else {
                if localUnion.found {
                  if !pep_c23_union_supported_layout(parsed.nodes, localUnion.node) {
                    return pep_c23_unsupported("Pep C23 tagged union has an unsupported layout")
                  } else {}
                  for part in ["  ", "pep_union_", int_text(localUnion.node.id), " pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
                } else {
                  for part in ["  ", "int64_t", " pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
                }
              }
            }
            for part in initial.sourceParts { bodyParts = append(bodyParts, part) }
            bodyParts = append(bodyParts, ";\n  (void)pep_local_")
            bodyParts = append(bodyParts, int_text(statement.id))
            bodyParts = append(bodyParts, ";\n")
          }
        }
      } else {
        if statement.parentId == node.id && statement.role == "statement" && statement.kind == "for_in" {
          if !localBindingsCollected {
            for local in parsed.nodes {
              if local.parentId == node.id && local.role == "statement" && local.kind == "var" {
                localBindings = append(localBindings, local)
              } else {}
            }
            localBindingsCollected = true
          } else {}
          let iterable = pep_c23_child(parsed.nodes, statement.id, "iterable", 0)
          let iterableList = if iterable.found { pep_c23_list_literal(parsed.nodes, node, iterable.node) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableRecordLiteral = if iterableList.found {
            pep_c23_record_list_declaration(parsed.nodes, iterableList.node)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableUnionLiteral = if iterableList.found && iterable.found && iterable.node.kind == "name" {
            pep_c23_union_list_local_declaration(parsed.nodes, node, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableLocal = if iterable.found && iterable.node.kind == "name" { pep_c23_mutable_list_binding(parsed.nodes, node, iterable.node.text) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableIntegerParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_int_list_parameter(parsed.nodes, node, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableBooleanParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_bool_list_parameter(parsed.nodes, node, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableRecordParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_record_list_parameter(parsed.nodes, node, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableUnionParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_union_list_parameter(parsed.nodes, node, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
          let iterableParameter = if iterableIntegerParameter.found { iterableIntegerParameter } else {
            if iterableBooleanParameter.found { iterableBooleanParameter } else {
              if iterableRecordParameter.found { iterableRecordParameter } else { iterableUnionParameter }
            }
          }
          if !iterable.found || (!iterableList.found && !iterableParameter.found && !iterableLocal.found) {
            return pep_c23_unsupported("Pep C23 for-in lowering requires a list literal, immutable literal binding, or supported list parameter")
          } else {}
          var elementCount = 0
          if iterableList.found {
            for element in parsed.nodes {
              if element.parentId == iterableList.node.id && element.role == "element" {
                if iterableUnionLiteral.found {
                  let actual = pep_c23_union_value_type(parsed.nodes, node, element)
                  if !actual.found || actual.node.id != iterableUnionLiteral.node.id ||
                     !pep_c23_union_list_element_supported(parsed.nodes, iterableUnionLiteral.node, element) {
                    return pep_c23_unsupported("Pep C23 recursive union list literals require matching constructors with scalar literal payloads")
                  } else {}
                } else {
                  if element.kind != "integer" && element.kind != "boolean" && !pep_c23_is_negative_int_literal(parsed.nodes, element) && (!iterableRecordLiteral.found || element.kind != "record") { return pep_c23_unsupported("Pep C23 for-in list literals currently require integer, Bool, or supported record elements") } else {}
                }
                elementCount = elementCount + 1
              } else {}
            }
          } else {}
          var arrayDeclaration: List[Str] = []
          if iterableParameter.found {
            if iterableRecordParameter.found {
              let recordParameterType = pep_c23_child(parsed.nodes, iterableRecordParameter.node.id, "type", 0)
              let record = if recordParameterType.found { pep_c23_record_list_declaration(parsed.nodes, recordParameterType.node) } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
              if !record.found { return pep_c23_unsupported("Pep C23 record list parameter has no declared record type") } else {}
              for part in ["  if (pep_arg_", int_text(iterableRecordParameter.node.id), ".length != 0 && pep_arg_", int_text(iterableRecordParameter.node.id), ".data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t pep_index_", int_text(statement.id), " = 0; pep_index_", int_text(statement.id), " < pep_arg_", int_text(iterableRecordParameter.node.id), ".length; ++pep_index_", int_text(statement.id), ") {\n    pep_record_", int_text(record.node.id), " pep_local_", int_text(statement.id), " = pep_arg_", int_text(iterableRecordParameter.node.id), ".data[pep_index_", int_text(statement.id), "];\n"] {
                arrayDeclaration = append(arrayDeclaration, part)
              }
            } else {}
            if iterableUnionParameter.found {
              let unionParameterType = pep_c23_child(parsed.nodes, iterableUnionParameter.node.id, "type", 0)
              let unionType = if unionParameterType.found {
                pep_c23_union_list_declaration(parsed.nodes, unionParameterType.node)
              } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
              if !unionType.found || !pep_c23_union_supported_layout(parsed.nodes, unionType.node) {
                return pep_c23_unsupported("Pep C23 recursive union list parameter has an unsupported layout")
              } else {}
              for part in ["  if (pep_arg_", int_text(iterableUnionParameter.node.id), ".length != 0 && pep_arg_", int_text(iterableUnionParameter.node.id), ".data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t pep_index_", int_text(statement.id), " = 0; pep_index_", int_text(statement.id), " < pep_arg_", int_text(iterableUnionParameter.node.id), ".length; ++pep_index_", int_text(statement.id), ") {\n    pep_union_", int_text(unionType.node.id), " pep_local_", int_text(statement.id), " = pep_arg_", int_text(iterableUnionParameter.node.id), ".data[pep_index_", int_text(statement.id), "];\n"] {
                arrayDeclaration = append(arrayDeclaration, part)
              }
            } else {}
            if !iterableRecordParameter.found && !iterableUnionParameter.found {
              for part in ["  if (pep_arg_", int_text(iterableParameter.node.id), ".length != 0 && pep_arg_", int_text(iterableParameter.node.id), ".data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t pep_index_", int_text(statement.id), " = 0; pep_index_", int_text(statement.id), " < pep_arg_", int_text(iterableParameter.node.id), ".length; ++pep_index_", int_text(statement.id), ") {\n    int64_t pep_local_", int_text(statement.id), " = pep_arg_", int_text(iterableParameter.node.id), ".data[pep_index_", int_text(statement.id), "];\n"] {
              arrayDeclaration = append(arrayDeclaration, part)
              }
            } else {}
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
                if iterableUnionLiteral.found {
                  arrayDeclaration = ["  pep_union_", int_text(iterableUnionLiteral.node.id), " pep_iter_", int_text(statement.id), "[] = {"]
                } else {
                  if iterableRecordLiteral.found {
                    arrayDeclaration = ["  pep_record_", int_text(iterableRecordLiteral.node.id), " pep_iter_", int_text(statement.id), "[] = {"]
                  } else {
                    arrayDeclaration = ["  int64_t pep_iter_", int_text(statement.id), "[] = {"]
                  }
                }
                for element in parsed.nodes {
                  if element.parentId == iterableList.node.id && element.role == "element" {
                    if element.kind == "boolean" {
                      arrayDeclaration = append(arrayDeclaration, if element.booleanValue { "1" } else { "0" })
                    } else {
                      let lowered = pep_c23_expression(parsed.nodes, node, element)
                      if lowered.status != "emitted" { return lowered } else {}
                      for part in lowered.sourceParts { arrayDeclaration = append(arrayDeclaration, part) }
                    }
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
                arrayDeclaration = append(arrayDeclaration, ") {\n    ")
                if iterableUnionLiteral.found {
                  arrayDeclaration = append(arrayDeclaration, "pep_union_")
                  arrayDeclaration = append(arrayDeclaration, int_text(iterableUnionLiteral.node.id))
                } else {
                  if iterableRecordLiteral.found {
                    arrayDeclaration = append(arrayDeclaration, "pep_record_")
                    arrayDeclaration = append(arrayDeclaration, int_text(iterableRecordLiteral.node.id))
                  } else { arrayDeclaration = append(arrayDeclaration, "int64_t") }
                }
                arrayDeclaration = append(arrayDeclaration, " pep_local_")
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
              let loweredBody = pep_c23_loop_statement(parsed.nodes, node, loopStatement, 0, localBindings, result)
              if loweredBody.status != "emitted" { return loweredBody } else {}
              for part in loweredBody.sourceParts { bodyParts = append(bodyParts, part) }
            } else {}
          }
          bodyParts = append(bodyParts, "  }\n")
        } else {
          if statement.parentId == node.id && statement.role == "statement" &&
             (statement.kind == "while" || (statement.kind == "if_statement" && !hasConditionalBody)) {
            if !localBindingsCollected {
              for local in parsed.nodes {
                if local.parentId == node.id && local.role == "statement" && local.kind == "var" {
                  localBindings = append(localBindings, local)
                } else {}
              }
              localBindingsCollected = true
            } else {}
            let loweredControl = if statement.kind == "while" {
              pep_c23_while_body(parsed.nodes, node, statement, localBindings, result)
            } else { pep_c23_loop_statement(parsed.nodes, node, statement, 0, localBindings, result) }
            if loweredControl.status != "emitted" { return loweredControl } else {}
            for part in loweredControl.sourceParts { bodyParts = append(bodyParts, part) }
          } else {
            if statement.parentId == node.id && statement.role == "statement" &&
               statement.kind == "expression_statement" {
              let loweredSay = pep_c23_say_statement(parsed.nodes, node, statement)
              if loweredSay.status != "emitted" { return loweredSay } else {}
              for part in loweredSay.sourceParts { bodyParts = append(bodyParts, part) }
            } else {}
          }
        }
      }
    }

    if hasConditionalBody {
      for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
    } else {
      bodyParts = append(bodyParts, "  ")
      for resultPart in pep_c23_c_parameter_type_parts(parsed.nodes, result.node) { bodyParts = append(bodyParts, resultPart) }
      bodyParts = append(bodyParts, " pep_result = ")
      for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
      bodyParts = append(bodyParts, ";\n  pep_leave();\n  return pep_result;\n")
    }
    for resultPart in pep_c23_c_parameter_type_parts(parsed.nodes, result.node) { reversed = prepend(reversed, resultPart) }
    reversed = prepend(reversed, " pep_fn_")
    reversed = prepend(reversed, node.text)
    if length(functionParameters) == 0 {
      if requiresArena { reversed = prepend(reversed, " (pep_arena_t *pep_arena) {\n") } else {
        reversed = prepend(reversed, " (void) {\n")
      }
    } else {
      reversed = prepend(reversed, "(")
      var signatureIndex = 0
      for parameterNode in functionParameters {
        let parameterType = pep_c23_child(parsed.nodes, parameterNode.id, "type", 0)
        if signatureIndex != 0 { reversed = prepend(reversed, ", ") } else {}
        for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, parameterType.node) { reversed = prepend(reversed, typePart) }
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameterNode.id))
        signatureIndex = signatureIndex + 1
      }
      if requiresArena {
        reversed = prepend(reversed, ", ")
        reversed = prepend(reversed, "pep_arena_t *pep_arena")
        reversed = prepend(reversed, ") {\n")
      } else { reversed = prepend(reversed, ") {\n") }
    }
    for part in bodyParts { reversed = prepend(reversed, part) }
    reversed = prepend(reversed, "}\n")
  } else {}
  return PepC23Emission { status: "emitted", sourceParts: reverse(reversed), diagnostic: "" }
}

fn pep_c23_declaration_definitions(parsed: ParserProgress, requiresArena: Bool, wantedId: Int) -> PepC23Emission {
  var reversed: List[Str] = []

  for record in parsed.nodes {
    if record.parentId == -1 && record.kind == "record_declaration" && (wantedId == -1 || record.id == wantedId) {
      var parts: List[Str] = ["typedef struct { "]
      var fieldCount = 0
      for field in parsed.nodes {
        if field.parentId == record.id && field.role == "field" && field.kind == "field_declaration" {
          let fieldType = pep_c23_child(parsed.nodes, field.id, "type", 0)
          let fieldKind = if fieldType.found { pep_c23_c_record_field_type(parsed.nodes, record, fieldType.node) } else { "" }
          if fieldKind == "" { return pep_c23_unsupported("Pep C23 record fields require Int, Bool, or a preceding record declaration") } else {}
          if fieldKind == "record" {
            let nested = pep_c23_record_declaration(parsed.nodes, fieldType.node.text)
            if !nested.found { return pep_c23_unsupported("Pep C23 nested record field has no declaration") } else {}
            parts = append(parts, "pep_record_")
            parts = append(parts, int_text(nested.node.id))
          } else {
            if fieldKind == "list" {
              for fieldPart in pep_c23_c_list_field_type_parts(parsed.nodes, record, fieldType.node) {
                parts = append(parts, fieldPart)
              }
            } else {
              parts = append(parts, fieldKind)
            }
          }
          parts = append(parts, " pep_field_")
          parts = append(parts, int_text(field.childIndex))
          parts = append(parts, "; ")
          fieldCount = fieldCount + 1
        } else {}
      }
      if fieldCount == 0 { return pep_c23_unsupported("Pep C23 does not lower empty records") } else {}
      parts = append(parts, "} pep_record_")
      parts = append(parts, int_text(record.id))
      parts = append(parts, ";\n")
      for part in parts { reversed = prepend(reversed, part) }
      var listParts: List[Str] = ["typedef struct { const pep_record_", int_text(record.id), "*data; size_t length; } pep_list_record_", int_text(record.id), ";\n"]
      for part in listParts { reversed = prepend(reversed, part) }
    } else {}
  }
  for declaration in parsed.nodes {
    if declaration.parentId == -1 && declaration.kind == "union_declaration" && (wantedId == -1 || declaration.id == wantedId) {
      if !pep_c23_union_supported_layout(parsed.nodes, declaration) {
        return pep_c23_unsupported("Pep C23 tagged union has an unsupported layout")
      } else {}
      let recursiveUnion = pep_c23_union_is_recursive(parsed.nodes, declaration)
      if pep_c23_union_has_recursive_list_payload(parsed.nodes, declaration) {
        var listParts: List[Str] = ["typedef struct { const struct pep_union_",
          int_text(declaration.id), " *data; size_t length; } pep_list_union_",
          int_text(declaration.id), ";\n"]
        for part in listParts { reversed = prepend(reversed, part) }
      } else {}
      var parts: List[Str] = []
      if recursiveUnion {
        parts = ["typedef struct pep_union_", int_text(declaration.id), " { uint32_t tag; union { "]
      } else {
        parts = ["typedef struct { uint32_t tag; union { "]
      }
      var payloadCount = 0
      for variant in parsed.nodes {
        if variant.parentId == declaration.id && variant.role == "variant" &&
           variant.kind == "variant_declaration" {
          let payload = pep_c23_child(parsed.nodes, variant.id, "field_type", 0)
          if payload.found {
            if payloadCount != 0 { parts = append(parts, " ") } else {}
            parts = append(parts, "struct { ")
            for payloadField in parsed.nodes {
              if payloadField.parentId == variant.id && payloadField.role == "field_type" {
                if payloadField.kind == "type_named" && payloadField.text == declaration.text {
                  parts = append(parts, "struct pep_union_")
                  parts = append(parts, int_text(declaration.id))
                  parts = append(parts, " *")
                } else {
                  for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, payloadField) {
                    parts = append(parts, typePart)
                  }
                }
                parts = append(parts, " field_")
                parts = append(parts, int_text(payloadField.childIndex))
                parts = append(parts, "; ")
              } else {}
            }
            parts = append(parts, "} payload_")
            parts = append(parts, int_text(variant.childIndex))
            parts = append(parts, ";")
            payloadCount = payloadCount + 1
          } else {}
        } else {}
      }
      parts = append(parts, " } payload; } pep_union_")
      parts = append(parts, int_text(declaration.id))
      parts = append(parts, ";\n")
      for part in parts { reversed = prepend(reversed, part) }
    } else {}
  }
  if requiresArena {
    for declaration in parsed.nodes {
      if declaration.parentId == -1 && declaration.kind == "union_declaration" &&
         (wantedId == -1 || declaration.id == wantedId) &&
         pep_c23_union_is_recursive(parsed.nodes, declaration) {
        for part in pep_c23_recursive_union_guard_source(declaration) { reversed = prepend(reversed, part) }
        for variant in parsed.nodes {
          if variant.parentId == declaration.id && variant.role == "variant" &&
             variant.kind == "variant_declaration" &&
             pep_c23_union_has_recursive_payload(parsed.nodes, declaration, variant) {
            for part in pep_c23_union_constructor_helper_source(parsed.nodes, declaration, variant) {
              reversed = prepend(reversed, part)
            }
          } else {}
        }
      } else {}
    }
  } else {}
  // Record list updates live with the other arena helpers, after every pep_list_record_N typedef.
  if requiresArena {
    for declaration in parsed.nodes {
      if declaration.parentId == -1 && declaration.kind == "record_declaration" && (wantedId == -1 || declaration.id == wantedId) {
        for part in pep_c23_record_list_update_source(declaration) { reversed = prepend(reversed, part) }
      } else {}
    }
  } else {}
  return PepC23Emission { status: "emitted", sourceParts: reverse(reversed), diagnostic: "" }
}

// One top-level record or union declaration, without the header, the prototypes or any other
// declaration. Its text is the same bytes the header contributes for that declaration, so a caller
// can assemble a translation unit from units plus the declarations it actually needs.
fn emit_c23_declaration_unit(parsed: ParserProgress, checked: CheckerReport, nodeId: Int) -> PepC23Emission {
  let authority = semantic_snapshot()
  if parsed.document != authority.document || parsed.revision != authority.revision ||
     checked.document != authority.document || checked.revision != authority.revision ||
     checked.syntaxNodeCount != length(parsed.nodes) {
    return pep_c23_unsupported("Pep C23 emission inputs do not match the authorised source revision")
  } else {}
  if parsed.status != "complete" || checked.status != "valid" {
    return pep_c23_unsupported("Pep C23 emission requires a valid Pep checker report")
  } else {}
  let declaration = pep_c23_declaration_by_id(parsed.nodes, nodeId)
  if !declaration.found || declaration.node.parentId != -1 {
    return pep_c23_unsupported("Pep C23 declaration unit requires a top-level declaration id")
  } else {}
  if declaration.node.kind != "record_declaration" && declaration.node.kind != "union_declaration" {
    return pep_c23_unsupported("Pep C23 declaration unit requires a record or union declaration")
  } else {}
  return pep_c23_declaration_definitions(parsed, pep_c23_requires_arena(parsed.nodes), nodeId)
}


fn emit_c23() -> PepC23Emission {
  let parsed = parser_parse_program()
  if parsed.status != "complete" {
    return pep_c23_unsupported("Pep C23 emission requires a complete program")
  } else {}
  let checked = analyze_parsed(parsed)
  return emit_c23_checked(parsed, checked)
}
// Section slicing helpers for the additive sectional entry point. Pep lists are values, so the
// accumulator can be snapshotted at a boundary for free and the sections recovered by length.
fn pep_c23_take_prefix(parts: List[Str], count: Int) -> List[Str] {
  var taken: List[Str] = []
  var index = 0
  for part in parts {
    if !(count <= index) { taken = append(taken, part) } else {}
    index = index + 1
  }
  return taken
}
fn pep_c23_drop_prefix(parts: List[Str], count: Int) -> List[Str] {
  var rest: List[Str] = []
  var index = 0
  for part in parts {
    if count <= index { rest = append(rest, part) } else {}
    index = index + 1
  }
  return rest
}
fn pep_c23_list_int_at(values: List[Int], wanted: Int) -> Int {
  var index = 0
  for value in values {
    if index == wanted { return value } else {}
    index = index + 1
  }
  return -1
}
fn emit_c23_checked(parsed: ParserProgress, checked: CheckerReport) -> PepC23Emission {
  return emit_c23_checked_part(parsed, checked, "all", -1)
}
// Additive sectional emission (LUCY-20261101-006 item 2). The one-shot output is ordered by
// construction: header, one definition per top-level function in source order, then the epilogue.
// Recording the accumulator length at the two boundaries lets each section be returned without
// duplicating the emission code, and concatenating the three is the one-shot output byte for byte.
fn emit_c23_section(parsed: ParserProgress, checked: CheckerReport, part: Str) -> PepC23Emission {
  return emit_c23_checked_part(parsed, checked, part, -1)
}
// One top-level function definition, in source order, for the bounded-emitter path.
fn emit_c23_function_unit(parsed: ParserProgress, checked: CheckerReport, index: Int) -> PepC23Emission {
  return emit_c23_checked_part(parsed, checked, "function-unit", index)
}
fn emit_c23_checked_part(parsed: ParserProgress, checked: CheckerReport, part: Str, index: Int) -> PepC23Emission {
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
  var topLevelFunctions: List[FlatAstNode] = []
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      functionCount = functionCount + 1
      topLevelFunctions = append(topLevelFunctions, node)
      if node.text == "main" { mainFound = true; mainId = node.id } else {}
    } else {}
  }
  // A bounded chunk may legitimately contain one function and no `main`: the caller lives in a
  // different chunk. Only the whole-program and epilogue paths need main, so they are the only
  // ones that require it. The requirement is unchanged for part == "all".
  let sectionNeedsMain = part == "all" || part == "main"
  // A declaration-only chunk has zero functions but real nodes, and it must still produce a
  // `header` for the bounded header+units+epilogue assembly. A completely empty document keeps
  // the original refusal (registration vectors pin it), as do whole/epilogue parts without main;
  // function-scoped parts over a declaration chunk fail-closed on their own (unit index out of
  // range).
  if (functionCount == 0 && length(parsed.nodes) == 0) || (sectionNeedsMain && !mainFound) {
    return pep_c23_unsupported("Pep C23 emission requires a top-level function named main")
  } else {}
  if mainFound {
    let mainType = pep_c23_child(parsed.nodes, mainId, "return_type", 0)
    if !mainType.found || mainType.node.kind != "type_scalar" || mainType.node.text != "Int" {
      return pep_c23_unsupported("Pep C23 main function must return Int")
    } else {}
  } else {}
  let requiresArena = pep_c23_requires_arena(parsed.nodes)
  if part == "function-unit" {
    let selected = pep_c23_function_at(topLevelFunctions, index)
    if !selected.found {
      return pep_c23_unsupported("Pep C23 function unit index is out of range")
    } else {}
    if selected.node.text == "main" {
      let mainReturn = pep_c23_child(parsed.nodes, selected.node.id, "return_type", 0)
      if !mainReturn.found || mainReturn.node.kind != "type_scalar" || mainReturn.node.text != "Int" {
        return pep_c23_unsupported("Pep C23 main function must return Int")
      } else {}
    } else {}
    return pep_c23_function_definition(parsed, selected.node, requiresArena, checked)
  } else {}
  var reversed: List[Str] = []
  reversed = prepend(reversed, "#include <stddef.h>\n")
  reversed = prepend(reversed, "#include <stdio.h>\n")
  reversed = prepend(reversed, "#include <stdint.h>\n")
  reversed = prepend(reversed, "#include <stdlib.h>\n")
  if requiresArena { reversed = prepend(reversed, "#include \"pep_arena.h\"\n") } else {}
  reversed = prepend(reversed, "typedef struct { const unsigned char *data; size_t length; } pep_source_bytes;\n[[maybe_unused]] static int64_t pep_byte_at(pep_source_bytes source, int64_t offset) {\n  if (source.length != 0 && source.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_SOURCE_BYTES\\n\", stderr); exit(1); }\n  if (offset < 0 || (uintmax_t)offset >= (uintmax_t)source.length) { fputs(\"PEP_RUNTIME_BYTE_RANGE\\n\", stderr); exit(1); }\n  return (int64_t)source.data[(size_t)offset];\n}\n")
  reversed = prepend(reversed, "[[maybe_unused]] static int64_t pep_byte_length(pep_source_bytes source) {\n  if (source.length != 0 && source.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_SOURCE_BYTES\\n\", stderr); exit(1); }\n  if ((uintmax_t)source.length > (uintmax_t)INT64_MAX) { fputs(\"PEP_RUNTIME_LENGTH_RANGE\\n\", stderr); exit(1); }\n  return (int64_t)source.length;\n}\n")
  reversed = prepend(reversed, "typedef struct { const unsigned char *data; size_t length; } pep_str;\n[[maybe_unused]] static _Bool pep_str_equal(pep_str left, pep_str right) {\n  if ((left.length != 0 && left.data == NULL) || (right.length != 0 && right.data == NULL)) { fputs(\"PEP_RUNTIME_INVALID_STR\\n\", stderr); exit(1); }\n  if (left.length != right.length) { return 0; }\n  for (size_t i = 0; i < left.length; ++i) { if (left.data[i] != right.data[i]) { return 0; } }\n  return 1;\n}\n[[maybe_unused]] static _Bool pep_str_contains(pep_str haystack, pep_str needle) {\n  if ((haystack.length != 0 && haystack.data == NULL) || (needle.length != 0 && needle.data == NULL)) { fputs(\"PEP_RUNTIME_INVALID_STR\\n\", stderr); exit(1); }\n  if (needle.length == 0) { return 1; }\n  if (needle.length > haystack.length) { return 0; }\n  size_t limit = haystack.length - needle.length;\n  for (size_t i = 0; i <= limit; ++i) {\n    size_t j = 0;\n    while (j < needle.length && haystack.data[i + j] == needle.data[j]) { ++j; }\n    if (j == needle.length) { return 1; }\n  }\n  return 0;\n}\n")
  // str_concat (Campaign G G-A2-7): a fresh region from a per-run bump pool, so EVERY
  // result stays valid for the whole run -- chains, siblings and let-bound aliases are all
  // sound by construction (no buffer reuse), which is what the staged checker's nested
  // message composition needs. The explicit divergence from the unbounded seed builtin:
  // capacity PEP_STR_CONCAT_CAPACITY, and overflow fails closed at RUNTIME with
  // PEP_RUNTIME_STR_CONCAT_RANGE (pinned by the probe's capacity negative). 4 KiB is a
  // deliberate, single-constant choice for compiler-A v1: diagnostic messages are tens to
  // hundreds of bytes, and a larger budget only delays the same fail-closed abort. Raising
  // it later is a one-line change PLUS its capacity negative -- never a silent bump.
  reversed = prepend(reversed, "#define PEP_STR_CONCAT_CAPACITY 4096\n[[maybe_unused]] static pep_str pep_str_concat(pep_str left, pep_str right) {\n  if ((left.length != 0 && left.data == NULL) || (right.length != 0 && right.data == NULL)) { fputs(\"PEP_RUNTIME_INVALID_STR\\n\", stderr); exit(1); }\n  if (left.length > PEP_STR_CONCAT_CAPACITY || right.length > PEP_STR_CONCAT_CAPACITY - left.length) { fputs(\"PEP_RUNTIME_STR_CONCAT_RANGE\\n\", stderr); exit(1); }\n  static unsigned char pep_concat_pool[PEP_STR_CONCAT_CAPACITY];\n  static size_t pep_concat_used = 0;\n  unsigned char *out = pep_concat_pool + pep_concat_used;\n  for (size_t i = 0; i < left.length; ++i) { out[i] = left.data[i]; }\n  for (size_t i = 0; i < right.length; ++i) { out[left.length + i] = right.data[i]; }\n  pep_concat_used += left.length + right.length;\n  return (pep_str){ .data = out, .length = left.length + right.length };\n}\n")
  reversed = prepend(reversed, "typedef struct { const int64_t *data; size_t length; } pep_list_int;\n_Bool pep_contains_int(pep_list_int values, int64_t needle) {\n  if (values.length != 0 && values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t i = 0; i < values.length; ++i) { if (values.data[i] == needle) { return 1; } }\n  return 0;\n}\n")
  reversed = prepend(reversed, "typedef struct { const _Bool *data; size_t length; } pep_list_bool;\n_Bool pep_contains_bool(pep_list_bool values, _Bool needle) {\n  if (values.length != 0 && values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t i = 0; i < values.length; ++i) { if (values.data[i] == needle) { return 1; } }\n  return 0;\n}\n")
  reversed = prepend(reversed, "typedef struct { const pep_str *data; size_t length; } pep_list_str;\n")
  // The print helper is placed unconditionally: detecting `say` with a node scan costs more
  // than the one-shot emit_c23 budget leaves on a near-ceiling fixture (the depth-510 recursion
  // regression tipped by ~hundreds of ticks with any conditional form; measured 2026-11-04).
  // [[maybe_unused]] keeps -Wunused clean when nothing calls it, and programs without say produce
  // byte-identical RUNTIME output -- only this fixed helper block is added to their generated C.
  reversed = prepend(reversed, "[[maybe_unused]] static void pep_say(const unsigned char *value, unsigned long long length) {\n  if (length != 0 && value == NULL) { fputs(\"PEP_RUNTIME_INVALID_STR\\n\", stderr); exit(1); }\n  for (unsigned long long pep_i = 0; pep_i < length; ++pep_i) { fputc((int)value[pep_i], stdout); }\n  fputc(10, stdout);\n}\n")
  if requiresArena {
    reversed = prepend(reversed, "[[maybe_unused]] static pep_list_int pep_list_int_prepend(pep_arena_t *pep_a, pep_list_int pep_values, int64_t pep_value) {\n  if (pep_values.length != 0 && pep_values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_values.length == SIZE_MAX || pep_values.length + 1 > SIZE_MAX / sizeof(int64_t)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  size_t pep_count = pep_values.length + 1;\n  int64_t *pep_out = (int64_t *)pep_arena_alloc(pep_a, pep_count * sizeof(int64_t), _Alignof(int64_t));\n  if (pep_out == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  pep_out[0] = pep_value;\n  for (size_t pep_i = 0; pep_i < pep_values.length; ++pep_i) { pep_out[pep_i + 1] = pep_values.data[pep_i]; }\n  return (pep_list_int){ .data = pep_out, .length = pep_count };\n}\n[[maybe_unused]] static pep_list_int pep_list_int_reverse(pep_arena_t *pep_a, pep_list_int pep_values) {\n  if (pep_values.length != 0 && pep_values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_values.length == 0) { return (pep_list_int){ .data = NULL, .length = 0 }; }\n  if (pep_values.length > SIZE_MAX / sizeof(int64_t)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  int64_t *pep_out = (int64_t *)pep_arena_alloc(pep_a, pep_values.length * sizeof(int64_t), _Alignof(int64_t));\n  if (pep_out == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  for (size_t pep_i = 0; pep_i < pep_values.length; ++pep_i) { pep_out[pep_i] = pep_values.data[pep_values.length - 1 - pep_i]; }\n  return (pep_list_int){ .data = pep_out, .length = pep_values.length };\n}\n")
    reversed = prepend(reversed, "[[maybe_unused]] static pep_list_bool pep_list_bool_prepend(pep_arena_t *pep_a, pep_list_bool pep_values, _Bool pep_value) {\n  if (pep_values.length != 0 && pep_values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_values.length == SIZE_MAX || pep_values.length + 1 > SIZE_MAX / sizeof(_Bool)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  size_t pep_count = pep_values.length + 1;\n  _Bool *pep_out = (_Bool *)pep_arena_alloc(pep_a, pep_count * sizeof(_Bool), _Alignof(_Bool));\n  if (pep_out == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  pep_out[0] = pep_value;\n  for (size_t pep_i = 0; pep_i < pep_values.length; ++pep_i) { pep_out[pep_i + 1] = pep_values.data[pep_i]; }\n  return (pep_list_bool){ .data = pep_out, .length = pep_count };\n}\n[[maybe_unused]] static pep_list_bool pep_list_bool_reverse(pep_arena_t *pep_a, pep_list_bool pep_values) {\n  if (pep_values.length != 0 && pep_values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_values.length == 0) { return (pep_list_bool){ .data = NULL, .length = 0 }; }\n  if (pep_values.length > SIZE_MAX / sizeof(_Bool)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  _Bool *pep_out = (_Bool *)pep_arena_alloc(pep_a, pep_values.length * sizeof(_Bool), _Alignof(_Bool));\n  if (pep_out == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  for (size_t pep_i = 0; pep_i < pep_values.length; ++pep_i) { pep_out[pep_i] = pep_values.data[pep_values.length - 1 - pep_i]; }\n  return (pep_list_bool){ .data = pep_out, .length = pep_values.length };\n}\n")
    reversed = prepend(reversed, "[[maybe_unused]] static pep_list_str pep_list_str_prepend(pep_arena_t *pep_a, pep_list_str pep_values, pep_str pep_value) {\n  if (pep_values.length != 0 && pep_values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_values.length == SIZE_MAX || pep_values.length + 1 > SIZE_MAX / sizeof(pep_str)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  size_t pep_count = pep_values.length + 1;\n  pep_str *pep_out = (pep_str *)pep_arena_alloc(pep_a, pep_count * sizeof(pep_str), _Alignof(pep_str));\n  if (pep_out == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  pep_out[0] = pep_value;\n  for (size_t pep_i = 0; pep_i < pep_values.length; ++pep_i) { pep_out[pep_i + 1] = pep_values.data[pep_i]; }\n  return (pep_list_str){ .data = pep_out, .length = pep_count };\n}\n[[maybe_unused]] static pep_list_str pep_list_str_reverse(pep_arena_t *pep_a, pep_list_str pep_values) {\n  if (pep_values.length != 0 && pep_values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  if (pep_values.length == 0) { return (pep_list_str){ .data = NULL, .length = 0 }; }\n  if (pep_values.length > SIZE_MAX / sizeof(pep_str)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  pep_str *pep_out = (pep_str *)pep_arena_alloc(pep_a, pep_values.length * sizeof(pep_str), _Alignof(pep_str));\n  if (pep_out == NULL) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); exit(1); }\n  for (size_t pep_i = 0; pep_i < pep_values.length; ++pep_i) { pep_out[pep_i] = pep_values.data[pep_values.length - 1 - pep_i]; }\n  return (pep_list_str){ .data = pep_out, .length = pep_values.length };\n}\n")
  } else {}
  reversed = prepend(reversed, "int64_t pep_add(int64_t a, int64_t b) {\n  if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a + b;\n}\nint64_t pep_sub(int64_t a, int64_t b) {\n  if ((b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a - b;\n}\nint64_t pep_mul(int64_t a, int64_t b) {\n  if (a > 0) { if ((b > 0 && a > INT64_MAX / b) || (b < 0 && b < INT64_MIN / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  else if (a < 0) { if ((b > 0 && a < INT64_MIN / b) || (b < 0 && b < INT64_MAX / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  return a * b;\n}\nint64_t pep_div(int64_t a, int64_t b) {\n  if (b == 0) { fputs(\"PEP_RUNTIME_DIVISION_BY_ZERO\\n\", stderr); exit(1); }\n  if (a == INT64_MIN && b == -1) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a / b;\n}\nint64_t pep_neg(int64_t a) {\n  if (a == INT64_MIN) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return -a;\n}\n[[maybe_unused]] static int64_t pep_checked_length(size_t length) { if ((uintmax_t)length > (uintmax_t)INT64_MAX) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } return (int64_t)length; }\nstatic int pep_call_depth = 0;\nstatic void pep_enter(void) { if (pep_call_depth >= 512) { fputs(\"PEP_RUNTIME_CALL_DEPTH\\n\", stderr); exit(1); } pep_call_depth += 1; }\nstatic void pep_leave(void) { pep_call_depth -= 1; }\n[[maybe_unused]] static int64_t pep_invalid_union_tag(void) { fputs(\"PEP_RUNTIME_INVALID_UNION\\n\", stderr); exit(1); }\n")
  let declarations = pep_c23_declaration_definitions(parsed, requiresArena, -1)
  if declarations.status != "emitted" { return declarations } else {}
  for part in declarations.sourceParts { reversed = prepend(reversed, part) }
  // Everything accumulated so far = runtime preamble + declaration definitions. The
  // `prototypes` part (Campaign G G-A2-4) returns ONLY the prototype block built below, so a
  // chunked assembly can place prototypes before ANY unit order. COST DISCIPLINE (measured:
  // a second length() walk of this large list tipped a near-ceiling fixture over the fixed
  // 100k budget): the walk happens exactly ONCE here, before the loop; sectionHeaderCount is
  // then arithmetic over a loop counter instead of a second walk (net ~+8 steps over the
  // pre-G-A2-4 baseline instead of a full extra traversal).
  // SYNC NOTE (Campaign G G-A2-4): the prototype-building loop below appears AGAIN inside
  // the `prototypes` part branch. The duplication is deliberate -- slicing the merged
  // `reversed` list needs the preamble+decls count, and the second length() walk measured
  // OVER the fixed 100k budget on a near-ceiling fixture. Keeping this common path byte-for-byte
  // at its pre-G-A2-4 cost is what the tip fixture requires; tests/test_c23_bounded_emission
  // pins `prototypes == header's tail`, so the two copies cannot drift without failing green.
  // Entry-parameter SourceBytes grant (A1 docs/NATIVE_SOURCE_GRANT_CONTRACT_DRAFT.md
  // @a802290, mode "entry-parameter"): `grantEntry` records whether the ENTRY declares
  // exactly one SourceBytes parameter. It is computed HERE, inside the prototype loop
  // that already walks topLevelFunctions and already calls pep_c23_parameters, because a
  // second traversal of that list measured OVER the fixed 100k budget on the near-ceiling
  // recursive-depth fixture (PEP_RUNTIME_STEP_LIMIT at 4455:8). Cost added: one string
  // compare per top-level function; the parameter lookups run for `main` only.
  var grantEntry = false
  for node in topLevelFunctions {
    if node.parentId == -1 && node.kind == "function" {
      let functionParameters = pep_c23_parameters(parsed.nodes, node)
      let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
      if node.text == "main" && length(functionParameters) == 1 {
        let grantParameter = pep_c23_child(parsed.nodes, node.id, "parameter", 0)
        let grantParameterType = if grantParameter.found {
          pep_c23_child(parsed.nodes, grantParameter.node.id, "type", 0)
        } else { PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() } }
        grantEntry = grantParameterType.found &&
          pep_c23_c_parameter_type(parsed.nodes, grantParameterType.node) == "pep_source_bytes"
      } else {}
      for resultPart in pep_c23_c_parameter_type_parts(parsed.nodes, result.node) { reversed = prepend(reversed, resultPart) }
      reversed = prepend(reversed, " pep_fn_")
      reversed = prepend(reversed, node.text)
      if length(functionParameters) == 0 {
        if requiresArena { reversed = prepend(reversed, "(pep_arena_t *pep_arena);\n") } else {
          reversed = prepend(reversed, "(void);\n")
        }
      } else {
        reversed = prepend(reversed, "(")
        var prototypeIndex = 0
        for parameterNode in functionParameters {
          let parameterType = pep_c23_child(parsed.nodes, parameterNode.id, "type", 0)
          if prototypeIndex != 0 { reversed = prepend(reversed, ", ") } else {}
          for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, parameterType.node) { reversed = prepend(reversed, typePart) }
          reversed = prepend(reversed, " pep_arg_")
          reversed = prepend(reversed, int_text(parameterNode.id))
          prototypeIndex = prototypeIndex + 1
        }
        if requiresArena {
          reversed = prepend(reversed, ", ")
          reversed = prepend(reversed, "pep_arena_t *pep_arena")
          reversed = prepend(reversed, ");\n")
        } else { reversed = prepend(reversed, ");\n") }
      }
    } else {}
  }
  let sectionHeaderCount = length(reversed)
  // `header` is everything up to here and nothing after it, so it can return before the body loop
  // runs. Assembling every body only to slice it off is what made a header request cost the whole
  // program.
  if part == "header" {
    return PepC23Emission { status: "emitted", sourceParts: reverse(reversed), diagnostic: "" }
  } else {}
  // Prototypes of THIS chunk's functions only: no preamble, no declarations, no bodies, no
  // epilogue (returned before any of that is built, so the step cost is the prototype loop
  // alone). Authentication is the checked chunk itself -- the same document/revision-gated
  // report that authorises the unit -- so no new facts or interface are needed. Placed after
  // the declaration header in an assembly, it makes unit ORDER irrelevant for C, which needs
  // a declaration before use.
  if part == "prototypes" {
    // SYNC PAIR of the prototype loop above (see the sync note) -- all cost of this part is
    // paid here, so every other section keeps its exact pre-G-A2-4 step profile.
    var prototypeParts: List[Str] = []
    for node in topLevelFunctions {
      if node.parentId == -1 && node.kind == "function" {
        let functionParameters = pep_c23_parameters(parsed.nodes, node)
        let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
        for resultPart in pep_c23_c_parameter_type_parts(parsed.nodes, result.node) { prototypeParts = prepend(prototypeParts, resultPart) }
        prototypeParts = prepend(prototypeParts, " pep_fn_")
        prototypeParts = prepend(prototypeParts, node.text)
        if length(functionParameters) == 0 {
          if requiresArena { prototypeParts = prepend(prototypeParts, "(pep_arena_t *pep_arena);\n") } else {
            prototypeParts = prepend(prototypeParts, "(void);\n")
          }
        } else {
          prototypeParts = prepend(prototypeParts, "(")
          var prototypeIndex = 0
          for parameterNode in functionParameters {
            let parameterType = pep_c23_child(parsed.nodes, parameterNode.id, "type", 0)
            if prototypeIndex != 0 { prototypeParts = prepend(prototypeParts, ", ") } else {}
            for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, parameterType.node) { prototypeParts = prepend(prototypeParts, typePart) }
            prototypeParts = prepend(prototypeParts, " pep_arg_")
            prototypeParts = prepend(prototypeParts, int_text(parameterNode.id))
            prototypeIndex = prototypeIndex + 1
          }
          if requiresArena {
            prototypeParts = prepend(prototypeParts, ", ")
            prototypeParts = prepend(prototypeParts, "pep_arena_t *pep_arena")
            prototypeParts = prepend(prototypeParts, ");\n")
          } else { prototypeParts = prepend(prototypeParts, ");\n") }
        }
      } else {}
    }
    // Built backward by prepending (same as the common loop); one reverse yields forward
    // prototype order -- the bounded-suite header-tail pin keeps this byte-identical to it.
    return PepC23Emission { status: "emitted",
      sourceParts: reverse(prototypeParts), diagnostic: "" }
  } else {}
  // `main` is the epilogue alone; the bodies are not part of it.
  var functionsToEmit: List[FlatAstNode] = topLevelFunctions
  if part == "main" { functionsToEmit = [] } else {}
  var sectionFunctionEnds: List[Int] = []
  for node in functionsToEmit {
    let definition = pep_c23_function_definition(parsed, node, requiresArena, checked)
    if definition.status != "emitted" { return definition } else {}
    for part in definition.sourceParts { reversed = prepend(reversed, part) }
    sectionFunctionEnds = append(sectionFunctionEnds, length(reversed))
  }
  let sectionBodyCount = length(reversed)
  if requiresArena {
    reversed = prepend(reversed, "int main(void) {\n")
    reversed = prepend(reversed, "  pep_arena_t *pep_arena = NULL;\n")
    reversed = prepend(reversed, "  if (pep_arena_init(&pep_arena, 0) != PEP_ARENA_OK) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); return 1; }\n")
    reversed = prepend(reversed, "  int64_t pep_main_result = pep_fn_")
    reversed = prepend(reversed, "main")
    reversed = prepend(reversed, "(pep_arena);\n")
    reversed = prepend(reversed, "  if (pep_arena_status(pep_arena) != PEP_ARENA_OK) { pep_arena_free(&pep_arena); fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); return 1; }\n")
    reversed = prepend(reversed, "  (void)printf(\"%lld\\n\", (long long)pep_main_result);\n")
    reversed = prepend(reversed, "  pep_arena_free(&pep_arena);\n")
    reversed = prepend(reversed, "  return 0;\n")
    reversed = prepend(reversed, "}\n")
  } else {
    // Entry-parameter SourceBytes grant (A1 contract @a802290): when the entry declares
    // exactly one SourceBytes parameter, the host wrapper supplies the opened target's
    // own bytes here -- `argv[1]`, read once. Without argv[1] there is no grant and the
    // program fails closed before the entry runs, so bytes can never be conjured. The
    // Pep source never obtains authority; the host hands it to the entry. Every other
    // entry shape takes the unchanged zero-argument wrapper below.
    // BOUNDARY: this is the non-arena wrapper. A granted entry that also needs the arena
    // is not a shape the lexer requires and is not handled here.
    // COST DISCIPLINE: grantEntry is computed inside the prototype loop above, not by a
    // second traversal here. A second walk of topLevelFunctions measured OVER the fixed
    // 100k budget on the near-ceiling recursive-depth fixture
    // (test_recursive_native_calls_enforce_pep_depth, PEP_RUNTIME_STEP_LIMIT at 4455:8).
    if grantEntry {
      // The wrapper opens the granted file itself. Windows/MSVC CRT marks fopen/ftell
      // deprecated and clang reports that under the bundle's -Werror as a *call-site*
      // diagnostic, so the two call sites carry a local pragma rather than a file-wide
      // opt-out: nothing else in the bundle is affected, and a non-MSVC-compatible
      // compiler never evaluates the guarded PP block.
      reversed = prepend(reversed, "int main(int argc, char **argv) {\n")
      reversed = prepend(reversed, "  if (argc < 2) { fputs(\"PEP_RUNTIME_SOURCE_CONTEXT\\n\", stderr); return 1; }\n")
      reversed = prepend(reversed, "#if defined(_MSC_VER)\n#pragma warning(push)\n#pragma warning(disable: 4996)\n#endif\n")
      reversed = prepend(reversed, "  FILE *pep_source_file = fopen(argv[1], \"rb\");\n")
      reversed = prepend(reversed, "  if (pep_source_file == NULL) { fputs(\"PEP_RUNTIME_SOURCE_OPEN\\n\", stderr); return 1; }\n")
      reversed = prepend(reversed, "  if (fseek(pep_source_file, 0, SEEK_END) != 0) { fputs(\"PEP_RUNTIME_SOURCE_OPEN\\n\", stderr); return 1; }\n")
      reversed = prepend(reversed, "  long pep_source_length = ftell(pep_source_file);\n")
      reversed = prepend(reversed, "  if (pep_source_length < 0) { fputs(\"PEP_RUNTIME_SOURCE_OPEN\\n\", stderr); return 1; }\n")
      reversed = prepend(reversed, "  if (fseek(pep_source_file, 0, SEEK_SET) != 0) { fputs(\"PEP_RUNTIME_SOURCE_OPEN\\n\", stderr); return 1; }\n")
      reversed = prepend(reversed, "  unsigned char *pep_source_data = (unsigned char *)malloc((size_t)pep_source_length + 1u);\n")
      reversed = prepend(reversed, "  if (pep_source_data == NULL) { fputs(\"PEP_RUNTIME_SOURCE_OPEN\\n\", stderr); return 1; }\n")
      reversed = prepend(reversed, "  if (pep_source_length > 0 && fread(pep_source_data, 1, (size_t)pep_source_length, pep_source_file) != (size_t)pep_source_length) { fputs(\"PEP_RUNTIME_SOURCE_OPEN\\n\", stderr); return 1; }\n")
      reversed = prepend(reversed, "  (void)fclose(pep_source_file);\n")
      reversed = prepend(reversed, "#if defined(_MSC_VER)\n#pragma warning(pop)\n#endif\n")
      reversed = prepend(reversed, "  (void)printf(\"%lld\\n\", (long long)(pep_fn_")
      reversed = prepend(reversed, "main")
      reversed = prepend(reversed, "((pep_source_bytes){ .data = pep_source_data, .length = (size_t)pep_source_length })));\n")
      reversed = prepend(reversed, "  free(pep_source_data);\n")
      reversed = prepend(reversed, "  return 0;\n")
      reversed = prepend(reversed, "}\n")
    } else {
      reversed = prepend(reversed, "int main(void) {\n")
      reversed = prepend(reversed, "  (void)printf(\"%lld\\n\", (long long)(pep_fn_")
      reversed = prepend(reversed, "main")
      reversed = prepend(reversed, "()));\n")
      reversed = prepend(reversed, "  return 0;\n")
      reversed = prepend(reversed, "}\n")
    }
  }
  // The epilogue parts are the ones prepended after the last body, i.e. the front of `reversed`.
  if part == "main" {
    let epilogueCount = length(reversed) - sectionBodyCount
    return PepC23Emission {
      status: "emitted",
      sourceParts: reverse(pep_c23_take_prefix(reversed, epilogueCount)),
      diagnostic: ""
    }
  } else {}
  let allParts = reverse(reversed)
  var selected: List[Str] = allParts
  if part == "header" {
    selected = pep_c23_take_prefix(allParts, sectionHeaderCount)
  } else {}
  if part == "function" {
    selected = pep_c23_drop_prefix(pep_c23_take_prefix(allParts, sectionBodyCount), sectionHeaderCount)
  } else {}
  if part == "main" {
    selected = pep_c23_drop_prefix(allParts, sectionBodyCount)
  } else {}
  if part == "function-unit" {
    let unitEnd = pep_c23_list_int_at(sectionFunctionEnds, index)
    let unitStart = if index == 0 {
      sectionHeaderCount
    } else { pep_c23_list_int_at(sectionFunctionEnds, index - 1) }
    if unitEnd == -1 || unitStart == -1 {
      return pep_c23_unsupported("Pep C23 function unit index is out of range")
    } else {}
    selected = pep_c23_drop_prefix(pep_c23_take_prefix(allParts, unitEnd), unitStart)
  } else {}
  return PepC23Emission { status: "emitted", sourceParts: selected, diagnostic: "" }
}
