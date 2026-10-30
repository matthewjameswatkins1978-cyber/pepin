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
fn pep_c23_is_negative_int_literal(nodes: List[FlatAstNode], value: FlatAstNode) -> Bool {
  if value.kind != "binary" || value.text != "neg" { return false } else {}
  let zero = pep_c23_child(nodes, value.id, "left", 0)
  let operand = pep_c23_child(nodes, value.id, "right", 1)
  return zero.found && zero.node.kind == "integer" && zero.node.integerValue == 0 && operand.found && operand.node.kind == "integer"
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
  let elementCount = count_children(nodes, node.id, "element")
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
          } else { PepC23NodeLookup { found: false, node: empty_node() } }
          let operand = if zero.found && zero.node.kind == "integer" && zero.node.integerValue == 0 {
            pep_c23_child(nodes, element.id, "right", 1)
          } else { PepC23NodeLookup { found: false, node: empty_node() } }
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
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_union_list_parameter(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for parameter in nodes {
    if parameter.parentId == function.id && parameter.role == "parameter" &&
       parameter.kind == "parameter" && parameter.text == name {
      let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
      if parameterType.found && pep_c23_union_list_declaration(nodes, parameterType.node).found {
        return PepC23NodeLookup { found: true, node: parameter }
      } else {}
      return PepC23NodeLookup { found: false, node: empty_node() }
    } else {}
  }
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
  let elementCount = count_children(nodes, node.id, "element")
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
  let variant = pep_c23_union_variant(nodes, element.text)
  if !variant.found { return false } else {}
  let owner = pep_c23_union_of_variant(nodes, variant.node)
  if !owner.found || owner.node.id != declaration.id ||
     count_children(nodes, element.id, "argument") != count_children(nodes, variant.node.id, "field_type") {
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
  var call = PepC23NodeLookup { found: false, node: empty_node() }
  for candidate in nodes {
    if candidate.id == node.parentId && candidate.kind == "call" {
      call = PepC23NodeLookup { found: true, node: candidate }
    } else {}
  }
  let callArgument = if call.found {
    pep_c23_child(nodes, call.node.id, "argument", node.childIndex)
  } else { PepC23NodeLookup { found: false, node: empty_node() } }
  if !call.found || call.node.role != "result" || !callArgument.found ||
     callArgument.node.id != node.id {
    return pep_c23_unsupported("Pep C23 recursive union list binding must be passed by a direct call in its match arm")
  } else {}
  var arm = PepC23NodeLookup { found: false, node: empty_node() }
  for candidate in nodes {
    if candidate.id == call.node.parentId && candidate.kind == "match_arm" && candidate.role == "arm" {
      arm = PepC23NodeLookup { found: true, node: candidate }
    } else {}
  }
  if !arm.found {
    return pep_c23_unsupported("Pep C23 recursive union list binding must come from the enclosing match arm")
  } else {}
  let armResult = pep_c23_child(nodes, arm.node.id, "result", 1)
  if !armResult.found || armResult.node.id != call.node.id {
    return pep_c23_unsupported("Pep C23 recursive union list binding must be the direct match-arm call argument")
  } else {}
  var matched = PepC23NodeLookup { found: false, node: empty_node() }
  for candidate in nodes {
    if candidate.id == arm.node.parentId && candidate.kind == "match" {
      matched = PepC23NodeLookup { found: true, node: candidate }
    } else {}
  }
  if !matched.found { return pep_c23_unsupported("Pep C23 recursive union list payload has no enclosing match") } else {}
  let pattern = pep_c23_child(nodes, arm.node.id, "pattern", 0)
  let binding = if pattern.found { pep_c23_child(nodes, pattern.node.id, "argument", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let extraBinding = if pattern.found { pep_c23_child(nodes, pattern.node.id, "argument", 1) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  if !pattern.found || pattern.node.kind != "constructor_pattern" ||
     !binding.found || binding.node.kind != "binding_pattern" || binding.node.text != node.text || extraBinding.found {
    return pep_c23_unsupported("Pep C23 recursive union list call requires its one-field constructor payload binding")
  } else {}
  let variant = pep_c23_union_variant(nodes, pattern.node.text)
  let owner = if variant.found { pep_c23_union_of_variant(nodes, variant.node) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let payload = if variant.found { pep_c23_child(nodes, variant.node.id, "field_type", binding.node.childIndex) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let extraPayload = if variant.found { pep_c23_child(nodes, variant.node.id, "field_type", 1) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let listType = if payload.found { pep_c23_union_list_declaration(nodes, payload.node) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  if !variant.found || !owner.found || owner.node.id != declaration.id || !payload.found || extraPayload.found ||
     !listType.found || listType.node.id != declaration.id {
    return pep_c23_unsupported("Pep C23 recursive union list match payload must be one List[Self] field")
  } else {}
  let subject = pep_c23_child(nodes, matched.node.id, "value", 0)
  let subjectUnion = if subject.found { pep_c23_union_value_type(nodes, function, subject.node) } else { PepC23NodeLookup { found: false, node: empty_node() } }
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
  parts = append(parts, int_text(binding.node.childIndex))
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
  let elementCount = count_children(nodes, node.id, "element")
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

fn pep_c23_c_record_field_type(nodes: List[FlatAstNode], owner: FlatAstNode, node: FlatAstNode) -> Str {
  let scalar = pep_c23_c_scalar_type(node)
  if scalar != "" { return scalar } else {}
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
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_union_declaration(nodes: List[FlatAstNode], name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == -1 && node.kind == "union_declaration" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
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
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_union_of_variant(nodes: List[FlatAstNode], variant: FlatAstNode) -> PepC23NodeLookup {
  for declaration in nodes {
    if declaration.parentId == -1 && declaration.kind == "union_declaration" &&
       variant.parentId == declaration.id && variant.role == "variant" {
      return PepC23NodeLookup { found: true, node: declaration }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
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
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_requires_arena(nodes: List[FlatAstNode]) -> Bool {
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
    return PepC23NodeLookup { found: false, node: empty_node() }
  } else {}
  if node.kind != "type_list" { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
  let elementType = pep_c23_child(nodes, node.id, "element_type", 0)
  if !elementType.found || elementType.node.kind != "type_named" {
    return PepC23NodeLookup { found: false, node: empty_node() }
  } else {}
  return pep_c23_record_declaration(nodes, elementType.node.text)
}
fn pep_c23_union_list_declaration(nodes: List[FlatAstNode], node: FlatAstNode) -> PepC23NodeLookup {
  if node.kind != "type_list" { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
  let elementType = pep_c23_child(nodes, node.id, "element_type", 0)
  if !elementType.found || elementType.node.kind != "type_named" {
    return PepC23NodeLookup { found: false, node: empty_node() }
  } else {}
  let declaration = pep_c23_union_declaration(nodes, elementType.node.text)
  if declaration.found && pep_c23_union_has_recursive_list_payload(nodes, declaration.node) {
    return declaration
  } else {}
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_union_list_local_declaration(nodes: List[FlatAstNode], function: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for binding in nodes {
    if binding.parentId == function.id && binding.role == "statement" &&
       binding.kind == "let" && binding.text == name {
      let annotation = pep_c23_child(nodes, binding.id, "annotation", 0)
      if annotation.found { return pep_c23_union_list_declaration(nodes, annotation.node) } else {}
      return PepC23NodeLookup { found: false, node: empty_node() }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_record_field_declaration(nodes: List[FlatAstNode], record: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == record.id && node.role == "field" && node.kind == "field_declaration" && node.text == name {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_record_value_type(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "record" { return pep_c23_record_declaration(nodes, value.text) } else {}
  if value.kind == "call" {
    let target = pep_c23_function(nodes, value.text)
    if !target.found { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    if result.found && result.node.kind == "type_named" {
      return pep_c23_record_declaration(nodes, result.node.text)
    } else {}
    return PepC23NodeLookup { found: false, node: empty_node() }
  } else {}
  if value.kind == "field_access" {
    let base = pep_c23_child(nodes, value.id, "value", 0)
    if !base.found { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
    let parent = pep_c23_record_value_type(nodes, function, base.node)
    if !parent.found { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
    let field = pep_c23_record_field_declaration(nodes, parent.node, value.text)
    if !field.found { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
    let fieldType = pep_c23_child(nodes, field.node.id, "type", 0)
    if !fieldType.found || fieldType.node.kind != "type_named" {
      return PepC23NodeLookup { found: false, node: empty_node() }
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
        return PepC23NodeLookup { found: false, node: empty_node() }
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
        return PepC23NodeLookup { found: false, node: empty_node() }
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
      return PepC23NodeLookup { found: false, node: empty_node() }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_union_value_type(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "call" {
    let variant = pep_c23_union_variant(nodes, value.text)
    if variant.found { return pep_c23_union_of_variant(nodes, variant.node) } else {}
    let target = pep_c23_function(nodes, value.text)
    if !target.found { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    if result.found && result.node.kind == "type_named" {
      return pep_c23_union_declaration(nodes, result.node.text)
    } else {}
    return PepC23NodeLookup { found: false, node: empty_node() }
  } else {}
  if value.kind == "name" {
    for parameter in nodes {
      if parameter.parentId == function.id && parameter.role == "parameter" &&
         parameter.kind == "parameter" && parameter.text == value.text {
        let parameterType = pep_c23_child(nodes, parameter.id, "type", 0)
        if parameterType.found && parameterType.node.kind == "type_named" {
          return pep_c23_union_declaration(nodes, parameterType.node.text)
        } else {}
        return PepC23NodeLookup { found: false, node: empty_node() }
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
        return PepC23NodeLookup { found: false, node: empty_node() }
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
        return PepC23NodeLookup { found: false, node: empty_node() }
      } else {}
    }
  } else {}
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_c_parameter_type(nodes: List[FlatAstNode], node: FlatAstNode) -> Str {
  if node.kind == "type_scalar" { return pep_c23_c_scalar_type(node) } else {}
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
fn pep_c23_parameter_expression(nodes: List[FlatAstNode], function: FlatAstNode, parameterName: Str, secondParameterName: Str, node: FlatAstNode) -> Bool {
  if node.kind == "match" {
    let subject = pep_c23_child(nodes, node.id, "value", 0)
    return subject.found && subject.node.kind == "name" &&
      (subject.node.text == parameterName || subject.node.text == secondParameterName)
  } else {}
  if node.kind == "integer" { return true } else {}
  if node.kind == "name" { return node.text == parameterName || node.text == secondParameterName } else {}
  if node.kind == "field_access" {
    let value = pep_c23_child(nodes, node.id, "value", 0)
    let parentRecord = if value.found {
      pep_c23_record_value_type(nodes, function, value.node)
    } else { PepC23NodeLookup { found: false, node: empty_node() } }
    let field = if parentRecord.found {
      pep_c23_record_field_declaration(nodes, parentRecord.node, node.text)
    } else { PepC23NodeLookup { found: false, node: empty_node() } }
    return value.found &&
      pep_c23_parameter_expression(nodes, function, parameterName, secondParameterName, value.node) &&
      parentRecord.found && field.found
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
    let firstParameterType = if firstParameter.found { pep_c23_child(nodes, firstParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
    let firstParameterIsBoolList = firstParameter.found && firstParameter.node.text == parameterName && firstParameterType.found &&
      pep_c23_c_parameter_type(nodes, firstParameterType.node) == "pep_list_bool"
    let secondArgumentMatches = (secondParameterName != "" && secondArgument.found &&
      secondArgument.node.kind == "name" && secondArgument.node.text == secondParameterName) ||
      (secondParameterName == "" && firstParameterIsBoolList && secondArgument.found && secondArgument.node.kind == "boolean")
    return argument.found && secondArgumentMatches && !extraArgument.found &&
      argument.node.kind == "name" && argument.node.text == parameterName
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
  let payloadCount = count_children(nodes, variant.id, "field_type")
  let argumentCount = count_children(nodes, node.id, "argument")
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
  let variantCount = count_children(nodes, declaration.node.id, "variant")
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
      var arm = PepC23NodeLookup { found: false, node: empty_node() }
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
          if result.node.kind == "name" && result.node.text == patternArgument.node.text {
            bindingIndex = 0
          } else {}
          if result.node.kind == "name" && result.node.text == secondPatternArgument.node.text {
            bindingIndex = 1
          } else {}
          if bindingIndex != -1 {
            let bindingType = if bindingIndex == 0 { payloadType.node } else { secondPayloadType.node }
            let recursiveBinding = bindingType.kind == "type_named" && bindingType.text == declaration.node.text
            resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts,
              variant, 2, bindingIndex,
              PepC23NodeLookup { found: false, node: empty_node() }, recursiveBinding)
          } else {
            let base = pep_c23_child(nodes, result.node.id, "value", 0)
            var projectionIndex = -1
            var projectionType = payloadType.node
            if result.node.kind == "field_access" && base.found &&
               base.node.kind == "name" && base.node.text == patternArgument.node.text {
              projectionIndex = 0
            } else {}
            if result.node.kind == "field_access" && base.found &&
               base.node.kind == "name" && base.node.text == secondPatternArgument.node.text {
              projectionIndex = 1
              projectionType = secondPayloadType.node
            } else {}
            if projectionIndex != -1 && projectionType.kind == "type_named" {
              let record = pep_c23_record_declaration(nodes, projectionType.text)
              let field = if record.found {
                pep_c23_record_field_declaration(nodes, record.node, result.node.text)
              } else { PepC23NodeLookup { found: false, node: empty_node() } }
              if !record.found || !field.found {
                return pep_c23_unsupported("Pep C23 record payload projection does not resolve a declared field")
              } else {}
              resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts, variant, 2, projectionIndex, field, false)
            } else {
              let loweredResult = pep_c23_expression(nodes, function, result.node)
              if loweredResult.status != "emitted" { return loweredResult } else {}
              resultParts = loweredResult.sourceParts
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
              PepC23NodeLookup { found: false, node: empty_node() }, false)
            resultParts = prepend(resultParts, "pep_checked_length(")
            resultParts = append(resultParts, ".length)")
          } else {
            if result.node.kind == "name" && result.node.text == patternArgument.node.text {
              let recursiveBinding = payloadType.node.kind == "type_named" && payloadType.node.text == declaration.node.text
              resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts, variant, 1, 0,
                PepC23NodeLookup { found: false, node: empty_node() }, recursiveBinding)
            } else {
              if result.node.kind == "field_access" && payloadType.node.kind == "type_named" {
                let base = pep_c23_child(nodes, result.node.id, "value", 0)
                if base.found && base.node.kind == "name" && base.node.text == patternArgument.node.text {
                  let record = pep_c23_record_declaration(nodes, payloadType.node.text)
                  let field = if record.found {
                    pep_c23_record_field_declaration(nodes, record.node, result.node.text)
                  } else { PepC23NodeLookup { found: false, node: empty_node() } }
                  if !record.found || !field.found {
                    return pep_c23_unsupported("Pep C23 record payload projection does not resolve a declared field")
                  } else {}
                  resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts, variant,
                    1, 0, field, false)
                } else {
                  if base.found && base.node.kind == "field_access" {
                    let root = pep_c23_child(nodes, base.node.id, "value", 0)
                    let record = pep_c23_record_declaration(nodes, payloadType.node.text)
                    let field = if record.found {
                      pep_c23_record_field_declaration(nodes, record.node, base.node.text)
                    } else { PepC23NodeLookup { found: false, node: empty_node() } }
                    let fieldType = if field.found {
                      pep_c23_child(nodes, field.node.id, "type", 0)
                    } else { PepC23NodeLookup { found: false, node: empty_node() } }
                    let nestedRecord = if fieldType.found && fieldType.node.kind == "type_named" {
                      pep_c23_record_declaration(nodes, fieldType.node.text)
                    } else { PepC23NodeLookup { found: false, node: empty_node() } }
                    let nestedField = if nestedRecord.found {
                      pep_c23_record_field_declaration(nodes, nestedRecord.node, result.node.text)
                    } else { PepC23NodeLookup { found: false, node: empty_node() } }
                    let nestedFieldType = if nestedField.found {
                      pep_c23_child(nodes, nestedField.node.id, "type", 0)
                    } else { PepC23NodeLookup { found: false, node: empty_node() } }
                    if !root.found || root.node.kind != "name" ||
                       root.node.text != patternArgument.node.text || !record.found ||
                       !field.found || !fieldType.found || !nestedRecord.found ||
                       !nestedField.found || !nestedFieldType.found ||
                       pep_c23_c_scalar_type(nestedFieldType.node) == "" {
                      return pep_c23_unsupported("Pep C23 nested record payload projection requires a scalar terminal field")
                    } else {}
                    resultParts = pep_c23_union_payload_parts(loweredSubject.sourceParts,
                      variant, 1, 0, field, false)
                    resultParts = append(resultParts, ".pep_field_")
                    resultParts = append(resultParts, int_text(nestedField.node.childIndex))
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
fn pep_c23_expression(nodes: List[FlatAstNode], function: FlatAstNode, node: FlatAstNode) -> PepC23Emission {
  if node.kind == "match" { return pep_c23_union_match_expression(nodes, function, node) } else {}
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
    let thirdParameter = pep_c23_child(nodes, function.id, "parameter", 2)
    if parameter.found && parameter.node.text == node.text {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(parameter.node.id)], diagnostic: "" }
    } else {}
    if secondParameter.found && secondParameter.node.text == node.text {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(secondParameter.node.id)], diagnostic: "" }
    } else {}
    if thirdParameter.found && thirdParameter.node.text == node.text {
      return PepC23Emission { status: "emitted", sourceParts: ["pep_arg_", int_text(thirdParameter.node.id)], diagnostic: "" }
    } else {}
    return pep_c23_unsupported("Pep C23 name lowering requires a direct immutable local let or scalar parameter")
  } else {}
  if node.kind == "record" {
    let declaration = pep_c23_record_declaration(nodes, node.text)
    if !declaration.found { return pep_c23_unsupported("Pep C23 record construction requires a declared record type") } else {}
    var parts: List[Str] = []
    parts = ["(pep_record_", int_text(declaration.node.id), "){ "]
    var fieldCount = 0
    for supplied in nodes {
      if supplied.parentId == node.id && supplied.role == "field" && supplied.kind == "record_field" {
        let declared = pep_c23_record_field_declaration(nodes, declaration.node, supplied.text)
        if !declared.found { return pep_c23_unsupported("Pep C23 record construction field does not resolve to a declaration") } else {}
        let fieldType = pep_c23_child(nodes, declared.node.id, "type", 0)
        if !fieldType.found || pep_c23_c_record_field_type(nodes, declaration.node, fieldType.node) == "" {
          return pep_c23_unsupported("Pep C23 record fields require Int, Bool, or a preceding record declaration")
        } else {}
        let value = pep_c23_child(nodes, supplied.id, "value", 0)
        if !value.found { return pep_c23_unsupported("Pep C23 record field has no value") } else {}
        if pep_c23_expression_may_fail(nodes, value.node) {
          return pep_c23_unsupported("Pep C23 record field initializers currently require expressions without runtime failure")
        } else {}
        let lowered = pep_c23_expression(nodes, function, value.node)
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
    let argument = pep_c23_child(nodes, node.id, "argument", 0)
    let secondArgument = pep_c23_child(nodes, node.id, "argument", 1)
    let thirdArgument = pep_c23_child(nodes, node.id, "argument", 2)
    let extraArgument = pep_c23_child(nodes, node.id, "argument", 3)
    let target = pep_c23_function(nodes, node.text)
    if node.text == "contains" {
      if !argument.found || !secondArgument.found || thirdArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 contains lowering requires a list and an Int value")
      } else {}
      let listParameter = if argument.node.kind == "name" {
        pep_c23_int_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
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
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
      if listParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_arg_", int_text(listParameter.node.id), ".length)"], diagnostic: "" }
      } else {}
      let boolListParameter = if argument.node.kind == "name" {
        pep_c23_bool_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
      if boolListParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_arg_", int_text(boolListParameter.node.id), ".length)"], diagnostic: "" }
      } else {}
      let recordListParameter = if argument.node.kind == "name" {
        pep_c23_record_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
      if recordListParameter.found {
        return PepC23Emission { status: "emitted", sourceParts: ["pep_checked_length(pep_arg_", int_text(recordListParameter.node.id), ".length)"], diagnostic: "" }
      } else {}
      let unionListParameter = if argument.node.kind == "name" {
        pep_c23_union_list_parameter(nodes, function, argument.node.text)
      } else { PepC23NodeLookup { found: false, node: empty_node() } }
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
      let list = pep_c23_list_literal(nodes, function, argument.node)
      if !list.found { return pep_c23_unsupported("Pep C23 length lowering requires a direct integer list literal or immutable list binding") } else {}
      return PepC23Emission { status: "emitted", sourceParts: [int_text(count_children(nodes, list.node.id, "element"))], diagnostic: "" }
    } else {}
    if !target.found || extraArgument.found {
      return pep_c23_unsupported("Pep C23 calls require a known target and at most three arguments")
    } else {}
    let parameter = pep_c23_child(nodes, target.node.id, "parameter", 0)
    let secondParameter = pep_c23_child(nodes, target.node.id, "parameter", 1)
    let thirdParameter = pep_c23_child(nodes, target.node.id, "parameter", 2)
    let extraParameter = pep_c23_child(nodes, target.node.id, "parameter", 3)
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    let recordResult = result.found && result.node.kind == "type_named" && pep_c23_record_declaration(nodes, result.node.text).found
    let unionResult = result.found && result.node.kind == "type_named" && pep_c23_union_declaration(nodes, result.node.text).found
    if extraParameter.found || !result.found || (pep_c23_c_scalar_type(result.node) == "" && !recordResult && !unionResult) {
      return pep_c23_unsupported("Pep C23 calls require a known target with a supported scalar, record, or tagged-union result")
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
          var parts: List[Str] = ["pep_fn_", int_text(target.node.id), "("]
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
        var parts: List[Str] = ["pep_fn_", int_text(target.node.id), "("]
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
        var parts: List[Str] = ["pep_fn_", int_text(target.node.id), "("]
        for part in loweredArgument.sourceParts { parts = append(parts, part) }
        parts = pep_c23_close_generated_call(nodes, parts, 1)
        return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
      }
    } else {
      if argument.found || secondArgument.found || thirdArgument.found || (!conditionalTarget && !pep_c23_call_free_expression(nodes, targetValue.node) && !(recordResult && targetValue.found && targetValue.node.kind == "record" && !pep_c23_expression_may_fail(nodes, targetValue.node))) {
        return pep_c23_unsupported("Pep C23 zero-argument calls require a call-free scalar result or a safe record construction; recursive calls are unsupported")
      } else {}
      var parts: List[Str] = ["pep_fn_", int_text(target.node.id), "("]
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
  var parts: List[Str] = ["if (!!("]
  for part in loweredCondition.sourceParts { parts = append(parts, part) }
  parts = append(parts, ")) {\n  int64_t pep_result = ")
  for part in loweredThen.sourceParts { parts = append(parts, part) }
  parts = append(parts, ";\n  pep_leave();\n  return pep_result;\n} else {\n  int64_t pep_result = ")
  for part in loweredElse.sourceParts { parts = append(parts, part) }
  parts = append(parts, ";\n  pep_leave();\n  return pep_result;\n}\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}

fn pep_c23_loop_statement(nodes: List[FlatAstNode], function: FlatAstNode, statement: FlatAstNode, depth: Int, localBindings: List[FlatAstNode]) -> PepC23Emission {
  if depth == 8 { return pep_c23_unsupported("Pep C23 loop condition nesting exceeds the supported depth") } else {}
  let indent = if depth == 0 { "    " } else { "      " }
  if statement.kind == "return" {
    let value = pep_c23_child(nodes, statement.id, "value", 0)
    let result = pep_c23_child(nodes, function.id, "return_type", 0)
    if !value.found || !result.found { return pep_c23_unsupported("Pep C23 loop return has no value or declared result type") } else {}
    let cType = pep_c23_c_scalar_type(result.node)
    if cType == "" { return pep_c23_unsupported("Pep C23 loop returns require a scalar result type") } else {}
    let lowered = pep_c23_expression(nodes, function, value.node)
    if lowered.status != "emitted" { return lowered } else {}
    var parts: List[Str] = [indent, cType, " pep_result_", int_text(statement.id), " = "]
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
          let loweredBranch = pep_c23_loop_statement(nodes, function, branchStatement, depth + 1, localBindings)
          if loweredBranch.status != "emitted" { return loweredBranch } else {}
          for part in loweredBranch.sourceParts { thenParts = append(thenParts, part) }
        } else {
          if branchStatement.parentId == statement.id && branchStatement.role == "else" {
            foundElse = true
            let loweredBranch = pep_c23_loop_statement(nodes, function, branchStatement, depth + 1, localBindings)
            if loweredBranch.status != "emitted" { return loweredBranch } else {}
            for part in loweredBranch.sourceParts { elseParts = append(elseParts, part) }
          } else {}
        }
      }
      if !foundThen || !foundElse { return pep_c23_unsupported("Pep C23 loop conditionals require non-empty assignment branches") } else {}
      var parts: List[Str] = [indent, "if (!!("]
      for part in loweredCondition.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")) {\n")
      for part in thenParts { parts = append(parts, part) }
      parts = append(parts, indent)
      parts = append(parts, "} else {\n")
      for part in elseParts { parts = append(parts, part) }
      parts = append(parts, indent)
      parts = append(parts, "}\n")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else { return pep_c23_unsupported("Pep C23 loop bodies support assignments, returns, and conditionals with assignment sequences") }
  }
}
fn pep_c23_while_body(nodes: List[FlatAstNode], function: FlatAstNode, loop: FlatAstNode, localBindings: List[FlatAstNode]) -> PepC23Emission {
  let condition = pep_c23_child(nodes, loop.id, "condition", 0)
  if !condition.found || count_children(nodes, loop.id, "body") == 0 {
    return pep_c23_unsupported("Pep C23 while lowering requires a condition and a non-empty assignment body")
  } else {}
  let loweredCondition = pep_c23_expression(nodes, function, condition.node)
  if loweredCondition.status != "emitted" { return loweredCondition } else {}
  var parts: List[Str] = ["  while (!!("]
  for part in loweredCondition.sourceParts { parts = append(parts, part) }
  parts = append(parts, ")) {\n")
  for statement in nodes {
    if statement.parentId == loop.id && statement.role == "body" {
      if statement.kind == "if_statement" || statement.kind == "return" {
        let loweredConditional = pep_c23_loop_statement(nodes, function, statement, 0, localBindings)
        if loweredConditional.status != "emitted" { return loweredConditional } else {}
        for part in loweredConditional.sourceParts { parts = append(parts, part) }
      } else {
        if statement.kind != "assignment" { return pep_c23_unsupported("Pep C23 while bodies support assignments, returns, and assignment-only conditionals") } else {}
        let value = pep_c23_child(nodes, statement.id, "value", 0)
        if !value.found { return pep_c23_unsupported("Pep C23 while assignment has no value") } else {}
        let loweredValue = pep_c23_expression(nodes, function, value.node)
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
      }
    } else {}
  }
  parts = append(parts, "  }\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_function_expression(nodes: List[FlatAstNode], function: FlatAstNode) -> PepC23Emission {
  let parameter = pep_c23_child(nodes, function.id, "parameter", 0)
  let secondParameter = pep_c23_child(nodes, function.id, "parameter", 1)
  let thirdParameter = pep_c23_child(nodes, function.id, "parameter", 2)
  let extraParameter = pep_c23_child(nodes, function.id, "parameter", 3)
  let parameterType = if parameter.found { pep_c23_child(nodes, parameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let secondParameterType = if secondParameter.found { pep_c23_child(nodes, secondParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let thirdParameterType = if thirdParameter.found { pep_c23_child(nodes, thirdParameter.node.id, "type", 0) } else { PepC23NodeLookup { found: false, node: empty_node() } }
  let result = pep_c23_child(nodes, function.id, "return_type", 0)
  let parameterCType = if parameterType.found { pep_c23_c_parameter_type(nodes, parameterType.node) } else { "" }
  let secondParameterCType = if secondParameterType.found { pep_c23_c_parameter_type(nodes, secondParameterType.node) } else { "" }
  let thirdParameterCType = if thirdParameterType.found { pep_c23_c_parameter_type(nodes, thirdParameterType.node) } else { "" }
  let resultCType = if result.found { pep_c23_c_parameter_type(nodes, result.node) } else { "" }
  if extraParameter.found || (secondParameter.found && !parameter.found) || (thirdParameter.found && !secondParameter.found) || (function.text == "main" && (parameter.found || secondParameter.found || thirdParameter.found)) || (parameter.found && parameterCType == "") || (secondParameter.found && secondParameterCType == "") || (thirdParameter.found && thirdParameterCType == "") || resultCType == "" || (function.text == "main" && result.node.text != "Int") {
    return pep_c23_unsupported("Pep C23 functions require supported parameters and scalar or record results")
  } else {}
  var localBindings: List[FlatAstNode] = []
  for local in nodes {
    if local.parentId == function.id && local.role == "statement" && local.kind == "var" {
      localBindings = append(localBindings, local)
    } else {}
  }
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
          let recursiveUnionList = if statement.kind == "let" {
            pep_c23_union_list_local_declaration(nodes, function, statement.text)
          } else { PepC23NodeLookup { found: false, node: empty_node() } }
          if recursiveUnionList.found {
            if count_children(nodes, initialValue.node.id, "element") == 0 {
              return pep_c23_unsupported("Pep C23 recursive union list local requires at least one constructor element")
            } else {}
            for item in nodes {
              if item.parentId == initialValue.node.id && item.role == "element" {
                let actual = pep_c23_union_value_type(nodes, function, item)
                if !actual.found || actual.node.id != recursiveUnionList.node.id ||
                   !pep_c23_union_list_element_supported(nodes, recursiveUnionList.node, item) {
                  return pep_c23_unsupported("Pep C23 recursive union list locals require matching constructors with scalar literal payloads")
                } else {}
              } else {}
            }
          } else {
            let recordList = pep_c23_record_list_declaration(nodes, initialValue.node)
            var hasRecordElement = false
            for item in nodes {
              if item.parentId == initialValue.node.id && item.role == "element" && item.kind == "record" { hasRecordElement = true } else {}
              if item.parentId == initialValue.node.id && item.role == "element" && item.kind != "integer" && item.kind != "boolean" && !pep_c23_is_negative_int_literal(nodes, item) && (item.kind != "record" || statement.kind != "let") {
                return pep_c23_unsupported("Pep C23 immutable collection bindings require Int, Bool, or supported record list literals")
              } else {}
            }
            if hasRecordElement && !recordList.found {
              return pep_c23_unsupported("Pep C23 immutable record list binding has no supported declared record type")
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
          let thirdParameter = pep_c23_child(nodes, function.id, "parameter", 2)
          if (firstParameter.found && firstParameter.node.text == statement.text) || (secondParameter.found && secondParameter.node.text == statement.text) || (thirdParameter.found && thirdParameter.node.text == statement.text) {
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
          let iterableRecordParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_record_list_parameter(nodes, function, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: empty_node() } }
          let iterableUnionParameter = if iterable.found && iterable.node.kind == "name" {
            pep_c23_union_list_parameter(nodes, function, iterable.node.text)
          } else { PepC23NodeLookup { found: false, node: empty_node() } }
          let iterableParameter = if iterableIntegerParameter.found { iterableIntegerParameter } else {
            if iterableBooleanParameter.found { iterableBooleanParameter } else {
              if iterableRecordParameter.found { iterableRecordParameter } else { iterableUnionParameter }
            }
          }
          if !iterable.found || (!iterableList.found && !iterableParameter.found && !iterableLocal.found) || count_children(nodes, statement.id, "body") == 0 {
            return pep_c23_unsupported("Pep C23 for-in lowering requires a supported list literal or parameter and a non-empty supported body")
          } else {}
          if iterableList.found {
            let recordLiteral = pep_c23_record_list_declaration(nodes, iterableList.node)
            let recursiveUnionList = if iterableList.found && iterable.found && iterable.node.kind == "name" {
              pep_c23_union_list_local_declaration(nodes, function, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
            if recursiveUnionList.found &&
               count_children(nodes, iterableList.node.id, "element") == 0 {
              return pep_c23_unsupported("Pep C23 recursive union list local requires at least one constructor element")
            } else {}
            for item in nodes {
              if item.parentId == iterableList.node.id && item.role == "element" {
                if recursiveUnionList.found {
                  let actual = pep_c23_union_value_type(nodes, function, item)
                  if !actual.found || actual.node.id != recursiveUnionList.node.id ||
                     !pep_c23_union_list_element_supported(nodes, recursiveUnionList.node, item) {
                    return pep_c23_unsupported("Pep C23 recursive union list locals require matching constructors with scalar literal payloads")
                  } else {}
                } else {
                  if recordLiteral.found {
                    if item.kind != "record" { return pep_c23_unsupported("Pep C23 record list iteration requires record values") } else {}
                  } else {
                    if item.kind != "integer" && item.kind != "boolean" && !pep_c23_is_negative_int_literal(nodes, item) {
                      return pep_c23_unsupported("Pep C23 for-in list literals currently require integer or Bool elements")
                    } else {}
                  }
                }
              } else {}
            }
          } else {}
          for bodyStatement in nodes {
            if bodyStatement.parentId == statement.id && bodyStatement.role == "body" {
              let loweredBody = pep_c23_loop_statement(nodes, function, bodyStatement, 0, localBindings)
              if loweredBody.status != "emitted" { return loweredBody } else {}
            } else {}
          }
        } else {
          if statement.kind == "while" && !returned {
            let loweredWhile = pep_c23_while_body(nodes, function, statement, localBindings)
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
  let requiresArena = pep_c23_requires_arena(parsed.nodes)
  var reversed: List[Str] = []
  reversed = prepend(reversed, "#include <stddef.h>\n")
  reversed = prepend(reversed, "#include <stdio.h>\n")
  reversed = prepend(reversed, "#include <stdint.h>\n")
  reversed = prepend(reversed, "#include <stdlib.h>\n")
  if requiresArena { reversed = prepend(reversed, "#include \"pep_arena.h\"\n") } else {}
  reversed = prepend(reversed, "typedef struct { const int64_t *data; size_t length; } pep_list_int;\n_Bool pep_contains_int(pep_list_int values, int64_t needle) {\n  if (values.length != 0 && values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t i = 0; i < values.length; ++i) { if (values.data[i] == needle) { return 1; } }\n  return 0;\n}\n")
  reversed = prepend(reversed, "typedef struct { const _Bool *data; size_t length; } pep_list_bool;\n_Bool pep_contains_bool(pep_list_bool values, _Bool needle) {\n  if (values.length != 0 && values.data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t i = 0; i < values.length; ++i) { if (values.data[i] == needle) { return 1; } }\n  return 0;\n}\n")
  reversed = prepend(reversed, "int64_t pep_add(int64_t a, int64_t b) {\n  if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a + b;\n}\nint64_t pep_sub(int64_t a, int64_t b) {\n  if ((b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a - b;\n}\nint64_t pep_mul(int64_t a, int64_t b) {\n  if (a > 0) { if ((b > 0 && a > INT64_MAX / b) || (b < 0 && b < INT64_MIN / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  else if (a < 0) { if ((b > 0 && a < INT64_MIN / b) || (b < 0 && b < INT64_MAX / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  return a * b;\n}\nint64_t pep_div(int64_t a, int64_t b) {\n  if (b == 0) { fputs(\"PEP_RUNTIME_DIVISION_BY_ZERO\\n\", stderr); exit(1); }\n  if (a == INT64_MIN && b == -1) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a / b;\n}\nint64_t pep_neg(int64_t a) {\n  if (a == INT64_MIN) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return -a;\n}\n[[maybe_unused]] static int64_t pep_checked_length(size_t length) { if ((uintmax_t)length > (uintmax_t)INT64_MAX) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } return (int64_t)length; }\nstatic int pep_call_depth = 0;\nstatic void pep_enter(void) { if (pep_call_depth >= 512) { fputs(\"PEP_RUNTIME_CALL_DEPTH\\n\", stderr); exit(1); } pep_call_depth += 1; }\nstatic void pep_leave(void) { pep_call_depth -= 1; }\n[[maybe_unused]] static int64_t pep_invalid_union_tag(void) { fputs(\"PEP_RUNTIME_INVALID_UNION\\n\", stderr); exit(1); }\n")
  for record in parsed.nodes {
    if record.parentId == -1 && record.kind == "record_declaration" {
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
            parts = append(parts, fieldKind)
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
    if declaration.parentId == -1 && declaration.kind == "union_declaration" {
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
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      let parameter = pep_c23_child(parsed.nodes, node.id, "parameter", 0)
      let secondParameter = pep_c23_child(parsed.nodes, node.id, "parameter", 1)
      let thirdParameter = pep_c23_child(parsed.nodes, node.id, "parameter", 2)
      let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
      for resultPart in pep_c23_c_parameter_type_parts(parsed.nodes, result.node) { reversed = prepend(reversed, resultPart) }
      reversed = prepend(reversed, " pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      if parameter.found {
        let parameterType = pep_c23_child(parsed.nodes, parameter.node.id, "type", 0)
        reversed = prepend(reversed, "(")
        for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, parameterType.node) { reversed = prepend(reversed, typePart) }
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameter.node.id))
        if secondParameter.found {
          let secondParameterType = pep_c23_child(parsed.nodes, secondParameter.node.id, "type", 0)
          reversed = prepend(reversed, ", ")
          for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, secondParameterType.node) { reversed = prepend(reversed, typePart) }
          reversed = prepend(reversed, " pep_arg_")
          reversed = prepend(reversed, int_text(secondParameter.node.id))
          if thirdParameter.found {
            let thirdParameterType = pep_c23_child(parsed.nodes, thirdParameter.node.id, "type", 0)
            reversed = prepend(reversed, ", ")
            for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, thirdParameterType.node) { reversed = prepend(reversed, typePart) }
            reversed = prepend(reversed, " pep_arg_")
            reversed = prepend(reversed, int_text(thirdParameter.node.id))
          } else {}
        } else {}
        if requiresArena {
          reversed = prepend(reversed, ", ")
          reversed = prepend(reversed, "pep_arena_t *pep_arena")
          reversed = prepend(reversed, ");\n")
        } else { reversed = prepend(reversed, ");\n") }
      } else {
        if requiresArena { reversed = prepend(reversed, "(pep_arena_t *pep_arena);\n") } else {
          reversed = prepend(reversed, "(void);\n")
        }
      }
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
      let thirdParameter = pep_c23_child(parsed.nodes, node.id, "parameter", 2)
      var bodyParts: List[Str] = ["  pep_enter();\n"]
      if requiresArena { bodyParts = append(bodyParts, "  (void)pep_arena;\n") } else {}
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
      if thirdParameter.found {
        bodyParts = append(bodyParts, "  (void)pep_arg_")
        bodyParts = append(bodyParts, int_text(thirdParameter.node.id))
        bodyParts = append(bodyParts, ";\n")
      } else {}
      var localBindings: List[FlatAstNode] = []
      for local in parsed.nodes {
        if local.parentId == node.id && local.role == "statement" && local.kind == "var" {
          localBindings = append(localBindings, local)
        } else {}
      }
      for statement in parsed.nodes {
        if statement.parentId == node.id && statement.role == "statement" && (statement.kind == "let" || statement.kind == "var") {
          let initialValue = pep_c23_child(parsed.nodes, statement.id, "value", 0)
          if !initialValue.found { return pep_c23_unsupported("Pep C23 local binding has no value") } else {}
          if initialValue.node.kind == "list" && statement.kind == "let" {
            // Immutable list literals are lowered at their direct length/for-in use sites.
          } else {
            if initialValue.node.kind == "list" && statement.kind == "var" {
              let elementKind = pep_c23_mutable_list_element_kind(parsed.nodes, statement)
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
              let localRecord = pep_c23_record_value_type(parsed.nodes, node, initialValue.node)
              let localUnion = pep_c23_union_value_type(parsed.nodes, node, initialValue.node)
              if initialValue.node.kind == "record" && !localRecord.found {
                return pep_c23_unsupported("Pep C23 record local has no declared record type")
              } else {}
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
              for part in initial.sourceParts { bodyParts = append(bodyParts, part) }
              bodyParts = append(bodyParts, ";\n")
            }
          }
        } else {
          if statement.parentId == node.id && statement.role == "statement" && statement.kind == "for_in" {
            let iterable = pep_c23_child(parsed.nodes, statement.id, "iterable", 0)
            let iterableList = if iterable.found { pep_c23_list_literal(parsed.nodes, node, iterable.node) } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableRecordLiteral = if iterableList.found {
              pep_c23_record_list_declaration(parsed.nodes, iterableList.node)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableUnionLiteral = if iterableList.found && iterable.found && iterable.node.kind == "name" {
              pep_c23_union_list_local_declaration(parsed.nodes, node, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableLocal = if iterable.found && iterable.node.kind == "name" { pep_c23_mutable_list_binding(parsed.nodes, node, iterable.node.text) } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableIntegerParameter = if iterable.found && iterable.node.kind == "name" {
              pep_c23_int_list_parameter(parsed.nodes, node, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableBooleanParameter = if iterable.found && iterable.node.kind == "name" {
              pep_c23_bool_list_parameter(parsed.nodes, node, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableRecordParameter = if iterable.found && iterable.node.kind == "name" {
              pep_c23_record_list_parameter(parsed.nodes, node, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
            let iterableUnionParameter = if iterable.found && iterable.node.kind == "name" {
              pep_c23_union_list_parameter(parsed.nodes, node, iterable.node.text)
            } else { PepC23NodeLookup { found: false, node: empty_node() } }
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
                let record = if recordParameterType.found { pep_c23_record_list_declaration(parsed.nodes, recordParameterType.node) } else { PepC23NodeLookup { found: false, node: empty_node() } }
                if !record.found { return pep_c23_unsupported("Pep C23 record list parameter has no declared record type") } else {}
                for part in ["  if (pep_arg_", int_text(iterableRecordParameter.node.id), ".length != 0 && pep_arg_", int_text(iterableRecordParameter.node.id), ".data == NULL) { fputs(\"PEP_RUNTIME_INVALID_LIST\\n\", stderr); exit(1); }\n  for (size_t pep_index_", int_text(statement.id), " = 0; pep_index_", int_text(statement.id), " < pep_arg_", int_text(iterableRecordParameter.node.id), ".length; ++pep_index_", int_text(statement.id), ") {\n    pep_record_", int_text(record.node.id), " pep_local_", int_text(statement.id), " = pep_arg_", int_text(iterableRecordParameter.node.id), ".data[pep_index_", int_text(statement.id), "];\n"] {
                  arrayDeclaration = append(arrayDeclaration, part)
                }
              } else {}
              if iterableUnionParameter.found {
                let unionParameterType = pep_c23_child(parsed.nodes, iterableUnionParameter.node.id, "type", 0)
                let unionType = if unionParameterType.found {
                  pep_c23_union_list_declaration(parsed.nodes, unionParameterType.node)
                } else { PepC23NodeLookup { found: false, node: empty_node() } }
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
                let loweredBody = pep_c23_loop_statement(parsed.nodes, node, loopStatement, 0, localBindings)
                if loweredBody.status != "emitted" { return loweredBody } else {}
                for part in loweredBody.sourceParts { bodyParts = append(bodyParts, part) }
              } else {}
            }
            bodyParts = append(bodyParts, "  }\n")
          } else {
            if statement.parentId == node.id && statement.role == "statement" && statement.kind == "while" {
              let loweredWhile = pep_c23_while_body(parsed.nodes, node, statement, localBindings)
              if loweredWhile.status != "emitted" { return loweredWhile } else {}
              for part in loweredWhile.sourceParts { bodyParts = append(bodyParts, part) }
            } else {}
          }
        }
      }

      if hasConditionalBody {
        for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
      } else {
        let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
        bodyParts = append(bodyParts, "  ")
        for resultPart in pep_c23_c_parameter_type_parts(parsed.nodes, result.node) { bodyParts = append(bodyParts, resultPart) }
        bodyParts = append(bodyParts, " pep_result = ")
        for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
        bodyParts = append(bodyParts, ";\n  pep_leave();\n  return pep_result;\n")
      }
      let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
      for resultPart in pep_c23_c_parameter_type_parts(parsed.nodes, result.node) { reversed = prepend(reversed, resultPart) }
      reversed = prepend(reversed, " pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      if parameter.found {
        let parameterType = pep_c23_child(parsed.nodes, parameter.node.id, "type", 0)
        reversed = prepend(reversed, "(")
        for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, parameterType.node) { reversed = prepend(reversed, typePart) }
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameter.node.id))
        if secondParameter.found {
          let secondParameterType = pep_c23_child(parsed.nodes, secondParameter.node.id, "type", 0)
          reversed = prepend(reversed, ", ")
          for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, secondParameterType.node) { reversed = prepend(reversed, typePart) }
          reversed = prepend(reversed, " pep_arg_")
          reversed = prepend(reversed, int_text(secondParameter.node.id))
          if thirdParameter.found {
            let thirdParameterType = pep_c23_child(parsed.nodes, thirdParameter.node.id, "type", 0)
            reversed = prepend(reversed, ", ")
            for typePart in pep_c23_c_parameter_type_parts(parsed.nodes, thirdParameterType.node) { reversed = prepend(reversed, typePart) }
            reversed = prepend(reversed, " pep_arg_")
            reversed = prepend(reversed, int_text(thirdParameter.node.id))
          } else {}
        } else {}
        if requiresArena {
          reversed = prepend(reversed, ", ")
          reversed = prepend(reversed, "pep_arena_t *pep_arena")
          reversed = prepend(reversed, ") {\n")
        } else { reversed = prepend(reversed, ") {\n") }
      } else {
        if requiresArena { reversed = prepend(reversed, " (pep_arena_t *pep_arena) {\n") } else {
          reversed = prepend(reversed, " (void) {\n")
        }
      }
      for part in bodyParts { reversed = prepend(reversed, part) }
      reversed = prepend(reversed, "}\n")
    } else {}
  }
  if requiresArena {
    reversed = prepend(reversed, "int main(void) {\n")
    reversed = prepend(reversed, "  pep_arena_t *pep_arena = NULL;\n")
    reversed = prepend(reversed, "  if (pep_arena_init(&pep_arena, 0) != PEP_ARENA_OK) { fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); return 1; }\n")
    reversed = prepend(reversed, "  int64_t pep_main_result = pep_fn_")
    reversed = prepend(reversed, int_text(mainId))
    reversed = prepend(reversed, "(pep_arena);\n")
    reversed = prepend(reversed, "  if (pep_arena_status(pep_arena) != PEP_ARENA_OK) { pep_arena_free(&pep_arena); fputs(\"PEP_RUNTIME_ARENA_FAILURE\\n\", stderr); return 1; }\n")
    reversed = prepend(reversed, "  (void)printf(\"%lld\\n\", (long long)pep_main_result);\n")
    reversed = prepend(reversed, "  pep_arena_free(&pep_arena);\n")
    reversed = prepend(reversed, "  return 0;\n")
    reversed = prepend(reversed, "}\n")
  } else {
    reversed = prepend(reversed, "int main(void) {\n")
    reversed = prepend(reversed, "  (void)printf(\"%lld\\n\", (long long)(pep_fn_")
    reversed = prepend(reversed, int_text(mainId))
    reversed = prepend(reversed, "()));\n")
    reversed = prepend(reversed, "  return 0;\n")
    reversed = prepend(reversed, "}\n")
  }
  return PepC23Emission { status: "emitted", sourceParts: reverse(reversed), diagnostic: "" }
}
