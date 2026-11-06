"""Do the native lexer functions COMPUTE correctly, or do they merely compile?

`probe_function_closure.py` proves four real lexer functions emit and that the
emitted C builds and runs under strict Clang and GCC. But its fixture `main`
returns 0, so the function is never actually exercised. "Compiles and runs" is
weaker than "computes the right answer".

This probe closes that gap for the four functions the emitter can currently lower:

  ascii_letter, ascii_digit, ascii_continue, advance_position

For each one it drives the SAME inputs through two independent paths and compares:

  native  -- the emitted C, included by a driver that calls `pep_fn_<name>`
  seed    -- the same Pep source at top level, run by the A1 seed

The seed runs top-level statements and the native path runs `main`, so the driver
and the oracle are written to print the same encoding. Bool results print 1/0
(there is no `bool_text` builtin); `advance_position` prints `line * 10 + column`.

Run: python tests/probe_lexer_functions_compute.py
"""
import importlib.util
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

BUILD = ROOT / "_build"
A1_SEED = BUILD / "a1_seed" / "pep.exe"
LEXER = ROOT / "examples" / "pep_lexer.pep"

# (function, C symbol, inputs, seed expression builder, native expression builder)
# Inputs are chosen to straddle every boundary in the real bodies.
BOOL_CASES = [
    ("ascii_letter", [65, 90, 97, 122, 95, 64, 91, 96, 123, 48]),
    ("ascii_digit", [48, 57, 47, 58, 65, 0]),
    ("ascii_continue", [65, 48, 95, 64, 58, 0]),
]
POSITION_CASES = [
    ("advance_position", [(1, 1, 10), (4, 7, 65), (1, 1, 0), (9, 9, 10)]),
]


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def split_source(text):
    lines = text.split("\n")
    declarations = []
    functions = []
    index = 0
    while index < len(lines) and not lines[index].startswith("fn "):
        declarations.append(lines[index])
        index += 1
    while index < len(lines):
        if not lines[index].startswith("fn "):
            index += 1
            continue
        start = index
        depth = 0
        opened = False
        while index < len(lines):
            depth += lines[index].count("{") - lines[index].count("}")
            if "{" in lines[index]:
                opened = True
            index += 1
            if opened and depth == 0:
                break
        block = "\n".join(lines[start:index])
        name = re.match(r"fn\s+(\w+)", lines[start]).group(1)
        functions.append((name, block))
    return "\n".join(declarations), functions


def split_declarations(declaration_text):
    found = {}
    for match in re.finditer(r"type\s+(\w+)\s*\{[^}]*\}", declaration_text):
        found[match.group(1)] = match.group(0)
    return found


def needed_declarations(declarations, block):
    chosen = []
    pending = [block]
    seen = set()
    while pending:
        text = pending.pop()
        for name, declaration in declarations.items():
            if name in seen:
                continue
            if re.search(rf"\b{re.escape(name)}\b", text):
                seen.add(name)
                chosen.append(declaration)
                pending.append(declaration)
    return "\n".join(chosen)


def needed_functions(functions, name, block):
    by_name = dict(functions)
    chosen = []
    pending = [(name, block)]
    seen = {name}
    while pending:
        _, text = pending.pop()
        for other_name, other_block in by_name.items():
            if other_name in seen:
                continue
            if re.search(rf"\b{re.escape(other_name)}\s*\(", text):
                seen.add(other_name)
                chosen.append(other_block)
                pending.append((other_name, other_block))
    return "\n".join(chosen)


def emit(session, revision, source, label):
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    require(target, "outcome", "ok", f"open {label}")
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    parsed = parse_target(session, payload, target, revision)
    checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-checker",
                            "arguments": [parsed], "semanticTarget": semantic})
    require(checked, "outcome", "ok", f"check {label}")
    cfields = fields_map(checked["result"])
    if cfields["status"]["value"] != "valid":
        return None, f"check status={cfields['status']['value']}"
    emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-emitter",
                            "arguments": [parsed, checked["result"]],
                            "semanticTarget": semantic})
    require(emitted, "outcome", "ok", f"emit {label}")
    efields = fields_map(emitted["result"])
    if efields["status"]["value"] != "emitted":
        return None, f"emit status={efields['status']['value']} " \
                     f"{efields['diagnostic']['value'][:120]}"
    return "".join(p["value"] for p in efields["sourceParts"]["value"]), "emitted"


def run_seed(source, label):
    path = BUILD / f"compute_seed_{label}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    ran = subprocess.run([str(A1_SEED), "run", str(path)],
                         capture_output=True, check=False)
    if ran.returncode:
        return None, ran.stderr.decode("utf-8", "replace")[:200]
    return ran.stdout.replace(b"\r\n", b"\n"), "ok"


def run_native(csrc, driver, label):
    c_path = BUILD / f"compute_{label}.c"
    c_path.write_text(csrc, encoding="utf-8", newline="\n")
    d_path = BUILD / f"compute_{label}_driver.c"
    d_path.write_text(driver, encoding="utf-8", newline="\n")
    outputs = {}
    for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        exe = BUILD / f"compute_{label}_{compiler_name}.exe"
        built = subprocess.run(
            [str(pep_c23.compiler_path(compiler_name)), *extra, "-Wall", "-Wextra",
             "-Wpedantic", "-Werror", "-O2", str(d_path), "-o", str(exe)],
            capture_output=True, text=True, check=False)
        if built.returncode:
            outputs[compiler_name] = (None, built.stderr[:300])
            continue
        ran = subprocess.run([str(exe)], capture_output=True, check=False)
        outputs[compiler_name] = (ran.stdout.replace(b"\r\n", b"\n"), "ok")
    return outputs


def main():
    if not A1_SEED.is_file():
        print("SKIP: no A1 seed exe at", A1_SEED)
        return 1
    declaration_text, functions = split_source(LEXER.read_text(encoding="utf-8"))
    declarations = split_declarations(declaration_text)
    by_name = dict(functions)
    failures = 0

    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")

        spec = importlib.util.spec_from_file_location(
            "pic", ROOT / "tests" / "probe_integration_case.py")
        pic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pic)
        pic.register(session, document, revision, sample["document"], sample["revision"])

        # ---- Bool-returning predicates -------------------------------------
        for name, inputs in BOOL_CASES:
            block = by_name[name]
            callees = needed_functions(functions, name, block)
            decls = needed_declarations(declarations, block + "\n" + callees)
            program = (decls + "\n" if decls else "") + callees + \
                ("\n" if callees else "") + block + "\nfn main() -> Int { return 0 }\n"
            csrc, detail = emit(session, revision, program, f"compute-{name}")
            if not csrc:
                print(f"{name:18s} EMIT-REFUSED {detail}")
                failures += 1
                continue

            # Seed oracle: same function, top-level statements, 1/0 encoding.
            oracle = (decls + "\n" if decls else "") + callees + \
                ("\n" if callees else "") + block
            for value in inputs:
                oracle += (f'if {name}({value}) {{ say("1") }} else {{ say("0") }}\n')
            seed_out, seed_detail = run_seed(oracle, name)
            if seed_out is None:
                print(f"{name:18s} SEED-FAILED {seed_detail}")
                failures += 1
                continue

            driver = '#include <stdio.h>\n#define main pep_program_main\n' \
                     f'#include "compute_{name}.c"\n#undef main\nint main(void) {{\n'
            for value in inputs:
                driver += f'  printf("%d\\n", (int)pep_fn_{name}({value}));\n'
            driver += "  return 0;\n}\n"
            outputs = run_native(csrc, driver, name)
            for compiler_name, (out, native_detail) in outputs.items():
                ok = out is not None and out == seed_out
                print(f"{name:18s} {compiler_name:6s} {'OK' if ok else 'FAIL'} "
                      f"seed={seed_out!r} native={out!r}")
                if not ok:
                    print(f"                   detail={native_detail}")
                    failures += 1

        # ---- record-returning advance_position -----------------------------
        for name, inputs in POSITION_CASES:
            block = by_name[name]
            callees = needed_functions(functions, name, block)
            decls = needed_declarations(declarations, block + "\n" + callees)
            program = (decls + "\n" if decls else "") + callees + \
                ("\n" if callees else "") + block + "\nfn main() -> Int { return 0 }\n"
            csrc, detail = emit(session, revision, program, f"compute-{name}")
            if not csrc:
                print(f"{name:18s} EMIT-REFUSED {detail}")
                failures += 1
                continue
            oracle = (decls + "\n" if decls else "") + callees + \
                ("\n" if callees else "") + block
            # Distinct binding names: the seed rejects a repeated `let` in one scope
            # (PEP_DUPLICATE_BINDING), which is a property of the oracle, not the function.
            for case_index, (line, column, byte) in enumerate(inputs):
                oracle += (f"let p{case_index} = {name}({line}, {column}, {byte})\n"
                           f"say(int_text(p{case_index}.line * 10 + "
                           f"p{case_index}.column))\n")
            seed_out, seed_detail = run_seed(oracle, name)
            if seed_out is None:
                print(f"{name:18s} SEED-FAILED {seed_detail}")
                failures += 1
                continue
            # The record's C type name is generated (pep_record_<n>), so read it off the
            # emitted prototype rather than hardcoding it.
            prototype = re.search(
                rf"(\w+)\s+pep_fn_{re.escape(name)}\s*\(", csrc)
            if prototype is None:
                print(f"{name:18s} DRIVER-FAILED no prototype for pep_fn_{name}")
                failures += 1
                continue
            record_type = prototype.group(1)
            driver = '#include <stdio.h>\n#define main pep_program_main\n' \
                     f'#include "compute_{name}.c"\n#undef main\nint main(void) {{\n'
            for case_index, (line, column, byte) in enumerate(inputs):
                driver += (f"  {record_type} p{case_index} = "
                           f"pep_fn_{name}({line}, {column}, {byte});\n"
                           f'  printf("%lld\\n", (long long)'
                           # Record fields are emitted positionally (pep_field_<n>), so
                           # SourcePosition's `line`/`column` are fields 0 and 1.
                           f"(p{case_index}.pep_field_0 * 10 + "
                           f"p{case_index}.pep_field_1));\n")
            driver += "  return 0;\n}\n"
            outputs = run_native(csrc, driver, name)
            for compiler_name, (out, native_detail) in outputs.items():
                ok = out is not None and out == seed_out
                print(f"{name:18s} {compiler_name:6s} {'OK' if ok else 'FAIL'} "
                      f"seed={seed_out!r} native={out!r}")
                if not ok:
                    print(f"                   detail={native_detail}")
                    failures += 1
    finally:
        session.close()

    print("\nlexer functions compute:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
