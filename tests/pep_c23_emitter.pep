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
  if node.kind == "field_access" {
    let base = pep_c23_child(nodes, node.id, "value", 0)
    return !base.found || pep_c23_expression_may_fail(nodes, base.node)
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
fn pep_c23_parameter_expression(nodes: List[FlatAstNode], parameterName: Str, secondParameterName: Str, node: FlatAstNode) -> Bool {
  if node.kind == "integer" { return true } else {}
  if node.kind == "name" { return node.text == parameterName || node.text == secondParameterName } else {}
  if node.kind == "field_access" {
    let base = pep_c23_child(nodes, node.id, "value", 0)
    return base.found && pep_c23_parameter_expression(nodes, parameterName, secondParameterName, base.node)
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
    return payload.text == "Int"
  } else {}
  if payload.kind == "type_named" {
    return pep_c23_record_declaration(nodes, payload.text).found
  } else {}
  return false
}
fn pep_c23_union_supported_layout(nodes: List[FlatAstNode], declaration: FlatAstNode) -> Bool {
  var variantCount = 0
  var hasPayload = false
  for variant in nodes {
    if variant.parentId == declaration.id && variant.role == "variant" &&
       variant.kind == "variant_declaration" {
      variantCount = variantCount + 1
      var variantPayloadCount = 0
      for payload in nodes {
        if payload.parentId == variant.id && payload.role == "field_type" {
          variantPayloadCount = variantPayloadCount + 1
          if !pep_c23_union_payload_type_supported(nodes, payload) { return false } else {}
        } else {}
      }
      if variantPayloadCount != 0 { hasPayload = true } else {}
    } else {}
  }
  return !(variantCount <= 1) && hasPayload
}

fn pep_c23_record_field(nodes: List[FlatAstNode], declaration: FlatAstNode, name: Str) -> PepC23NodeLookup {
  for field in nodes {
    if field.parentId == declaration.id && field.role == "field" &&
       field.kind == "field_declaration" && field.text == name {
      return PepC23NodeLookup { found: true, node: field }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_record_layout_supported(nodes: List[FlatAstNode], declaration: FlatAstNode) -> Bool {
  var fieldCount = 0
  for field in nodes {
    if field.parentId == declaration.id && field.role == "field" &&
       field.kind == "field_declaration" {
      fieldCount = fieldCount + 1
      let fieldType = pep_c23_child(nodes, field.id, "type", 0)
      if !fieldType.found || pep_c23_c_scalar_type(fieldType.node) == "" { return false } else {}
    } else {}
  }
  return fieldCount != 0
}
fn pep_c23_record_type(nodes: List[FlatAstNode], typeNode: FlatAstNode) -> PepC23NodeLookup {
  if typeNode.kind != "type_named" { return PepC23NodeLookup { found: false, node: empty_node() } } else {}
  let declaration = pep_c23_record_declaration(nodes, typeNode.text)
  if declaration.found && pep_c23_record_layout_supported(nodes, declaration.node) { return declaration } else {}
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
  } else {}
  return PepC23NodeLookup { found: false, node: empty_node() }
}

fn pep_c23_c_type_parts(nodes: List[FlatAstNode], typeNode: FlatAstNode) -> List[Str] {
  let scalar = pep_c23_c_scalar_type(typeNode)
  if scalar != "" { return [scalar] } else {}
  let record = pep_c23_record_type(nodes, typeNode)
  if record.found { return ["pep_record_", int_text(record.node.id)] } else {}
  if typeNode.kind == "type_named" {
    let unionType = pep_c23_union_declaration(nodes, typeNode.text)
    if unionType.found && pep_c23_union_supported_layout(nodes, unionType.node) { return ["pep_union_", int_text(unionType.node.id)] } else {}
  } else {}
  return []
}
fn pep_c23_c_type(nodes: List[FlatAstNode], typeNode: FlatAstNode) -> Str {
  let scalar = pep_c23_c_scalar_type(typeNode)
  if scalar != "" { return scalar } else {}
  let record = pep_c23_record_type(nodes, typeNode)
  if record.found { return "record" } else {}
  if typeNode.kind == "type_named" {
    let unionType = pep_c23_union_declaration(nodes, typeNode.text)
    if unionType.found && pep_c23_union_supported_layout(nodes, unionType.node) { return "union" } else {}
  } else {}
  return ""
}
fn pep_c23_record_value_type(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23NodeLookup {
  if value.kind == "record" { return pep_c23_record_declaration(nodes, value.text) } else {}
  if value.kind == "call" {
    let target = pep_c23_function(nodes, value.text)
    if target.found {
      let returnType = pep_c23_child(nodes, target.node.id, "return_type", 0)
      if returnType.found { return pep_c23_record_type(nodes, returnType.node) } else {}
    } else {}
  } else {}
  if value.kind == "name" {
    for parameter in nodes {
      if parameter.parentId == function.id && parameter.role == "parameter" && parameter.text == value.text {
        let typeNode = pep_c23_child(nodes, parameter.id, "type", 0)
        if typeNode.found { return pep_c23_record_type(nodes, typeNode.node) } else {}
      } else {}
    }
    for binding in nodes {
      if binding.parentId == function.id && binding.role == "statement" &&
         binding.kind == "let" && binding.text == value.text {
        let initial = pep_c23_child(nodes, binding.id, "value", 0)
        if initial.found { return pep_c23_record_value_type(nodes, function, initial.node) } else {}
      } else {}
    }
  } else {}
  return PepC23NodeLookup { found: false, node: empty_node() }
}
fn pep_c23_c_expression_type(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> Str {
  if value.kind == "integer" || value.kind == "binary" { return "int64_t" } else {}
  if value.kind == "boolean" || (value.kind == "unary" && value.text == "!") { return "_Bool" } else {}
  if value.kind == "record" || value.kind == "name" {
    let declaration = pep_c23_record_value_type(nodes, function, value)
    if declaration.found { return "record" } else {}
  } else {}
  if value.kind == "field_access" {
    let base = pep_c23_child(nodes, value.id, "value", 0)
    if base.found {
      let declaration = pep_c23_record_value_type(nodes, function, base.node)
      if declaration.found {
        let field = pep_c23_record_field(nodes, declaration.node, value.text)
        if field.found {
          let fieldType = pep_c23_child(nodes, field.node.id, "type", 0)
          if fieldType.found { return pep_c23_c_scalar_type(fieldType.node) } else {}
        } else {}
      } else {}
    } else {}
  } else {}
  return ""
}
fn pep_c23_record_declaration_source(nodes: List[FlatAstNode], declaration: FlatAstNode) -> PepC23Emission {
  if !pep_c23_record_layout_supported(nodes, declaration) {
    return pep_c23_unsupported("Pep C23 record layout supports non-empty records with scalar Int or Bool fields")
  } else {}
  var parts: List[Str] = ["typedef struct { "]
  for field in nodes {
    if field.parentId == declaration.id && field.role == "field" &&
       field.kind == "field_declaration" {
      let fieldType = pep_c23_child(nodes, field.id, "type", 0)
      parts = append(parts, pep_c23_c_scalar_type(fieldType.node))
      parts = append(parts, " pep_field_")
      parts = append(parts, int_text(field.childIndex))
      parts = append(parts, "; ")
    } else {}
  }
  parts = append(parts, "} pep_record_")
  parts = append(parts, int_text(declaration.id))
  parts = append(parts, ";\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}
fn pep_c23_union_declaration_source(nodes: List[FlatAstNode], declaration: FlatAstNode) -> PepC23Emission {
  if !pep_c23_union_supported_layout(nodes, declaration) {
    return pep_c23_unsupported("Pep C23 tagged union has an unsupported layout")
  } else {}
  var parts: List[Str] = ["typedef struct { uint32_t tag; union { "]
  var payloadCount = 0
  for variant in nodes {
    if variant.parentId == declaration.id && variant.role == "variant" &&
       variant.kind == "variant_declaration" {
      var fieldCount = 0
      for payload in nodes {
        if payload.parentId == variant.id && payload.role == "field_type" {
          if fieldCount == 0 { parts = append(parts, "struct { ") } else { parts = append(parts, " ") }
          for typePart in pep_c23_c_type_parts(nodes, payload) { parts = append(parts, typePart) }
          parts = append(parts, " field_")
          parts = append(parts, int_text(payload.childIndex))
          parts = append(parts, ";")
          fieldCount = fieldCount + 1
        } else {}
      }
      if fieldCount != 0 {
        parts = append(parts, " } payload_")
        parts = append(parts, int_text(variant.childIndex))
        parts = append(parts, "; ")
        payloadCount = payloadCount + 1
      } else {}
    } else {}
  }
  parts = append(parts, " } payload; } pep_union_")
  parts = append(parts, int_text(declaration.id))
  parts = append(parts, ";\n")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
}

fn pep_c23_record_expression(nodes: List[FlatAstNode], function: FlatAstNode, value: FlatAstNode) -> PepC23Emission {
  let declaration = pep_c23_record_declaration(nodes, value.text)
  if !declaration.found || !pep_c23_record_layout_supported(nodes, declaration.node) {
    return pep_c23_unsupported("Pep C23 record construction requires a declared scalar-field record layout")
  } else {}
  let expectedCount = count_children(nodes, declaration.node.id, "field")
  let suppliedCount = count_children(nodes, value.id, "field")
  if expectedCount != suppliedCount {
    return pep_c23_unsupported("Pep C23 record construction must initialize every declared field exactly once")
  } else {}
  var parts: List[Str] = ["(pep_record_", int_text(declaration.node.id), "){ "]
  var index = 0
  for supplied in nodes {
    if supplied.parentId == value.id && supplied.role == "field" && supplied.kind == "record_field" {
      let declared = pep_c23_record_field(nodes, declaration.node, supplied.text)
      if !declared.found { return pep_c23_unsupported("Pep C23 record initializer contains an undeclared field") } else {}
      for prior in nodes {
        if prior.parentId == value.id && prior.role == "field" && prior.kind == "record_field" &&
           prior.text == supplied.text && prior.id != supplied.id {
          return pep_c23_unsupported("Pep C23 record initializer repeats a field")
        } else {}
      }
      let fieldValue = pep_c23_child(nodes, supplied.id, "value", 0)
      if !fieldValue.found { return pep_c23_unsupported("Pep C23 record initializer field has no value") } else {}
      if pep_c23_expression_may_fail(nodes, fieldValue.node) {
        return pep_c23_unsupported("Pep C23 record initializer expressions must not contain fallible operations")
      } else {}
      let lowered = pep_c23_expression(nodes, function, fieldValue.node)
      if lowered.status != "emitted" { return lowered } else {}
      if index != 0 { parts = append(parts, ", ") } else {}
      parts = append(parts, ".pep_field_")
      parts = append(parts, int_text(declared.node.childIndex))
      parts = append(parts, " = ")
      for part in lowered.sourceParts { parts = append(parts, part) }
      index = index + 1
    } else {}
  }
  parts = append(parts, " }")
  return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
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
  var parts: List[Str] = ["(pep_union_", int_text(declaration.node.id), "){ .tag = ", int_text(variant.childIndex)]
  if payloadCount != 0 {
    parts = append(parts, ", .payload.payload_")
    parts = append(parts, int_text(variant.childIndex))
    parts = append(parts, " = { ")
    var emittedCount = 0
    var fallibleArgumentCount = 0
    for payloadType in nodes {
      if payloadType.parentId == variant.id && payloadType.role == "field_type" {
        if !pep_c23_union_payload_type_supported(nodes, payloadType) {
          return pep_c23_unsupported("Pep C23 constructor payload type is unsupported")
        } else {}
        let argument = pep_c23_child(nodes, node.id, "argument", payloadType.childIndex)
        if !argument.found { return pep_c23_unsupported("Pep C23 constructor payload argument is missing") } else {}
        if pep_c23_expression_may_fail(nodes, argument.node) { fallibleArgumentCount = fallibleArgumentCount + 1 } else {}
        if fallibleArgumentCount == 2 { return pep_c23_unsupported("Pep C23 rejects multiple fallible constructor arguments because C evaluation order is unspecified") } else {}
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
      let payloadCount = count_children(nodes, variant.id, "field_type")
      let patternCount = count_children(nodes, pattern.node.id, "argument")
      if payloadCount != patternCount {
        return pep_c23_unsupported("Pep C23 constructor pattern argument count must match the variant")
      } else {}
      for patternArgument in nodes {
        if patternArgument.parentId == pattern.node.id && patternArgument.role == "argument" &&
           patternArgument.kind != "binding_pattern" && patternArgument.kind != "wildcard_pattern" {
          return pep_c23_unsupported("Pep C23 constructor payload patterns require bindings or wildcards")
        } else {}
      }
      let result = pep_c23_child(nodes, arm.node.id, "result", 1)
      if !result.found { return pep_c23_unsupported("Pep C23 match arm has no result") } else {}
      var bindingName = ""
      if result.node.kind == "name" { bindingName = result.node.text } else {}
      if result.node.kind == "field_access" {
        let base = pep_c23_child(nodes, result.node.id, "value", 0)
        if base.found && base.node.kind == "name" { bindingName = base.node.text } else {}
      } else {}
      var bindingIndex = -1
      for patternArgument in nodes {
        if patternArgument.parentId == pattern.node.id && patternArgument.role == "argument" &&
           patternArgument.kind == "binding_pattern" && patternArgument.text == bindingName {
          bindingIndex = patternArgument.childIndex
        } else {}
      }
      var resultParts: List[Str] = []
      if bindingIndex != -1 {
        let payloadType = pep_c23_child(nodes, variant.id, "field_type", bindingIndex)
        if !payloadType.found { return pep_c23_unsupported("Pep C23 bound constructor payload is missing") } else {}
        for part in loweredSubject.sourceParts { resultParts = append(resultParts, part) }
        resultParts = append(resultParts, ".payload.payload_")
        resultParts = append(resultParts, int_text(variant.childIndex))
        resultParts = append(resultParts, ".field_")
        resultParts = append(resultParts, int_text(bindingIndex))
        if result.node.kind == "field_access" {
          if payloadType.node.kind != "type_named" {
            return pep_c23_unsupported("Pep C23 field projection binding must carry a declared record")
          } else {}
          let record = pep_c23_record_declaration(nodes, payloadType.node.text)
          let field = if record.found {
            pep_c23_record_field(nodes, record.node, result.node.text)
          } else { PepC23NodeLookup { found: false, node: empty_node() } }
          if !record.found || !field.found {
            return pep_c23_unsupported("Pep C23 record payload projection does not resolve a declared field")
          } else {}
          resultParts = append(resultParts, ".pep_field_")
          resultParts = append(resultParts, int_text(field.node.childIndex))
        } else {}
      } else {
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
        parts = append(parts, " : pep_invalid_union_tag())")
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
  if node.kind == "record" { return pep_c23_record_expression(nodes, function, node) } else {}
  if node.kind == "field_access" {
    let base = pep_c23_child(nodes, node.id, "value", 0)
    if !base.found { return pep_c23_unsupported("Pep C23 record field access has no base value") } else {}
    let declaration = pep_c23_record_value_type(nodes, function, base.node)
    if !declaration.found { return pep_c23_unsupported("Pep C23 field access requires a local declared record value") } else {}
    let field = pep_c23_record_field(nodes, declaration.node, node.text)
    if !field.found { return pep_c23_unsupported("Pep C23 field access does not resolve to a declared record field") } else {}
    let loweredBase = pep_c23_expression(nodes, function, base.node)
    if loweredBase.status != "emitted" { return loweredBase } else {}
    var parts: List[Str] = []
    for part in loweredBase.sourceParts { parts = append(parts, part) }
    parts = append(parts, ".pep_field_")
    parts = append(parts, int_text(field.node.childIndex))
    return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
  } else {}
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
      if candidate.parentId == function.id && candidate.role == "statement" && candidate.kind == "let" && candidate.text == node.text {
        localFound = true
        localId = candidate.id
      } else {}
    }
    if localFound { return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(localId)], diagnostic: "" } } else {}
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
    let variant = pep_c23_union_variant(nodes, node.text)
    if variant.found { return pep_c23_union_constructor(nodes, function, node, variant.node) } else {}
    let argument = pep_c23_child(nodes, node.id, "argument", 0)
    let secondArgument = pep_c23_child(nodes, node.id, "argument", 1)
    let extraArgument = pep_c23_child(nodes, node.id, "argument", 2)
    let target = pep_c23_function(nodes, node.text)
    if !target.found || extraArgument.found {
      return pep_c23_unsupported("Pep C23 calls require a known target and at most two arguments")
    } else {}
    let parameter = pep_c23_child(nodes, target.node.id, "parameter", 0)
    let secondParameter = pep_c23_child(nodes, target.node.id, "parameter", 1)
    let extraParameter = pep_c23_child(nodes, target.node.id, "parameter", 2)
    let result = pep_c23_child(nodes, target.node.id, "return_type", 0)
    if extraParameter.found || !result.found || pep_c23_c_type(nodes, result.node) == "" {
      return pep_c23_unsupported("Pep C23 calls require a known target with a supported scalar or record result")
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
      let targetRecordResult = pep_c23_record_type(nodes, result.node)
      if argument.found || secondArgument.found {
        return pep_c23_unsupported("Pep C23 zero-argument calls cannot receive arguments")
      } else {}
      if !conditionalTarget {
        if targetRecordResult.found {
          if targetValue.node.kind != "record" { return pep_c23_unsupported("Pep C23 zero-argument record calls require direct record construction") } else {}
        } else {
          if !pep_c23_call_free_expression(nodes, targetValue.node) {
            return pep_c23_unsupported("Pep C23 zero-argument calls require a call-free scalar result; recursive calls are unsupported")
          } else {}
        }
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
  let parameterCType = if parameterType.found { pep_c23_c_type(nodes, parameterType.node) } else { "" }
  let secondParameterCType = if secondParameterType.found { pep_c23_c_type(nodes, secondParameterType.node) } else { "" }
  let resultCType = if result.found { pep_c23_c_type(nodes, result.node) } else { "" }
  if extraParameter.found || (secondParameter.found && !parameter.found) || (function.text == "main" && (parameter.found || secondParameter.found)) || (parameter.found && parameterCType == "") || (secondParameter.found && secondParameterCType == "") || resultCType == "" || (function.text == "main" && result.node.text != "Int") {
    return pep_c23_unsupported("Pep C23 functions require supported scalar or record parameters and results")
  } else {}
  var returned = false
  var statementCount = 0
  var returnStatement = PepC23NodeLookup { found: false, node: empty_node() }
  for statement in nodes {
    if statement.parentId == function.id && statement.role == "statement" {
      statementCount = statementCount + 1
      if statement.kind == "let" && !returned {
        let initialValue = pep_c23_child(nodes, statement.id, "value", 0)
        if !initialValue.found { return pep_c23_unsupported("Pep C23 local let has no value") } else {}
        let initial = pep_c23_expression(nodes, function, initialValue.node)
        if initial.status != "emitted" { return initial } else {}
      } else {
        if statement.kind == "return" && !returned {
          returned = true
          returnStatement = PepC23NodeLookup { found: true, node: statement }
        } else {
          return pep_c23_unsupported("Pep C23 functions require direct local lets followed by one return")
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
  reversed = prepend(reversed, "#include <stdio.h>\n")
  reversed = prepend(reversed, "#include <stdint.h>\n")
  reversed = prepend(reversed, "#include <stdlib.h>\n")
  reversed = prepend(reversed, "int64_t pep_add(int64_t a, int64_t b) {\n  if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a + b;\n}\nint64_t pep_sub(int64_t a, int64_t b) {\n  if ((b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a - b;\n}\nint64_t pep_mul(int64_t a, int64_t b) {\n  if (a > 0) { if ((b > 0 && a > INT64_MAX / b) || (b < 0 && b < INT64_MIN / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  else if (a < 0) { if ((b > 0 && a < INT64_MIN / b) || (b < 0 && b < INT64_MAX / a)) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); } }\n  return a * b;\n}\nint64_t pep_div(int64_t a, int64_t b) {\n  if (b == 0) { fputs(\"PEP_RUNTIME_DIVISION_BY_ZERO\\n\", stderr); exit(1); }\n  if (a == INT64_MIN && b == -1) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return a / b;\n}\nint64_t pep_neg(int64_t a) {\n  if (a == INT64_MIN) { fputs(\"PEP_RUNTIME_OVERFLOW\\n\", stderr); exit(1); }\n  return -a;\n}\nstatic int pep_call_depth = 0;\nstatic void pep_enter(void) { if (pep_call_depth >= 512) { fputs(\"PEP_RUNTIME_CALL_DEPTH\\n\", stderr); exit(1); } pep_call_depth += 1; }\nstatic void pep_leave(void) { pep_call_depth -= 1; }\n")
  reversed = prepend(reversed, "static int64_t pep_invalid_union_tag(void) { fputs(\"PEP_RUNTIME_INVALID_UNION\\n\", stderr); exit(1); return 0; }\n")
  for declaration in parsed.nodes {
    if declaration.parentId == -1 && declaration.kind == "record_declaration" {
      let generated = pep_c23_record_declaration_source(parsed.nodes, declaration)
      if generated.status != "emitted" { return generated } else {}
      for part in generated.sourceParts { reversed = prepend(reversed, part) }
    } else {}
  }
  for declaration in parsed.nodes {
    if declaration.parentId == -1 && declaration.kind == "union_declaration" {
      let generated = pep_c23_union_declaration_source(parsed.nodes, declaration)
      if generated.status != "emitted" { return generated } else {}
      for part in generated.sourceParts { reversed = prepend(reversed, part) }
    } else {}
  }
  for node in parsed.nodes {
    if node.parentId == -1 && node.kind == "function" {
      let parameter = pep_c23_child(parsed.nodes, node.id, "parameter", 0)
      let secondParameter = pep_c23_child(parsed.nodes, node.id, "parameter", 1)
      let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
      for typePart in pep_c23_c_type_parts(parsed.nodes, result.node) { reversed = prepend(reversed, typePart) }
      reversed = prepend(reversed, " pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      if parameter.found {
        let parameterType = pep_c23_child(parsed.nodes, parameter.node.id, "type", 0)
        reversed = prepend(reversed, "(")
        for typePart in pep_c23_c_type_parts(parsed.nodes, parameterType.node) { reversed = prepend(reversed, typePart) }
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameter.node.id))
        if secondParameter.found {
          let secondParameterType = pep_c23_child(parsed.nodes, secondParameter.node.id, "type", 0)
          reversed = prepend(reversed, ", ")
          for typePart in pep_c23_c_type_parts(parsed.nodes, secondParameterType.node) { reversed = prepend(reversed, typePart) }
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
        if statement.parentId == node.id && statement.role == "statement" && statement.kind == "let" {
          let initialValue = pep_c23_child(parsed.nodes, statement.id, "value", 0)
          if !initialValue.found { return pep_c23_unsupported("Pep C23 local let has no value") } else {}
          let initial = pep_c23_expression(parsed.nodes, node, initialValue.node)
          let inferredType = pep_c23_c_expression_type(parsed.nodes, node, initialValue.node)
          let recordType = pep_c23_record_value_type(parsed.nodes, node, initialValue.node)
          let unionType = pep_c23_union_value_type(parsed.nodes, node, initialValue.node)
          if recordType.found {
            bodyParts = append(bodyParts, "  pep_record_")
            bodyParts = append(bodyParts, int_text(recordType.node.id))
            bodyParts = append(bodyParts, " pep_local_")
            bodyParts = append(bodyParts, int_text(statement.id))
            bodyParts = append(bodyParts, " = ")
          } else {
            if unionType.found {
              bodyParts = append(bodyParts, "  pep_union_")
              bodyParts = append(bodyParts, int_text(unionType.node.id))
              bodyParts = append(bodyParts, " pep_local_")
              bodyParts = append(bodyParts, int_text(statement.id))
              bodyParts = append(bodyParts, " = ")
            } else {
              let localType = if inferredType == "" { "int64_t" } else { inferredType }
              for part in ["  ", localType, " pep_local_", int_text(statement.id), " = "] { bodyParts = append(bodyParts, part) }
            }
          }
          for part in initial.sourceParts { bodyParts = append(bodyParts, part) }
          bodyParts = append(bodyParts, ";\n")
        } else {}
      }
      if hasConditionalBody {
        for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
      } else {
        let functionResultType = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
        bodyParts = append(bodyParts, "  ")
        for typePart in pep_c23_c_type_parts(parsed.nodes, functionResultType.node) { bodyParts = append(bodyParts, typePart) }
        bodyParts = append(bodyParts, " pep_result = ")
        for part in lowered.sourceParts { bodyParts = append(bodyParts, part) }
        bodyParts = append(bodyParts, ";\n  pep_leave();\n  return pep_result;\n")
      }
      let result = pep_c23_child(parsed.nodes, node.id, "return_type", 0)
      for typePart in pep_c23_c_type_parts(parsed.nodes, result.node) { reversed = prepend(reversed, typePart) }
      reversed = prepend(reversed, " pep_fn_")
      reversed = prepend(reversed, int_text(node.id))
      if parameter.found {
        let parameterType = pep_c23_child(parsed.nodes, parameter.node.id, "type", 0)
        reversed = prepend(reversed, "(")
        for typePart in pep_c23_c_type_parts(parsed.nodes, parameterType.node) { reversed = prepend(reversed, typePart) }
        reversed = prepend(reversed, " pep_arg_")
        reversed = prepend(reversed, int_text(parameter.node.id))
        if secondParameter.found {
          let secondParameterType = pep_c23_child(parsed.nodes, secondParameter.node.id, "type", 0)
          reversed = prepend(reversed, ", ")
          for typePart in pep_c23_c_type_parts(parsed.nodes, secondParameterType.node) { reversed = prepend(reversed, typePart) }
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
