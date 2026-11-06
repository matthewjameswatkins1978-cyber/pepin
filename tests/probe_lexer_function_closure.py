"""Which real lexer functions can the C23 emitter actually lower, and what is the
FIRST refusal for each one that cannot?

This is the A2-side closure measurement for Road 1: not a synthetic feature matrix,
but the actual top-level functions of `examples/pep_lexer.pep`, each compiled as a
real program.

Each function is compiled with ONLY the type declarations it transitively needs, so
the measurement is about that function rather than about the whole lexer's
declaration block. Each row reports one line:

  FUNCTION | CHECK(valid/reason) | EMIT(emitted/reason) | FIRST_BLOCKER

Nothing here is a model of the emitter: it drives the real `pep_c23` session, the
real emitter bundle and the real checker. A refusal is reported verbatim, never
paraphrased, so the next slice can be chosen from evidence.

Run: python tests/probe_lexer_function_closure.py
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

LEXER = ROOT / "examples" / "pep_lexer.pep"
BUILD = ROOT / "_build"


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def split_lexer(text):
    """Type declarations, then each top-level function by brace depth.

    A function block ends only after at least one `{` has been seen, so a
    multi-line parameter list (make_cursor, make_token, make_progress) is not cut
    off at its first line.
    """
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
    """`type Name { ... }` blocks, keyed by name."""
    found = {}
    for match in re.finditer(r"type\s+(\w+)\s*\{[^}]*\}", declaration_text):
        found[match.group(1)] = match.group(0)
    return found


def needed_declarations(declarations, block):
    """Transitive closure of declared types referenced by the block."""
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
    """Transitive closure of top-level lexer functions the block CALLS.

    Without this, `ascii_continue` reports PEP_UNKNOWN_FUNCTION for `ascii_digit`
    and the row measures the probe's omission rather than the emitter.
    """
    by_name = dict(functions)
    chosen = []
    pending = [(name, block)]
    seen = {name}
    while pending:
        current_name, text = pending.pop()
        for other_name, other_block in by_name.items():
            if other_name in seen:
                continue
            if re.search(rf"\b{re.escape(other_name)}\s*\(", text):
                seen.add(other_name)
                chosen.append(other_block)
                pending.append((other_name, other_block))
    return "\n".join(chosen)


def main():
    declaration_text, functions = split_lexer(LEXER.read_text(encoding="utf-8"))
    declarations = split_declarations(declaration_text)
    print(f"lexer functions: {len(functions)}; declared types: {len(declarations)}")
    rows = []
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

        for name, block in functions:
            callees = needed_functions(functions, name, block)
            decls = needed_declarations(declarations, block + "\n" + callees)
            source = (decls + "\n" if decls else "") + callees + \
                ("\n" if callees else "") + block + \
                "\nfn main() -> Int { return 0 }\n"
            payload = source.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"lexer-{name}", "bytes": list(payload)})
            if target.get("outcome") != "ok":
                rows.append((name, "open-failed", "-", str(target.get("error"))[:80]))
                continue
            semantic = {"document": target["document"],
                        "revision": target["revision"], "entryFunctions": []}
            try:
                parsed = parse_target(session, payload, target, revision)
            except Exception as error:  # noqa: BLE001
                rows.append((name, "parse-failed", "-", str(error)[:100]))
                continue
            try:
                checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_invoke", "tool": "pep-c23-checker",
                                        "arguments": [parsed], "semanticTarget": semantic})
            except RuntimeError as error:
                # The 1 MiB JSONL transport limit is a real, named boundary (the same one
                # that makes lexer_step need interior staging). Report it, do not crash.
                rows.append((name, "transport-1MiB", "-", str(error)[:100]))
                continue
            if checked.get("outcome") != "ok":
                error = checked.get("error") or {}
                rows.append((name, error.get("code", "check-error"), "-",
                             (error.get("message") or "")[:100]))
                continue
            cfields = fields_map(checked["result"])
            status = cfields["status"]["value"]
            if status != "valid":
                codes = [fields_map(d).get("code", {}).get("value")
                         for d in (cfields.get("diagnostics", {}).get("value") or [])]
                rows.append((name, f"invalid {codes[:2]}", "-", "checker refused"))
                continue
            try:
                emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_invoke", "tool": "pep-c23-emitter",
                                        "arguments": [parsed, checked["result"]],
                                        "semanticTarget": semantic})
            except RuntimeError as error:
                rows.append((name, "valid", "transport-1MiB", str(error)[:100]))
                continue
            if emitted.get("outcome") != "ok":
                error = emitted.get("error") or {}
                rows.append((name, "valid", error.get("code", "emit-error"),
                             (error.get("message") or "")[:100]))
                continue
            efields = fields_map(emitted["result"])
            estatus = efields["status"]["value"]
            detail = efields["diagnostic"]["value"] if estatus != "emitted" else ""
            if estatus == "emitted":
                # "emitted" is not "native". Compile the emitted C with BOTH strict
                # compilers and run it: the fixture's main returns 0, so a clean run
                # proves the function lowered to valid, executable C23.
                csrc = "".join(p["value"] for p in efields["sourceParts"]["value"])
                c_path = BUILD / f"lexer_fn_{name}.c"
                c_path.write_text(csrc, encoding="utf-8", newline="\n")
                native = []
                for compiler_name, extra in (("clang", ["-std=c23"]),
                                             ("gcc", ["-std=c2x"])):
                    exe = BUILD / f"lexer_fn_{name}_{compiler_name}.exe"
                    built = subprocess.run(
                        [str(pep_c23.compiler_path(compiler_name)), *extra,
                         "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                         str(c_path), "-o", str(exe)],
                        capture_output=True, text=True, check=False)
                    if built.returncode:
                        native.append(f"{compiler_name}:build-fail")
                        continue
                    ran = subprocess.run([str(exe)], capture_output=True, check=False)
                    native.append(f"{compiler_name}:{'ok' if ran.returncode == 0 else 'run-fail'}")
                detail = " ".join(native)
                if any("fail" in item for item in native):
                    estatus = "emitted-but-not-native"
            rows.append((name, "valid", estatus, detail[:110]))
    finally:
        session.close()

    print()
    width = max(len(r[0]) for r in rows) if rows else 10
    for name, check, emit, detail in rows:
        print(f"{name:<{width}} | {check:<14} | {emit:<12} | {detail}")
    emitted = sum(1 for r in rows if r[2] == "emitted")
    print(f"\n{emitted}/{len(rows)} lexer functions emit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
