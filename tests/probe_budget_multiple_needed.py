"""How many times the budget would have to grow for lexer_step's biggest statement?

The cost model is now settled: the checker is ~linear in node count with a
construct-dependent constant, and the ceiling is ~40-56 nodes per 100k budget. That
means each node costs roughly 100k / ceiling steps.

This turns that into the number a design decision actually needs: for the largest
single statement in the compiler source, how many times over budget is it?

A1's receipt 017 reports a 1033-node statement in lexer_step. If a node costs ~2000
steps, that statement needs ~2M steps against a 100k budget.

This is arithmetic on measured ceilings, not a new measurement, and it is labelled as
such. The per-node cost varies by construct, so the answer is a range, not a point.

Run: python tests/probe_budget_multiple_needed.py
"""
import sys

BUDGET = 100_000

# Measured ceilings from probe_checker_construct_cost.py: (construct, max nodes).
CEILINGS = [
    ("record", 37),
    ("let", 40),
    ("call", 44),
    ("if", 56),
    ("while", 56),
    ("string", 56),
]

# A1 receipt 017: the largest single statement in lexer_step.
LEXER_STEP_STATEMENT_NODES = 1033


def main():
    print(f"budget: {BUDGET:,} steps\n")
    print(f"{'construct':10s} | {'ceiling':>7} | {'steps/node':>10} | "
          f"{'1033-node stmt needs':>20} | multiple")
    multiples = []
    for name, ceiling in CEILINGS:
        per_node = BUDGET / ceiling
        needed = per_node * LEXER_STEP_STATEMENT_NODES
        multiple = needed / BUDGET
        multiples.append(multiple)
        print(f"{name:10s} | {ceiling:>7} | {per_node:>10,.0f} | "
              f"{needed:>20,.0f} | {multiple:>6.1f}x")

    low, high = min(multiples), max(multiples)
    print(f"\nlexer_step's 1033-node statement needs {low:.1f}x to {high:.1f}x the "
          f"current budget.")
    print(f"Equivalently, the per-node cost would have to fall by the same factor.")
    print(f"\nThis is arithmetic on measured ceilings, not a new measurement. The")
    print(f"per-node cost varies by construct, so read it as a range.")
    print(f"\nIt also means: no amount of statement-level carving helps, because ONE")
    print(f"statement is already {low:.0f}x over. The unit has to be smaller than a")
    print(f"statement, or the per-node cost has to fall.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
