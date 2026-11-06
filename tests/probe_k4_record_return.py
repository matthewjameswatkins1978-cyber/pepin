"""K4 native probe: does a record-RETURNING function lower to C23 that strict Clang
and GCC both build and run, matching the seed oracle?

A4 (`spec/agent4-spec-lab@c25fab6`, `docs/spec/K4-STDLIB-PRIMITIVE.md`) named
function-result records as the one primitive gap blocking the lexer header, and
stated its own falsifier: if the L3 `advance_position` shape already lowers, the
primitive EXISTS and the card flips to NO-CHANGE with the L6 control-flow residual.

This probe runs that falsifier. It drives the real `pep_c23` session, the real
emitter bundle and the real A1 seed at the pinned `A1_SHA`; nothing here models
the emitter.

Two fixtures, one per branch of the real lexer function (`examples/pep_lexer.pep:90`):
the newline branch (`byte == 10`) and the ordinary branch. They are separate
programs because two call sites in one `main` exceed the known one-shot checker
ceiling (measured: `PEP_RUNTIME_STEP_LIMIT` at 2441:3).

The emitter's `main` wrapper prints `main`'s Int return, so the native oracle is
the return value itself. The seed runs top-level statements, so its oracle is
`say(int_text(...))` -- the documented entry-point difference, stated everywhere
in this lane.

NOTE: A4's doc says the oracle "prints 2/1/4/8" via top-level `say`. That does not
reproduce: `say` is `[Str] -> Unit` at both the 727f8af seed and the campaign tree
`57fe424`, so `say(a.line)` is `PEP_TYPE_MISMATCH`. The values are right; the call
shape needs `int_text`. Measured, not assumed.

Run: python tests/probe_k4_record_return.py
"""
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

BUILD = ROOT / "_build"
A1_SEED = BUILD / "a1_seed" / "pep.exe"

DECL = (
    "type SourcePosition { line: Int, column: Int }\n"
    "fn advance_position(line: Int, column: Int, byte: Int) -> SourcePosition {\n"
    "  if byte == 10 { return SourcePosition { line: line + 1, column: 1 } } else {\n"
    "    return SourcePosition { line: line, column: column + 1 }\n"
    "  }\n"
    "}\n")

CASES = [
    ("newline", "advance_position(1, 1, 10)", b"21\n"),
    ("ordinary", "advance_position(4, 7, 65)", b"48\n"),
]


def native_source(call):
    return DECL + (
        "fn main() -> Int {\n"
        f"  let p = {call}\n"
        "  return p.line * 10 + p.column\n"
        "}\n")


def seed_source(call):
    return DECL + (
        f"let p = {call}\n"
        "say(int_text(p.line * 10 + p.column))\n")


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def run_case(label, call, expected):
    seed_path = BUILD / f"k4_seed_oracle_{label}.pep"
    seed_path.write_text(seed_source(call), encoding="utf-8", newline="\n")
    seed = subprocess.run([str(A1_SEED), "run", str(seed_path)],
                          capture_output=True, check=False)
    seed_out = seed.stdout.replace(b"\r\n", b"\n")
    print(f"[{label}] seed-oracle   {'OK' if seed_out == expected else 'FAIL'} "
          f"exit={seed.returncode} out={seed_out!r}")
    if seed.returncode:
        print(f"[{label}]   seed stderr:", seed.stderr.decode("utf-8", "replace")[:300])
        return 1

    source = native_source(call)
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

        payload = source.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": f"k4-{label}", "bytes": list(payload)})
        require(target, "outcome", "ok", "open k4 fixture")
        semantic = {"document": target["document"], "revision": target["revision"],
                    "entryFunctions": []}
        parsed = parse_target(session, payload, target, revision)
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
        if checked.get("outcome") != "ok":
            print(f"[{label}] check         FAIL {checked.get('error')}")
            return 1
        cfields = fields_map(checked["result"])
        codes = [fields_map(d).get("code", {}).get("value")
                 for d in (cfields.get("diagnostics", {}).get("value") or [])]
        print(f"[{label}] check         "
              f"{'OK' if cfields['status']['value'] == 'valid' else 'FAIL'} "
              f"status={cfields['status']['value']} diags={codes[:3]}")
        if cfields["status"]["value"] != "valid":
            return 1

        emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-emitter",
                                "arguments": [parsed, checked["result"]],
                                "semanticTarget": semantic})
        if emitted.get("outcome") != "ok":
            print(f"[{label}] emit          FAIL {emitted.get('error')}")
            return 1
        efields = fields_map(emitted["result"])
        status = efields["status"]["value"]
        csrc = "".join(p["value"] for p in efields["sourceParts"]["value"])
        print(f"[{label}] emit          {'OK' if status == 'emitted' else 'FAIL'} "
              f"status={status} bytes={len(csrc)} "
              f"diag={efields['diagnostic']['value'][:200]}")
        if status != "emitted":
            return 1
    finally:
        session.close()

    c_path = BUILD / f"k4_record_return_{label}.c"
    c_path.write_text(csrc, encoding="utf-8", newline="\n")
    failures = 0
    for name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        exe = BUILD / f"k4_record_return_{label}_{name}.exe"
        built = subprocess.run(
            [str(pep_c23.compiler_path(name)), *extra, "-Wall", "-Wextra",
             "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
            capture_output=True, text=True, check=False)
        if built.returncode:
            print(f"[{label}] native-{name:6s}  FAIL build exit={built.returncode} "
                  f"{built.stderr[:400]}")
            failures += 1
            continue
        ran = subprocess.run([str(exe)], capture_output=True, check=False)
        out = ran.stdout.replace(b"\r\n", b"\n")
        ok = out == expected
        print(f"[{label}] native-{name:6s}  {'OK' if ok else 'FAIL'} out={out!r}")
        if not ok:
            failures += 1
    return 1 if failures else 0


def main():
    failures = 0
    for label, call, expected in CASES:
        failures += run_case(label, call, expected)
    print("K4 record-return native:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
