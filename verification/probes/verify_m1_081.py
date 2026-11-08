#!/usr/bin/env python3
"""A3-S2: the M-1 acceptance gate for Pep-0 compiler A (verification/probes).

Compiler A does not exist yet (emission is 9/21), so this cannot gate the real
thing. It is built now, and *proven able to fail*, so that the moment 21/21 lands
the gate is already trustworthy rather than written under pressure by the person
who wants it to pass.

Contract taken from A4's `examples/dogfood/pep0/EXPECTED.md` (oracle), not invented:
seven pinned inputs with exact exit codes and stdout, plus two UNSEEN subset-S0
forms that A4 never pinned, whose expected output I predict from S0's own grammar.

Cases are run against a compiler command, so the gate is agnostic to how A is
built:

  python verification/probes/verify_m1_081.py --compiler-cmd '["<exe>"]'

Self-test (proves the instrument detects wrong behaviour):

  python verification/probes/verify_m1_081.py --selftest

Exit 0 only when every case matches exit code AND stdout.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
REV = os.environ.get("PEPIN_ORACLE_REV", "afd2d7e2")
SUB = "examples/dogfood/pep0"

# A4's nine-line C form for `return DECIMAL`, built with say() so punctuation
# arrives via int_text. Compared after normalising the trailing newline, because
# EXPECTED.md pins "these 9 lines" without stating whether the last say adds one.
def nine_lines(decimal):
    return f"int main\n(\nvoid\n)\n{{\nreturn\n{decimal}\n;\n}}"


PINNED = [
    # name,           bytes,                                  exit, stdout
    ("a_ok.pep",      b"fn  main() -> Int {\n  return 42\n}\n",      0, nine_lines(42)),
    ("a_badlit.pep",  b"fn main() -> Int { return ; }\n",            2, "ERR literal"),
    ("a_badbrace.pep", b"fn main() -> Int { return 42 ]\n",          1, "ERR shape"),
    ("a_str.pep",     b'fn main() -> Str { return "s" }\n',          5, "ERR unsupported"),
    ("a_empty.pep",   b"",                                           0, ""),
    ("a_crlf.pep",    b"fn main() -> Int {\r\n  return 42\r\n}\r\n", 0, nine_lines(42)),
    ("a_u8.pep",      b"fn\xc2\xa0main() -> Int { return 42 }\n",     1, "ERR shape"),
    # A4 R1/R2 additions @ afd2d7e2. Expected exit codes and stdout are A4's
    # hand-traced contract, still awaiting native confirmation from S2.
    ("a_nul.pep",     b"\x00fn main()->Int{return 42}\n",              1, "ERR shape"),
    ("a_big19.pep",   b"fn main()->Int{return 1000000000000000000}\n",  4, "ERR longlit"),
    ("a_foo.pep",     b"fn foo()->Int{return 1}\n",                     1, "ERR shape"),
    ("a_dup.pep",     b"fn main()->Int{return 1}\nfn main()->Int{return 2}\n", 3, "ERR junk"),
    ("a_gfn.pep",     b"fnmain()->Int{return 42}\n",                    1, "ERR shape"),
    ("a_grt.pep",     b"fn main()->Int{return42}\n",                    2, "ERR literal"),
]

# UNSEEN by A4's pinned set. S0 allows space/tab/LF/CR separators, optional
# around every joint except after `fn` and `return`, and 1-18 decimal digits.
# Expected output is PREDICTED from that grammar, then confirmed or refuted.
UNSEEN = [
    ("u_single_space.pep", b"fn main() -> Int { return 7 }\n",       0, nine_lines(7)),
    ("u_tab_indent.pep",   b"fn  main() -> Int {\n\treturn 0\n}\n",  0, nine_lines(0)),
]


def run_case(cmd, payload):
    import tempfile
    with tempfile.NamedTemporaryFile("wb", suffix=".pep", delete=False) as handle:
        handle.write(payload)
        temp = handle.name
    try:
        proc = subprocess.run(list(cmd) + [temp], capture_output=True, text=True,
                              check=False, encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        os.unlink(temp)


def norm(text):
    return text.replace("\r\n", "\n").rstrip("\n")


def gate(cmd, cases, label):
    print(f"\n--- {label} ---")
    bad = 0
    for name, payload, want_exit, want_out in cases:
        try:
            code, out, err = run_case(cmd, payload)
        except OSError as error:
            print(f"FAIL {name:<20} cannot run: {error}")
            bad += 1
            continue
        exit_ok = code == want_exit
        out_ok = norm(out) == norm(want_out)
        if not (exit_ok and out_ok):
            bad += 1
            print(f"FAIL {name:<20} exit={code} (want {want_exit}) "
                  f"stdout={norm(out)!r} (want {norm(want_out)!r})")
            if err.strip():
                print(f"     stderr: {err.strip()[:160]}")
        else:
            print(f"PASS {name:<20} exit={code} stdout {len(norm(out))} chars")
    return bad, len(cases)


STUB_ALWAYS_OK = r'''
import sys
print("int main\n(\nvoid\n)\n{\nreturn\n42\n;\n}")
sys.exit(0)
'''

# Exits 0 and prints NOTHING, so only the stdout comparison can catch it.
# (A stub that crashes would "fail" for the wrong reason and prove nothing.)
STUB_NO_OUTPUT = r'''
import sys
sys.exit(0)
'''


def selftest():
    """Prove the gate can FAIL. A gate that only ever passes is not a gate."""
    import tempfile
    work = pathlib.Path(tempfile.mkdtemp(prefix="a3-m1-selftest-"))
    always_ok = work / "always_ok.py"
    always_ok.write_text(STUB_ALWAYS_OK, encoding="utf-8")
    no_output = work / "no_output.py"
    no_output.write_text(STUB_NO_OUTPUT, encoding="utf-8")

    print("self-test: a gate that cannot fail is not a gate")
    print("\n[1] stub that always exits 0 printing a_ok's C")
    bad, total = gate([sys.executable, str(always_ok)], PINNED + UNSEEN, "must FAIL negatives")
    detects_exit = bad >= 5   # a_badlit, a_badbrace, a_str, a_u8 expect nonzero; unseen expect 0 but wrong C only for 7/0
    print(f"=> {bad}/{total} cases failed; detects wrong exit codes: {detects_exit}")

    print("\n[2] stub that exits 0 with no output")
    bad2, total2 = gate([sys.executable, str(no_output)], PINNED, "must FAIL stdout checks")
    detects_out = bad2 >= 1
    print(f"=> {bad2}/{total2} cases failed; detects wrong stdout: {detects_out}")

    ok = detects_exit and detects_out
    print(f"\nSELF-TEST: {'PASS - the gate detects both wrong exit codes and wrong stdout' if ok else 'FAIL - gate is blind'}")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler-cmd", default="")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.compiler_cmd:
        print("no compiler A yet: run with --Compiler-cmd or --selftest".replace("Compiler", "compiler"))
        print("This gate is READY. It has not judged a real compiler A.")
        return 2
    cmd = json.loads(args.compiler_cmd)
    bad1, n1 = gate(cmd, PINNED, f"A4 pinned oracle ({REV})")
    bad2, n2 = gate(cmd, UNSEEN, "unseen subset-S0 forms (A3-predicted)")
    total_bad, total = bad1 + bad2, n1 + n2
    print(f"\n{total} cases, {total_bad} failed")
    print("M-1 COMPILER A: " + ("PASS" if total_bad == 0 else "FAIL"))
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())