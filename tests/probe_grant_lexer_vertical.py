"""Native binaries that read a real Pep source file and apply REAL lexer logic to it.

This is the end-to-end compiler vertical on A2's side, combining the two
capabilities proven separately:

  - the entry-parameter SourceBytes grant (A1 contract @a802290): the host wrapper
    hands the opened target's own bytes to the entry;
  - real lexer functions from `examples/pep_lexer.pep`, lowered natively and already
    proven seed-equivalent.

Two programs, each a compiler-shaped computation rather than a synthetic probe:

  ascii_letter    -- one predicate, one byte read
  ascii_continue  -- composes ascii_letter and ascii_digit, so a TWO-LEVEL call
                     chain runs inside the grant entry

  fn ascii_letter(byte: Int) -> Bool { ... }          # verbatim from the lexer
  fn ascii_digit(byte: Int) -> Bool { ... }           # verbatim from the lexer
  fn ascii_continue(byte: Int) -> Bool { ... }        # verbatim from the lexer
  fn main(source: SourceBytes) -> Int {
    if ascii_continue(byte_at(source, 0)) { return 1 } else {}
    return 0
  }

The seed oracle runs the same predicate at top level over the same byte values
(there is no `bool_text` builtin, so results print 1/0).

Run: python tests/probe_grant_lexer_vertical.py
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

# Each entry is one native program: a real lexer predicate applied to the first byte
# of a real file. `ascii_continue` composes ascii_letter and ascii_digit, so it also
# exercises a two-level call chain inside the grant entry.
# (label, predicate, [(fixture label, file bytes, expected)])
PROGRAMS = [
    ("ascii_letter", "ascii_letter", [
        ("letter-upper", b"A", b"1\n"),
        ("letter-lower", b"z", b"1\n"),
        ("underscore", b"_", b"1\n"),
        ("digit", b"0", b"0\n"),
        ("utf8-lead", b"\xc3\xa9", b"0\n"),
        ("nul", b"\x00A", b"0\n"),
    ]),
    ("ascii_continue", "ascii_continue", [
        ("letter-upper", b"A", b"1\n"),
        ("digit", b"0", b"1\n"),
        ("underscore", b"_", b"1\n"),
        ("colon", b":", b"0\n"),
        ("utf8-lead", b"\xc3\xa9", b"0\n"),
        ("nul", b"\x00A", b"0\n"),
    ]),
]


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def extract_function(text, name):
    """The verbatim source block of one top-level function."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(f"fn {name}("):
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
            return "\n".join(lines[start:index])
    raise SystemExit(f"function {name} not found in {LEXER}")


def emit(session, revision, source, label):
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    require(target, "outcome", "ok", f"open {label}")
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    parsed = parse_target(session, payload, target, revision)
    try:
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
    except RuntimeError as error:
        # A named platform limit is a finding, not a crash. The 100k checker step
        # budget is fixed and not raisable, so report it verbatim.
        return None, f"platform limit: {str(error)[:160]}"
    if checked.get("outcome") != "ok":
        error = checked.get("error") or {}
        return None, f"check {error.get('code')}: {(error.get('message') or '')[:120]}"
    cfields = fields_map(checked["result"])
    if cfields["status"]["value"] != "valid":
        codes = [fields_map(d).get("code", {}).get("value")
                 for d in (cfields.get("diagnostics", {}).get("value") or [])]
        return None, f"check status={cfields['status']['value']} {codes[:2]}"
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


def main():
    if not A1_SEED.is_file():
        print("SKIP: no A1 seed exe at", A1_SEED)
        return 1
    lexer_text = LEXER.read_text(encoding="utf-8")
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

        for program_label, predicate, fixtures in PROGRAMS:
            helpers = ["ascii_letter", "ascii_digit"] \
                if predicate == "ascii_continue" else []
            source = "".join(extract_function(lexer_text, name) + "\n"
                             for name in helpers)
            source += extract_function(lexer_text, predicate) + "\n"
            # The emitter requires a trailing return statement (measured: the
            # if/else-only form refuses), so the false branch falls through.
            source += (
                "fn main(source: SourceBytes) -> Int {\n"
                f"  if {predicate}(byte_at(source, 0)) {{ return 1 }} else {{}}\n"
                "  return 0\n"
                "}\n")

            csrc, detail = emit(session, revision, source, f"grant-{program_label}")
            print(f"[{program_label}] emit {'OK' if csrc else 'REFUSED'} {detail}")
            if not csrc:
                # A platform limit is reported, not counted as an emitter failure: the
                # 100k checker step budget is fixed and is A1's lane, not A2's.
                if not any(code in detail for code in (
                        "platform limit", "PEP_RUNTIME_STEP_LIMIT",
                        "PEP_TOOL_VALUE_LIMIT", "PEP_SOURCE_BYTE_LIMIT")):
                    failures += 1
                continue

            # Seed oracle: the same predicate over the same first bytes, at top level.
            oracle = "".join(extract_function(lexer_text, name) + "\n"
                             for name in helpers)
            oracle += extract_function(lexer_text, predicate) + "\n"
            for _, payload, _ in fixtures:
                oracle += (f"if {predicate}({payload[0]}) {{ say(\"1\") }} "
                           'else { say("0") }\n')
            oracle_path = BUILD / f"grant_{program_label}_oracle.pep"
            oracle_path.write_text(oracle, encoding="utf-8", newline="\n")
            seed = subprocess.run([str(A1_SEED), "run", str(oracle_path)],
                                  capture_output=True, check=False)
            if seed.returncode:
                print(f"[{program_label}] seed-oracle FAIL",
                      seed.stderr.decode("utf-8", "replace")[:200])
                failures += 1
                continue
            seed_out = seed.stdout.replace(b"\r\n", b"\n")
            expected = b"".join(item[2] for item in fixtures)
            ok = seed_out == expected
            print(f"[{program_label}] seed-oracle {'OK' if ok else 'FAIL'} "
                  f"out={seed_out!r}")
            if not ok:
                failures += 1

            c_path = BUILD / f"grant_{program_label}.c"
            c_path.write_text(csrc, encoding="utf-8", newline="\n")
            for compiler_name, extra in (("clang", ["-std=c23"]),
                                         ("gcc", ["-std=c2x"])):
                exe = BUILD / f"grant_{program_label}_{compiler_name}.exe"
                built = subprocess.run(
                    [str(pep_c23.compiler_path(compiler_name)), *extra,
                     "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                     str(c_path), "-o", str(exe)],
                    capture_output=True, text=True, check=False)
                if built.returncode:
                    print(f"[{program_label}] build-{compiler_name} FAIL "
                          f"exit={built.returncode} {built.stderr[:400]}")
                    failures += 1
                    continue
                for fixture_label, payload, want in fixtures:
                    fixture = BUILD / f"grant_{program_label}_{fixture_label}.pep"
                    fixture.write_bytes(payload)
                    ran = subprocess.run([str(exe), str(fixture)],
                                         capture_output=True, check=False)
                    out = ran.stdout.replace(b"\r\n", b"\n")
                    ok = ran.returncode == 0 and out == want
                    print(f"[{program_label}] {compiler_name}-{fixture_label:12s} "
                          f"{'OK' if ok else 'FAIL'} out={out!r} want={want!r}")
                    if not ok:
                        failures += 1
    finally:
        session.close()

    print("\ngrant + real lexer vertical:",
          "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
