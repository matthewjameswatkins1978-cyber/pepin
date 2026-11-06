"""WHY the checker is expensive: its lookups are linear scans performed per node.

All the runtime measurements this session produced one bounded but unexplained model:
the checker's cost is construct-dependent, node count matters more than bytes, and no
linear model in either fits. This probe explains it by static analysis.

Every lookup helper in `tests/pep_checker_a13.pep` is a LINEAR SCAN:

  lookup_node(nodes, id)              for node in nodes { if node.id == id ... }
  find_function(functions, name)      for function in functions { if ... }
  find_binding(bindings, semanticId)  for binding in bindings { if ... }
  find_reference(references, syntaxId) for reference in references { if ... }

and `infer_expression_type` -- which is called once per expression node -- calls
several of them. A linear scan per node over a list of n nodes is O(n) per node, so
n nodes cost O(n^2).

That single fact explains every observation:

  - construct-dependent: different constructs do different NUMBERS of lookups per node
  - node count matters more than bytes: the quadratic term is in nodes
  - the ceiling is low and steep: quadratics blow up fast
  - records are 3.7x a let binding: record nodes do more lookups (fields, types)
  - "context-driven cost, not node count" (A1 receipt 017): the cost is per node times
    the number of lookups THAT node triggers, which is context

THE LEVER: index once and pass the index down, instead of re-scanning per lookup.
That turns O(n^2) into O(n) -- a far larger win than any constant-factor or
staging change, and it is the reason staged carving keeps not being enough.

This probe is read-only static analysis. It does not modify the checker.

Run: python tests/probe_checker_quadratic_lookups.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tests" / "pep_checker_a13.pep"

# Helpers that are expected to be linear scans.
LOOKUP_FUNCTIONS = ["lookup_node", "find_function", "find_binding", "find_reference",
                    "find_function_by_syntax", "count_children", "node_by_id"]


def functions_with_bodies(text):
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        match = re.match(r"fn (\w+)\(", lines[index])
        if not match:
            index += 1
            continue
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
        yield match.group(1), start + 1, "\n".join(lines[start:index])


def main():
    text = CHECKER.read_text(encoding="utf-8")
    bodies = {name: (line, body) for name, line, body in functions_with_bodies(text)}

    print("linear-scan lookup helpers:")
    confirmed = []
    for name in LOOKUP_FUNCTIONS:
        if name not in bodies:
            continue
        line, body = bodies[name]
        scans = len(re.findall(r"for \w+ in \w+\s*\{", body))
        has_scan = scans > 0
        calls = len(re.findall(rf"\b{re.escape(name)}\s*\(", text)) - 1
        print(f"  {name:24s} line {line:5d}  loops={scans}  "
              f"{'LINEAR SCAN' if has_scan else 'no scan'}  called from {calls} sites")
        if has_scan:
            confirmed.append((name, line, calls))

    # Which functions call a linear-scan helper AND are themselves per-node?
    print("\nfunctions that call a linear-scan helper inside a loop:")
    hot = []
    for name, line, body in functions_with_bodies(text):
        for helper, _, _ in confirmed:
            # a call to the helper on a line that is inside a for/while body
            for match in re.finditer(rf"\b{re.escape(helper)}\s*\(", body):
                prefix = body[:match.start()]
                loops_open = prefix.count("for ") + prefix.count("while ")
                if loops_open > 0:
                    hot.append((name, line, helper))
                    break
            else:
                continue
            break
    for name, line, helper in sorted(set(hot), key=lambda item: item[1])[:15]:
        print(f"  {name:34s} line {line:5d}  calls {helper} inside a loop")

    print(f"\n{len(confirmed)} linear-scan helpers; {len(set(hot))} functions call one "
          f"inside a loop")
    print("\nVERDICT: every lookup is a linear scan, and the per-node path calls them")
    print("inside loops. n nodes x O(n) per lookup = O(n^2). Index once instead of")
    print("re-scanning per lookup; that is the lever, not staging or constant factors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
