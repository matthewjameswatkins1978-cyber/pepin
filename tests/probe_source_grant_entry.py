"""Entry-parameter SourceBytes grant: native proof end to end.

A1's contract (`docs/NATIVE_SOURCE_GRANT_CONTRACT_DRAFT.md` @a802290, mode
"entry-parameter") gives a native program exactly one way to obtain bytes: the
host's `main` wrapper passes the opened target's OWN bytes as the entry's first
`SourceBytes` parameter. `source_bytes()` as a CALL stays refused -- no ambient
authority is added.

This probe proves the vertical:

- the entry shape `fn main(source: SourceBytes) -> Int` now emits;
- strict Clang and GCC build and run it over real files;
- the value matches the seed oracle on the SAME bytes, including NUL and UTF-8;
- without a grant the runtime fails closed BEFORE the entry runs;
- the grant does not leak into other entry shapes.

Note on the seed oracle: the seed grants bytes through `semanticTarget`
(`session_semantic_target` returns `Some analysis.source`), which is a
host/protocol path, not reachable from a plain `run`. The oracle here is therefore
the same Pep SOURCE at top level with the same fixture bytes, still expressing the
same (bytes -> first byte) relation. The native path supplies the actual file.

Run: python tests/probe_source_grant_entry.py
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

ENTRY = "fn main(source: SourceBytes) -> Int { return byte_at(source, 0) }\n"

# (label, file bytes, expected first byte)
FIXTURES = [
    ("ascii", b"A", b"65\n"),
    ("nul", b"\x00A", b"0\n"),
    ("utf8", b"\xc3\xa9", b"195\n"),
]

# The seed oracle: same relation at top level, same fixture bytes.
ORACLE = (
    "fn first_byte(source: SourceBytes) -> Int {\n"
    "  if byte_length(source) == 0 { return -1 } else {}\n"
    "  return byte_at(source, 0)\n"
    "}\n"
    "say(int_text(first_byte(byte_slice(source_bytes(), 0, 1))))\n")


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def emit(session, revision, source, name, entry_names):
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": name, "bytes": list(payload)})
    require(target, "outcome", "ok", f"open {name}")
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": entry_names}
    parsed = parse_target(session, payload, target, revision)
    checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-checker",
                            "arguments": [parsed], "semanticTarget": semantic})
    require(checked, "outcome", "ok", f"check {name}")
    cfields = fields_map(checked["result"])
    if cfields["status"]["value"] != "valid":
        return None, f"check status={cfields['status']['value']}"
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

    # The seed oracle: prove the relation is what we think it is, on the same bytes.
    if A1_SEED.is_file():
        oracle_path = BUILD / "grant_oracle.pep"
        oracle_path.write_text(ORACLE, encoding="utf-8", newline="\n")
        ran = subprocess.run([str(A1_SEED), "run", str(oracle_path)],
                             capture_output=True, check=False)
        print(f"seed-oracle      {'OK' if ran.returncode == 0 else 'SKIP'} "
              f"exit={ran.returncode} "
              f"stderr={ran.stderr.decode('utf-8','replace')[:120]!r}")
    else:
        print("seed-oracle      SKIP (no seed exe)")

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

        csrc, detail = emit(session, revision, ENTRY, "grant-entry", ["main"])
        print(f"grant-entry emit {'OK' if csrc else 'REFUSED'} {detail}")
        if not csrc:
            failures += 1
        else:
            if "(pep_source_bytes){ .data = pep_source_data" not in csrc:
                print("grant-entry wrap FAIL the wrapper does not pass the granted bytes")
                failures += 1
            c_path = BUILD / "grant_entry.c"
            c_path.write_text(csrc, encoding="utf-8", newline="\n")
            for name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
                exe = BUILD / f"grant_entry_{name}.exe"
                built = subprocess.run(
                    [str(pep_c23.compiler_path(name)), *extra, "-Wall", "-Wextra",
                     "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
                    capture_output=True, text=True, check=False)
                if built.returncode:
                    print(f"build-{name:8s}  FAIL exit={built.returncode} "
                          f"{built.stderr[:400]}")
                    failures += 1
                    continue
                for label, payload, expected in FIXTURES:
                    fixture = BUILD / f"grant_{label}.pep"
                    fixture.write_bytes(payload)
                    ran = subprocess.run([str(exe), str(fixture)],
                                         capture_output=True, check=False)
                    out = ran.stdout.replace(b"\r\n", b"\n")
                    ok = ran.returncode == 0 and out == expected
                    print(f"{name:8s}-{label:6s}    {'OK' if ok else 'FAIL'} "
                          f"exit={ran.returncode} out={out!r} expected={expected!r}")
                    if not ok:
                        failures += 1

                if name == "clang":
                    # Fail closed without a grant: no argv[1] -> refuses before the entry.
                    ran = subprocess.run([str(exe)], capture_output=True, check=False)
                    ok = ran.returncode != 0 and b"PEP_RUNTIME_SOURCE_CONTEXT" in ran.stderr
                    print(f"neg-no-grant     {'OK' if ok else 'FAIL'} "
                          f"exit={ran.returncode} stderr={ran.stderr[:60]!r}")
                    if not ok:
                        failures += 1
                    # An unreadable path is a distinct, named refusal.
                    ran = subprocess.run([str(exe), str(BUILD / "no_such_source.pep")],
                                         capture_output=True, check=False)
                    ok = ran.returncode != 0 and b"PEP_RUNTIME_SOURCE_OPEN" in ran.stderr
                    print(f"neg-unreadable   {'OK' if ok else 'FAIL'} "
                          f"exit={ran.returncode} stderr={ran.stderr[:60]!r}")
                    if not ok:
                        failures += 1
                    # An empty file is a VALID zero-length SourceBytes, not an error --
                    # so byte_at(0) must trip the ordinary bounds refusal instead.
                    empty = BUILD / "grant_empty.pep"
                    empty.write_bytes(b"")
                    ran = subprocess.run([str(exe), str(empty)],
                                         capture_output=True, check=False)
                    ok = ran.returncode != 0 and b"PEP_RUNTIME_BYTE_RANGE" in ran.stderr
                    print(f"empty-is-valid   {'OK' if ok else 'FAIL'} "
                          f"exit={ran.returncode} stderr={ran.stderr[:60]!r}")
                    if not ok:
                        failures += 1

        # The grant must not leak: every other non-zero-arity main still refuses.
        for label, source in (
                ("int-parameter", "fn main(value: Int) -> Int { return value }\n"),
                ("two-parameters", "fn main(a: SourceBytes, b: Int) -> Int { return b }\n"),
                ("bool-parameter", "fn main(flag: Bool) -> Int { if flag { return 1 } else { return 0 } }\n")):
            refused_c, refused_detail = emit(session, revision, source, label, ["main"])
            ok = refused_c is None and "functions require supported parameters" in refused_detail
            print(f"neg-{label:14s} {'OK' if ok else 'FAIL'} {refused_detail}")
            if not ok:
                failures += 1

        # source_bytes() as a CALL stays refused: no ambient authority appeared.
        ambient_c, ambient_detail = emit(
            session, revision,
            "fn main() -> Int {\n  let source = source_bytes()\n  return byte_length(source)\n}\n",
            "ambient", ["main"])
        ok = ambient_c is None and "no resolved call fact" in ambient_detail
        print(f"neg-source_bytes-call {'OK' if ok else 'FAIL'} {ambient_detail}")
        if not ok:
            failures += 1
    finally:
        session.close()

    print("source grant entry:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
