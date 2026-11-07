"""Merged host+emitter grant test: A1's `emit_granted` driving A2's native wrapper.

A1 asked A2 to "consume emit_granted in your vertical (replace your probe's local emit
helper at the merged SHA) and answer the runtime-bytes question so the merged
integration test runs the actual file".

This is that test. It uses A1's host function (`pep_c23.emit_granted`, grant contract v1
derived mode @0640bee) to produce the C, then builds it with strict Clang AND GCC and
runs it over REAL FILES.

RUNTIME-BYTES MECHANISM (the answer A1 asked for): **argv/file**. The emitted wrapper
requires `argc >= 2`, opens `argv[1]`, reads the whole file once into a malloc'd buffer,
binds it as `pep_source_bytes`, and frees it after the entry returns. No cached global,
no second read path -- but there IS a path, which is the open divergence against v1 s6
("no path"). This test therefore runs the actual file, as A1 asked.

Requires the merged host SHA (A1 `0866530` or later), which contains `emit_granted`.
On a tree without it the probe SKIPS rather than failing, so it is safe on A2's branch.

Run: python tests/probe_grant_host_merged.py
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402

BUILD = ROOT / "_build"

ENTRY = "fn main(source: SourceBytes) -> Int { return byte_at(source, 0) }\n"

# (label, file bytes, expected stdout)
FIXTURES = [
    ("ascii", b"A", b"65\n"),
    ("nul", b"\x00A", b"0\n"),
    ("utf8", b"\xc3\xa9", b"195\n"),
]


def main():
    if not hasattr(pep_c23, "emit_granted"):
        print("SKIP: this tree has no pep_c23.emit_granted (needs A1 0866530 or later)")
        return 0
    emit_granted = pep_c23.emit_granted
    GrantRefusal = pep_c23.GrantRefusal

    failures = 0
    session = pep_c23.Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        pep_c23.require(opened, "outcome", "ok", "open compiler bundle")
        pep_c23.require(opened, "status", "valid", "check compiler bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "validate", "bytes": []})
        pep_c23.require(sample, "outcome", "ok", "open validation source")

        spec = __import__("importlib.util", fromlist=["util"]).spec_from_file_location(
            "pic", ROOT / "tests" / "probe_integration_case.py")
        pic = __import__("importlib.util", fromlist=["util"]).module_from_spec(spec)
        spec.loader.exec_module(pic)
        pic.register(session, document, revision, sample["document"], sample["revision"])

        # emit_granted reads the entry shape from chunk_signatures (the checked report
        # elides entry params), so that tool must be registered and active too.
        target_spec = {"document": sample["document"],
                       "revision": sample["revision"], "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(sample["document"], sample["revision"])
        for op, payload, expect_status in (
                ("tool_register",
                 {"tool": "pep-c23-checker-sigs", "document": document,
                  "revision": revision, "function": "chunk_signatures"},
                 "Registered"),
                ("tool_validate",
                 {"tool": "pep-c23-checker-sigs", "document": document,
                  "revision": revision,
                  "testVectors": [{"arguments": [empty_parsed],
                                   "expect": {"type": "List[ResolvedSignature]",
                                              "value": []},
                                   "semanticTarget": target_spec}]},
                 "Validated"),
                ("tool_activate",
                 {"tool": "pep-c23-checker-sigs", "document": document,
                  "revision": revision},
                 "Active")):
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": op, **payload})
            pep_c23.require(response, "status", expect_status, f"{op} sigs")

        # ---- granted: host emits, we build and run the actual file -------------
        result = emit_granted(session, revision, ENTRY.encode("utf-8"),
                              name="grant-merged", entry_name="main", granted=True)
        status = result.get("status")
        csrc = result.get("c_source")
        print(f"host emit_granted  status={status} bytes={len(csrc or '')}")
        if status != "emitted" or not csrc:
            print(f"  refusal={result.get('refusal')}")
            failures += 1
        else:
            if "pep_source_data" not in csrc:
                print("  FAIL: emitted C does not bind pep_source_data")
                failures += 1
            c_path = BUILD / "grant_merged.c"
            c_path.write_text(csrc, encoding="utf-8", newline="\n")
            for compiler_name, extra in (("clang", ["-std=c23"]),
                                         ("gcc", ["-std=c2x"])):
                exe = BUILD / f"grant_merged_{compiler_name}.exe"
                built = subprocess.run(
                    [str(pep_c23.compiler_path(compiler_name)), *extra,
                     "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                     str(c_path), "-o", str(exe)],
                    capture_output=True, text=True, check=False)
                if built.returncode:
                    print(f"  build-{compiler_name} FAIL {built.stderr[:300]}")
                    failures += 1
                    continue
                for label, payload, expected in FIXTURES:
                    fixture = BUILD / f"grant_merged_{label}.pep"
                    fixture.write_bytes(payload)
                    ran = subprocess.run([str(exe), str(fixture)],
                                         capture_output=True, check=False)
                    out = ran.stdout.replace(b"\r\n", b"\n")
                    ok = ran.returncode == 0 and out == expected
                    print(f"  {compiler_name}-{label:6s} {'OK' if ok else 'FAIL'} "
                          f"out={out!r}")
                    if not ok:
                        failures += 1
                if compiler_name == "clang":
                    # argv/file mechanism: no path must fail closed BEFORE the entry.
                    ran = subprocess.run([str(exe)], capture_output=True, check=False)
                    ok = (ran.returncode != 0
                          and b"PEP_RUNTIME_SOURCE_CONTEXT" in ran.stderr)
                    print(f"  neg-no-path    {'OK' if ok else 'FAIL'} "
                          f"exit={ran.returncode}")
                    if not ok:
                        failures += 1

        # ---- the three host refusals, all pre-emitter -------------------------
        for label, source, granted, expected_code in (
                ("GRANT_DENIED", ENTRY, False, "GRANT_DENIED"),
                ("GRANT_SHAPE_MISMATCH",
                 "fn main(value: Int) -> Int { return value }\n", True,
                 "GRANT_SHAPE_MISMATCH"),
                ("GRANT_ENTRY_MISSING",
                 "fn other() -> Int { return 0 }\n", True, "GRANT_ENTRY_MISSING")):
            try:
                emit_granted(session, revision, source.encode("utf-8"),
                             name=f"refuse-{label}", entry_name="main",
                             granted=granted)
                print(f"  {label:20s} FAIL (no refusal raised)")
                failures += 1
            except GrantRefusal as refusal:
                # GrantRefusal carries .code; args[0] is the rendered "code: detail".
                ok = getattr(refusal, "code", None) == expected_code
                print(f"  {label:20s} {'OK' if ok else 'FAIL'} code={refusal.code}")
                if not ok:
                    failures += 1
    finally:
        session.close()

    print("\nmerged host+emitter grant:",
          "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
