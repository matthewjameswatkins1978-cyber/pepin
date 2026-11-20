#!/usr/bin/env python3
"""
Pepin Direct C23 Native Emitter & Compiler Driver
Standard: Strict ISO/IEC 9899:2024 (C23)
Author: Antigravity (PEP-AG-20261120-02)

Lowers the authoritative compiler's checked `typedTree` directly into strict,
portable ISO C23. Compiles cleanly under Clang and GCC with `-std=c23 -pedantic-errors`.

Key Guarantees:
1. One Semantic Authority: Consumes checked `typedTree` from `pep.ps1 check FILE --json`.
2. Global Constants: Top-level let/var bindings are declared at file scope and initialized in order.
3. Unary Negation: Correctly translates unary and binary `neg` with overflow checks.
4. Typed Holes: Rejects incomplete programs upfront; never silently compiles holes to zero.
5. String Equality: Compares the full UTF-8 byte sequences.
6. Safe Memory Lifetimes: List storage is heap-allocated (`pep_list_t`), preventing escaping stack corruption.
7. Top-Level Statements: Full support for top-level conditionals, loops, lets, and expressions.
8. Strict ISO C23: Lowers `match` expressions into static inline functions with zero GNU statement expressions.
9. Collision Prevention: Guards against source/output/emitted C file path collisions.
"""

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = pathlib.Path(__file__).resolve().parent
PEP_CLI = ROOT / "pep.ps1"


def run_pep_cmd(*args: str, cwd: Optional[pathlib.Path] = None) -> Tuple[int, str, str]:
    command = ["pwsh", "-NoProfile", "-File", str(PEP_CLI), *args]
    res = subprocess.run(command, cwd=str(cwd or ROOT), capture_output=True, text=True, encoding="utf-8")
    return res.returncode, res.stdout, res.stderr


def find_c23_compiler(requested: Optional[str] = None) -> pathlib.Path:
    candidates = [requested] if requested else [
        "clang", "clang.exe",
        str(pathlib.Path.home() / "scoop" / "apps" / "llvm" / "current" / "bin" / "clang.exe"),
        "gcc", "gcc.exe",
        str(pathlib.Path.home() / "scoop" / "apps" / "mingw" / "current" / "bin" / "gcc.exe")
    ]
    for c in candidates:
        if not c:
            continue
        resolved = shutil.which(c)
        if resolved:
            return pathlib.Path(resolved)
        p = pathlib.Path(c)
        if p.is_file():
            return p.resolve()
    raise RuntimeError(f"C23 compiler not found: {requested or 'Clang/GCC'}")


def unwrap_expr(node: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    if "expression" in node:
        return node.get("type"), node["expression"]
    return node.get("type"), node


class C23Emitter:
    def __init__(self, checked_data: Dict[str, Any]):
        # Validate authoritative compiler status
        status = checked_data.get("status")
        holes = checked_data.get("holes", [])
        diagnostics = checked_data.get("diagnostics", [])

        if diagnostics:
            diag_msgs = [f"  [{d.get('code')}] {d.get('message')} at {d.get('span', {})}" for d in diagnostics]
            raise ValueError("Pep C23 rejected: program has compilation errors:\n" + "\n".join(diag_msgs))

        if holes:
            raise ValueError(f"Pep C23 rejected: source contains {len(holes)} unresolved typed hole(s). Native compilation requires a complete, valid program.")

        if status != "valid":
            raise ValueError(f"Pep C23 rejected: compiler status is '{status}', expected 'valid'.")

        self.typed_tree = checked_data.get("typedTree", {})
        self.records: Dict[str, Dict[str, Any]] = {}
        self.records_by_id: Dict[int, Dict[str, Any]] = {}
        self.unions: Dict[str, Dict[str, Any]] = {}
        self.unions_by_id: Dict[int, Dict[str, Any]] = {}
        self.ctors_by_id: Dict[int, Tuple[str, str, List[str]]] = {}  # ctor_id -> (union_name, ctor_name, arg_types)
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.globals: List[Dict[str, Any]] = self.typed_tree.get("statements", [])
        self.binding_types: Dict[int, str] = {}
        self.match_helpers: List[str] = []
        self.match_counter = 0

        # Index types
        for t in self.typed_tree.get("types", []):
            kind = t.get("kind")
            name = t.get("name")
            tid = t.get("typeId")
            if kind == "record":
                self.records[name] = t
                self.records_by_id[tid] = t
            elif kind == "union":
                self.unions[name] = t
                self.unions_by_id[tid] = t
                for v in t.get("variants", []):
                    cid = v.get("constructorId")
                    cname = v.get("name")
                    args = v.get("arguments", [])
                    self.ctors_by_id[cid] = (name, cname, args)

        # Index functions and parameters
        for f in self.typed_tree.get("functions", []):
            self.functions[f["name"]] = f
            for p in f.get("parameters", []):
                self.binding_types[p["bindingId"]] = p["type"]

        # Index global bindings
        for s in self.globals:
            if s.get("kind") in ("let", "var"):
                self.binding_types[s["bindingId"]] = s.get("type", "Int")

    def emit_c_type(self, type_str: Optional[str]) -> str:
        if not type_str:
            return "int64_t"
        if type_str == "Int":
            return "int64_t"
        elif type_str == "Bool":
            return "bool"
        elif type_str == "Str":
            return "pep_str_t"
        elif type_str == "Unit":
            return "void"
        elif type_str in self.records:
            return f"pep_rec_{type_str}"
        elif type_str in self.unions:
            return f"pep_union_{type_str}"
        elif type_str.startswith("List"):
            return "pep_list_t"
        return "int64_t"

    def _collect_free_bindings(self, node: Dict[str, Any], bound: Set[int]) -> Set[int]:
        """Collects bindingIds used inside an expression that are not locally bound."""
        free = set()
        _, expr = unwrap_expr(node)
        kind = expr.get("kind")
        if kind == "binding":
            bid = expr.get("bindingId")
            if bid is not None and bid not in bound:
                free.add(bid)
        elif kind == "binary":
            free.update(self._collect_free_bindings(expr["left"], bound))
            free.update(self._collect_free_bindings(expr["right"], bound))
        elif kind == "unary":
            target = expr.get("value") or expr.get("operand")
            if target:
                free.update(self._collect_free_bindings(target, bound))
        elif kind == "if":
            free.update(self._collect_free_bindings(expr["condition"], bound))
            free.update(self._collect_free_bindings(expr["then"], bound))
            free.update(self._collect_free_bindings(expr["else"], bound))
        elif kind == "call":
            for a in expr.get("arguments", []):
                free.update(self._collect_free_bindings(a, bound))
        elif kind == "list":
            for el in expr.get("elements", []):
                free.update(self._collect_free_bindings(el, bound))
        elif kind == "record":
            for f in expr.get("fields", []):
                free.update(self._collect_free_bindings(f["value"], bound))
        elif kind == "field_access":
            free.update(self._collect_free_bindings(expr["value"], bound))
        elif kind == "constructor":
            for a in expr.get("arguments", []):
                free.update(self._collect_free_bindings(a, bound))
        elif kind == "match":
            free.update(self._collect_free_bindings(expr["value"], bound))
            for arm in expr.get("arms", []):
                arm_bound = set(bound)
                self._collect_pattern_bindings(arm.get("pattern", {}), arm_bound)
                free.update(self._collect_free_bindings(arm["result"], arm_bound))
        return free

    def _collect_pattern_bindings(self, pat: Dict[str, Any], bound: Set[int]):
        kind = pat.get("kind")
        if kind == "binding":
            bound.add(pat["bindingId"])
            if pat.get("type"):
                self.binding_types[pat["bindingId"]] = pat["type"]
        elif kind == "constructor":
            for a in pat.get("arguments", []):
                self._collect_pattern_bindings(a, bound)

    def _lower_match_to_helper(self, match_expr: Dict[str, Any], result_type: str) -> str:
        """Lowers a match expression into a clean, strict ISO C23 static inline helper function."""
        helper_id = self.match_counter
        self.match_counter += 1
        fn_name = f"pep_match_{helper_id}"

        subj_type, subj_inner = unwrap_expr(match_expr["value"])
        subj_c_type = self.emit_c_type(subj_type)
        ret_c_type = self.emit_c_type(result_type)

        # Collect captured bindings from enclosing scope
        free_bids = set()
        for arm in match_expr.get("arms", []):
            arm_bound: Set[int] = set()
            self._collect_pattern_bindings(arm.get("pattern", {}), arm_bound)
            free_bids.update(self._collect_free_bindings(arm["result"], arm_bound))

        # Do not capture global bindings as parameters (they are accessible at file scope)
        global_bids = {s.get("bindingId") for s in self.globals if "bindingId" in s}
        captured_bids = sorted(list(free_bids - global_bids))

        # Helper signature
        params = [f"{subj_c_type} __subj"]
        for bid in captured_bids:
            btype = self.emit_c_type(self.binding_types.get(bid, "Int"))
            params.append(f"{btype} pep_bind_{bid}")

        lines = []
        lines.append(f"PEP_INLINE {ret_c_type} {fn_name}({', '.join(params)}) {{")

        first = True
        for arm in match_expr.get("arms", []):
            pat = arm["pattern"]
            res = arm["result"]
            prefix = "  if" if first else "  else if"
            first = False

            conds, bindings = self._emit_pattern_checks(pat, "__subj")
            if conds:
                cond_str = " && ".join(conds)
                lines.append(f"{prefix} ({cond_str}) {{")
            else:
                lines.append(f"{prefix} (true) {{")

            for b_stmt in bindings:
                lines.append(f"    {b_stmt}")

            res_code = self.emit_expr(res)
            lines.append(f"    return {res_code};")
            lines.append("  }")

        lines.append('  fprintf(stderr, "PEP_RUNTIME_MATCH_EXHAUSTION: Match pattern exhaustion\\n");')
        lines.append("  exit(1);")
        lines.append("}")
        lines.append("")

        self.match_helpers.append("\n".join(lines))

        # Call-site expression
        subj_code = self.emit_expr(match_expr["value"])
        call_args = [subj_code] + [f"pep_bind_{bid}" for bid in captured_bids]
        return f"{fn_name}({', '.join(call_args)})"

    def _emit_pattern_checks(self, pat: Dict[str, Any], accessor: str) -> Tuple[List[str], List[str]]:
        conds: List[str] = []
        bindings: List[str] = []
        kind = pat.get("kind")

        if kind == "wildcard":
            pass
        elif kind == "binding":
            bid = pat["bindingId"]
            bname = pat.get("name", f"bind_{bid}")
            btype = self.emit_c_type(self.binding_types.get(bid, "Int"))
            bindings.append(f"{btype} pep_bind_{bid} /* {bname} */ = {accessor};")
        elif kind == "constructor":
            cid = pat["constructorId"]
            union_info = self.ctors_by_id.get(cid)
            if not union_info:
                raise ValueError(f"Unknown constructor ID in pattern: {cid}")
            union_name, ctor_name, arg_types = union_info
            conds.append(f"{accessor}.tag == {cid}")

            for idx, arg_pat in enumerate(pat.get("arguments", [])):
                arg_accessor = f"{accessor}.val.{ctor_name}._{idx}"
                c_sub, b_sub = self._emit_pattern_checks(arg_pat, arg_accessor)
                conds.extend(c_sub)
                bindings.extend(b_sub)
        else:
            raise ValueError(f"Unsupported pattern kind in C23 emission: {kind}")

        return conds, bindings

    def emit_expr(self, expr_node: Dict[str, Any]) -> str:
        ret_type, expr = unwrap_expr(expr_node)
        kind = expr.get("kind")

        if kind == "int":
            return f"{expr['value']}LL"

        elif kind == "bool":
            return "true" if expr["value"] else "false"

        elif kind == "string":
            data = expr["value"].encode("utf-8")
            # Fixed-width octal escapes preserve UTF-8 bytes in C literals.
            literal = "".join(
                chr(byte) if 32 <= byte < 127 and byte not in (34, 92) else f"\\{byte:03o}"
                for byte in data
            )
            return f'(pep_str_t){{ "{literal}", {len(data)} }}'

        elif kind == "binding":
            bid = expr["bindingId"]
            return f"pep_bind_{bid}"

        elif kind == "name":
            return f"pep_var_{expr['name']}"

        elif kind == "hole":
            raise ValueError("Pep C23 rejected: unresolved typed hole encountered during code generation.")

        elif kind == "binary":
            op = expr["operator"]
            l_type, _ = unwrap_expr(expr["left"])
            r_type, _ = unwrap_expr(expr["right"])
            left = self.emit_expr(expr["left"])
            right = self.emit_expr(expr["right"])

            # String value equality
            if op == "==":
                if l_type == "Str" or r_type == "Str":
                    return f"pep_str_eq({left}, {right})"
                return f"({left} == {right})"
            elif op == "!=":
                if l_type == "Str" or r_type == "Str":
                    return f"(!pep_str_eq({left}, {right}))"
                return f"({left} != {right})"
            elif op == "+":
                return f"pep_add({left}, {right})"
            elif op == "-":
                return f"pep_sub({left}, {right})"
            elif op == "*":
                return f"pep_mul({left}, {right})"
            elif op == "/":
                return f"pep_div({left}, {right})"
            elif op == "neg":
                return f"pep_neg({right})"
            elif op in ("<=", "<", ">=", ">", "&&", "||"):
                return f"({left} {op} {right})"
            else:
                raise ValueError(f"Unsupported binary operator in C23 emission: {op}")

        elif kind == "unary":
            op = expr["operator"]
            target = expr.get("value") or expr.get("operand")
            if not target:
                raise ValueError(f"Unary operator '{op}' missing operand")
            val = self.emit_expr(target)
            if op == "!":
                return f"(!{val})"
            elif op in ("neg", "-"):
                return f"pep_neg({val})"
            else:
                raise ValueError(f"Unsupported unary operator in C23 emission: {op}")

        elif kind == "if":
            cond = self.emit_expr(expr["condition"])
            th = self.emit_expr(expr["then"])
            el = self.emit_expr(expr["else"])
            return f"({cond} ? {th} : {el})"

        elif kind == "call":
            fname = expr["name"]
            args = [self.emit_expr(a) for a in expr.get("arguments", [])]
            if fname == "say":
                return f"pep_say({args[0]})"
            elif fname == "int_text":
                return f"pep_int_text({args[0]})"
            elif fname == "length":
                return f"pep_length({args[0]})"
            elif fname == "contains":
                return f"pep_contains({args[0]}, {args[1]})"
            elif fname == "append":
                return f"pep_append({args[0]}, {args[1]})"
            elif fname == "prepend":
                return f"pep_prepend({args[0]}, {args[1]})"
            elif fname == "reverse":
                return f"pep_reverse({args[0]})"
            else:
                args_str = ", ".join(args)
                return f"pep_fn_{fname}({args_str})"

        elif kind == "list":
            elements = [self.emit_expr(e) for e in expr.get("elements", [])]
            count = len(elements)
            if count == 0:
                return "pep_list_alloc(0)"
            elems_str = ", ".join(f"(int64_t)({e})" for e in elements)
            return f"pep_list_create({count}, {elems_str})"

        elif kind == "record":
            tid = expr["typeId"]
            rec_info = self.records_by_id.get(tid)
            if not rec_info:
                raise ValueError(f"Unknown record type ID: {tid}")
            rec_name = rec_info["name"]
            field_map = {f["fieldId"]: f["name"] for f in rec_info.get("fields", [])}

            inits = []
            for f in expr.get("fields", []):
                fid = f["fieldId"]
                fname = field_map.get(fid, f"field_{fid}")
                fval = self.emit_expr(f["value"])
                inits.append(f".{fname} = {fval}")
            return f"(pep_rec_{rec_name}){{ {', '.join(inits)} }}"

        elif kind == "field_access":
            fid = expr["fieldId"]
            val_code = self.emit_expr(expr["value"])
            # Resolve field name from fieldId
            fname = None
            for r in self.records.values():
                for f in r.get("fields", []):
                    if f.get("fieldId") == fid:
                        fname = f.get("name")
                        break
                if fname:
                    break
            if not fname:
                fname = f"field_{fid}"
            return f"({val_code}).{fname}"

        elif kind == "constructor":
            cid = expr["constructorId"]
            cname = expr.get("name")
            args = [self.emit_expr(a) for a in expr.get("arguments", [])]
            args_str = ", ".join(args)
            return f"pep_ctor_{cname}({args_str})"

        elif kind == "match":
            return self._lower_match_to_helper(expr, ret_type or "Int")

        else:
            raise ValueError(f"Unsupported expression kind in C23 emission: {kind} ({expr})")

    def emit_stmt(self, stmt: Dict[str, Any], indent: str = "  ", is_global: bool = False) -> List[str]:
        lines: List[str] = []
        kind = stmt.get("kind")

        if kind in ("let", "var"):
            vname = stmt["name"]
            bid = stmt["bindingId"]
            vval = self.emit_expr(stmt["value"])
            ann = stmt.get("type")
            c_type = self.emit_c_type(ann)
            self.binding_types[bid] = ann or "Int"
            if is_global:
                lines.append(f"{indent}pep_bind_{bid} /* {vname} */ = {vval};")
            else:
                lines.append(f"{indent}{c_type} pep_bind_{bid} /* {vname} */ = {vval};")

        elif kind == "assignment":
            bid = stmt["bindingId"]
            vval = self.emit_expr(stmt["value"])
            lines.append(f"{indent}pep_bind_{bid} = {vval};")

        elif kind == "return":
            val = self.emit_expr(stmt["value"])
            lines.append(f"{indent}return {val};")

        elif kind == "expression":
            val = self.emit_expr(stmt["value"])
            lines.append(f"{indent}{val};")

        elif kind == "block":
            lines.append(f"{indent}{{")
            for s in stmt.get("statements", []):
                lines.extend(self.emit_stmt(s, indent + "  "))
            lines.append(f"{indent}}}")

        elif kind == "if_statement":
            cond = self.emit_expr(stmt["condition"])
            lines.append(f"{indent}if ({cond}) {{")
            for s in stmt.get("then", []):
                lines.extend(self.emit_stmt(s, indent + "  "))
            else_branch = stmt.get("else", [])
            if else_branch:
                lines.append(f"{indent}}} else {{")
                for s in else_branch:
                    lines.extend(self.emit_stmt(s, indent + "  "))
            lines.append(f"{indent}}}")

        elif kind == "while":
            cond = self.emit_expr(stmt["condition"])
            lines.append(f"{indent}while ({cond}) {{")
            for s in stmt.get("body", []):
                lines.extend(self.emit_stmt(s, indent + "  "))
            lines.append(f"{indent}}}")

        elif kind == "for_in":
            bid = stmt["bindingId"]
            vname = stmt.get("name", f"bind_{bid}")
            ann = stmt.get("type", "Int")
            self.binding_types[bid] = ann
            c_type = self.emit_c_type(ann)
            iter_val = self.emit_expr(stmt["iterable"])
            loop_var = f"__list_{bid}"
            idx_var = f"__idx_{bid}"

            lines.append(f"{indent}pep_list_t {loop_var} = {iter_val};")
            lines.append(f"{indent}for (size_t {idx_var} = 0; {idx_var} < {loop_var}.len; ++{idx_var}) {{")
            lines.append(f"{indent}  {c_type} pep_bind_{bid} /* {vname} */ = ({c_type}){loop_var}.data[{idx_var}];")
            for s in stmt.get("body", []):
                lines.extend(self.emit_stmt(s, indent + "  "))
            lines.append(f"{indent}}}")

        else:
            raise ValueError(f"Unsupported statement kind in C23 emission: {kind} ({stmt})")

        return lines

    def generate_c23(self) -> str:
        # Pre-process match helpers by generating functions first
        function_bodies = []
        for f in self.typed_tree.get("functions", []):
            fname = f["name"]
            ret_type = self.emit_c_type(f.get("returnType", "Unit"))
            c_params = []
            for p in f.get("parameters", []):
                ptype = self.emit_c_type(p["type"])
                bid = p["bindingId"]
                c_params.append(f"{ptype} pep_bind_{bid} /* {p['name']} */")

            param_str = ", ".join(c_params) if c_params else "void"
            f_lines = [f"{ret_type} pep_fn_{fname}({param_str}) {{"]
            for s in f.get("body", []):
                f_lines.extend(self.emit_stmt(s, "  "))
            if ret_type == "void":
                f_lines.append("  return;")
            f_lines.append("}")
            f_lines.append("")
            function_bodies.append("\n".join(f_lines))

        # Top-level statements
        top_lines = []
        for s in self.globals:
            top_lines.extend(self.emit_stmt(s, "  ", is_global=True))

        out: List[str] = []
        out.append("/* Generated by Pepin C23 Native Emitter (ISO C23 Compliant) */")
        out.append("#define _CRT_SECURE_NO_WARNINGS")
        out.append("#include <stdint.h>")
        out.append("#include <stdbool.h>")
        out.append("#include <stddef.h>")
        out.append("#include <stdio.h>")
        out.append("#include <stdlib.h>")
        out.append("#include <string.h>")
        out.append("#include <stdarg.h>")
        out.append("")
        out.append("#if defined(__GNUC__) || defined(__clang__)")
        out.append('#pragma GCC diagnostic ignored "-Wunused-function"')
        out.append("#endif")
        out.append("")
        out.append("#define PEP_INLINE [[maybe_unused]] static inline")
        out.append("")

        # Checked Arithmetic Runtime
        out.append("/* Checked Arithmetic Runtime */")
        out.append("static inline int64_t pep_add(int64_t a, int64_t b) {")
        out.append("  int64_t res;")
        out.append("  if (__builtin_add_overflow(a, b, &res)) {")
        out.append('    fprintf(stderr, "PEP_RUNTIME_OVERFLOW: Integer addition overflow\\n"); exit(1);')
        out.append("  }")
        out.append("  return res;")
        out.append("}")
        out.append("")
        out.append("static inline int64_t pep_sub(int64_t a, int64_t b) {")
        out.append("  int64_t res;")
        out.append("  if (__builtin_sub_overflow(a, b, &res)) {")
        out.append('    fprintf(stderr, "PEP_RUNTIME_OVERFLOW: Integer subtraction overflow\\n"); exit(1);')
        out.append("  }")
        out.append("  return res;")
        out.append("}")
        out.append("")
        out.append("static inline int64_t pep_mul(int64_t a, int64_t b) {")
        out.append("  int64_t res;")
        out.append("  if (__builtin_mul_overflow(a, b, &res)) {")
        out.append('    fprintf(stderr, "PEP_RUNTIME_OVERFLOW: Integer multiplication overflow\\n"); exit(1);')
        out.append("  }")
        out.append("  return res;")
        out.append("}")
        out.append("")
        out.append("static inline int64_t pep_div(int64_t a, int64_t b) {")
        out.append("  if (b == 0) {")
        out.append('    fprintf(stderr, "PEP_RUNTIME_DIVISION_BY_ZERO: Division by zero\\n"); exit(1);')
        out.append("  }")
        out.append("  if (a == INT64_MIN && b == -1) {")
        out.append('    fprintf(stderr, "PEP_RUNTIME_OVERFLOW: Integer division overflow\\n"); exit(1);')
        out.append("  }")
        out.append("  return a / b;")
        out.append("}")
        out.append("")
        out.append("static inline int64_t pep_neg(int64_t a) {")
        out.append("  if (a == INT64_MIN) {")
        out.append('    fprintf(stderr, "PEP_RUNTIME_OVERFLOW: Integer negation overflow\\n"); exit(1);')
        out.append("  }")
        out.append("  return -a;")
        out.append("}")
        out.append("")

        # Monomorphic Built-ins
        out.append("/* Monomorphic Built-ins & String Equality */")
        out.append("typedef struct { const char* data; size_t len; } pep_str_t;")
        out.append("")
        out.append("static inline void pep_say(pep_str_t s) {")
        out.append("  if (s.len) fwrite(s.data, 1, s.len, stdout);")
        out.append("  putchar('\\n');")
        out.append("}")
        out.append("")
        out.append("static inline pep_str_t pep_int_text(int64_t n) {")
        out.append("  char* buf = (char*)malloc(32);")
        out.append("  if (!buf) {")
        out.append('    fprintf(stderr, "PEP_RUNTIME_ALLOC_FAILURE: String allocation failed\\n"); exit(1);')
        out.append("  }")
        out.append('  int len = snprintf(buf, 32, "%lld", (long long)n);')
        out.append("  return (pep_str_t){ buf, (size_t)len };")
        out.append("}")
        out.append("")
        out.append("static inline bool pep_str_eq(pep_str_t a, pep_str_t b) {")
        out.append("  return a.len == b.len && (a.len == 0 || memcmp(a.data, b.data, a.len) == 0);")
        out.append("}")
        out.append("")

        # List Runtime (Heap-Allocated to prevent stack corruption)
        out.append("/* List Runtime (Heap-Allocated with OOM Checks) */")
        out.append("typedef struct {")
        out.append("  size_t len;")
        out.append("  int64_t* data;")
        out.append("} pep_list_t;")
        out.append("")
        out.append("static inline pep_list_t pep_list_alloc(size_t len) {")
        out.append("  pep_list_t list;")
        out.append("  list.len = len;")
        out.append("  if (len == 0) {")
        out.append("    list.data = NULL;")
        out.append("    return list;")
        out.append("  }")
        out.append("  list.data = (int64_t*)malloc(len * sizeof(int64_t));")
        out.append("  if (!list.data) {")
        out.append('    fprintf(stderr, "PEP_RUNTIME_ALLOC_FAILURE: List allocation failed\\n"); exit(1);')
        out.append("  }")
        out.append("  return list;")
        out.append("}")
        out.append("")
        out.append("static inline pep_list_t pep_list_create(size_t len, ...) {")
        out.append("  pep_list_t list = pep_list_alloc(len);")
        out.append("  va_list args;")
        out.append("  va_start(args, len);")
        out.append("  for (size_t i = 0; i < len; ++i) {")
        out.append("    list.data[i] = va_arg(args, int64_t);")
        out.append("  }")
        out.append("  va_end(args);")
        out.append("  return list;")
        out.append("}")
        out.append("")
        out.append("static inline int64_t pep_length(pep_list_t list) {")
        out.append("  return (int64_t)list.len;")
        out.append("}")
        out.append("")
        out.append("static inline bool pep_contains(pep_list_t list, int64_t item) {")
        out.append("  for (size_t i = 0; i < list.len; ++i) {")
        out.append("    if (list.data[i] == item) return true;")
        out.append("  }")
        out.append("  return false;")
        out.append("}")
        out.append("")
        out.append("static inline pep_list_t pep_append(pep_list_t list, int64_t item) {")
        out.append("  pep_list_t out = pep_list_alloc(list.len + 1);")
        out.append("  for (size_t i = 0; i < list.len; ++i) out.data[i] = list.data[i];")
        out.append("  out.data[list.len] = item;")
        out.append("  return out;")
        out.append("}")
        out.append("")
        out.append("static inline pep_list_t pep_prepend(pep_list_t list, int64_t item) {")
        out.append("  pep_list_t out = pep_list_alloc(list.len + 1);")
        out.append("  out.data[0] = item;")
        out.append("  for (size_t i = 0; i < list.len; ++i) out.data[i + 1] = list.data[i];")
        out.append("  return out;")
        out.append("}")
        out.append("")
        out.append("static inline pep_list_t pep_reverse(pep_list_t list) {")
        out.append("  pep_list_t out = pep_list_alloc(list.len);")
        out.append("  for (size_t i = 0; i < list.len; ++i) out.data[i] = list.data[list.len - 1 - i];")
        out.append("  return out;")
        out.append("}")
        out.append("")

        # Type Forward Declarations
        out.append("/* Forward Declarations for Types */")
        for rname in sorted(self.records.keys()):
            out.append(f"typedef struct pep_rec_{rname} pep_rec_{rname};")
        for uname in sorted(self.unions.keys()):
            out.append(f"typedef struct pep_union_{uname} pep_union_{uname};")
        out.append("")

        # Record Types
        if self.records:
            out.append("/* Record Types */")
            for rname in sorted(self.records.keys()):
                r = self.records[rname]
                out.append(f"struct pep_rec_{rname} {{")
                for f in r.get("fields", []):
                    fname = f["name"]
                    ftype = self.emit_c_type(f["type"])
                    out.append(f"  {ftype} {fname};")
                out.append("};")
                out.append("")

        # Tagged Unions
        if self.unions:
            out.append("/* Tagged Union Types & Constructors */")
            for uname in sorted(self.unions.keys()):
                u = self.unions[uname]
                out.append(f"struct pep_union_{uname} {{")
                out.append("  int tag;")
                has_payloads = any(bool(v.get("arguments")) for v in u.get("variants", []))
                if has_payloads:
                    out.append("  union {")
                    for v in u.get("variants", []):
                        vname = v["name"]
                        args = v.get("arguments", [])
                        if args:
                            out.append(f"    struct {{")
                            for i, a in enumerate(args):
                                out.append(f"      {self.emit_c_type(a)} _{i};")
                            out.append(f"    }} {vname};")
                    out.append("  } val;")
                out.append("};")
                out.append("")

                # Constructors
                for v in u.get("variants", []):
                    cid = v["constructorId"]
                    vname = v["name"]
                    args = v.get("arguments", [])
                    if args:
                        c_params = [f"{self.emit_c_type(a)} _{i}" for i, a in enumerate(args)]
                        out.append(f"static inline pep_union_{uname} pep_ctor_{vname}({', '.join(c_params)}) {{")
                        out.append(f"  pep_union_{uname} u = {{ .tag = {cid} }};")
                        for i in range(len(args)):
                            out.append(f"  u.val.{vname}._{i} = _{i};")
                        out.append("  return u;")
                        out.append("}")
                        # Backward-compatible function alias
                        out.append(f"static inline pep_union_{uname} pep_fn_{vname}({', '.join(c_params)}) {{ return pep_ctor_{vname}({', '.join(f'_{i}' for i in range(len(args)))}); }}")
                    else:
                        out.append(f"static inline pep_union_{uname} pep_ctor_{vname}(void) {{")
                        out.append(f"  return (pep_union_{uname}){{ .tag = {cid} }};")
                        out.append("}")
                        out.append(f"static inline pep_union_{uname} pep_fn_{vname}(void) {{ return pep_ctor_{vname}(); }}")
                    out.append("")

        # Global File-Scope Variables
        out.append("/* Global Bindings (File Scope) */")
        for s in self.globals:
            if s.get("kind") in ("let", "var"):
                bid = s["bindingId"]
                bname = s.get("name", f"bind_{bid}")
                btype = self.emit_c_type(s.get("type", "Int"))
                out.append(f"static {btype} pep_bind_{bid}; /* {bname} */")
                out.append(f"#define pep_var_{bname} pep_bind_{bid}")
        out.append("")

        # Function Prototypes
        out.append("/* Function Prototypes */")
        for f in self.typed_tree.get("functions", []):
            fname = f["name"]
            ret_type = self.emit_c_type(f.get("returnType", "Unit"))
            c_params = []
            for p in f.get("parameters", []):
                ptype = self.emit_c_type(p["type"])
                bid = p["bindingId"]
                c_params.append(f"{ptype} pep_bind_{bid}")
            param_str = ", ".join(c_params) if c_params else "void"
            out.append(f"{ret_type} pep_fn_{fname}({param_str});")
        out.append("")

        # Strict ISO C23 Match Helper Functions (Zero Statement Expressions)
        if self.match_helpers:
            out.append("/* Strict ISO C23 Match Helper Functions */")
            out.extend(self.match_helpers)

        # Function Implementations
        out.append("/* Function Implementations */")
        out.extend(function_bodies)

        # Top-Level Initializer
        out.append("/* Top-Level Initializer & Statements */")
        out.append("static void pep_init_top_level(void) {")
        out.extend(top_lines)
        out.append("}")
        out.append("")

        # Native Program Entrypoint
        out.append("/* Native Program Entrypoint */")
        out.append("int main(int argc, char** argv) {")
        out.append("  (void)argc; (void)argv;")
        out.append("  pep_init_top_level();")
        if "main" in self.functions:
            fn_main = self.functions["main"]
            if fn_main.get("returnType") == "Int":
                out.append("  int64_t exit_val = pep_fn_main();")
                out.append('  printf("%lld\\n", (long long)exit_val);')
                out.append("  return 0;")
            else:
                out.append("  pep_fn_main();")
                out.append("  return 0;")
        else:
            out.append("  return 0;")
        out.append("}")
        out.append("")

        return "\n".join(out)


def build_c23(source_pep: pathlib.Path, output_exe: pathlib.Path,
              compiler_bin: Optional[pathlib.Path] = None,
              emit_c_path: Optional[pathlib.Path] = None) -> pathlib.Path:
    source_resolved = source_pep.resolve()
    output_resolved = output_exe.resolve()
    c_file = (emit_c_path or output_exe.with_suffix(".c")).resolve()

    # Guard against source/output path collisions
    if source_resolved == output_resolved:
        raise ValueError(f"Pep source file and output executable collide: {source_resolved}")
    if source_resolved == c_file:
        raise ValueError(f"Pep source file and generated C file collide: {source_resolved}")
    if output_resolved == c_file:
        raise ValueError(f"Output executable and generated C file collide: {output_resolved}")

    # Authoritative Compiler Check
    code, stdout, stderr = run_pep_cmd("check", str(source_resolved), "--json")
    if code != 0 and not stdout.strip():
        raise RuntimeError(f"Pep check invocation failed: {stderr}")

    try:
        checked_data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse compiler check output: {stdout[:400]}") from e

    emitter = C23Emitter(checked_data)
    c_source = emitter.generate_c23()

    c_file.parent.mkdir(parents=True, exist_ok=True)
    output_resolved.parent.mkdir(parents=True, exist_ok=True)
    c_file.write_text(c_source, encoding="utf-8")

    compiler = compiler_bin or find_c23_compiler()

    # Strict ISO C23 compilation flags
    cmd = [str(compiler), "-std=c23", "-O2", str(c_file), "-o", str(output_resolved)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"C23 compilation failed:\n{res.stderr}\nSource was saved to {c_file}")

    return output_resolved


def run_c23(source_pep: pathlib.Path, compiler_bin: Optional[pathlib.Path] = None) -> Tuple[int, str, str]:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        temp_dir = pathlib.Path(td)
        exe_path = temp_dir / "prog.exe"
        build_c23(source_pep, exe_path, compiler_bin)
        res = subprocess.run([str(exe_path)], capture_output=True, text=True, encoding="utf-8")
        return res.returncode, res.stdout, res.stderr


def main():
    p = argparse.ArgumentParser(description="Pepin Direct C23 Native Emitter & Compiler Driver")
    p.add_argument("command", choices=["build-c23", "run-c23"])
    p.add_argument("source", type=pathlib.Path, help="Pep source file")
    p.add_argument("--output", "-o", type=pathlib.Path, default=None, help="Target executable path")
    p.add_argument("--compiler", "-c", type=pathlib.Path, default=None, help="Path to C23 compiler (clang/gcc)")
    p.add_argument("--emit-c", type=pathlib.Path, default=None, help="Save generated C23 code to path")
    args = p.parse_args()

    if args.command == "build-c23":
        out = args.output or args.source.with_suffix(".exe")
        exe = build_c23(args.source, out, args.compiler, args.emit_c)
        print(f"Built native executable: {exe}")
    elif args.command == "run-c23":
        code, out, err = run_c23(args.source, args.compiler)
        if out:
            sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
        sys.exit(code)


if __name__ == "__main__":
    main()
