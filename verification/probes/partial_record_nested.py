"""A3-022: nested/nominal record fields across the fact boundary (PRE-REGISTERED).

Pre-registration, written before any cell ran:
  verification/acceptance/PRE-REGISTRATION-A3-022-NESTED-RECORD.md

Reuses the A3-021 driver (`partial_record_matrix.py`) for the harness, fact plumbing
and grading, so the two matrices are comparable cell-for-cell.

Exit codes: 0 = every cell met its contract requirement, 1 = at least one did not.
Usage: python partial_record_nested.py <candidate-worktree>
"""
import importlib.util
import pathlib
import sys

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("partial_record_matrix",
                                             HERE / "partial_record_matrix.py")
prm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prm)
base = prm.base

NESTED = ("type Inner {\n    n: Int\n}\n\n"
          "type Outer {\n    inner: Inner\n    tag: Str\n}\n\n"
          "fn make_outer(n: Int, tag: Str) -> Outer {\n"
          "    return Outer { inner: Inner { n: n }, tag: tag }\n}\n\n"
          "fn main() -> Int {\n    let o = make_outer(1, \"x\")\n"
          "    return o.inner.n\n}\n")

FORGED_INNER = ("type Inner {\n    n: Int\n}\n\n"
                "type Outer {\n    inner: Inner\n    tag: Str\n}\n\n"
                "fn make_outer() -> Outer {\n"
                "    return Outer { inner: 3, tag: \"x\" }\n}\n\n"
                "fn main() -> Int {\n    return 0\n}\n")

BAD_NESTED_VALUE = ("type Inner {\n    n: Int\n}\n\n"
                    "type Outer {\n    inner: Inner\n    tag: Str\n}\n\n"
                    "fn make_outer() -> Outer {\n"
                    "    return Outer { inner: Inner { n: \"s\" }, tag: \"x\" }\n}\n\n"
                    "fn main() -> Int {\n    return 0\n}\n")


def main():
    print(f"REPO={prm.REPO}")
    harness = base.Harness()
    try:
        # ------------------------------------------------------------ N0 control
        sem, parsed = harness.prepare(NESTED, "pn-n0")
        facts = prm.decl_facts(harness, parsed, sem)
        inner = prm.by_name(facts, "Inner")
        outer = prm.by_name(facts, "Outer")
        ids = prm.ids_for(parsed, "make_outer")
        prm.cell("N0", "honest facts for Inner and Outer, nested literal",
                 prm.seed_class(NESTED),
                 prm.staged_status(harness, parsed, sem, ids, [inner, outer], "make_outer"),
                 ("valid",))

        # ------------------------------------------------------------ N1 nominal -> builtin retype
        sem_f, parsed_f = harness.prepare(FORGED_INNER, "pn-n1")
        forged = prm.rewrite_field(prm.by_name(prm.decl_facts(harness, parsed_f, sem_f), "Outer"),
                                   "inner", "Int")
        prm.cell("N1", "Outer fact retypes nominal field 'inner' to Int; literal supplies 3",
                 prm.seed_class(FORGED_INNER),
                 prm.staged_status(harness, parsed_f, sem_f,
                                   prm.ids_for(parsed_f, "make_outer"),
                                   [prm.by_name(prm.decl_facts(harness, parsed_f, sem_f),
                                                "Inner"), forged], "make_outer"),
                 ("invalid",))

        # ------------------------------------------------------------ N2 field renamed in fact
        renamed = prm.with_fields(outer, [
            prm.field_entry("other", "Inner", "nominal"),
            [item for item in prm.field_list(outer) if prm.entry_name(item) == "tag"][0]])
        prm.cell("N2", "Outer fact renames 'inner' to 'other'; literal supplies inner",
                 prm.seed_class(NESTED),
                 prm.staged_status(harness, parsed, sem, ids, [inner, renamed], "make_outer"),
                 ("invalid",))

        # ------------------------------------------------------------ N3 truncated declaration set
        prm.cell("N3", "Inner fact withheld; only Outer supplied",
                 prm.seed_class(NESTED),
                 prm.staged_status(harness, parsed, sem, ids, [outer], "make_outer"),
                 ("invalid", "unsupported"))

        # ------------------------------------------- N3' post-hoc: withheld decl + bad inner
        # NOT pre-registered. N3 measured `valid` instead of the predicted refusal, so the
        # discriminating question became: with the Inner fact withheld, is an INVALID nested
        # literal also accepted? Seed for the same source is invalid.
        sem_h, parsed_h = harness.prepare(BAD_NESTED_VALUE, "pn-n3b")
        prm.cell("N3'", "Inner fact withheld AND the nested literal supplies n: \"s\"",
                 prm.seed_class(BAD_NESTED_VALUE),
                 prm.staged_status(harness, parsed_h, sem_h,
                                   prm.ids_for(parsed_h, "make_outer"),
                                   [prm.by_name(prm.decl_facts(harness, parsed_h, sem_h),
                                                "Outer")], "make_outer"),
                 ("invalid",), "post-hoc control (not pre-registered)")

        # ------------------------------------- N3'' post-hoc: no facts at all
        # NOT pre-registered. If an absent declaration means "unchecked", then a literal whose
        # own record declaration is also withheld must be accepted however wrong its contents.
        nofacts = ("type Inner {\n    n: Int\n}\n\n"
                   "type Outer {\n    inner: Inner\n    tag: Str\n}\n\n"
                   "fn make_outer() -> Outer {\n"
                   "    return Outer { inner: Inner { n: \"s\" }, tag: 3 }\n}\n\n"
                   "fn main() -> Int {\n    return 0\n}\n")
        sem_z, parsed_z = harness.prepare(nofacts, "pn-n3c")
        prm.cell("N3''", "no type facts at all, both values wrong for their fields",
                 prm.seed_class(nofacts),
                 prm.staged_status(harness, parsed_z, sem_z,
                                   prm.ids_for(parsed_z, "make_outer"), [], "make_outer"),
                 ("invalid",), "post-hoc control (not pre-registered)")
        # ------------------------------------------------------------ N4 wrong inner value type
        sem_b, parsed_b = harness.prepare(BAD_NESTED_VALUE, "pn-n4")
        facts_b = prm.decl_facts(harness, parsed_b, sem_b)
        prm.cell("N4", "nested literal supplies n: \"s\" with honest facts",
                 prm.seed_class(BAD_NESTED_VALUE),
                 prm.staged_status(harness, parsed_b, sem_b,
                                   prm.ids_for(parsed_b, "make_outer"),
                                   [prm.by_name(facts_b, "Inner"),
                                    prm.by_name(facts_b, "Outer")], "make_outer"),
                 ("invalid",))

        # ------------------------------------------------------------ N5 padded inner declaration
        padded_inner = prm.with_field(inner, "extra", "Int")
        prm.cell("N5", "Inner fact padded with field 'extra' the source never declares",
                 prm.seed_class(NESTED),
                 prm.staged_status(harness, parsed, sem, ids, [padded_inner, outer],
                                   "make_outer"),
                 ("valid",))

        # ------------------------------------------------------------ N6 duplicate field name
        tag_entry = [item for item in prm.field_list(outer) if prm.entry_name(item) == "tag"][0]
        inner_entry = [item for item in prm.field_list(outer)
                       if prm.entry_name(item) == "inner"][0]
        dup_str = prm.field_entry("tag", "Int")
        order_a = prm.with_fields(outer, [inner_entry, tag_entry, dup_str])
        order_b = prm.with_fields(outer, [inner_entry, dup_str, tag_entry])
        a_status = prm.staged_status(harness, parsed, sem, ids, [inner, order_a], "make_outer")
        b_status = prm.staged_status(harness, parsed, sem, ids, [inner, order_b], "make_outer")
        prm.cell("N6", "Outer fact lists 'tag' twice (Str, Int) in both orders",
                 prm.seed_class(NESTED), f"{a_status}|{b_status}", ("invalid|invalid",),
                 f"orderA={a_status} orderB={b_status}")
    finally:
        harness.close()

    failed = [item for item in prm.CELLS if item["verdict"] == "FAIL"]
    print()
    for item in prm.CELLS:
        print(item)
    print(f"SUMMARY cells={len(prm.CELLS)} pass={len(prm.CELLS) - len(failed)} "
          f"fail={len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
