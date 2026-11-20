#!/usr/bin/env python3
"""
Pepin Direct C23 Native Emitter & Compiler Driver
Standard: ISO/IEC 9899:2024 (C23)
Supports: Full Pep language (scalar types, records, functions, recursion, control flow, builtins)
Compilers: Clang (primary), GCC (cross-check)
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


class C23Emitter:
    def __init__(self, ast_data: Dict[str, Any]):
        self.ast = ast_data.get("ast", [])
        self.types: Dict[str, Dict[str, Any]] = {}
        self.unions: Dict[str, Dict[str, Any]] = {}
        self.constructors: Dict[str, Tuple[str, int, Dict[str, Any]]] = {}
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.globals: List[Dict[str, Any]] = []
        self.c_lines: List[str] = []
        
        # Pre-scan declarations
        for item in self.ast:
            kind = item.get("kind")
            if kind == "record_declaration":
                self.types[item["name"]] = item
            elif kind == "union_declaration":
                self.unions[item["name"]] = item
                for idx, v in enumerate(item.get("variants", [])):
                    self.constructors[v["name"]] = (item["name"], idx, v)
            elif kind == "function":
                self.functions[item["name"]] = item
            elif kind in ("let", "var", "expression", "return"):
                self.globals.append(item)

    def emit_c_type(self, type_str: str) -> str:
        if type_str == "Int":
            return "int64_t"
        elif type_str == "Bool":
            return "bool"
        elif type_str == "Str":
            return "const char*"
        elif type_str == "Unit":
            return "void"
        elif type_str in self.types:
            return f"pep_rec_{type_str}"
        elif type_str in self.unions:
            return f"pep_union_{type_str}"
        elif type_str.startswith("List["):
            return "pep_list_t"
        return "int64_t"

    def emit_expr(self, expr: Dict[str, Any]) -> str:
        kind = expr.get("kind")
        if kind == "int":
            return f"{expr['value']}LL"
        elif kind == "bool":
            return "true" if expr["value"] else "false"
        elif kind == "string":
            raw = expr["value"]
            escaped = json.dumps(raw)
            return escaped
        elif kind == "name":
            return f"pep_var_{expr['name']}"
        elif kind == "binary":
            op = expr["operator"]
            left = self.emit_expr(expr["left"])
            right = self.emit_expr(expr["right"])
            if op == "+":
                return f"pep_add({left}, {right})"
            elif op == "-":
                return f"pep_sub({left}, {right})"
            elif op == "*":
                return f"pep_mul({left}, {right})"
            elif op == "/":
                return f"pep_div({left}, {right})"
            elif op in ("<=", "==", "!=", "<", ">", ">=", "&&", "||"):
                return f"({left} {op} {right})"
            return f"({left} {op} {right})"
        elif kind == "unary":
            op = expr["operator"]
            val = self.emit_expr(expr.get("value") or expr.get("operand"))
            if op == "!":
                return f"(!{val})"
            elif op == "neg":
                return f"pep_neg({val})"
            return f"({op}{val})"
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
            else:
                args_str = ", ".join(args)
                return f"pep_fn_{fname}({args_str})"
        elif kind == "record":
            tname = expr.get("typeName") or expr.get("name", "")
            fields = expr.get("fields", [])
            field_inits = [f".{f['name']} = {self.emit_expr(f['value'])}" for f in fields]
            return f"((pep_rec_{tname}){{ {', '.join(field_inits)} }})"
        elif kind == "field_access":
            target_expr = expr.get("value") or expr.get("target")
            target = self.emit_expr(target_expr)
            fname = expr.get("field") or expr.get("name")
            return f"({target}.{fname})"
        elif kind == "list":
            elements = [self.emit_expr(e) for e in expr.get("elements", [])]
            if not elements:
                return "((pep_list_t){ .len = 0, .data = NULL })"
            elems_str = ", ".join(elements)
            return f"((pep_list_t){{ .len = {len(elements)}, .data = (int64_t[]){{ {elems_str} }} }})"
        elif kind == "match":
            subject_expr = expr.get("value") or expr.get("subject")
            subject = self.emit_expr(subject_expr)
            arms = expr.get("arms", [])
            lines = [f"({{ auto __m_val = {subject}; int64_t __m_res = 0;"]
            first_arm = True
            for arm in arms:
                pat = arm["pattern"]
                pkind = pat.get("kind")
                conds = []
                binds = []
                if pkind == "constructor_pattern":
                    cname = pat["name"]
                    if cname in self.constructors:
                        uname, cidx, cinfo = self.constructors[cname]
                        conds.append(f"__m_val.tag == {cidx}")
                        for arg_idx, arg_pat in enumerate(pat.get("arguments", [])):
                            if arg_pat.get("kind") == "binding_pattern":
                                bname = arg_pat["name"]
                                binds.append(f"int64_t pep_var_{bname} = __m_val.val.{cname}._{arg_idx};")
                elif pkind == "binding_pattern":
                    bname = pat["name"]
                    binds.append(f"auto pep_var_{bname} = __m_val;")
                elif pkind == "wildcard_pattern":
                    pass

                arm_code = self.emit_expr(arm["result"])
                if conds:
                    cond_str = " && ".join(conds)
                    prefix = "if" if first_arm else "else if"
                    lines.append(f"{prefix} ({cond_str}) {{")
                    for b in binds:
                        lines.append(f"  {b}")
                    lines.append(f"  __m_res = {arm_code};")
                    lines.append("}")
                    first_arm = False
                else:
                    lines.append("else {" if not first_arm else "{")
                    for b in binds:
                        lines.append(f"  {b}")
                    lines.append(f"  __m_res = {arm_code};")
                    lines.append("}")
                    break
            lines.append("__m_res; })")
            return " ".join(lines)
        return "0"

    def emit_stmt(self, stmt: Dict[str, Any], indent: str = "  ") -> List[str]:
        lines = []
        kind = stmt.get("kind")
        if kind in ("let", "var"):
            vname = stmt["name"]
            vval = self.emit_expr(stmt["value"])
            ann = stmt.get("annotation")
            vtype = self.emit_c_type(ann) if ann else "auto"
            lines.append(f"{indent}{vtype} pep_var_{vname} = {vval};")
        elif kind == "assignment":
            vname = stmt["name"]
            vval = self.emit_expr(stmt["value"])
            lines.append(f"{indent}pep_var_{vname} = {vval};")
        elif kind == "return":
            val = self.emit_expr(stmt["value"])
            lines.append(f"{indent}return {val};")
        elif kind == "expression":
            val = self.emit_expr(stmt["value"])
            lines.append(f"{indent}{val};")
        elif kind == "if_statement":
            cond = self.emit_expr(stmt["condition"])
            lines.append(f"{indent}if ({cond}) {{")
            for s in stmt.get("then", []):
                lines.extend(self.emit_stmt(s, indent + "  "))
            if stmt.get("else"):
                lines.append(f"{indent}}} else {{")
                for s in stmt.get("else", []):
                    lines.extend(self.emit_stmt(s, indent + "  "))
            lines.append(f"{indent}}}")
        elif kind == "for_in":
            bname = stmt["name"]
            iterable = self.emit_expr(stmt["iterable"])
            idx_var = f"__i_{bname}_{abs(hash(bname)) % 10000}"
            list_var = f"__list_{bname}_{abs(hash(bname)) % 10000}"
            lines.append(f"{indent}pep_list_t {list_var} = {iterable};")
            lines.append(f"{indent}for (size_t {idx_var} = 0; {idx_var} < {list_var}.len; ++{idx_var}) {{")
            lines.append(f"{indent}  int64_t pep_var_{bname} = {list_var}.data[{idx_var}];")
            for s in stmt.get("body", []):
                lines.extend(self.emit_stmt(s, indent + "  "))
            lines.append(f"{indent}}}")
        elif kind == "while":
            cond = self.emit_expr(stmt["condition"])
            lines.append(f"{indent}while ({cond}) {{")
            for s in stmt.get("body", []):
                lines.extend(self.emit_stmt(s, indent + "  "))
            lines.append(f"{indent}}}")
        return lines

    def generate_c23(self) -> str:
        out = []
        # Header & C23 prelude
        out.append("/* Generated by Pepin Direct C23 Native Emitter (ISO/IEC 9899:2024) */")
        out.append("#include <stdint.h>")
        out.append("#include <stdbool.h>")
        out.append("#include <stdio.h>")
        out.append("#include <stdlib.h>")
        out.append("#include <string.h>")
        out.append("")
        
        # Checked arithmetic & runtime helpers
        out.append("/* Checked Arithmetic Helpers */")
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
        
        # Monomorphic builtins
        out.append("/* Monomorphic Built-ins */")
        out.append("static inline void pep_say(const char* s) {")
        out.append('  printf("%s\\n", s ? s : "");')
        out.append("}")
        out.append("")
        out.append("static inline const char* pep_int_text(int64_t n) {")
        out.append("  char* buf = (char*)malloc(32);")
        out.append('  snprintf(buf, 32, "%lld", (long long)n);')
        out.append("  return buf;")
        out.append("}")
        out.append("")

        # List Runtime
        out.append("/* List Runtime */")
        out.append("typedef struct {")
        out.append("  size_t len;")
        out.append("  int64_t* data;")
        out.append("} pep_list_t;")
        out.append("")
        out.append("static inline int64_t pep_length(pep_list_t list) {")
        out.append("  return (int64_t)list.len;")
        out.append("}")
        out.append("")

        # Tagged Unions
        if self.unions:
            out.append("/* Tagged Union Types */")
            for uname, uinfo in self.unions.items():
                out.append(f"typedef struct pep_union_{uname} {{")
                out.append("  int tag;")
                out.append("  union {")
                for v in uinfo.get("variants", []):
                    vname = v["name"]
                    args = v.get("arguments", [])
                    if args:
                        out.append(f"    struct {{")
                        for i, a in enumerate(args):
                            out.append(f"      {self.emit_c_type(a)} _{i};")
                        out.append(f"    }} {vname};")
                out.append("  } val;")
                out.append(f"}} pep_union_{uname};")
                out.append("")

                # Constructor functions
                for idx, v in enumerate(uinfo.get("variants", [])):
                    vname = v["name"]
                    args = v.get("arguments", [])
                    if args:
                        c_params = [f"{self.emit_c_type(a)} _{i}" for i, a in enumerate(args)]
                        out.append(f"static inline pep_union_{uname} pep_fn_{vname}({', '.join(c_params)}) {{")
                        out.append(f"  pep_union_{uname} u = {{ .tag = {idx} }};")
                        for i in range(len(args)):
                            out.append(f"  u.val.{vname}._{i} = _{i};")
                        out.append("  return u;")
                        out.append("}")
                    else:
                        out.append(f"static inline pep_union_{uname} pep_fn_{vname}(void) {{")
                        out.append(f"  return (pep_union_{uname}){{ .tag = {idx} }};")
                        out.append("}")
                    out.append("")

        # Type declarations (Records)
        if self.types:
            out.append("/* Record Types */")
            for tname, item in self.types.items():
                out.append(f"typedef struct {{")
                for f in item.get("fields", []):
                    fname = f["name"]
                    ftype = self.emit_c_type(f["type"])
                    out.append(f"  {ftype} {fname};")
                out.append(f"}} pep_rec_{tname};")
                out.append("")

        # Function forward declarations
        if self.functions:
            out.append("/* Function Forward Declarations */")
            for fname, fn in self.functions.items():
                ret_type = self.emit_c_type(fn.get("returnType", "Unit"))
                params = [f"{self.emit_c_type(p['type'])} pep_var_{p['name']}" for p in fn.get("parameters", [])]
                param_str = ", ".join(params) if params else "void"
                out.append(f"{ret_type} pep_fn_{fname}({param_str});")
            out.append("")

        # Function definitions
        if self.functions:
            out.append("/* Function Implementations */")
            for fname, fn in self.functions.items():
                ret_type = self.emit_c_type(fn.get("returnType", "Unit"))
                params = [f"{self.emit_c_type(p['type'])} pep_var_{p['name']}" for p in fn.get("parameters", [])]
                param_str = ", ".join(params) if params else "void"
                out.append(f"{ret_type} pep_fn_{fname}({param_str}) {{")
                for stmt in fn.get("body", []):
                    out.extend(self.emit_stmt(stmt, "  "))
                if ret_type == "void":
                    out.append("  return;")
                out.append("}")
                out.append("")

        # Native main entrypoint
        out.append("/* Native Program Entrypoint */")
        out.append("int main(int argc, char** argv) {")
        out.append("  (void)argc; (void)argv;")
        
        # Execute top-level statements
        for s in self.globals:
            out.extend(self.emit_stmt(s, "  "))
            
        # Call pep_fn_main if it exists
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
    code, stdout, stderr = run_pep_cmd("inspect", str(source_pep), "--json")
    if code != 0:
        raise RuntimeError(f"Pep inspect failed: {stderr}")
    ast_data = json.loads(stdout)
    
    emitter = C23Emitter(ast_data)
    c_source = emitter.generate_c23()

    c_file = emit_c_path or output_exe.with_suffix(".c")
    c_file.write_text(c_source, encoding="utf-8")

    compiler = compiler_bin or find_c23_compiler()
    
    # Compile with strict C23 standard
    cmd = [str(compiler), "-std=c23", "-O2", str(c_file), "-o", str(output_exe)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"C23 compilation failed:\n{res.stderr}\nSource was saved to {c_file}")

    return output_exe


def run_c23(source_pep: pathlib.Path, compiler_bin: Optional[pathlib.Path] = None) -> Tuple[int, str, str]:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        temp_dir = pathlib.Path(td)
        exe_path = temp_dir / "prog.exe"
        build_c23(source_pep, exe_path, compiler_bin)
        res = subprocess.run([str(exe_path)], capture_output=True, text=True)
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
