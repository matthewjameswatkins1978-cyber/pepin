"""SourceBytes ingress probe: what lowers, what refuses, and how the emitted runtime
behaves on the byte edges the lexer actually meets.

Two separate questions, kept separate on purpose:

1. **Does the emitter lower SourceBytes byte access?** A function taking a
   `SourceBytes` parameter and reading it through `byte_length` / `byte_at` is the
   shape the real lexer's `scan_*_at` helpers use. Measured here: it lowers.
2. **Can a native program OBTAIN a SourceBytes?** `source_bytes()` is a host grant.
   Measured here: the emitter refuses it, so a native program cannot mint one.

Because (2) refuses, a Pep-level native program cannot yet exercise byte access
end to end. So the runtime substrate is tested directly: the emitted C is compiled
with its `main` renamed (`-Dmain=pep_program_main`) and linked against a small
driver that supplies `pep_source_bytes` values. This is a **runtime-substrate**
test, not a claim of Pep-level native execution -- the driver is hand-written C,
and it is labelled as such in the output.

Run: python tests/probe_source_bytes_runtime.py
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

# The real lexer's scan_*_at shape: a SourceBytes parameter read through
# byte_length and byte_at. The trailing return is required by the emitter's
# "functions require a return statement" rule (measured: the if/else-only form
# refuses with exactly that diagnostic, which is a shape rule, not a SourceBytes one).
SB_PARAM = (
    "fn first_byte(source: SourceBytes) -> Int {\n"
    "  if byte_length(source) == 0 { return -1 } else {}\n"
    "  return byte_at(source, 0)\n"
    "}\n"
    "fn main() -> Int { return 0 }\n")

# The separate question: can a native program obtain a SourceBytes at all?
SB_GRANT = (
    "fn main() -> Int {\n"
    "  let source = source_bytes()\n"
    "  return byte_length(source)\n"
    "}\n")

DRIVER = r"""
#include <stdio.h>
/* Include the emitted program so the driver sees its typedefs and runtime helpers.
   `main` is renamed only for the included text, so the driver keeps its own. */
#define main pep_program_main
#include "sb_param_program.c"
#undef main

int main(void) {
  const unsigned char empty[] = "";
  const unsigned char one[] = "A";
  const unsigned char nul[] = {0x00, 0x41};
  const unsigned char utf8[] = {0xC3, 0xA9}; /* U+00E9, two bytes */
  printf("%lld\n", (long long)pep_fn_first_byte((pep_source_bytes){empty, 0}));
  printf("%lld\n", (long long)pep_fn_first_byte((pep_source_bytes){one, 1}));
  printf("%lld\n", (long long)pep_fn_first_byte((pep_source_bytes){nul, 2}));
  printf("%lld\n", (long long)pep_fn_first_byte((pep_source_bytes){utf8, 2}));
  return 0;
}
"""

# Out-of-bounds and invalid-handle negatives, each its own process so the abort is
# observable as an exit code and a stderr code rather than killing the whole run.
NEG_DRIVER = r"""
#include <stdio.h>
#define main pep_program_main
#include "sb_param_program.c"
#undef main
int main(void) {
  const unsigned char one[] = "A";
  printf("%lld\n", (long long)pep_byte_at((pep_source_bytes){one, 1}, 1));
  return 0;
}
"""

NEG_INVALID_DRIVER = r"""
#include <stdio.h>
#define main pep_program_main
#include "sb_param_program.c"
#undef main
int main(void) {
  printf("%lld\n", (long long)pep_byte_length((pep_source_bytes){NULL, 5}));
  return 0;
}
"""

EXPECTED = b"-1\n65\n0\n195\n"


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

        param_c, param_detail = emit(session, revision, SB_PARAM, "sb-param")
        print(f"sb-param emit    {'OK' if param_c else 'REFUSED'} {param_detail}")
        if not param_c:
            failures += 1

        grant_c, grant_detail = emit(session, revision, SB_GRANT, "sb-grant")
        print(f"sb-grant emit    {'OK' if grant_c else 'REFUSED'} {grant_detail}")
        # A refusal here is the FINDING, not a failure: source_bytes() is a host grant.
    finally:
        session.close()

    if not param_c:
        print("SourceBytes runtime: SKIP (byte access did not emit)")
        return 1

    c_path = BUILD / "sb_param_program.c"
    c_path.write_text(param_c, encoding="utf-8", newline="\n")
    driver_path = BUILD / "sb_param_driver.c"
    driver_path.write_text(DRIVER, encoding="utf-8", newline="\n")

    for name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        exe = BUILD / f"sb_param_{name}.exe"
        built = subprocess.run(
            [str(pep_c23.compiler_path(name)), *extra, "-Wall", "-Wextra",
             "-Wpedantic", "-Werror", "-O2",
             str(driver_path), "-o", str(exe)],
            capture_output=True, text=True, check=False)
        if built.returncode:
            print(f"runtime-{name:6s}  FAIL build exit={built.returncode} "
                  f"{built.stderr[:400]}")
            failures += 1
            continue
        ran = subprocess.run([str(exe)], capture_output=True, check=False)
        out = ran.stdout.replace(b"\r\n", b"\n")
        ok = out == EXPECTED
        print(f"runtime-{name:6s}  {'OK' if ok else 'FAIL'} "
              f"empty/one/NUL/UTF-8 out={out!r}")
        if not ok:
            failures += 1

    # Bounds and invalid-handle negatives: the runtime must fail closed, not read past.
    for label, source, code in (
            ("bounds", NEG_DRIVER, b"PEP_RUNTIME_BYTE_RANGE"),
            ("invalid-handle", NEG_INVALID_DRIVER, b"PEP_RUNTIME_INVALID_SOURCE_BYTES")):
        neg_path = BUILD / f"sb_neg_{label}.c"
        neg_path.write_text(source, encoding="utf-8", newline="\n")
        exe = BUILD / f"sb_neg_{label}.exe"
        built = subprocess.run(
            [str(pep_c23.compiler_path("clang")), "-std=c23", "-Wall", "-Wextra",
             "-Wpedantic", "-Werror", "-O2",
             str(neg_path), "-o", str(exe)],
            capture_output=True, text=True, check=False)
        if built.returncode:
            print(f"neg-{label:14s} FAIL build exit={built.returncode} "
                  f"{built.stderr[:300]}")
            failures += 1
            continue
        ran = subprocess.run([str(exe)], capture_output=True, check=False)
        ok = ran.returncode != 0 and code in ran.stderr
        print(f"neg-{label:14s} {'OK' if ok else 'FAIL'} exit={ran.returncode} "
              f"stderr={ran.stderr[:80]!r}")
        if not ok:
            failures += 1

    print("SourceBytes runtime:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
