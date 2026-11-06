"""Computed call arguments inside non-main functions: emit, run natively, and prove
the evaluation-order safety rules still hold.

Before this slice the emitter refused `return f(n - 1) + 1` inside an ordinary
function with "Pep C23 one-parameter calls require one argument and a call-free
target expression". The gate was `pep_c23_parameter_expression`'s generic call
branch, which required a call argument to be a BARE parameter name. A computed
argument over parameters and literals is just as pure, so the gate now accepts it
through `pep_c23_parameter_value_expression`.

What must NOT change, and is asserted here as negatives:

- two fallible operands in one expression (`f(1) + g(2)`) still refuse, because C
  operand evaluation order is unspecified;
- a nested call as an argument (`f(g(n))`) still refuses, for the same reason.

Run: python tests/probe_computed_call_args.py
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

# (label, native program, seed oracle program, expected stdout)
CASES = [
    (
        "recursion",
        "fn countdown(n: Int) -> Int {\n"
        "  if n <= 0 { return 0 } else {}\n"
        "  return countdown(n - 1) + 1\n"
        "}\n"
        "fn main() -> Int { return countdown(3) }\n",
        "fn countdown(n: Int) -> Int {\n"
        "  if n <= 0 { return 0 } else {}\n"
        "  return countdown(n - 1) + 1\n"
        "}\n"
        "say(int_text(countdown(3)))\n",
        b"3\n",
    ),
    (
        "computed-arg-nonmain",
        "fn f(n: Int) -> Int { return n }\n"
        "fn g(n: Int) -> Int {\n"
        "  if n <= 0 { return 0 } else {}\n"
        "  return f(n - 1) + 1\n"
        "}\n"
        "fn main() -> Int { return g(1) }\n",
        "fn f(n: Int) -> Int { return n }\n"
        "fn g(n: Int) -> Int {\n"
        "  if n <= 0 { return 0 } else {}\n"
        "  return f(n - 1) + 1\n"
        "}\n"
        "say(int_text(g(1)))\n",
        b"1\n",
    ),
]

# Safety negatives: these must still refuse, with the reason named.
NEGATIVES = [
    (
        "two-fallible-operands",
        "fn f(n: Int) -> Int { return n }\n"
        "fn g(n: Int) -> Int { return n }\n"
        "fn main() -> Int { return f(1) + g(2) }\n",
        "evaluation order",
    ),
    (
        "nested-call-argument",
        "fn f(n: Int) -> Int { return n }\n"
        "fn g(n: Int) -> Int { return n }\n"
        "fn h(n: Int) -> Int {\n"
        "  if n <= 0 { return 0 } else {}\n"
        "  return f(g(n)) + 1\n"
        "}\n"
        "fn main() -> Int { return h(1) }\n",
        "call-free target expression",
    ),
]


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def emit(session, revision, source, name):
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": name, "bytes": list(payload)})
    require(target, "outcome", "ok", f"open {name}")
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    parsed = parse_target(session, payload, target, revision)
    checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-checker",
                            "arguments": [parsed], "semanticTarget": semantic})
    require(checked, "outcome", "ok", f"check {name}")
    cfields = fields_map(checked["result"])
    if cfields["status"]["value"] != "valid":
        codes = [fields_map(d).get("code", {}).get("value")
                 for d in (cfields.get("diagnostics", {}).get("value") or [])]
        return None, f"check status={cfields['status']['value']} {codes[:2]}"
    emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-emitter",
                            "arguments": [parsed, checked["result"]],
                            "semanticTarget": semantic})
    require(emitted, "outcome", "ok", f"emit {name}")
    efields = fields_map(emitted["result"])
    status = efields["status"]["value"]
    csrc = "".join(p["value"] for p in efields["sourceParts"]["value"])
    return (csrc if status == "emitted" else None), \
        f"status={status} diag={efields['diagnostic']['value'][:200]}"


def main():
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

        for label, native_src, seed_src, expected in CASES:
            seed_path = BUILD / f"cca_seed_{label}.pep"
            seed_path.write_text(seed_src, encoding="utf-8", newline="\n")
            seed = subprocess.run([str(A1_SEED), "run", str(seed_path)],
                                  capture_output=True, check=False)
            seed_out = seed.stdout.replace(b"\r\n", b"\n")
            ok = seed.returncode == 0 and seed_out == expected
            print(f"[{label}] seed-oracle   {'OK' if ok else 'FAIL'} "
                  f"exit={seed.returncode} out={seed_out!r}")
            if not ok:
                print(f"[{label}]   seed stderr:",
                      seed.stderr.decode("utf-8", "replace")[:300])
                failures += 1

            csrc, detail = emit(session, revision, native_src, label)
            print(f"[{label}] emit          {'OK' if csrc else 'REFUSED'} {detail}")
            if not csrc:
                failures += 1
                continue

            c_path = BUILD / f"cca_{label}.c"
            c_path.write_text(csrc, encoding="utf-8", newline="\n")
            for name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
                exe = BUILD / f"cca_{label}_{name}.exe"
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

        for label, source, reason in NEGATIVES:
            csrc, detail = emit(session, revision, source, label)
            refused = csrc is None and reason in detail
            print(f"neg-{label:22s} {'OK' if refused else 'FAIL'} {detail}")
            if not refused:
                failures += 1
    finally:
        session.close()

    print("computed call args:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
