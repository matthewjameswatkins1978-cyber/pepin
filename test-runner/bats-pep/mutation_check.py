"""Mutation check: does the self-test actually detect semantic bugs?

`differential.py` proves the oracle agrees with the Rust reference. This proves
something different and complementary: that a semantic defect in the oracle's own
logic changes the self-test output.

That distinction matters. A suite of ninety-odd cases that still passes after `all`
and `any` have their precedence swapped is not evidence, however long it looks. Each
mutation below is a single exact-string defect applied to `oracle.pep`; the check fails
if any mutation leaves the output identical.

Usage: python mutation_check.py
Exit 0 when every mutation is detected, 1 if any survives, 2 if the harness cannot run.
"""
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PEP = REPO / "pep.ps1"
ORACLE = REPO / "test-runner" / "bats-pep" / "oracle.pep"
SELFTEST = REPO / "test-runner" / "bats-pep" / "selftest.pep"

# (name, exact text in oracle.pep, defective replacement)
#
# Each one is a plausible mistake rather than a random character flip: swapping a
# comparison, dropping a guard, ignoring a whole input field, or returning the
# confident verdict where the reference demands the cautious one.
MUTATIONS = [
    ("equals-inverted",
     "ObservedExit(code) => if code == expected {",
     "ObservedExit(code) => if code != expected {"),
    ("not-stops-inverting",
     'NotObserved(why) => Proven("the negated condition was not falsified")',
     'NotObserved(why) => NotObserved("the negated condition was not falsified")'),
    ("run-phase-misspelled",
     'if phase == "run" { known = true }',
     'if phase == "runner" { known = true }'),
    ("untracked-ignored",
     "return contains(changes.untracked_paths, path)",
     "return false"),
    ("unloadable-source-fires",
     "SourceContentUnavailable(why) => Inconclusive(why)",
     'SourceContentUnavailable(why) => Proven("unavailable")'),
    ("not-utf8-fires",
     "SourceContentNotUtf8(why) => Inconclusive(why)",
     'SourceContentNotUtf8(why) => Proven("bytes")'),
    ("text-search-inverted",
     'Proven("the needle is present in the source text")',
     'NotObserved("the needle is present in the source text")'),

    ("find-step-ignores-phase",
     "step.phase == phase && step.index == index",
     "step.index == index"),
    ("empty-all-fires",
     'var verdict = Proven("every condition was falsified")',
     'var verdict = NotObserved("every condition was falsified")'),
    ("both-modes-not-invalid",
     'Invalid("both equals and not_equals were specified")',
     'NotObserved("both equals and not_equals were specified")'),
    ("bad-stream-accepted",
     'return SourceRejected("stream must be `stdout` or `stderr`")',
     "return SourceShapeValid()"),
]


def run_composed(oracle_text, workdir, tag):
    composed = workdir / ("composed_%s.pep" % tag)
    source = oracle_text + "\n" + SELFTEST.read_text(encoding="utf-8")
    composed.write_text(source, encoding="utf-8", newline="\n")
    proc = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP), "run", str(composed)],
                          text=True, capture_output=True, timeout=600)
    return proc.returncode, (proc.stdout or "").splitlines()


def main():
    origin = ORACLE.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        workdir = pathlib.Path(tmp)
        base_rc, base = run_composed(origin, workdir, "baseline")
        if base_rc != 0 or not base:
            print("HARNESS-ERROR baseline self-test did not run cleanly")
            return 2
        print("baseline: %d output lines" % len(base))

        survived = []
        stale = []
        for name, defect, replacement in MUTATIONS:
            count = origin.count(defect)
            if count != 1:
                # A mutation that no longer matches is a stale guard, not a pass.
                stale.append("%s (%d matches)" % (name, count))
                print("CASE %-24s STALE: anchor matched %d times, expected 1"
                      % (name, count))
                continue
            rc, out = run_composed(origin.replace(defect, replacement), workdir, name)
            if rc != 0:
                print("CASE %-24s CAUGHT (mutant failed to run)" % name)
                continue
            first = next((i for i in range(max(len(base), len(out)))
                          if i >= len(base) or i >= len(out) or base[i] != out[i]), None)
            if first is None:
                survived.append(name)
                print("CASE %-24s SURVIVED (output identical)" % name)
            else:
                got = out[first] if first < len(out) else "<missing>"
                print("CASE %-24s CAUGHT output line %d: %s -> %s"
                      % (name, first, base[first], got))

    print("SUMMARY mutations=%d survived=%d stale=%d"
          % (len(MUTATIONS), len(survived), len(stale)))
    return 0 if not survived and not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
