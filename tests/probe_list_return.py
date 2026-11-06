"""`return [ ... ]` -- a prerequisite for the emitter emitting itself.

Measured before this slice:

  return ["a", "b"]        REFUSED  "expression lowering does not support this expression"
  let xs = ["a", "b"]      EMITTED  (then `return xs` also emitted)

So a list literal was fine as a BINDING but had no lowering as a RETURN value. Five
of the emitter's own 101 functions return `List[Str]` literals directly:

  pep_c23_c_list_field_type_parts
  pep_c23_c_parameter_type_parts
  pep_c23_recursive_union_guard_source
  pep_c23_union_payload_record_path_parts
  pep_c23_record_list_update_source

The return path now routes a `List[Str]` literal through the same argument builder
the call path already uses. `List[Int]` and `List[Bool]` returns are still refused
and are asserted here as negatives, so the widening is exactly as wide as the
self-hosting need and no wider.

HONEST SCOPE -- this is a prerequisite, not the self-hosting fix. Two gaps remain
and are asserted here so the next reader does not mistake this for completion:

  1. `int_text` has no lowering, and it is the FIRST blocker for
     pep_c23_recursive_union_guard_source (`let id = int_text(declaration.id)`).
  2. Calling a function that RETURNS a list is refused by the call gate
     ("calls require a known target with a supported scalar, Str, record, or
     tagged-union result"). So a list-returning function can emit its body but
     cannot yet be called.

Because of (2) a `List[Str]` return cannot be observed natively end to end, so the
proof here is: the emitted C is valid and runs under both strict compilers, and a
list literal used as a call ARGUMENT -- which IS observable -- computes correctly.

Run: python tests/probe_list_return.py
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

# Emit-only: the body must lower and the C must be valid. main returns 0, so a clean
# run proves the emitted translation unit is well-formed.
RETURN_CASES = [
    ("two-strings", 'fn parts() -> List[Str] {\n  return ["a", "b"]\n}\n'
                    'fn main() -> Int { return 0 }\n'),
    ("one-string", 'fn parts() -> List[Str] {\n  return ["only"]\n}\n'
                   'fn main() -> Int { return 0 }\n'),
    ("empty-list", 'fn parts() -> List[Str] {\n  return []\n}\n'
                   'fn main() -> Int { return 0 }\n'),
]

# Observable end to end: a list literal as a call ARGUMENT, which already lowered.
ARGUMENT_CASE = (
    "list-argument",
    'fn count(xs: List[Str]) -> Int { return length(xs) }\n'
    'fn main() -> Int { return count(["a", "b"]) }\n',
    'fn count(xs: List[Str]) -> Int { return length(xs) }\n'
    'say(int_text(count(["a", "b"])))\n',
    b"2\n",
)

# Deliberately still refused: the widening is only as wide as the self-hosting need.
NEGATIVES = [
    ("int-list-return",
     'fn parts() -> List[Int] {\n  return [1, 2]\n}\nfn main() -> Int { return 0 }\n',
     "expression lowering does not support this expression"),
    ("bool-list-return",
     'fn parts() -> List[Bool] {\n  return [true, false]\n}\nfn main() -> Int { return 0 }\n',
     "expression lowering does not support this expression"),
    # Documents the NEXT gap, not a regression: a list-returning function can emit its
    # body but cannot yet be called.
    ("call-list-returning-fn",
     'fn parts() -> List[Str] {\n  return ["a", "b"]\n}\n'
     'fn main() -> Int {\n  let xs = parts()\n  return length(xs)\n}\n',
     "calls require a known target with a supported scalar, Str, record, or tagged-union result"),
]


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


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
                     f"{efields['diagnostic']['value'][:160]}"
    return "".join(p["value"] for p in efields["sourceParts"]["value"]), "emitted"


def build_and_run(csrc, label, expected):
    """Compile with both strict compilers and compare stdout."""
    c_path = BUILD / f"listret_{label}.c"
    c_path.write_text(csrc, encoding="utf-8", newline="\n")
    failures = 0
    for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        exe = BUILD / f"listret_{label}_{compiler_name}.exe"
        built = subprocess.run(
            [str(pep_c23.compiler_path(compiler_name)), *extra,
             "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
             str(c_path), "-o", str(exe)],
            capture_output=True, text=True, check=False)
        if built.returncode:
            print(f"{label:22s} build-{compiler_name} FAIL "
                  f"exit={built.returncode} {built.stderr[:300]}")
            failures += 1
            continue
        ran = subprocess.run([str(exe)], capture_output=True, check=False)
        out = ran.stdout.replace(b"\r\n", b"\n")
        ok = ran.returncode == 0 and out == expected
        print(f"{label:22s} {compiler_name:6s} {'OK' if ok else 'FAIL'} out={out!r}")
        if not ok:
            failures += 1
    return failures


def main():
    if not A1_SEED.is_file():
        print("SKIP: no A1 seed exe at", A1_SEED)
        return 1
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

        for label, source in RETURN_CASES:
            csrc, detail = emit(session, revision, source, f"listret-{label}")
            if not csrc:
                print(f"{label:22s} EMIT-REFUSED {detail}")
                failures += 1
                continue
            # main returns 0, so a clean run proves the unit is well-formed.
            failures += build_and_run(csrc, label, b"0\n")

        label, native, oracle, expected = ARGUMENT_CASE
        seed_path = BUILD / f"listret_seed_{label}.pep"
        seed_path.write_text(oracle, encoding="utf-8", newline="\n")
        seed = subprocess.run([str(A1_SEED), "run", str(seed_path)],
                              capture_output=True, check=False)
        seed_out = seed.stdout.replace(b"\r\n", b"\n")
        if seed.returncode or seed_out != expected:
            print(f"{label:22s} SEED-FAILED exit={seed.returncode} out={seed_out!r}")
            failures += 1
        else:
            csrc, detail = emit(session, revision, native, f"listret-{label}")
            if not csrc:
                print(f"{label:22s} EMIT-REFUSED {detail}")
                failures += 1
            else:
                # This native program has no `say`: main RETURNS the count, and the
                # wrapper prints main's Int return. So the native stream is just that
                # value, which is the same number the seed oracle says.
                failures += build_and_run(csrc, label, expected)

        for label, source, expected_detail in NEGATIVES:
            csrc, detail = emit(session, revision, source, f"listret-{label}")
            ok = csrc is None and expected_detail in detail
            print(f"neg-{label:18s} {'OK' if ok else 'FAIL'} {detail[:110]}")
            if not ok:
                failures += 1
    finally:
        session.close()

    print("\nlist-literal return:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
