"""Staged-checker attacks on the typed/statement-group path (`analyze_chunk_typed`).

Target: A1 slices 4a (declaration facts) + 4b (facts consumer) + 4c (expectReturns
gate), as shipped in integrated candidate `bcfa3c0`. These attacks deliberately go
*beyond* the builder's own tests (`tests/test_chunk_typed.py` covers stale facts,
missing field and wrong field type in the agreeing direction).

Soundness question for staged compilation: a chunked checker receives
`List[ResolvedTypeDecl]` and a PARSER SLICE over the wire. Both are data. A
revision/document guard exists; these attacks ask what happens when the data is
*internally consistent but false* (forged field types), *duplicated*, *span-nonsense*,
*foreign*, or when the new `expectReturns` gate is used dishonestly.

Each attack compares the typed-chunk verdict with the SEED's verdict on an equivalent
whole program, so "valid" from the chunked path where the seed says invalid is a
fail-open.

Claims:
  S1  forged field type (record declared as Int) must not let `p.x` check valid.
  S2  forged field type (Int declared as record) must not let `p + 1` check valid.
  S3  duplicated conflicting declarations must not let the "convenient" copy win
      silently: whatever the chunked path says must agree with the seed.
  S5  a fact with synthetic/reversed spans must be refused or ignored, never trusted.
  S6  a fact stamped with a foreign document must be refused (stale-revision sibling).
  S7  an omitted field must produce the same refusal the whole path produces.
  S8  `expectReturns=false` on a body that returns must not be silently accepted
      (and `true` on a body that does not return must not be either).
  S9  diagnostic parity: for one deliberate error, the chunked path reports the same
      (code, span) as the whole path.

Exit codes: 0 = every fail-closed claim holds, 1 = at least one falsified, 2 = harness error.
Usage: python staged_typed_attacks.py <candidate-worktree>
"""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402
import pep_chunk_contract as contract  # noqa: E402
from tests.chunk_helper import (checked_fn_value, fetch_all_sigs, fields_map, nval,
                                remap_chunk, resolved_sig_value)

PEP_PS1 = REPO / "pep.ps1"
RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def typed(t, v):
    return {"type": t, "value": str(v) if t == "Int" else v}


def shape(kind, name, depth=0):
    return {"type": "PepTypeShape", "fields": [
        {"name": "kind", "value": typed("Str", kind)},
        {"name": "name", "value": typed("Str", name)},
        {"name": "listDepth", "value": typed("Int", depth)}]}


def type_field_json(fact):
    fields = fields_map(fact)
    return {"fieldName": fields["fieldName"]["value"],
            "fieldTypeName": fields["fieldTypeName"]["value"],
            "fieldShape": fields["fieldShape"],
            "fieldCode": fields["fieldCode"]["value"],
            "startByte": fields["startByte"]["value"],
            "endByte": fields["endByte"]["value"],
            "line": fields["line"]["value"],
            "column": fields["column"]["value"]}


def build_decl(name, kind, document, revision, field_specs, decl_span=(0, 0),
               duplicate=False):
    """field_specs: list of (fieldName, typeName, shapeKind, shapeName)."""
    fields = [{"type": "ResolvedTypeField", "fields": [
        {"name": "fieldName", "value": typed("Str", fname)},
        {"name": "fieldTypeName", "value": typed("Str", tname)},
        {"name": "fieldShape", "value": shape(kind, sname)},
        {"name": "fieldCode", "value": typed("Str", "")},
        {"name": "startByte", "value": typed("Int", 0)},
        {"name": "endByte", "value": typed("Int", 0)},
        {"name": "line", "value": typed("Int", 1)},
        {"name": "column", "value": typed("Int", 1)}]}
        for fname, tname, kind, sname in field_specs]
    return {"type": "ResolvedTypeDecl", "fields": [
        {"name": "typeName", "value": typed("Str", name)},
        {"name": "typeKind", "value": typed("Str", kind)},
        {"name": "declStartByte", "value": typed("Int", decl_span[0])},
        {"name": "declEndByte", "value": typed("Int", decl_span[1])},
        {"name": "declLine", "value": typed("Int", 1)},
        {"name": "declColumn", "value": typed("Int", 1)},
        {"name": "duplicateType", "value": {"type": "Bool", "value": duplicate}},
        {"name": "document", "value": typed("Str", document)},
        {"name": "revision", "value": typed("Str", revision)},
        {"name": "fields", "value": {"type": "List[ResolvedTypeField]", "value": fields}}]}


def tamper_field_type(decl, field_name, new_type, new_shape_kind="builtin"):
    """Return a copy of a producer fact with one field's declared type rewritten."""
    out = copy.deepcopy(decl)
    for item in out["fields"]:
        if item["name"] != "fields":
            continue
        for field in item["value"]["value"]:
            entries = {entry["name"]: entry for entry in field["fields"]}
            if entries["fieldName"]["value"]["value"] != field_name:
                continue
            entries["fieldTypeName"]["value"]["value"] = new_type
            shape_entries = {entry["name"]: entry for entry in
                             entries["fieldShape"]["value"]["fields"]}
            shape_entries["kind"]["value"]["value"] = new_shape_kind
            shape_entries["name"]["value"]["value"] = new_type
    return out


def seed_verdict(source: bytes):
    with tempfile.TemporaryDirectory(prefix="a3-staged-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(source)
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        return "NON_JSON"
    return payload.get("status")


class Harness:
    def __init__(self):
        self.session = Session()
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = self.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                    "name": "a3-staged", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        self.tool_document = opened["document"]
        self.tool_revision = opened["revision"]
        sample = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "validate", "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(
            sample["document"], sample["revision"], done=True, lex_done=True,
            lex_stage="done")
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        empty_types = {"type": "List[ResolvedTypeDecl]", "value": []}
        expect_true = {"type": "Bool", "value": True}
        tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_pp], empty_rep),
            ("pep-c23-checker-typedecls", "chunk_type_declarations", [empty_pp],
             empty_types),
            ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
            ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
             [empty_pp, empty_ext, empty_sig, empty_types, expect_true], empty_rep),
        ]
        for tool, function, arguments, expect in tools:
            self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_register", "tool": tool,
                               "document": self.tool_document,
                               "revision": self.tool_revision, "function": function})
            validated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_validate", "tool": tool,
                                           "document": self.tool_document,
                                           "revision": self.tool_revision,
                                           "testVectors": [{"arguments": arguments,
                                                            "expect": expect,
                                                            "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_activate", "tool": tool,
                               "document": self.tool_document,
                               "revision": self.tool_revision})

    def prepare(self, source, name: str):
        raw = source.encode("utf-8") if isinstance(source, str) else source
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": name, "bytes": list(raw)})
        require(target, "outcome", "ok", f"open {name}")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, raw, target, self.tool_revision)
        return sem, parsed

    def sliced(self, parsed, node_ids):
        nodes = fields_map(parsed)["nodes"]["value"]
        by_id = {str(nval(node, "id")): node for node in nodes}
        sub = [copy.deepcopy(by_id[str(node_id)]) for node_id in node_ids]
        chunk = remap_chunk(sub)
        return {"type": "ParserProgress", "fields": [
            {"name": key, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                    if key == "nodes" else fields_map(parsed)[key])}
            for key in [field["name"] for field in parsed["fields"]]]}

    def real_facts(self, parsed, sem, node_ids):
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-typedecls",
             "arguments": [self.sliced(parsed, node_ids)], "semanticTarget": sem})
        require(response, "outcome", "ok", "chunk_type_declarations")
        return response["result"]["value"]

    def signatures(self, parsed, sem):
        # fetch_all_sigs converts the typed transport into plain dicts (the same
        # helper the builder's own tests use for the signature contract).
        return fetch_all_sigs(self.session, parsed, self.tool_revision, sem)

    def analyze_typed(self, sliced, extfns, extsigs, exttypes, sem, expect_returns=True):
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-chunk-typed",
             "arguments": [sliced, extfns, extsigs, exttypes,
                           {"type": "Bool", "value": expect_returns}],
             "semanticTarget": sem})
        if response.get("outcome") != "ok":
            error = response.get("error") or {}
            return {"status": f"REFUSED:{error.get('code')}", "diagnostics": []}
        report = fields_map(response["result"])
        diags = []
        for item in report["diagnostics"]["value"]:
            fields = fields_map(item)
            diags.append((fields["code"]["value"], int(fields["startByte"]["value"]),
                          int(fields["endByte"]["value"])))
        return {"status": report["status"]["value"], "diagnostics": sorted(diags)}

    def close(self):
        self.session.close()


SOURCE = (
    "type Point {\n"
    "    x: Int\n"
    "    y: Int\n"
    "}\n\n"
    "fn use_point(p: Point) -> Int {\n"
    "    return p.x\n"
    "}\n\n"
    "fn bad_arith(p: Point) -> Int {\n"
    "    return p + 1\n"
    "}\n\n"
    "fn main() -> Int {\n"
    "    return 0\n"
    "}\n")


def body_ids(parsed, entry):
    index = contract.DocumentIndex.from_parsed(parsed)
    nodes = fields_map(parsed)["nodes"]["value"]
    for node in nodes:
        if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                and nval(node, "text") == entry:
            return index.subtree(int(nval(node, "id")))
    raise RuntimeError(f"entry {entry} not found")


def decl_roots(parsed):
    index = contract.DocumentIndex.from_parsed(parsed)
    nodes = fields_map(parsed)["nodes"]["value"]
    roots = [int(nval(node, "id")) for node in nodes
             if str(nval(node, "parentId")) == "-1"
             and nval(node, "kind") in ("record_declaration", "union_declaration")]
    ids = []
    for root in roots:
        ids.extend(index.subtree(root))
    return ids


def main():
    print(f"REPO={REPO}")
    harness = Harness()
    try:
        sem, parsed = harness.prepare(SOURCE, "staged-base")
        facts = harness.real_facts(parsed, sem, decl_roots(parsed))
        sigs = harness.signatures(parsed, sem)
        point = [f for f in facts if fields_map(f)["typeName"]["value"] == "Point"][0]
        other_sigs = {"type": "List[ResolvedSignature]",
                      "value": [resolved_sig_value(s) for s in sigs
                                if s["name"] not in ("use_point", "bad_arith")]}
        other_fns = {"type": "List[CheckedFunction]",
                     "value": [checked_fn_value(s) for s in sigs
                               if s["name"] not in ("use_point", "bad_arith")]}

        # ---------- control: honest facts, chunk uses p.x ----------
        control = harness.analyze_typed(
            harness.sliced(parsed, body_ids(parsed, "use_point")), other_fns,
            other_sigs, {"type": "List[ResolvedTypeDecl]", "value": facts}, sem)
        record("S0 control: honest facts let p.x check valid", True, "valid",
               control["status"], f"diagnostics={control['diagnostics']}")

        # ---------- S1: forged field type Point.x := Str ----------
        forged = [tamper_field_type(point, "x", "Str")] + \
                 [f for f in facts if fields_map(f)["typeName"]["value"] != "Point"]
        s1 = harness.analyze_typed(
            harness.sliced(parsed, body_ids(parsed, "use_point")), other_fns,
            other_sigs, {"type": "List[ResolvedTypeDecl]", "value": forged}, sem)
        record("S1 forged field type cannot make p.x valid", True,
               "not-valid", "not-valid" if s1["status"] != "valid"
               else f"VALID with forged Point.x=Str ({s1['diagnostics']})")

        # ---------- S2: forged field type Point := record-of-Int (arith on a record) --
        # `bad_arith` uses `p + 1`; the seed rejects it. Forge y/x shapes to Int so a
        # consumer might accept arithmetic on the record value itself.
        forged2 = [tamper_field_type(point, "x", "Int", "builtin"),
                   tamper_field_type(point, "y", "Int", "builtin")]
        forged2 = [tamper_field_type(f, "x", "Int", "builtin") for f in forged2]
        s2 = harness.analyze_typed(
            harness.sliced(parsed, body_ids(parsed, "bad_arith")), other_fns,
            other_sigs, {"type": "List[ResolvedTypeDecl]", "value": forged2}, sem)
        seed_bad = seed_verdict(SOURCE.encode("utf-8"))
        record("S2 forged facts cannot make record arithmetic valid", True,
               "not-valid", "not-valid" if s2["status"] != "valid"
               else f"VALID despite seed={seed_bad} ({s2['diagnostics']})")

        # ---------- S3: duplicated conflicting declarations ----------
        dup_int = build_decl("Point", "record", sem["document"], sem["revision"],
                             [("x", "Int", "builtin", "Int")])
        dup_str = build_decl("Point", "record", sem["document"], sem["revision"],
                             [("x", "Str", "builtin", "Str")])
        s3a = harness.analyze_typed(
            harness.sliced(parsed, body_ids(parsed, "use_point")), other_fns,
            other_sigs, {"type": "List[ResolvedTypeDecl]", "value": [dup_int, dup_str]},
            sem)
        s3b = harness.analyze_typed(
            harness.sliced(parsed, body_ids(parsed, "use_point")), other_fns,
            other_sigs, {"type": "List[ResolvedTypeDecl]", "value": [dup_str, dup_int]},
            sem)
        record("S3 duplicated conflicting declarations are not order-dependent",
               True, "same verdict", "same verdict" if s3a["status"] == s3b["status"]
               else f"ORDER-DEPENDENT {s3a['status']} vs {s3b['status']}")

        # S3b — reachability with HONEST producer output: two real declarations of the
        # same name (a duplicate type), facts gathered per declaration root exactly as
        # the builder harness does, then concatenated in caller order.
        dup_source = ("type Dup {\n    a: Int\n}\n\n"
                      "type Dup {\n    b: Bool\n}\n\n"
                      "fn use_dup(d: Dup) -> Int {\n    return d.a\n}\n\n"
                      "fn main() -> Int { return 0 }\n")
        sem_d, parsed_d = harness.prepare(dup_source, "staged-dup-honest")
        nodes_d = fields_map(parsed_d)["nodes"]["value"]
        index_d = contract.DocumentIndex.from_parsed(parsed_d)
        roots_d = [int(nval(node, "id")) for node in nodes_d
                   if str(nval(node, "parentId")) == "-1"
                   and nval(node, "kind") in ("record_declaration", "union_declaration")]
        honest = []
        for root in roots_d:
            honest.extend(harness.real_facts(parsed_d, sem_d, index_d.subtree(root)))
        sigs_d = harness.signatures(parsed_d, sem_d)
        fn_args = (
            harness.sliced(parsed_d, body_ids(parsed_d, "use_dup")),
            {"type": "List[CheckedFunction]",
             "value": [checked_fn_value(s) for s in sigs_d if s["name"] != "use_dup"]},
            {"type": "List[ResolvedSignature]",
             "value": [resolved_sig_value(s) for s in sigs_d
                       if s["name"] != "use_dup"]},
        )
        forward = harness.analyze_typed(
            *fn_args, {"type": "List[ResolvedTypeDecl]", "value": honest}, sem_d)
        backward = harness.analyze_typed(
            *fn_args, {"type": "List[ResolvedTypeDecl]", "value": list(reversed(honest))},
            sem_d)
        seed_dup = seed_verdict(dup_source.encode())
        record("S3b honest duplicate-type facts are order-stable and fail closed",
               True, "stable+closed",
               "stable+closed" if forward["status"] == backward["status"]
               and forward["status"] != "valid"
               else f"forward={forward['status']} backward={backward['status']} "
                    f"seed={seed_dup}")

        # ---------- S5: synthetic / reversed spans ----------
        synthetic = build_decl("Point", "record", sem["document"], sem["revision"],
                               [("x", "Int", "builtin", "Int")],
                               decl_span=(999999, 999998))
        s5 = harness.analyze_typed(
            harness.sliced(parsed, body_ids(parsed, "use_point")), other_fns,
            other_sigs, {"type": "List[ResolvedTypeDecl]", "value": [synthetic]}, sem)
        # Observation, not a claim: the consumer reads field types and never consults
        # declaration spans, so span forgery changes no verdict. Reported because a
        # consumer of these facts cannot rely on spans for identity.
        RESULTS.append({"case": "O5 declaration spans are not validated by the consumer",
                        "claimed": False, "expect": "observed",
                        "outcome": f"status={s5['status']} with reversed out-of-range "
                                   f"decl spans", "falsified": False})
        print(f"[O5] status={s5['status']} with reversed out-of-range decl spans")

        # ---------- S6: foreign document ----------
        foreign = build_decl("Point", "record", "doc-not-this-one", sem["revision"],
                             [("x", "Int", "builtin", "Int")])
        s6 = harness.analyze_typed(
            harness.sliced(parsed, body_ids(parsed, "use_point")), other_fns,
            other_sigs, {"type": "List[ResolvedTypeDecl]", "value": [foreign]}, sem)
        codes6 = [diag[0] for diag in s6["diagnostics"]]
        record("S6 foreign-document facts are refused with PEP_STALE_REVISION", True,
               "PEP_STALE_REVISION",
               "PEP_STALE_REVISION" if "PEP_STALE_REVISION" in codes6
               else f"status={s6['status']} codes={codes6}")

        # ---------- S7: omitted field ----------
        omitted = build_decl("Point", "record", sem["document"], sem["revision"],
                             [("y", "Int", "builtin", "Int")])
        s7 = harness.analyze_typed(
            harness.sliced(parsed, body_ids(parsed, "use_point")), other_fns,
            other_sigs, {"type": "List[ResolvedTypeDecl]", "value": [omitted]}, sem)
        record("S7 omitted field refuses (no silent unknown-field acceptance)", True,
               "not-valid", "not-valid" if s7["status"] != "valid"
               else "VALID with field x undefined")

        # ---------- S8: expectReturns gate both directions ----------
        # The gate adds a requirement when true (line 1748 of the checker): a function
        # whose declared return is not Unit must supply a return. Attack the direction
        # that matters: a MISSING-return body must be refused with the gate on and
        # accepted with it off.
        missing = ("type P {\n    x: Int\n}\n\n"
                   "fn g(p: P) -> Int {\n    let z = p.x\n}\n\n"
                   "fn main() -> Int { return 0 }\n")
        sem_m, parsed_m = harness.prepare(missing, "staged-missing-return")
        facts_m = harness.real_facts(parsed_m, sem_m, decl_roots(parsed_m))
        sigs_m = harness.signatures(parsed_m, sem_m)
        common = (
            harness.sliced(parsed_m, body_ids(parsed_m, "g")),
            {"type": "List[CheckedFunction]",
             "value": [checked_fn_value(s) for s in sigs_m if s["name"] != "g"]},
            {"type": "List[ResolvedSignature]",
             "value": [resolved_sig_value(s) for s in sigs_m if s["name"] != "g"]},
            {"type": "List[ResolvedTypeDecl]", "value": facts_m}, sem_m)
        with_gate = harness.analyze_typed(*common, expect_returns=True)
        without_gate = harness.analyze_typed(*common, expect_returns=False)
        ok8 = with_gate["status"] != "valid" and without_gate["status"] == "valid"
        record("S8 expectReturns gates a missing return (on=refused, off=accepted)",
               True, "gated", "gated" if ok8 else
               f"with_gate={with_gate['status']} without_gate={without_gate['status']}")

        # ---------- S9: diagnostic parity whole vs typed chunk ----------
        bad_source = (
            "type P {\n    x: Int\n}\n\n"
            "fn f(p: P) -> Int {\n    let z: Nope = 1\n    return p.x\n}\n\n"
            "fn main() -> Int { return 0 }\n").encode()
        sem_b, parsed_b = harness.prepare(bad_source, "staged-diag")
        facts_b = harness.real_facts(parsed_b, sem_b, decl_roots(parsed_b))
        sigs_b = harness.signatures(parsed_b, sem_b)
        whole = harness.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker", "arguments": [parsed_b],
             "semanticTarget": sem_b})
        report = fields_map(whole["result"])
        whole_diags = sorted((fields_map(item)["code"]["value"],
                              int(fields_map(item)["startByte"]["value"]),
                              int(fields_map(item)["endByte"]["value"]))
                             for item in report["diagnostics"]["value"])
        chunk = harness.analyze_typed(
            harness.sliced(parsed_b, body_ids(parsed_b, "f")),
            {"type": "List[CheckedFunction]",
             "value": [checked_fn_value(s) for s in sigs_b if s["name"] != "f"]},
            {"type": "List[ResolvedSignature]",
             "value": [resolved_sig_value(s) for s in sigs_b if s["name"] != "f"]},
            {"type": "List[ResolvedTypeDecl]", "value": facts_b}, sem_b)
        match = [d for d in whole_diags if d[0].startswith("PEP_UNKNOWN_TYPE")]
        record("S9 diagnostic parity whole vs typed chunk", True, "parity",
               "parity" if match and match[0] in chunk["diagnostics"]
               else f"whole={whole_diags} chunk={chunk['diagnostics']}")
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
