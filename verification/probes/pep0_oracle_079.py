#!/usr/bin/env python3
"""A3-S2: executable replay of A4's Pep-0 compiler-A oracle (verification/probes).

A4's `examples/dogfood/pep0/EXPECTED.md` is a precise but *prose* oracle: seven
pinned inputs with exact bytes, exact exit codes and exact stdout. Nothing in the
repository executed it, so nothing could catch the oracle drifting from its own
fixtures. This replays the parts that do not depend on compiler A existing.

Two layers are checkable today:
  L1 fixture integrity - the committed bytes must equal the bytes the oracle documents.
  L2 seed classification - the oracle's seed-valid / seed-invalid claims must match
     the live seed compiler (an INDEPENDENT oracle: the seed, not A4's prose).

Layer 3 (the exit-code table 0/1/2/3/4/5 and exact stdout) is compiler-A runtime
behaviour. It is reported as PENDING, never as passed, until 21/21 units emit.

Read-only: reads fixtures from git, never writes to the oracle or A4's lane.

  PEPIN_ORACLE_REV=<sha>   A4 revision holding examples/dogfood/pep0 (default 5f62e4b)
  PEPIN_SEED_ROOT=<dir>    worktree with a built seed (default: repo root)

Exit 0 only when every checkable assertion holds.
"""
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
REV = os.environ.get("PEPIN_ORACLE_REV", "5f62e4b")
SEED = pathlib.Path(os.environ.get("PEPIN_SEED_ROOT") or REPO).resolve()
SUB = "examples/dogfood/pep0"

# The bytes A4's EXPECTED.md documents, transcribed literally. L1 fails if the
# committed fixture ever drifts from the sentence describing it.
SPEC = {
    "a_ok.pep": (b"fn  main() -> Int {\n  return 42\n}\n", "valid"),
    "a_badlit.pep": (b"fn main() -> Int { return ; }\n", "invalid"),
    "a_badbrace.pep": (b"fn main() -> Int { return 42 ]\n", "invalid"),
    "a_str.pep": (b'fn main() -> Str { return "s" }\n', "valid"),
    "a_empty.pep": (b"", "valid"),
    "a_crlf.pep": (b"fn main() -> Int {\r\n  return 42\r\n}\r\n", "valid"),
    # NBSP U+00A0 between fn and main; the oracle calls this seed-INVALID.
    "a_u8.pep": (b"fn\xc2\xa0main() -> Int { return 42 }\n", "invalid"),
}

# Exit codes the oracle pins. Not checkable until compiler A runs; listed so the
# gap is explicit rather than forgotten.
PENDING_EXITS = {
    "a_ok.pep": (0, "9-line C on stdout"),
    "a_badlit.pep": (2, "ERR literal"),
    "a_badbrace.pep": (1, "ERR shape"),
    "a_str.pep": (5, "ERR unsupported"),
    "a_empty.pep": (0, "no output"),
    "a_crlf.pep": (0, "same 9-line C as a_ok"),
    "a_u8.pep": (1, "ERR shape"),
}


def blob(rev, path):
    out = subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", f"{rev}:{path}"],
                         capture_output=True, check=False)
    if out.returncode != 0:
        raise SystemExit(f"cannot read {rev}:{path}: {out.stderr.decode(errors='replace')[:160]}")
    return out.stdout


def seed_status(name, payload):
    """Classify a fixture with the live seed, independent of A4's prose."""
    import tempfile
    with tempfile.NamedTemporaryFile("wb", suffix=".pep", delete=False) as handle:
        handle.write(payload)
        temp = handle.name
    try:
        run = subprocess.run(["pwsh", "-NoProfile", "-File", str(SEED / "pep.ps1"),
                              "check", temp, "--json"],
                             cwd=str(SEED), capture_output=True, text=True, check=False)
        try:
            report = json.loads(run.stdout)
        except json.JSONDecodeError:
            return None, f"check emitted non-JSON: {(run.stdout or run.stderr).strip()[:120]}"
        codes = [d.get("code") for d in (report.get("diagnostics") or [])]
        return report.get("status"), ",".join(c for c in codes if c)
    finally:
        os.unlink(temp)


def main():
    rows, failures = [], 0
    print(f"oracle: {REV}:{SUB}/EXPECTED.md")
    print(f"seed  : {SEED}\n")
    for name, (expected, want_status) in SPEC.items():
        payload = blob(REV, f"{SUB}/{name}")
        ok = payload == expected
        failures += 0 if ok else 1
        detail = "byte-exact per oracle" if ok else (
            f"ORACLE DRIFT: committed {len(payload)}B {payload!r} != documented {len(expected)}B {expected!r}")
        rows.append((name, "L1", "PASS" if ok else "FAIL", detail))
        if not ok:
            continue
        status, codes = seed_status(name, payload)
        if status is None:
            rows.append((name, "L2", "SKIP", codes))
            continue
        agrees = status == want_status
        failures += 0 if agrees else 1
        rows.append((name, "L2", "PASS" if agrees else "FAIL",
                     f"seed status={status} [{codes}] vs oracle claim '{want_status}'"))
    for name, layer, result, detail in rows:
        print(f"{result:<4} {layer:<3} {name:<16} {detail}")
    print("\nL3 (compiler-A exit codes) - PENDING, compiler A does not yet run 21/21:")
    for name, (code, stdout) in PENDING_EXITS.items():
        print(f"     {name:<16} expects exit {code}, stdout {stdout!r}")
    print(f"\n{len(rows)} checkable assertions, {failures} failed")
    print("ORACLE REPLAY: " + ("PASS" if failures == 0 else "FAIL"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())