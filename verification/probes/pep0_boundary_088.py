#!/usr/bin/env python3
"""A3-S2: independently reproduce A4's normative Pep-0 boundary evidence.

`examples/dogfood/pep0/PEP0_SUBSET.md` @ afd2d7e2 states a NORMATIVE boundary for
compiler-A acceptance and a "Boundary evidence (all measured, this mission)"
section listing seed verdicts for ~17 probe classes. That section is the contract
compiler A is built against, so a wrong verdict there misdirects A silently.

A4 measured them on ignored scratch (`_build/s1/`), which is not replayable. This
regenerates every probe from the documented description and re-runs the seed.

  PEPIN_SEED_ROOT=<worktree with a built seed>

Exit 0 only when every claim reproduces.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(os.environ.get("PEPIN_SEED_ROOT") or
                    pathlib.Path(__file__).resolve().parents[2]).resolve()

# (label, bytes, expected status, expected code substring or "" for valid)
# Transcribed from PEP0_SUBSET.md's claims, in its own order.
PROBES = [
    ("i64max",        b"fn main() -> Int { return 9223372036854775807 }\n",  "valid",   ""),
    ("i64max+1",      b"fn main() -> Int { return 9223372036854775808 }\n",  "invalid", "PEP_INT_LITERAL_RANGE"),
    ("23-digit",      b"fn main() -> Int { return 99999999999999999999999 }\n", "invalid", "PEP_INT_LITERAL_RANGE"),
    ("007",           b"fn main() -> Int { return 007 }\n",                  "valid",   ""),
    ("19-digit",      b"fn main() -> Int { return 1000000000000000000 }\n",   "valid",   ""),
    ("unary-minus",   b"fn main() -> Int { return -42 }\n",                   "valid",   ""),
    ("binop",         b"fn main() -> Int { return 0-42 }\n",                  "valid",   ""),
    ("Main",          b"fn Main() -> Int { return 42 }\n",                    "valid",   ""),
    ("cr-only",       b"fn main() -> Int {\r  return 42\r}\r",                "valid",   ""),
    ("cr-tab",        b"fn\tmain() -> Int {\r\treturn 42\r}\r",               "valid",   ""),
    ("nul-mid",       b"fn ma\x00in() -> Int { return 42 }\n",                "invalid", "PEP_UNEXPECTED_CHARACTER"),
    ("nul-trail",     b"fn main() -> Int { return 42 }\x00\n",                "invalid", "PEP_UNEXPECTED_CHARACTER"),
    ("bom",           b"\xef\xbb\xbffn main() -> Int { return 42 }\n",        "invalid", "PEP_UNEXPECTED_CHARACTER"),
    ("vtab",          b"fn\x0bmain() -> Int { return 42 }\n",                 "invalid", "PEP_UNEXPECTED_CHARACTER"),
    ("nbsp",          b"fn\xc2\xa0main() -> Int { return 42 }\n",             "invalid", "PEP_UNEXPECTED_CHARACTER"),
    ("uppercase-FN",  b"FN main() -> Int { return 42 }\n",                    "invalid", "PEP_PARSE_EXPRESSION"),
    ("lowercase-int", b"fn main() -> int { return 42 }\n",                    "invalid", "PEP_UNKNOWN_TYPE"),
]


def verdict(payload):
    with tempfile.NamedTemporaryFile("wb", suffix=".pep", delete=False) as handle:
        handle.write(payload)
        temp = handle.name
    try:
        run = subprocess.run(["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
                              "check", temp, "--json"],
                             cwd=str(ROOT), capture_output=True, text=True, check=False)
        try:
            report = json.loads(run.stdout)
        except json.JSONDecodeError:
            return None, "no-json", (run.stdout or run.stderr).strip()[:100]
        codes = [d.get("code") or "" for d in (report.get("diagnostics") or [])]
        return report.get("status"), codes, ""
    finally:
        os.unlink(temp)


def main():
    print(f"seed: {ROOT}\nclaim source: PEP0_SUBSET.md @ afd2d7e2\n")
    bad = 0
    for label, payload, want_status, want_code in PROBES:
        status, codes, err = verdict(payload)
        if status is None:
            print(f"FAIL {label:<14} {err}")
            bad += 1
            continue
        status_ok = status == want_status
        code_ok = (not want_code) or (want_code in codes)
        if status_ok and code_ok:
            print(f"PASS {label:<14} status={status:<8} codes={codes}")
        else:
            bad += 1
            print(f"FAIL {label:<14} status={status} (want {want_status}) "
                  f"codes={codes} (want {want_code or 'none'})")
    print(f"\n{len(PROBES)} probes, {bad} disagreeing with A4's documented boundary")
    print("A4 BOUNDARY EVIDENCE: " + ("REPRODUCES" if bad == 0 else "DOES NOT REPRODUCE"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())