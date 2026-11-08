#!/usr/bin/env python3
"""A3-S2: independently re-derive A1's Pep-0 semantic oracle (verification/probes).

A1's `tests/test_a1_pep0_oracle.py` pins 23 fixtures against the SEED with an exact
diagnostic code AND an exact span (start offset, endOffset, line, column), and states
"any mismatch is a finding, not an oracle edit". That is the second independent oracle
the dispatch wants alongside A4's EXPECTED.md.

A1's test asserts its own table. This re-derives the same assertions from a separate
implementation, reading fixtures out of git so it cannot be fooled by a working-tree
copy. Spans are compared because status-only checks miss offset drift, which is exactly
what the neg_brace expectation changed to (30,30,3,1 -> 28,28,2,1).

  PEPIN_SEED_ROOT=<worktree with a built seed>
  PEPIN_ORACLE_REV=<ledger revision holding tests/fixtures/pep0_oracle>  (default 23d91f6e)

Read-only. Exit 0 only when all 23 match status AND first diagnostic tuple.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

SEED = pathlib.Path(os.environ.get("PEPIN_SEED_ROOT") or
                    pathlib.Path(__file__).resolve().parents[2]).resolve()
REPO = pathlib.Path(__file__).resolve().parents[2]
REV = os.environ.get("PEPIN_ORACLE_REV", "23d91f6e")
SUB = "tests/fixtures/pep0_oracle"

# name -> (status, [(code, start_offset, endOffset, line, column)]), transcribed from
# A1's table at REV. Only the FIRST diagnostic is compared, matching A1's own assertion.
EXPECTED = {
    "pos_42": ("valid", []),
    "pos_ws": ("valid", []),
    "pos_twofn": ("valid", []),
    "neg_unknown": ("invalid", [("PEP_UNKNOWN_FUNCTION", 26, 37, 1, 27)]),
    "neg_arity": ("invalid", [("PEP_ARGUMENT_COUNT", 73, 79, 2, 27)]),
    "neg_rettype": ("invalid", [("PEP_TYPE_MISMATCH", 26, 30, 1, 27)]),
    "neg_brace": ("invalid", [("PEP_PARSE_EXPECTED", 28, 28, 2, 1)]),
    "neg_trail": ("invalid", [("PEP_UNKNOWN_VARIABLE", 30, 37, 1, 31)]),
    "neg_badlit": ("invalid", [("PEP_UNREACHABLE", 27, 28, 1, 28)]),
    "crlf_ok": ("valid", []),
    "nbsp_fn": ("invalid", [("PEP_UNEXPECTED_CHARACTER", 2, 3, 1, 3)]),
    "inc_ws": ("valid", []),
    "empty_zero": ("valid", []),
    "inc_fn": ("invalid", [("PEP_PARSE_EXPECTED", 19, 19, 2, 1)]),
    "inc_ret": ("invalid", [("PEP_PARSE_EXPRESSION", 26, 26, 2, 1)]),
    "out_match": ("invalid", [("PEP_PARSE_PATTERN", 42, 43, 3, 5)]),
    "out_str": ("valid", []),
    "a_nul": ("invalid", [("PEP_UNEXPECTED_CHARACTER", 0, 1, 1, 1)]),
    "a_big19": ("valid", []),
    "a_foo": ("valid", []),
    "a_dup": ("invalid", [("PEP_DUPLICATE_FUNCTION", 25, 49, 2, 1)]),
    "a_gfn": ("invalid", [("PEP_PARSE_EXPRESSION", 8, 10, 1, 9)]),
    "a_grt": ("invalid", [("PEP_UNKNOWN_VARIABLE", 15, 23, 1, 16)]),
}


def fixture(name):
    """Exact bytes from git, never the working tree."""
    blob = subprocess.run(["git", "-C", str(REPO), "cat-file", "blob",
                           f"{REV}:{SUB}/{name}.pep"],
                          capture_output=True, check=False)
    return blob.stdout


def shape(payload):
    with tempfile.NamedTemporaryFile("wb", suffix=".pep", delete=False) as handle:
        handle.write(payload)
        temp = handle.name
    try:
        run = subprocess.run(["pwsh", "-NoProfile", "-File", str(SEED / "pep.ps1"),
                              "check", temp, "--json"],
                             cwd=str(SEED), capture_output=True, text=True, check=False)
        text = (run.stdout or "").strip().lstrip("\ufeff")
        start = text.find("{")
        if start < 0:
            return None, [], (run.stdout or run.stderr or "").strip()[:120]
        try:
            data = json.loads(text[start:])
        except json.JSONDecodeError:
            return None, [], "non-JSON from check"
        diags = []
        for diag in data.get("diagnostics") or []:
            span = diag.get("span") or {}
            begin = span.get("start") or {}
            diags.append((diag.get("code"), begin.get("offset"),
                          span.get("endOffset"), begin.get("line"), begin.get("column")))
        return data.get("status"), diags, ""
    finally:
        os.unlink(temp)


def main():
    print(f"seed  : {SEED}")
    print(f"oracle: {REV}:{SUB}\n")
    bad = 0
    for name, (want_status, want_diags) in EXPECTED.items():
        payload = fixture(name)
        if payload is None:
            print(f"FAIL {name:<12} fixture unreadable")
            bad += 1
            continue
        status, diags, err = shape(payload)
        if status is None:
            print(f"FAIL {name:<12} {err}")
            bad += 1
            continue
        got = diags[:1]
        if status != want_status or got != want_diags[:1]:
            bad += 1
            print(f"FAIL {name:<12} want {(want_status, want_diags[:1])}")
            print(f"{'':<18} got  {(status, got)}  ({len(payload)}B)")
            if len(diags) > 1:
                print(f"{'':<18} note: {len(diags)} diagnostics total")
        else:
            print(f"PASS {name:<12} {status:<8} {got}")
    print(f"\n{len(EXPECTED)} cases, {bad} disagreeing")
    print("A1 SEMANTIC ORACLE: " + ("REPRODUCES" if bad == 0 else "DRIFT"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())