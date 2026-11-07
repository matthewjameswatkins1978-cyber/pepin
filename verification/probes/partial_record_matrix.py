"""A3-021: hostile partial-record field/identity matrix (PRE-REGISTERED).

Pre-registration, written before any cell ran:
  verification/acceptance/PRE-REGISTRATION-A3-021-PARTIAL-RECORD.md

Question under test: when a record's *field set* arrives only as an external
`ResolvedTypeDecl` fact, what attests that the set is complete and correctly
identified for the revision being checked?  Each cell checks one function body
as the chunk (the `type` declaration lives outside it and is supplied as fact),
and prints the SEED verdict class for the same whole source next to the chunk's
class.  The seed is authoritative for the valid/invalid question because the
source really does, or really does not, declare those fields.

Direction vocabulary (deliberately asymmetric):
  ACCEPTING-INVALID  chunk valid, seed invalid  -> fail-open, worst class
  FALSE-REFUSAL      chunk invalid, seed valid  -> fail-closed but wrong
  STABLE             matches the seed

`requires` is the contract requirement each cell is graded against -- what a sound
checker must do for that input. Where the pre-registration also predicted a
specific divergence, that prediction is reported in the receipt, not in this
gate: a cell can FAIL its requirement while its prediction was exactly right.
Exit codes: 0 = every cell met its contract requirement, 1 = at least one
cell did not, 2 = harness error.
Usage: python partial_record_matrix.py <candidate-worktree>
"""
import copy
import importlib.util
import json
import pathlib
import sys

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
spec = importlib.util.spec_from_file_location("staged_typed_attacks",
                                             HERE / "staged_typed_attacks.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
import pep_chunk_contract as contract  # noqa: E402
from tests.chunk_helper import fields_map, nval  # noqa: E402

CELLS = []


def cell(name, claim, seed_cls, staged_cls, expected, detail=""):
    ok = staged_cls in expected
    if staged_cls == "valid" and seed_cls == "invalid":
        direction = "ACCEPTING-INVALID"
    elif staged_cls == "invalid" and seed_cls == "valid":
        direction = "FALSE-REFUSAL"
    elif staged_cls == seed_cls:
        direction = "STABLE"
    else:
        direction = "OTHER"
    CELLS.append({"cell": name, "claim": claim, "seed": seed_cls, "staged": staged_cls,
                  "requires": list(expected), "verdict": "PASS" if ok else "FAIL",
                  "direction": direction, "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name:<4} seed={seed_cls:<9} "
          f"staged={staged_cls:<22} {direction:<17} require={sorted(expected)} {detail}")
    return ok


# ---------------------------------------------------------------- fact plumbing
def decl_facts(harness, parsed, sem):
    index = contract.DocumentIndex.from_parsed(parsed)
    ids = []
    for node in fields_map(parsed)["nodes"]["value"]:
        if str(nval(node, "parentId")) == "-1" and nval(node, "kind") in (
                "record_declaration", "union_declaration"):
            ids.extend(index.subtree(int(nval(node, "id"))))
    return harness.real_facts(parsed, sem, ids)


def field_list(fact):
    for item in fact["fields"]:
        if item["name"] == "fields":
            return item["value"]["value"]
    raise KeyError("fields")


def field_entry(name, type_name, kind="builtin", code=""):
    return {"type": "ResolvedTypeField", "fields": [
        {"name": "fieldName", "value": base.typed("Str", name)},
        {"name": "fieldTypeName", "value": base.typed("Str", type_name)},
        {"name": "fieldShape", "value": base.shape(kind, type_name)},
        {"name": "fieldCode", "value": base.typed("Str", code)},
        {"name": "startByte", "value": base.typed("Int", 0)},
        {"name": "endByte", "value": base.typed("Int", 0)},
        {"name": "line", "value": base.typed("Int", 1)},
        {"name": "column", "value": base.typed("Int", 1)}]}


def entry_name(entry):
    return {item["name"]: item for item in entry["fields"]}["fieldName"]["value"]["value"]


def with_fields(fact, entries):
    out = copy.deepcopy(fact)
    field_list(out)[:] = entries
    return out


def without_field(fact, name):
    return with_fields(fact, [item for item in field_list(fact) if entry_name(item) != name])


def with_field(fact, name, type_name, kind="builtin", code=""):
    return with_fields(fact, field_list(fact) + [field_entry(name, type_name, kind, code)])


def rewrite_field(fact, name, type_name, kind="builtin"):
    return with_fields(fact, [field_entry(name, type_name, kind)
                              if entry_name(item) == name else item
                              for item in field_list(fact)])


def set_field_code(fact, name, code):
    out = copy.deepcopy(fact)
    for entry in field_list(out):
        if entry_name(entry) != name:
            continue
        for item in entry["fields"]:
            if item["name"] == "fieldCode":
                item["value"]["value"] = code
    return out


def set_decl(fact, name, value):
    out = copy.deepcopy(fact)
    for item in out["fields"]:
        if item["name"] == name:
            item["value"]["value"] = value
            return out
    raise KeyError(name)


# ---------------------------------------------------------------- checker plumbing
def ids_for(parsed, entry):
    index = contract.DocumentIndex.from_parsed(parsed)
    for node in fields_map(parsed)["nodes"]["value"]:
        if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                and nval(node, "text") == entry:
            return index.subtree(int(nval(node, "id")))
    raise RuntimeError(f"entry {entry} not found")


def all_ids(parsed):
    return contract.DocumentIndex.from_parsed(parsed).node_ids()


def signature_args(harness, parsed, sem, entry):
    sigs = harness.signatures(parsed, sem)
    return (
        {"type": "List[CheckedFunction]",
         "value": [base.checked_fn_value(s) for s in sigs if s["name"] != entry]},
        {"type": "List[ResolvedSignature]",
         "value": [base.resolved_sig_value(s) for s in sigs if s["name"] != entry]},
    )


def staged_status(harness, parsed, sem, ids, facts, entry, expect_returns=True):
    extfns, extsigs = signature_args(harness, parsed, sem, entry)
    raw = harness.analyze_typed(harness.sliced(parsed, ids), extfns, extsigs,
                                {"type": "List[ResolvedTypeDecl]", "value": facts}, sem,
                                expect_returns=expect_returns)
    status = raw["status"]
    if status.startswith("REFUSED"):
        return "transport_refusal"
    return status


def seed_class(source):
    verdict = base.seed_verdict(source.encode("utf-8"))
    head = verdict.split("/")[0]
    return head if head in ("valid", "invalid", "incomplete", "unsupported") else verdict


def by_name(facts, name):
    for fact in facts:
        for item in fact["fields"]:
            if item["name"] == "typeName" and item["value"]["value"] == name:
                return fact
    raise KeyError(name)



def type_decl_ids(parsed, name):
    index = contract.DocumentIndex.from_parsed(parsed)
    ids = []
    for node in fields_map(parsed)["nodes"]["value"]:
        if nval(node, "kind") == "record_declaration" \
                and str(nval(node, "parentId")) == "-1" and nval(node, "text") == name:
            ids.extend(index.subtree(int(nval(node, "id"))))
    return ids


def staged_status_no_fns(harness, parsed, sem, ids, facts, expect_returns=True):
    empty_fns = {"type": "List[CheckedFunction]", "value": []}
    empty_sigs = {"type": "List[ResolvedSignature]", "value": []}
    raw = harness.analyze_typed(harness.sliced(parsed, ids), empty_fns, empty_sigs,
                                {"type": "List[ResolvedTypeDecl]", "value": facts}, sem,
                                expect_returns=expect_returns)
    status = raw["status"]
    return "transport_refusal" if status.startswith("REFUSED") else status
# ---------------------------------------------------------------- sources
CURSOR = ("type Cursor {\n    index: Int\n    source: Str\n}\n\n"
          "fn make_cursor(index: Int, source: Str) -> Cursor {\n"
          "    return Cursor { index: index, source: source }\n}\n\n"
          "fn main() -> Int {\n    let c = make_cursor(1, \"abcdef\")\n"
          "    return c.index\n}\n")

TWO_RECORDS = ("type Cursor {\n    index: Int\n    source: Str\n}\n\n"
               "type Frame {\n    index: Str\n}\n\n"
               "fn make_cursor(index: Int, source: Str) -> Cursor {\n"
               "    return Cursor { index: index, source: source }\n}\n\n"
               "fn main() -> Int {\n    let c = make_cursor(1, \"abcdef\")\n"
               "    return c.index\n}\n")


def main():
    print(f"REPO={REPO}")
    harness = base.Harness()
    try:
        # ------------------------------------------------------------ R0 control
        sem, parsed = harness.prepare(CURSOR, "pr-r0")
        facts = decl_facts(harness, parsed, sem)
        cursor = by_name(facts, "Cursor")
        entry_ids = ids_for(parsed, "make_cursor")
        cell("R0", "honest fact, literal supplies every declared field",
             seed_class(CURSOR),
             staged_status(harness, parsed, sem, entry_ids, [cursor], "make_cursor"),
             ("valid",))

        # ------------------------------------------------------------ R1 truncated
        cell("R1", "fact truncated: declared field 'source' dropped",
             seed_class(CURSOR),
             staged_status(harness, parsed, sem, entry_ids,
                           [without_field(cursor, "source")], "make_cursor"),
             ("invalid",))

        # ------------------------------------------------------------ R2 padded
        padded_src = ("type Cursor {\n    index: Int\n    source: Str\n}\n\n"
                      "fn make_cursor(index: Int) -> Cursor {\n"
                      "    return Cursor { index: index, source: \"x\", ghost: 3 }\n}\n\n"
                      "fn main() -> Int {\n    let c = make_cursor(1)\n"
                      "    return c.index\n}\n")
        sem_p, parsed_p = harness.prepare(padded_src, "pr-r2")
        padded = with_field(by_name(decl_facts(harness, parsed_p, sem_p), "Cursor"),
                            "ghost", "Int")
        cell("R2", "fact padded with field 'ghost' the source never declares",
             seed_class(padded_src),
             staged_status(harness, parsed_p, sem_p, ids_for(parsed_p, "make_cursor"),
                           [padded], "make_cursor"),
             ("invalid",))

        # ------------------------------------------------------------ R3 type forgery
        forgery_src = ("type Cursor {\n    index: Int\n    source: Str\n}\n\n"
                       "fn make_cursor() -> Cursor {\n"
                       "    return Cursor { index: 1, source: 3 }\n}\n\n"
                       "fn main() -> Int {\n    let c = make_cursor()\n"
                       "    return c.index\n}\n")
        sem_f, parsed_f = harness.prepare(forgery_src, "pr-r3")
        forged = rewrite_field(by_name(decl_facts(harness, parsed_f, sem_f), "Cursor"),
                               "source", "Int")
        cell("R3", "fact rewrites field 'source' Str->Int, literal supplies an Int",
             seed_class(forgery_src),
             staged_status(harness, parsed_f, sem_f, ids_for(parsed_f, "make_cursor"),
                           [forged], "make_cursor"),
             ("invalid",))

        # ------------------------------------------------------------ R4 order
        cell("R4", "fact field order reversed, distinct names",
             seed_class(CURSOR),
             staged_status(harness, parsed, sem, entry_ids,
                           [with_fields(cursor, list(reversed(field_list(cursor))))],
                           "make_cursor"),
             ("valid",))

        # ------------------------------------------------------------ R5 duplicate field name
        int_entry = [item for item in field_list(cursor) if entry_name(item) == "index"][0]
        str_entry = field_entry("index", "Str")
        others = [item for item in field_list(cursor) if entry_name(item) != "index"]
        order_a = with_fields(cursor, others + [int_entry, str_entry])
        order_b = with_fields(cursor, others + [str_entry, int_entry])
        a_status = staged_status(harness, parsed, sem, entry_ids, [order_a], "make_cursor")
        b_status = staged_status(harness, parsed, sem, entry_ids, [order_b], "make_cursor")
        cell("R5", "one fact lists field 'index' twice (Int, Str) in both orders",
             seed_class(CURSOR), f"{a_status}|{b_status}", ("invalid|invalid",),
             f"orderA={a_status} orderB={b_status} (a repeated name must not be silently "
             f"resolved first-wins)")

        # ------------------------------------------------------------ R6 local decl + forged fact
        # Chunk = the local type declaration + the literal's function, with no
        # external function facts: a whole-document chunk trips
        # PEP_DUPLICATE_FUNCTION before the type facts are ever consulted
        # (measured; the first shape of this cell was inconclusive for that reason).
        chunk_ids = sorted(set(type_decl_ids(parsed, "Cursor")) | set(entry_ids))
        cell("R6", "chunk carries the local declaration AND a forged external fact",
             seed_class(CURSOR),
             staged_status_no_fns(harness, parsed, sem, chunk_ids,
                                  [without_field(cursor, "source")]),
             ("invalid", "unsupported", "transport_refusal"),
             "documented precondition 'chunk carries no type decl also supplied "
             "externally' is unenforced")

        # ------------------------------------------------------------ R7 empty field list
        cell("R7", "fact carries an empty field list for a record the literal fills",
             seed_class(CURSOR),
             staged_status(harness, parsed, sem, entry_ids,
                           [set_decl(cursor, "fields", [])], "make_cursor"),
             ("invalid",))

        # ------------------------------------------------------------ I1 duplicate type name
        sem_t, parsed_t = harness.prepare(TWO_RECORDS, "pr-i1")
        facts_t = decl_facts(harness, parsed_t, sem_t)
        twin = rewrite_field(by_name(facts_t, "Cursor"), "index", "Str")
        cell("I1", "two facts share typeName Cursor, neither flagged duplicateType",
             seed_class(TWO_RECORDS),
             staged_status(harness, parsed_t, sem_t, ids_for(parsed_t, "make_cursor"),
                           [by_name(facts_t, "Cursor"), twin], "make_cursor"),
             ("invalid", "unsupported", "transport_refusal"))

        # ------------------------------------------------------------ I2 cross-record isolation
        cell("I2", "Frame also declares 'index' (Str); Cursor's index must stay Int",
             seed_class(TWO_RECORDS),
             staged_status(harness, parsed_t, sem_t, ids_for(parsed_t, "make_cursor"),
                           [by_name(facts_t, "Cursor"), by_name(facts_t, "Frame")],
                           "make_cursor"),
             ("valid",))

        # ------------------------------------------------------------ I3 stale revision
        cell("I3", "fact stamped with a foreign revision",
             seed_class(CURSOR),
             staged_status(harness, parsed, sem, entry_ids,
                           [set_decl(cursor, "revision", "not-this-revision")],
                           "make_cursor"),
             ("invalid", "transport_refusal"))

        # ------------------------------------------------------------ I4 supportedness channel
        coded = set_field_code(cursor, "index", "PEP_A13_TYPE_UNSUPPORTED")
        cell("I4", "fact field carries a non-empty fieldCode but an honest type",
             seed_class(CURSOR),
             staged_status(harness, parsed, sem, entry_ids, [coded], "make_cursor"),
             ("valid",),
             "predicted: fieldCode is never consulted on the literal path")
    finally:
        harness.close()

    failed = [item for item in CELLS if item["verdict"] == "FAIL"]
    print()
    for item in CELLS:
        print(json.dumps(item, sort_keys=True))
    print(f"SUMMARY cells={len(CELLS)} pass={len(CELLS) - len(failed)} fail={len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
