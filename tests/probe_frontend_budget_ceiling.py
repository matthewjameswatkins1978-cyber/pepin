"""How many bytes of Pep source can the compiler's own front end process in one budget?

This is the scalability number for Road 1, and it is much smaller than the project's
own documentation implies.

The zero-argument `emit_c23()` entry does `parser_parse_program()` ->
`analyze_parsed(parsed)` -> `emit_c23_checked(...)` inside ONE 100k step budget. That
is the path `tests/test_a14_c23.py` drives. Measured here by A/B on a single byte:

  144 bytes  -> emitted
  145 bytes  -> PEP_RUNTIME_STEP_LIMIT

So the front end costs roughly 700 steps per source byte, and the whole budget buys
about 144 bytes. The compiler source closure is ~536 KB, so self-hosting needs
roughly 3700x more budget than one invocation provides -- or a fundamentally cheaper
front end, or staged checking.

WHY THIS MATTERS FOR A2: it explains the "emitter headroom" finding. The emitter is
not too big; the budget is consumed LEXING AND PARSING the fixture (the step limit
fires inside `lexer_step`'s name-scanning loop, at byte 9218 of the bundle, which is
`examples/pep_lexer.pep`). Any addition anywhere on the per-node path leaves less for
the front end, which is why per-node emitter functions are frozen while O(1) ones are
not.

The probe asserts the CURRENT ceiling so that a future improvement is visible as a
number moving, not as a vague claim.

Run: python tests/probe_frontend_budget_ceiling.py
"""
import sys

ROOT = None
try:
    import pathlib
    ROOT = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
except Exception:  # noqa: BLE001
    pass

from tests.test_a14_c23 import A14C23EmissionTests  # noqa: E402

# The fixture the recursive-depth test uses, with and without its trailing newline.
BASE = ("fn main() -> Int { return countdown(510) }\n"
        "fn countdown(value: Int) -> Int {\n"
        " if value <= 0 { return 42 } else { return countdown(value - 1) }\n}")

# (label, source, expect_emitted)
CASES = [
    ("144-bytes", BASE, True),
    ("145-bytes", BASE + "\n", False),
]


def main():
    A14C23EmissionTests.setUpClass()
    test = A14C23EmissionTests("test_recursive_native_calls_enforce_pep_depth")
    test.setUp()
    failures = 0
    try:
        for label, source, expect_emitted in CASES:
            size = len(source.encode("utf-8"))
            try:
                result = test._emit(source)
                status = result.get("status", {}).get("value")
                emitted = status == "emitted"
                detail = f"status={status}"
            except AssertionError as error:
                text = str(error)
                emitted = False
                detail = "PEP_RUNTIME_STEP_LIMIT" if "STEP_LIMIT" in text else text[:80]
            ok = emitted == expect_emitted
            print(f"{label:12s} bytes={size:4d} emitted={emitted!s:5s} "
                  f"expected={expect_emitted!s:5s} {'OK' if ok else 'CHANGED'} {detail}")
            if not ok:
                failures += 1
    finally:
        test.tearDown()

    if failures:
        print("\nfront-end budget ceiling: CHANGED -- update this probe's expectation "
              "and the Road 1 scalability note")
    else:
        print("\nfront-end budget ceiling: 144 bytes (unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
