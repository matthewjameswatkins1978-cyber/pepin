#!/usr/bin/env python3
"""Deterministic, test-only C23 artifact generator for checked-AST-shaped fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
GENERATOR_VERSION = "pep-c23-artifact-05.1"
FEATURES = {"bool_literals", "checked_arithmetic", "comparisons", "constructors", "field_access", "function_calls", "int_literals", "list_literals", "list_sum", "parameters", "pattern_matching", "record_literals", "string_literals", "unit_literals"}
FAILURES = {"overflow", "division_by_zero", "allocation", "invalid_variant", "depth"}
PRIMITIVES = {"Int", "Bool", "Str", "Unit"}
ID_RE = re.compile(r"^[a-z0-9_.-]+$")


class FixtureError(Exception):
    def __init__(self, code: str, message: str, **context: Any):
        super().__init__(message)
        self.code = code
        self.context = context

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": str(self), "context": self.context}


def fail(code: str, message: str, **context: Any) -> None:
    raise FixtureError(code, message, **context)


def checked_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        fail("invalid_identity", f"{where} is not a stable identity", where=where)
    return value


def checked_span(value: Any, where: str) -> None:
    if (not isinstance(value, dict) or set(value) != {"start", "end"}
            or not isinstance(value["start"], int) or not isinstance(value["end"], int)
            or value["start"] < 0 or value["end"] < value["start"]):
        fail("invalid_span", f"{where} has an invalid source span", where=where)


def checked_type(value: Any, known: set[str], where: str) -> str:
    if not isinstance(value, str) or not value or (value not in PRIMITIVES and value != "List[Int]" and value not in known):
        fail("invalid_type", f"{where} has no declared checked type", where=where, type=value)
    return value


def validate_expr(expr: Any, known: set[str], bindings: dict[str, str], functions: dict[str, dict[str, Any]], seen: set[str], features: set[str], where: str, type_declarations: list[dict[str, Any]]) -> str:
    if not isinstance(expr, dict):
        fail("invalid_expression", f"{where} is not an object", where=where)
    missing = {"node_id", "kind", "type", "span"} - set(expr)
    if missing:
        fail("missing_expression_fact", f"{where} omits checked facts", where=where, missing=sorted(missing))
    node_id = checked_id(expr["node_id"], f"{where}.node_id")
    if node_id in seen:
        fail("duplicate_checked_node_id", f"duplicate checked node id {node_id}", node_id=node_id)
    seen.add(node_id)
    kind = expr["kind"]
    result_type = checked_type(expr["type"], known, f"{where}.type")
    checked_span(expr["span"], f"{where}.span")
    tags = {"int": "int_literals", "bool": "bool_literals", "unit": "unit_literals", "str": "string_literals", "binary": "checked_arithmetic", "call": "function_calls", "param_ref": "parameters", "record": "record_literals", "field_access": "field_access", "list": "list_literals", "list_sum": "list_sum", "constructor": "constructors", "match": "pattern_matching"}
    if kind not in tags:
        fail("unsupported_expression_tag", f"{where} uses unsupported expression tag {kind}", kind=kind)
    features.add("comparisons" if kind == "binary" and expr.get("op") in {"==", "<"} else tags[kind])
    if kind == "int":
        if result_type != "Int" or not isinstance(expr.get("value"), int) or not -(1 << 63) <= expr["value"] < (1 << 63):
            fail("invalid_integer_literal", f"{where} is not a checked Int literal", where=where)
    elif kind == "bool":
        if result_type != "Bool" or not isinstance(expr.get("value"), bool):
            fail("invalid_boolean_literal", f"{where} is not a checked Bool literal", where=where)
    elif kind == "unit":
        if result_type != "Unit":
            fail("invalid_unit_literal", f"{where} is not Unit", where=where)
    elif kind == "str":
        if result_type != "Str" or not isinstance(expr.get("bytes"), list) or any(not isinstance(item, int) or not 0 <= item <= 255 for item in expr["bytes"]):
            fail("invalid_utf8_literal", f"{where} is not an explicit byte string", where=where)
        try:
            bytes(expr["bytes"]).decode("utf-8")
        except UnicodeDecodeError:
            fail("invalid_utf8_literal", f"{where} is not valid UTF-8", where=where)
    elif kind == "param_ref":
        binding_id = checked_id(expr.get("binding_id"), f"{where}.binding_id")
        if binding_id not in bindings:
            fail("unknown_binding_identity", f"{where} references an unknown binding", binding_id=binding_id)
        if result_type != bindings[binding_id]:
            fail("binding_type_mismatch", f"{where} type disagrees with binding", binding_id=binding_id)
    elif kind == "binary":
        op = expr.get("op")
        if op not in {"+", "-", "*", "/", "==", "<"}:
            fail("unsupported_binary_operator", f"{where} uses unsupported operator", op=op)
        left = validate_expr(expr.get("left"), known, bindings, functions, seen, features, where + ".left", type_declarations)
        right = validate_expr(expr.get("right"), known, bindings, functions, seen, features, where + ".right", type_declarations)
        if op in {"+", "-", "*", "/"} and (left != "Int" or right != "Int" or result_type != "Int"):
            fail("binary_type_mismatch", f"{where} arithmetic operands are not Int", where=where)
        if op in {"==", "<"} and (left != right or result_type != "Bool"):
            fail("binary_type_mismatch", f"{where} comparison types are inconsistent", where=where)
    elif kind == "call":
        target = checked_id(expr.get("target"), f"{where}.target")
        if target not in functions:
            fail("missing_function_target", f"{where} target is absent from checked function table", target=target)
        args = expr.get("args")
        if not isinstance(args, list) or len(args) != len(functions[target]["parameters"]):
            fail("call_arity_mismatch", f"{where} argument count disagrees with target", target=target)
        for index, (arg, param) in enumerate(zip(args, functions[target]["parameters"])):
            actual = validate_expr(arg, known, bindings, functions, seen, features, f"{where}.args[{index}]", type_declarations)
            if actual != param["type"]:
                fail("call_type_mismatch", f"{where} argument type disagrees with target", target=target, index=index)
        if result_type != functions[target]["return_type"]:
            fail("call_return_type_mismatch", f"{where} return type disagrees with target", target=target)
    elif kind == "record":
        declaration = next((item for item in type_declarations if item["id"] == result_type), None)
        if declaration is None or declaration["kind"] != "record":
            fail("invalid_nominal_type", f"{where} is not a record type", type=result_type)
        fields = expr.get("fields")
        expected = {field["id"]: field["type"] for field in declaration["fields"]}
        if not isinstance(fields, dict) or set(fields) != set(expected):
            fail("incorrect_field_count", f"{where} does not provide exactly the declared fields", type=result_type)
        for field_id, field_expr in fields.items():
            actual = validate_expr(field_expr, known, bindings, functions, seen, features, f"{where}.fields.{field_id}", type_declarations)
            if actual != expected[field_id]:
                fail("field_type_mismatch", f"{where} field type disagrees", field_id=field_id)
    elif kind == "field_access":
        target_type = expr.get("target_type")
        if not isinstance(target_type, str) or target_type not in known:
            fail("invalid_nominal_type", f"{where} has no checked record target", type=target_type)
        target = validate_expr(expr.get("target"), known, bindings, functions, seen, features, where + ".target", type_declarations)
        if target != target_type:
            fail("field_target_type_mismatch", f"{where} target type disagrees", expected=target_type, actual=target)
        declaration = next((item for item in type_declarations if item["id"] == target_type), None)
        field = next((item for item in declaration["fields"] if item["id"] == expr.get("field_id")), None) if declaration else None
        if field is None or result_type != field["type"]:
            fail("unknown_field_identity", f"{where} field identity is absent or has the wrong type", field_id=expr.get("field_id"))
    elif kind == "list":
        if result_type != "List[Int]" or not isinstance(expr.get("items"), list):
            fail("invalid_list_literal", f"{where} is not a checked Int list", where=where)
        for index, item in enumerate(expr["items"]):
            if validate_expr(item, known, bindings, functions, seen, features, f"{where}.items[{index}]", type_declarations) != "Int":
                fail("list_element_type_mismatch", f"{where} list item is not Int", index=index)
    elif kind == "list_sum":
        if result_type != "Int" or validate_expr(expr.get("target"), known, bindings, functions, seen, features, where + ".target", type_declarations) != "List[Int]":
            fail("list_sum_type_mismatch", f"{where} does not sum a checked Int list", where=where)
    elif kind == "constructor":
        declaration = next((item for item in type_declarations if item["id"] == result_type and item["kind"] == "union"), None)
        constructor_id = checked_id(expr.get("constructor_id"), f"{where}.constructor_id")
        constructor = next((item for item in declaration["constructors"] if item["id"] == constructor_id), None) if declaration else None
        if constructor is None:
            fail("unknown_constructor_identity", f"{where} references an unknown constructor", constructor_id=constructor_id)
        fields = expr.get("fields")
        expected = {field["id"]: field["type"] for field in constructor["fields"]}
        if not isinstance(fields, dict) or set(fields) != set(expected):
            fail("constructor_arity_mismatch", f"{where} does not provide the declared constructor payload", constructor_id=constructor_id)
        for field_id, field_expr in fields.items():
            actual = validate_expr(field_expr, known, bindings, functions, seen, features, f"{where}.fields.{field_id}", type_declarations)
            if actual != expected[field_id]:
                fail("constructor_field_type_mismatch", f"{where} constructor payload type disagrees", field_id=field_id)
    elif kind == "match":
        if not isinstance(expr.get("arms"), list) or not expr["arms"]:
            fail("incomplete_match_information", f"{where} lacks checked match arms")
    return result_type


def validate_manifest(manifest: Any, expected_revision: str | None = None) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        fail("manifest_shape", "manifest root must be an object")
    required = {"schema_version", "fixture_id", "entry_function", "source", "pep_source", "functions", "types", "ownership", "potential_failures", "supported_features", "expected"}
    if set(manifest) != required:
        fail("manifest_keys", "manifest keys are not exact", missing=sorted(required - set(manifest)), extra=sorted(set(manifest) - required))
    if manifest["schema_version"] != SCHEMA_VERSION:
        fail("unsupported_fixture_schema", "unsupported artifact schema", schema_version=manifest["schema_version"])
    checked_id(manifest["fixture_id"], "fixture_id")
    source = manifest["source"]
    if not isinstance(source, dict) or set(source) != {"document_id", "revision", "span"}:
        fail("source_provenance", "source provenance is incomplete")
    checked_id(source["document_id"], "source.document_id")
    if not isinstance(source["revision"], str) or not source["revision"].startswith("sha256:"):
        fail("source_provenance", "source revision must be a sha256 commitment")
    checked_span(source["span"], "source.span")
    if expected_revision is not None and source["revision"] != expected_revision:
        fail("source_revision_conflict", "source revision does not match requested revision", expected=expected_revision, actual=source["revision"])
    if not isinstance(manifest["pep_source"], str):
        fail("pep_source_shape", "pep_source must be text")
    known: set[str] = set()
    declarations = manifest["types"]
    for declaration in declarations:
        if not isinstance(declaration, dict) or not isinstance(declaration.get("id"), str):
            fail("type_declaration_shape", "types must be exact declaration objects")
        type_id = checked_id(declaration["id"], "type.id")
        if type_id in known:
            fail("duplicate_type_identity", "duplicate type identity", type_id=type_id)
        known.add(type_id)
    for declaration in declarations:
        type_id = declaration["id"]
        if declaration.get("kind") == "record":
            if set(declaration) != {"id", "kind", "fields"} or not isinstance(declaration["fields"], list):
                fail("type_declaration_shape", "record declarations are incomplete", type_id=type_id)
            members = declaration["fields"]
            member_ids: set[str] = set()
            for field in members:
                if not isinstance(field, dict) or set(field) != {"id", "name", "type"}:
                    fail("field_shape", "record field facts are incomplete", type_id=type_id)
                field_id = checked_id(field["id"], "field.id")
                if field_id in member_ids:
                    fail("duplicate_field_identity", "duplicate field identity", field_id=field_id)
                member_ids.add(field_id)
                checked_type(field["type"], known, "field.type")
        elif declaration.get("kind") == "union":
            if set(declaration) != {"id", "kind", "constructors"} or not isinstance(declaration["constructors"], list):
                fail("type_declaration_shape", "union declarations are incomplete", type_id=type_id)
            constructor_ids: set[str] = set()
            for constructor in declaration["constructors"]:
                if not isinstance(constructor, dict) or set(constructor) != {"id", "name", "fields"} or not isinstance(constructor["fields"], list):
                    fail("constructor_shape", "union constructor facts are incomplete", type_id=type_id)
                constructor_id = checked_id(constructor["id"], "constructor.id")
                if constructor_id in constructor_ids:
                    fail("duplicate_constructor_identity", "duplicate constructor identity", constructor_id=constructor_id)
                constructor_ids.add(constructor_id)
                field_ids: set[str] = set()
                for field in constructor["fields"]:
                    if not isinstance(field, dict) or set(field) != {"id", "name", "type"}:
                        fail("field_shape", "constructor field facts are incomplete", constructor_id=constructor_id)
                    field_id = checked_id(field["id"], "field.id")
                    if field_id in field_ids:
                        fail("duplicate_field_identity", "duplicate constructor field identity", field_id=field_id)
                    field_ids.add(field_id)
                    checked_type(field["type"], known, "constructor.field.type")
            continue
        else:
            fail("unsupported_type_declaration", "only record and union declarations are accepted", type_id=type_id)
        member_ids: set[str] = set()
        for field in members:
            if not isinstance(field, dict) or set(field) != {"id", "name", "type"}:
                fail("field_shape", "record/constructor field facts are incomplete", type_id=type_id)
            field_id = checked_id(field["id"], "field.id")
            if field_id in member_ids:
                fail("duplicate_field_identity", "duplicate field identity", field_id=field_id)
            member_ids.add(field_id)
            checked_type(field["type"], known, "field.type")
    functions: dict[str, dict[str, Any]] = {}
    for function in manifest["functions"]:
        if not isinstance(function, dict) or set(function) != {"id", "name", "parameters", "return_type", "statements", "result"}:
            fail("function_shape", "function facts are incomplete")
        function_id = checked_id(function["id"], "function.id")
        if function_id in functions:
            fail("duplicate_function_identity", "duplicate function identity", function_id=function_id)
        functions[function_id] = function
    for function_id, function in functions.items():
        checked_id(function["name"], "function.name")
        if not isinstance(function["parameters"], list) or not isinstance(function["statements"], list) or function["statements"]:
            fail("statement_shape", "slice 1 accepts only expression-bodied functions", function_id=function_id)
        bindings: dict[str, str] = {}
        for parameter in function["parameters"]:
            if not isinstance(parameter, dict) or set(parameter) != {"binding_id", "name", "type"}:
                fail("binding_shape", "parameter binding facts are incomplete", function_id=function_id)
            binding_id = checked_id(parameter["binding_id"], "binding_id")
            if binding_id in bindings:
                fail("duplicate_binding_identity", "duplicate binding identity", binding_id=binding_id)
            bindings[binding_id] = checked_type(parameter["type"], known, "parameter.type")
        checked_type(function["return_type"], known, "function.return_type")
    entry = checked_id(manifest["entry_function"], "entry_function")
    if entry not in functions:
        fail("missing_entry_function", "entry function is absent", entry_function=entry)
    features: set[str] = set()
    seen: set[str] = set()
    for function_id, function in functions.items():
        bindings = {parameter["binding_id"]: parameter["type"] for parameter in function["parameters"]}
        actual = validate_expr(function["result"], known, bindings, functions, seen, features, f"functions[{function_id}].result", manifest["types"])
        if actual != function["return_type"]:
            fail("function_result_type_mismatch", "function result does not match declared return type", function_id=function_id)
    declared = manifest["supported_features"]
    if not isinstance(declared, list) or any(feature not in FEATURES for feature in declared) or set(declared) != features:
        fail("feature_set_mismatch", "supported features must exactly describe checked expression tags", declared=declared, observed=sorted(features))
    if not isinstance(manifest["potential_failures"], list) or any(failure not in FAILURES for failure in manifest["potential_failures"]):
        fail("failure_set_shape", "potential failures are not from the closed set")
    expected = manifest["expected"]
    if not isinstance(expected, dict) or set(expected) != {"status", "value", "error", "interpreter_comparable", "value_encoding"} or expected["status"] not in {"success", "runtime_error"} or expected["value_encoding"] not in {"plain", "utf8_hex"} or not isinstance(expected["interpreter_comparable"], bool):
        fail("expected_shape", "expected outcome facts are incomplete")
    ownership = manifest["ownership"]
    if not isinstance(ownership, dict) or set(ownership) != {"parameters", "results", "lifetimes"} or not isinstance(ownership["parameters"], dict) or not isinstance(ownership["results"], dict) or not isinstance(ownership["lifetimes"], list):
        fail("missing_ownership_annotation", "ownership facts are incomplete")
    for function_id in functions:
        if function_id not in ownership["results"]:
            fail("missing_ownership_annotation", "function result has no ownership fact", function_id=function_id)
    return manifest


def load_manifest(path: Path, expected_revision: str | None = None) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail("manifest_read", f"cannot read manifest: {exc}", path=str(path))
    return validate_manifest(raw, expected_revision)


def c_type(type_name: str, nominal_types: set[str] | None = None) -> str:
    try:
        return {"Int": "int64_t", "Bool": "bool", "Str": "pep_str", "Unit": "pep_unit", "List[Int]": "pep_i64_list"}[type_name]
    except KeyError:
        if nominal_types and type_name in nominal_types:
            return symbol("type", type_name)
        fail("unsupported_type", "artifact generator has no C representation for type", type=type_name)


def symbol(prefix: str, identity: str) -> str:
    return f"pep_a05_{prefix}_{hashlib.sha256(identity.encode()).hexdigest()[:16]}"


def emit_expr(expr: dict[str, Any], names: dict[str, str], symbols: dict[str, str], returns: dict[str, str], lines: list[str], counter: list[int], nominal_types: set[str], type_declarations: list[dict[str, Any]]) -> str:
    kind = expr["kind"]
    if kind == "int":
        return f"INT64_C({expr['value']})"
    if kind == "bool":
        return "true" if expr["value"] else "false"
    if kind == "unit":
        return "(pep_unit){ 0 }"
    if kind == "str":
        target = f"value_{counter[0] + 1}"
        raw = ", ".join(str(item) for item in expr["bytes"]) or "0"
        length = len(expr["bytes"])
        lines.extend([f"    static const unsigned char bytes_{counter[0] + 1}[] = {{ {raw} }};", f"    pep_str {target};", f"    pep_status status_{counter[0] + 1} = pep_str_from_bytes(bytes_{counter[0] + 1}, {length}, &{target});", f"    if (status_{counter[0] + 1} != PEP_OK) return status_{counter[0] + 1};"])
        counter[0] += 1
        return target
    if kind == "param_ref":
        return names[expr["binding_id"]]
    counter[0] += 1
    number = counter[0]
    status_name = f"status_{number}"
    if kind == "binary":
        left = emit_expr(expr["left"], names, symbols, returns, lines, counter, nominal_types, type_declarations)
        right = emit_expr(expr["right"], names, symbols, returns, lines, counter, nominal_types, type_declarations)
        if expr["op"] in {"==", "<"}:
            target = f"value_{number}"
            lines.append(f"    bool {target} = ({left} {expr['op']} {right});")
            return target
        target = f"value_{number}"
        helper = {"+": "pep_checked_add", "-": "pep_checked_sub", "*": "pep_checked_mul", "/": "pep_checked_div"}[expr["op"]]
        lines.extend([f"    int64_t {target} = 0;", f"    pep_status {status_name} = {helper}({left}, {right}, &{target});", f"    if ({status_name} != PEP_OK) return {status_name};"])
        return target
    if kind == "call":
        target = f"result_{number}"
        lines.append(f"    {c_type(returns[expr['target']], nominal_types)} {target};")
        args = [emit_expr(arg, names, symbols, returns, lines, counter, nominal_types, type_declarations) for arg in expr["args"]]
        lines.extend([f"    pep_status {status_name} = {symbols[expr['target']]}({', '.join(args + [f'&{target}'])});", f"    if ({status_name} != PEP_OK) return {status_name};"])
        return target
    if kind == "record":
        counter[0] += 1
        target = f"record_{counter[0]}"
        lines.append(f"    {c_type(expr['type'], nominal_types)} {target};")
        declaration = next(item for item in type_declarations if item["id"] == expr["type"])
        values = expr["fields"]
        for field in declaration["fields"]:
            value = emit_expr(values[field["id"]], names, symbols, returns, lines, counter, nominal_types, type_declarations)
            lines.append(f"    {target}.{symbol('field', field['id'])} = {value};")
        return target
    if kind == "field_access":
        target = emit_expr(expr["target"], names, symbols, returns, lines, counter, nominal_types, type_declarations)
        return f"{target}.{symbol('field', expr['field_id'])}"
    if kind == "list":
        counter[0] += 1
        target = f"list_{counter[0]}"
        values = [emit_expr(item, names, symbols, returns, lines, counter, nominal_types, type_declarations) for item in expr["items"]]
        raw = ", ".join(values) or "0"
        lines.extend([f"    static const int64_t items_{counter[0]}[] = {{ {raw} }};", f"    pep_i64_list {target} = {{ 0 }};", f"    pep_status status_{counter[0]} = pep_list_from_array(items_{counter[0]}, {len(values)}, &{target});", f"    if (status_{counter[0]} != PEP_OK) return status_{counter[0]};"])
        return target
    if kind == "list_sum":
        target = emit_expr(expr["target"], names, symbols, returns, lines, counter, nominal_types, type_declarations)
        counter[0] += 1
        value = f"value_{counter[0]}"
        status_name = f"status_{counter[0]}"
        lines.extend([f"    int64_t {value} = 0;", f"    pep_status {status_name} = pep_list_sum(&{target}, &{value});", f"    pep_list_dispose(&{target});", f"    if ({status_name} != PEP_OK) return {status_name};"])
        return value
    raise AssertionError(kind)


def render_c(manifest: dict[str, Any]) -> str:
    validate_manifest(manifest)
    functions = {function["id"]: function for function in manifest["functions"]}
    type_declarations = [declaration for declaration in manifest["types"] if declaration["kind"] == "record"]
    nominal_types = {declaration["id"] for declaration in type_declarations}
    symbols = {function_id: symbol("fn", function_id) for function_id in functions}
    returns = {function_id: function["return_type"] for function_id, function in functions.items()}
    declarations: list[str] = []
    bodies: list[str] = []
    for function_id in sorted(functions):
        function = functions[function_id]
        parameters = [f"{c_type(parameter['type'], nominal_types)} {symbol('local', parameter['binding_id'])}" for parameter in function["parameters"]]
        signature = ", ".join(parameters + [f"{c_type(function['return_type'], nominal_types)} *out"])
        declarations.append(f"static pep_status {symbols[function_id]}({signature});")
        names = {parameter["binding_id"]: symbol("local", parameter["binding_id"]) for parameter in function["parameters"]}
        lines = [f"static pep_status {symbols[function_id]}({signature}) {{", "    if (out == NULL) return PEP_ERR_RANGE;"]
        result = emit_expr(function["result"], names, symbols, returns, lines, [0], nominal_types, type_declarations)
        lines.extend([f"    *out = {result};", "    return PEP_OK;", "}"])
        bodies.extend(lines)
    entry = functions[manifest["entry_function"]]
    entry_type = entry["return_type"]
    if entry_type == "Int":
        print_value = 'printf("%" PRId64, value);'
    elif entry_type == "Bool":
        print_value = 'printf("%s", value ? "true" : "false");'
    elif entry_type == "Str":
        print_value = 'for (size_t index = 0; index < value.len; ++index) printf("%02x", value.data[index]);'
    else:
        print_value = 'printf("unit");'
    type_lines: list[str] = []
    for declaration in sorted(type_declarations, key=lambda item: item["id"]):
        fields = [f"    {c_type(field['type'], nominal_types)} {symbol('field', field['id'])};" for field in declaration["fields"]]
        type_lines.extend([f"typedef struct {symbol('type', declaration['id'])} {{", *fields, f"}} {symbol('type', declaration['id'])};", ""])
    lines = ["#include \"c23_runtime.h\"", "#include <inttypes.h>", "#include <stdbool.h>", "#include <stdio.h>", "", f"/* fixture={manifest['fixture_id']} generator={GENERATOR_VERSION} */", *type_lines, *declarations, "", *bodies, "", "int main(void) {", f"    {c_type(entry_type, nominal_types)} value;", f"    pep_status status = {symbols[manifest['entry_function']]}(&value);", f"    if (status != PEP_OK) {{ printf(\"ARTIFACT|fixture={manifest['fixture_id']}|status=runtime_error|error=%s\\n\", pep_status_name(status)); return 2; }}", f"    printf(\"ARTIFACT|fixture={manifest['fixture_id']}|status=success|value=\");", f"    {print_value}", '    puts("");', "    return 0;", "}", ""]
    return "\n".join(lines)


def canonical_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    validate_manifest(manifest)
    return (json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def validate_generated_source(source: str, manifest: dict[str, Any]) -> None:
    """Small independent invariants for generated ownership/status obligations."""
    features = set(manifest["supported_features"])
    if "checked_arithmetic" in features and not any(helper in source for helper in ("pep_checked_add", "pep_checked_sub", "pep_checked_mul", "pep_checked_div")):
        fail("missing_checked_status", "arithmetic artifact has no checked runtime helper")
    if "list_sum" in features and "pep_list_dispose(&" not in source:
        fail("missing_cleanup", "list artifact has no deterministic disposal path")
    if "string_literals" in features and "pep_str_from_bytes" not in source:
        fail("missing_string_validation", "string artifact has no UTF-8 validation call")


def generate(manifest_path: Path, output_path: Path, expected_revision: str | None = None) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, expected_revision)
    data = render_c(manifest).replace("\r\n", "\n").encode()
    validate_generated_source(data.decode("utf-8"), manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return {"fixture_id": manifest["fixture_id"], "generator_version": GENERATOR_VERSION, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "output": str(output_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("manifest")
    validate_parser.add_argument("--expected-revision")
    generate_parser = sub.add_parser("generate")
    generate_parser.add_argument("manifest")
    generate_parser.add_argument("output")
    generate_parser.add_argument("--expected-revision")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            result = load_manifest(Path(args.manifest), args.expected_revision)
            print(json.dumps({"fixture_id": result["fixture_id"], "valid": True}, sort_keys=True))
        else:
            print(json.dumps(generate(Path(args.manifest), Path(args.output), args.expected_revision), sort_keys=True))
        return 0
    except FixtureError as exc:
        print(json.dumps(exc.as_dict(), sort_keys=True), file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
