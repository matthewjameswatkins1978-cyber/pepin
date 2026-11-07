"""Which functions of a real Pep compiler source can the C23 emitter lower, and
what is the FIRST refusal for each one that cannot?

This is the A2-side closure measurement for Road 1. It runs on the ACTUAL
top-level functions of a single-file Pep source -- the lexer, the parser, the
checker or the emitter itself -- rather than on a synthetic feature matrix. Each
function is compiled as a real program with only the type declarations and callees
it transitively needs.

Each row reports one line:

  FUNCTION | CHECK(valid/reason) | EMIT(emitted/reason) | FIRST_BLOCKER

Nothing here is a model of the emitter: it drives the real `pep_c23` session, the
real emitter bundle and the real checker. A refusal is reported verbatim, never
paraphrased, so the next slice can be chosen from evidence.

Usage:
  python tests/probe_function_closure.py                                  # the lexer, native
  python tests/probe_function_closure.py examples/pep_parser.pep          # the parser, native
  python tests/probe_function_closure.py examples/pep_parser.pep --no-native
  python tests/probe_function_closure.py tests/pep_c23_emitter.pep --filter parse

`--no-native` skips the strict Clang/GCC compile-and-run step. Use it for a first
blocker map over a large source; "emitted" is not "native", so re-run without it
on the rows you intend to claim.
"""
import argparse
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


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def split_source(text):
    """Type declarations, then each top-level function by brace depth.

    A function block ends only after at least one `{` has been seen, so a
    multi-line parameter list is not cut off at its first line.
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
    """Type declarations keyed by name: record blocks AND union declarations.

    Both shapes occur in the real compiler source. `examples/pep_parser.pep` opens
    with a 37-variant union (`type AstValue = AstAbsent() | ...`), and a splitter
    that only understood `type Name { ... }` silently dropped it, which made every
    parser fixture fail to parse for a reason that had nothing to do with the
    function under test.
    """
    found = {}
    for match in re.finditer(r"type\s+(\w+)\s*\{[^}]*\}", declaration_text):
        found[match.group(1)] = match.group(0)
    for match in re.finditer(r"type\s+(\w+)\s*=\s*[^\n]+", declaration_text):
        found.setdefault(match.group(1), match.group(0))
    return found


def needed_declarations(declarations, block):
    """Transitive closure of declared types referenced by the block, in DEPENDENCY order.

    Order matters: the emitter refuses a record field whose type is a record declared
    later ("record fields require Int, Bool, or a preceding record declaration"). The
    first version of this helper returned declarations in discovery order, which put
    CheckedFunction before PepTypeShape even though CheckedFunction has a
    `returnShape: PepTypeShape` field -- producing a FALSE emitter refusal on
    append_checked_functions. Emit dependencies first.
    """
    needed = []
    pending = [block]
    seen = set()
    while pending:
        text = pending.pop()
        for name, declaration in declarations.items():
            if name in seen:
                continue
            if re.search(rf"\b{re.escape(name)}\b", text):
                seen.add(name)
                needed.append((name, declaration))
                pending.append(declaration)

    # Topological order: a declaration may only be emitted once every declaration it
    # references has been emitted. Cycles cannot occur in a valid Pep source.
    ordered = []
    emitted = set()
    remaining = list(needed)
    while remaining:
        progressed = False
        for name, declaration in list(remaining):
            deps = {other for other, _ in needed
                    if other != name and re.search(rf"\b{re.escape(other)}\b", declaration)}
            if deps <= emitted:
                ordered.append(declaration)
                emitted.add(name)
                remaining.remove((name, declaration))
                progressed = True
        if not progressed:
            # Unresolvable cycle: fall back to discovery order rather than dropping.
            ordered.extend(declaration for _, declaration in remaining)
            break
    return "\n".join(ordered)


def needed_functions(functions, name, block):
    """Transitive closure of top-level functions the block CALLS.

    Without this, a function that calls a sibling reports PEP_UNKNOWN_FUNCTION and
    the row measures the probe's omission rather than the emitter.
    """
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


def measure(session, revision, source, name, label):
    """check -> emit -> (optionally) native. Returns (check, emit, detail)."""
    payload = source.encode("utf-8")
    # Name the fixture-size boundary BEFORE the host refuses it, so a row that is
    # really "this probe built too big a fixture" is not reported as a parse failure.
    # 65536 is the host's documented source-open limit; it is not raisable.
    if len(payload) > 65536:
        return "fixture-too-large", "-", \
            f"{len(payload)} bytes > 65536 source-open limit (probe limitation)"
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    if target.get("outcome") != "ok":
        return "open-failed", "-", str(target.get("error"))[:80]
    semantic = {"document": target["document"],
                "revision": target["revision"], "entryFunctions": []}
    try:
        parsed = parse_target(session, payload, target, revision)
    except Exception as error:  # noqa: BLE001
        # parse_target raises a generic RuntimeError, but the CAUSE is often a named
        # platform limit inside the parser-step tool. Classify by the real code so a
        # budget failure is not misfiled as a probe defect.
        text = str(error)
        for code in ("PEP_RUNTIME_STEP_LIMIT", "PEP_TOOL_VALUE_LIMIT",
                     "PEP_SOURCE_BYTE_LIMIT", "PEP_RUNTIME_CALL_DEPTH"):
            if code in text:
                return code, "-", text[:100]
        return "parse-failed", "-", text[:100]
    try:
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
    except RuntimeError as error:
        # The 1 MiB JSONL transport limit is a real, named boundary (the same one that
        # makes lexer_step need interior staging). Report it, do not crash.
        return "transport-1MiB", "-", str(error)[:100]
    if checked.get("outcome") != "ok":
        error = checked.get("error") or {}
        return error.get("code", "check-error"), "-", (error.get("message") or "")[:100]
    cfields = fields_map(checked["result"])
    status = cfields["status"]["value"]
    if status != "valid":
        codes = [fields_map(d).get("code", {}).get("value")
                 for d in (cfields.get("diagnostics", {}).get("value") or [])]
        return f"invalid {codes[:2]}", "-", "checker refused"
    try:
        emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-emitter",
                                "arguments": [parsed, checked["result"]],
                                "semanticTarget": semantic})
    except RuntimeError as error:
        return "valid", "transport-1MiB", str(error)[:100]
    if emitted.get("outcome") != "ok":
        error = emitted.get("error") or {}
        return "valid", error.get("code", "emit-error"), (error.get("message") or "")[:100]
    efields = fields_map(emitted["result"])
    estatus = efields["status"]["value"]
    if estatus != "emitted":
        return "valid", estatus, efields["diagnostic"]["value"][:110]
    if not NATIVE:
        return "valid", estatus, "(native step skipped)"
    # "emitted" is not "native". Compile the emitted C with BOTH strict compilers and
    # run it: the fixture's main returns 0, so a clean run proves the function lowered
    # to valid, executable C23.
    csrc = "".join(p["value"] for p in efields["sourceParts"]["value"])
    c_path = BUILD / f"fn_closure_{re.sub(r'[^A-Za-z0-9_]', '_', label)}.c"
    c_path.write_text(csrc, encoding="utf-8", newline="\n")
    native = []
    for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        exe = BUILD / f"fn_closure_{re.sub(r'[^A-Za-z0-9_]', '_', label)}_{compiler_name}.exe"
        built = subprocess.run(
            [str(pep_c23.compiler_path(compiler_name)), *extra, "-Wall", "-Wextra",
             "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
            capture_output=True, text=True, check=False)
        if built.returncode:
            native.append(f"{compiler_name}:build-fail")
            continue
        ran = subprocess.run([str(exe)], capture_output=True, check=False)
        native.append(f"{compiler_name}:{'ok' if ran.returncode == 0 else 'run-fail'}")
    detail = " ".join(native)
    if any("fail" in item for item in native):
        estatus = "emitted-but-not-native"
    return "valid", estatus, detail


NATIVE = True


def main():
    global NATIVE
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="examples/pep_lexer.pep")
    parser.add_argument("--with", dest="extra", action="append", default=[],
                        help="another source whose TYPE DECLARATIONS are also available "
                             "(the parser source is not self-contained: it uses the "
                             "lexer's LexToken/LexCursor). Repeatable.")
    parser.add_argument("--no-native", action="store_true",
                        help="skip strict Clang/GCC compile-and-run")
    parser.add_argument("--filter", default="", help="only names containing this substring")
    arguments = parser.parse_args()
    NATIVE = not arguments.no_native

    source_path = (ROOT / arguments.path).resolve()
    declaration_text, functions = split_source(source_path.read_text(encoding="utf-8"))
    declarations = split_declarations(declaration_text)
    for extra in arguments.extra:
        extra_path = (ROOT / extra).resolve()
        extra_text, _ = split_source(extra_path.read_text(encoding="utf-8"))
        for name, declaration in split_declarations(extra_text).items():
            declarations.setdefault(name, declaration)
    if arguments.filter:
        functions = [(n, b) for n, b in functions if arguments.filter in n]
    print(f"{source_path.name}: {len(functions)} function(s); "
          f"{len(declarations)} declared type(s) "
          f"(+{len(arguments.extra)} companion source(s)); native={NATIVE}")

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

        for index, (name, block) in enumerate(functions):
            callees = needed_functions(functions, name, block)
            decls = needed_declarations(declarations, block + "\n" + callees)
            source = (decls + "\n" if decls else "") + callees + \
                ("\n" if callees else "") + block + \
                "\nfn main() -> Int { return 0 }\n"
            check, emit, detail = measure(session, revision, source,
                                          name, f"{source_path.stem}-{name}")
            rows.append((name, check, emit, detail))
            print(f"  [{index + 1}/{len(functions)}] {name}: {check} / {emit}",
                  flush=True)
    finally:
        session.close()

    print()
    width = max(len(r[0]) for r in rows) if rows else 10
    for name, check, emit, detail in rows:
        print(f"{name:<{width}} | {check:<26} | {emit:<24} | {detail}")

    # Classify ROWS HONESTLY. A bare "N/M emit" is misleading on a large source:
    # probe-level fixture failures and platform limits both masquerade as refusals,
    # and only the emitter refusals are A2's to act on.
    emitter_refusals = [r for r in rows if r[2] == "unsupported"]
    non_native = [r for r in rows if r[2] == "emitted-but-not-native"]
    probe_limited = [r for r in rows if r[1] in ("parse-failed", "open-failed",
                                                 "fixture-too-large")]
    platform = [r for r in rows if r[1] in ("PEP_RUNTIME_STEP_LIMIT", "transport-1MiB",
                                            "PEP_TOOL_VALUE_LIMIT", "PEP_SOURCE_BYTE_LIMIT",
                                            "PEP_RUNTIME_CALL_DEPTH")
                or r[2] in ("transport-1MiB", "PEP_TOOL_VALUE_LIMIT")]
    checker_refused = [r for r in rows if r[1].startswith("invalid")]
    emitted = [r for r in rows if r[2] == "emitted"]

    print(f"\ntotal {len(rows)}")
    print(f"  emitted{' (and native)' if NATIVE else ''}: {len(emitted)}")
    print(f"  emitter refusals (A2's to act on): {len(emitter_refusals)}")
    print(f"  emitted but NOT native: {len(non_native)}")
    print(f"  checker refused: {len(checker_refused)}")
    print(f"  platform limits (checker step / 1 MiB / tool / source bytes): {len(platform)}")
    print(f"  PROBE-limited fixture failures (not evidence): {len(probe_limited)}")
    if probe_limited:
        print("  NOTE: probe-limited rows are fixture-construction failures in this\n"
              "        probe, not emitter or platform findings. Do not read them as\n"
              "        refusals. A whole-program fixture strategy does not scale to a\n"
              "        80+ function source; use the staged/chunked path instead.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
