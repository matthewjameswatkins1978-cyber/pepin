"""BindingPool / external binding-fact attacks (mission PEP-WB-A3-20261104-B, priority 3).

A1's new staged path (`analyze_chunk_typed_bound`) accepts caller-supplied
`List[BindingFact]`, and `pep_chunk_contract.BindingPool` renumbers and dedupes them
so chained chunks can share binding facts. Binding facts are *data over the wire*, so
they are attacked the way type facts were.

Structural observation tested here: `analyze_chunk_typed_bound` guards only
`externalTypes` for document/revision identity. `BindingFact` has no document or
revision field at all, so the STALE1-style provenance guard cannot apply to binding
facts by construction.

Claims:
  A1  BindingPool dedupe key omits the binding's TYPE: two facts with one source
      identity but different types collapse to the first — a type change is dropped.
  A2  the key omits MUTABLE: mutability changes are dropped the same way.
  A3  renumbering really renumbers: admitted ids are >= BASE and unique, and the
      original semantic ids are not preserved.
  A4  `facts()` hands out the pool's own dicts (mutating a returned fact changes the
      pool), so a caller can corrupt the pool through the getter.
  B1  control: honest pooled facts let the later statement check valid.
  B2  a forged binding type must not make a later statement valid.
  B3  no facts => the later statement is not valid (non-vacuity for B1/B2).
  B4  a binding fact owned by ANOTHER function must not make this function's
      statement valid.
  O1  stale binding facts cannot be refused: revise the target and reuse the facts,
      record what happens (type facts would be refused with PEP_STALE_REVISION).

Exit codes: 0 = every claim held, 1 = a claim falsified, 2 = harness error.
Usage: python binding_pool_attacks.py <candidate-worktree>
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

import pep_c23  # noqa: E402
import pep_chunk_contract as contract  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402
from tests.chunk_helper import fields_map, nval  # noqa: E402

RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def binding(name, type_name, owner=0, scope=0, visible=0, mutable=False, sid=2_000_000):
    return {"type": "BindingFact", "fields": [
        {"name": "semanticId", "value": base.typed("Int", sid)},
        {"name": "syntaxId", "value": base.typed("Int", 0)},
        {"name": "name", "value": base.typed("Str", name)},
        {"name": "ownerFunctionId", "value": base.typed("Int", owner)},
        {"name": "scopeId", "value": base.typed("Int", scope)},
        {"name": "visibleFrom", "value": base.typed("Int", visible)},
        {"name": "mutable", "value": {"type": "Bool", "value": mutable}},
        {"name": "typeName", "value": base.typed("Str", type_name)},
        {"name": "typeShape", "value": base.shape("builtin", type_name)},
    ]}


def field(fact, name):
    for item in fact["fields"]:
        if item["name"] == name:
            return item["value"]["value"]
    return None


class Bound:
    """Session with the additional `analyze_chunk_typed_bound` tool registered."""

    def __init__(self):
        self.base = base.Harness()
        self.session = self.base.session
        sample = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "bound-vectors", "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        arguments = [empty_pp,
                     {"type": "List[CheckedFunction]", "value": []},
                     {"type": "List[ResolvedSignature]", "value": []},
                     {"type": "List[ResolvedTypeDecl]", "value": []},
                     {"type": "List[BindingFact]", "value": []},
                     {"type": "Bool", "value": True}]
        registered = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_register", "tool": "pep-c23-bound",
                                        "document": self.base.tool_document,
                                        "revision": self.base.tool_revision,
                                        "function": "analyze_chunk_typed_bound"})
        require(registered, "status", "Registered", "register pep-c23-bound")
        validated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_validate", "tool": "pep-c23-bound",
                                       "document": self.base.tool_document,
                                       "revision": self.base.tool_revision,
                                       "testVectors": [{"arguments": arguments,
                                                        "expect": empty_rep,
                                                        "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", "validate pep-c23-bound")
        activated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_activate", "tool": "pep-c23-bound",
                                       "document": self.base.tool_document,
                                       "revision": self.base.tool_revision})
        require(activated, "status", "Active", "activate pep-c23-bound")

    def invoke(self, parsed, slice_ids, facts, types, sem, expect_returns=False):
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-bound",
             "arguments": [self.base.sliced(parsed, slice_ids),
                           {"type": "List[CheckedFunction]", "value": []},
                           {"type": "List[ResolvedSignature]", "value": []},
                           {"type": "List[ResolvedTypeDecl]", "value": types},
                           {"type": "List[BindingFact]", "value": facts},
                           {"type": "Bool", "value": expect_returns}],
             "semanticTarget": sem})
        if response.get("outcome") != "ok":
            return f"REFUSED:{(response.get('error') or {}).get('code')}", []
        report = fields_map(response["result"])
        bindings = report["bindings"]["value"]
        return report["status"]["value"], bindings

    def close(self):
        self.base.close()


SOURCE = ("fn f() -> Int {\n"
          "    let x: Int = 1\n"
          "    return x + 1\n"
          "}\n\n"
          "fn g() -> Int {\n"
          "    return 0\n"
          "}\n\n"
          "fn main() -> Int { return 0 }\n")


def ids(parsed, entry):
    index = contract.DocumentIndex.from_parsed(parsed)
    for node in fields_map(parsed)["nodes"]["value"]:
        if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                and nval(node, "text") == entry:
            return int(nval(node, "id")), index
    raise RuntimeError(f"entry {entry} not found")


def statement_ids(index, function_id):
    return index.statement_children(function_id)


def main():
    print(f"REPO={REPO}")

    # ---------------- Part A: pure BindingPool behaviour ----------------------
    pool = contract.BindingPool()
    landed = pool.add([binding("x", "Int"), binding("x", "Str")])
    types = [field(fact, "typeName") for fact in pool.facts()]
    record("A1 BindingPool dedupe keeps the first type", True,
           "type-change dropped", "type-change dropped" if landed == 1 and types == ["Int"]
           else f"DROPPED-WRONG-THING landed={landed} types={types}",
           f"admitted={landed} types={types} for one source identity")

    # A1b — the caller-facing question: can a consumer tell "already have it" from
    # "already have a DIFFERENT one"? add() returns a count only.
    pool_dup = contract.BindingPool()
    first = pool_dup.add([binding("x", "Int")])
    same = pool_dup.add([binding("x", "Int")])
    conflict = pool_dup.add([binding("x", "Bool")])
    record("A1b a conflicting fact is distinguishable from an identical duplicate",
           True, "distinguishable",
           "distinguishable" if (same, conflict) != (0, 0) or first != 1
           else "indistinguishable",
           f"add() returned first={first} identical={same} conflict={conflict}")

    pool2 = contract.BindingPool()
    pool2.add([binding("y", "Int", mutable=True), binding("y", "Int", mutable=False)])
    mutables = [field(fact, "mutable") for fact in pool2.facts()]
    record("A2 BindingPool dedupe keeps the first mutability", True,
           "mutable-change dropped",
           "mutable-change dropped" if len(mutables) == 1 and mutables == [True]
           else f"landed={len(mutables)} mutables={mutables}")

    pool3 = contract.BindingPool()
    pool3.add([binding("a", "Int", sid=2_000_000), binding("b", "Int", sid=2_000_001)])
    pooled = [(field(fact, "name"), int(field(fact, "semanticId")))
              for fact in pool3.facts()]
    ids_ok = all(sid >= contract.BindingPool.BASE for _, sid in pooled) and \
        len({sid for _, sid in pooled}) == len(pooled)
    record("A3 BindingPool renumbers admitted ids", True, "renumbered",
           "renumbered" if ids_ok else f"ids={pooled}",
           f"{pooled}, original ids 2000000/2000001")

    pool4 = contract.BindingPool()
    pool4.add([binding("z", "Int")])
    handed = pool4.facts()
    handed[0]["fields"][7]["value"]["value"] = "Str"
    read_back = field(pool4.facts()[0], "typeName")
    record("A4 facts() hands out the pool's own dicts", True, "aliased",
           "aliased" if read_back == "Str" else "isolated",
           f"mutating a returned fact changed the pool: typeName={read_back}")

    # ---------------- Part B: transport-level attacks -------------------------
    harness = Bound()
    try:
        sem, parsed = harness.base.prepare(SOURCE, "bp-source")
        function_id, index = ids(parsed, "f")
        statements = statement_ids(index, function_id)
        prefix_ids = sorted(set(index.subtree(function_id)) - {
            node for later in statements[1:] for node in index.subtree(later)})
        later_ids = sorted(set(index.subtree(function_id)) - {
            node for earlier in statements[:1] for node in index.subtree(earlier)})

        status_prefix, produced = harness.invoke(parsed, prefix_ids, [], [], sem,
                                                 expect_returns=False)
        record("B0 prefix chunk with no external facts is valid", False, "observed",
               status_prefix, f"bindings produced={len(produced)}")

        honest = produced
        status_valid, _ = harness.invoke(parsed, later_ids, honest, [], sem)
        record("B1 honest pooled bindings let the later statement check valid", True,
               "valid", status_valid, f"bindings={len(honest)}")

        forged = copy.deepcopy(honest)
        for fact in forged:
            for entry in fact["fields"]:
                if entry["name"] == "typeName":
                    entry["value"]["value"] = "Str"
        status_forged, _ = harness.invoke(parsed, later_ids, forged, [], sem)
        record("B2 forged binding type cannot make the later statement valid", True,
               "not-valid", "not-valid" if status_forged != "valid"
               else f"VALID with x: Str ({status_forged})")

        status_none, _ = harness.invoke(parsed, later_ids, [], [], sem)
        record("B3 without facts the later statement is not valid", True, "not-valid",
               "not-valid" if status_none != "valid" else "VALID without facts")

        foreign_owner = copy.deepcopy(honest)
        for fact in foreign_owner:
            for entry in fact["fields"]:
                if entry["name"] == "ownerFunctionId":
                    entry["value"]["value"] = "999999"
        status_owner, _ = harness.invoke(parsed, later_ids, foreign_owner, [], sem)
        record("B4 a binding owned by another function is not treated as visible",
               True, "not-valid", "not-valid" if status_owner != "valid"
               else f"VALID with foreign ownerFunctionId ({status_owner})")

        # O1: stale bindings cannot be refused — re-derive nothing, just revise the
        # target and reuse the same facts. BindingFact carries no revision, so the
        # host has nothing to compare.
        advance = harness.session.send({"schemaVersion": 3, "op": "apply_edit",
                                        "document": sem["document"],
                                        "expected_revision": sem["revision"],
                                        "start_byte": 0, "end_byte": 0,
                                        "replacement": "//x\n"})
        require(advance, "outcome", "ok", "advance revision")
        new_sem = {"document": sem["document"], "revision": advance["revision"],
                   "entryFunctions": []}
        target = harness.session.send({"schemaVersion": 3, "op": "open_bytes",
                                       "name": "bp-stale", "bytes":
                                       list(("//x\n" + SOURCE).encode("utf-8"))})
        require(target, "outcome", "ok", "open revised target")
        new_sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
        parsed_new = parse_target(harness.session,
                                  ("//x\n" + SOURCE).encode("utf-8"), target,
                                  harness.base.tool_revision)
        new_function_id, new_index = ids(parsed_new, "f")
        new_statements = statement_ids(new_index, new_function_id)
        new_later_ids = sorted(set(new_index.subtree(new_function_id)) - {
            node for earlier in new_statements[:1] for node in new_index.subtree(earlier)})
        status_stale, _ = harness.invoke(parsed_new, new_later_ids, honest, [], new_sem)
        # O1b — parity expectation: type facts of another revision are refused with
        # PEP_STALE_REVISION, so binding facts of another revision should be refused too.
        record("O1b binding facts of another revision are refused like type facts",
               True, "refused", "refused" if str(status_stale).startswith("REFUSED")
               or status_stale != "valid" else
               f"ACCEPTED stale binding facts against rev2 ({status_stale})")
        # O1c — the decisive version: facts sourced from `let x: Int = 1` are reused to
        # check the later statement of a program whose source now says `let x: Str = "a"`.
        # The seed rejects that program; if the chunked path validates, the stale fact
        # decided the verdict. (BindingFact carries no document or revision, so no guard
        # can tell this fact apart from a fresh one — that is the structural finding.)
        changed_source = SOURCE.replace("let x: Int = 1", 'let x: Str = "a"')
        target3 = harness.session.send({"schemaVersion": 3, "op": "open",
                                        "source": changed_source,
                                        "name": "bp-changed-binding"})
        require(target3, "outcome", "ok", "open changed-binding program")
        sem3 = {"document": target3["document"], "revision": target3["revision"],
                "entryFunctions": []}
        parsed3 = parse_target(harness.session, changed_source.encode("utf-8"), target3,
                               harness.base.tool_revision)
        fid3, index3 = ids(parsed3, "f")
        st3 = statement_ids(index3, fid3)
        later3 = sorted(set(index3.subtree(fid3)) - {
            node for earlier in st3[:1] for node in index3.subtree(earlier)})
        with_stale, _ = harness.invoke(parsed3, later3, honest, [], sem3)
        without, _ = harness.invoke(parsed3, later3, [], [], sem3)
        seed_changed = base.seed_verdict(changed_source.encode("utf-8"))
        record("O1c a stale binding fact cannot change a verdict", True,
               "same-with-and-without",
               "same-with-and-without" if with_stale == without
               else f"DIFFERS with_stale={with_stale} without={without}",
               f"seed={seed_changed} with_stale={with_stale} without={without}")

        RESULTS.append({"case": "O1 stale binding facts: no revision field to check",
                        "claimed": False, "expect": "observed",
                        "outcome": f"rev1 facts against rev2 chunk -> {status_stale}",
                        "falsified": False,
                        "detail": "BindingFact has no document/revision; the host guard in "
                                  "analyze_chunk_typed_bound covers externalTypes only"})
        print(f"[O1] rev1 binding facts against a rev2 chunk -> {status_stale} "
              f"(no revision field exists to guard)")
    finally:
        harness.close()

    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['detail'] or item['outcome']}")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
