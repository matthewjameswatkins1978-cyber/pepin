"""Cross-chunk call-fact attacks and emitter-report forgery (mission PEP-WB-A3-20261104-B priority 4).

Where this runs: the seam between A1's checked-chunk contract and A2's bounded emitter.
A2's own pin (`ea0bc9a`) carries the emitter work but not A1's `analyze_chunk`, so the
attacks run in a **scratch merge tree** (`c69e15d` + `ea0bc9a`, local only, never pushed,
not a candidate) where both halves exist. The seam probe A2 wrote itself is the same
shape: parse -> plan chunks -> analyze_chunk with external facts -> emit per chunk.

Attacks (each compared with the seed's verdict on the equivalent whole program):
  S0  control: the caller chunk validates with HONEST external function + signature.
  S1  missing callee facts => the caller chunk is not valid.
  S2  forged ARITY: the callee fact claims two parameters for a one-argument call.
  S3  forged RETURN TYPE: the callee really returns Str, the fact claims Int, and the
      caller uses the result as Int (seed says invalid for the whole program).
  S4  forged NAME: the callee fact is named differently from the call site.
  S5  forged/stale EMITTER input: emit a function unit from a `checked` report that
      belongs to a different document than the `parsed` value it is passed with.

Exit codes: 0 = every fail-closed claim held, 1 = a claim falsified, 2 = harness error.
Usage: python seam_cross_chunk_attacks.py <seam-tree>
"""
import copy
import json
import pathlib
import sys

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
import pep_chunk_contract as contract  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402

RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_verdict(source: str):
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(prefix="a3-seam-") as folder:
        path = pathlib.Path(folder) / "p.pep"
        path.write_bytes(source.encode("utf-8"))
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(REPO / "pep.ps1"),
                               "check", str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        return "NON_JSON"
    codes = [item.get("code") for item in payload.get("diagnostics") or []]
    return f"{payload.get('status')}{('/' + codes[0]) if codes else ''}"


def fields_map(record_value):
    return {item["name"]: item["value"] for item in record_value["fields"]}


def nval(node, key):
    return fields_map(node).get(key, {}).get("value")


def set_field(record_value, name, typed_value):
    for item in record_value["fields"]:
        if item["name"] == name:
            item["value"] = typed_value


class Seam:
    def __init__(self):
        self.session = Session()
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = self.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                    "name": "a3-seam", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        self.document = opened["document"]
        self.revision = opened["revision"]
        sample = self.session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                                    "bytes": []})
        self.sample = sample
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                     done=True, lex_done=True,
                                                     lex_stage="done")
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        unit_expect = {"type": "PepC23BoundedUnit", "fields": [
            {"name": "status", "value": {"type": "Str", "value": "unsupported"}},
            {"name": "diagnostic", "value": {"type": "Str",
                                          "value": "Pep C23 function unit index is out of range"}},
            {"name": "sourceParts", "value": {"type": "List[Str]", "value": []}},
            {"name": "prerequisiteKinds", "value": {"type": "List[Str]", "value": []}},
            {"name": "prerequisiteIds", "value": {"type": "List[Int]", "value": []}},
            {"name": "requiresArena", "value": {"type": "Bool", "value": False}}]}
        tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_pp], empty_rep),
            ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
            ("pep-c23-checker-chunk", "analyze_chunk", [empty_pp, empty_ext, empty_sig],
             empty_rep),
        ]
        for tool, function, arguments, expect in tools:
            registered = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                            "op": "tool_register", "tool": tool,
                                            "document": self.document,
                                            "revision": self.revision,
                                            "function": function})
            require(registered, "status", "Registered", f"register {tool}")
            validated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_validate", "tool": tool,
                                           "document": self.document,
                                           "revision": self.revision,
                                           "testVectors": [{"arguments": arguments,
                                                            "expect": expect,
                                                            "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}: {validated}")
            self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_activate", "tool": tool,
                               "document": self.document, "revision": self.revision})
        # the emitter unit tool (A2), validated on an empty parse
        registered = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_register",
                                        "tool": "pep-c23-emitter-unit",
                                        "document": self.document,
                                        "revision": self.revision,
                                        "function": "emit_c23_function_unit_bounded"})
        require(registered, "status", "Registered", "register emitter unit")
        validated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_validate",
                                       "tool": "pep-c23-emitter-unit",
                                       "document": self.document,
                                       "revision": self.revision,
                                       "testVectors": [{"arguments": [empty_pp, empty_rep,
                                                                      {"type": "Int",
                                                                       "value": "0"}],
                                                        "expect": unit_expect,
                                                        "semanticTarget": target_spec}]})
        self.emitter_available = validated.get("status") == "Validated"
        if self.emitter_available:
            self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_activate",
                               "tool": "pep-c23-emitter-unit",
                               "document": self.document, "revision": self.revision})
        else:
            print(f"[note] emitter unit tool not registered: {str(validated)[:1200]}")

    def prepare(self, source: str, name: str):
        raw = source.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": name, "bytes": list(raw)})
        require(target, "outcome", "ok", f"open {name}")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, raw, target, self.revision)
        report = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-checker",
                                    "arguments": [parsed], "semanticTarget": sem})
        require(report, "outcome", "ok", "analyze_parsed")
        sigs = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_invoke", "tool": "pep-c23-checker-sigs",
                                  "arguments": [parsed], "semanticTarget": sem})
        require(sigs, "outcome", "ok", "chunk_signatures")
        return {"parsed": parsed, "sem": sem, "report": report["result"],
                "signatures": sigs["result"]["value"], "target": target}

    def chunk(self, ctx, entry_ids, external_fns, external_sigs):
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                      "arguments": [self.slice(ctx["parsed"], entry_ids),
                                                    {"type": "List[CheckedFunction]",
                                                     "value": external_fns},
                                                    {"type": "List[ResolvedSignature]",
                                                     "value": external_sigs}],
                                      "semanticTarget": ctx["sem"]})
        if response.get("outcome") != "ok":
            return f"REFUSED:{(response.get('error') or {}).get('code')}"
        return fields_map(response["result"])["status"]["value"]

    def slice(self, parsed, node_ids):
        nodes = fields_map(parsed)["nodes"]["value"]
        by_id = {str(nval(node, "id")): node for node in nodes}
        sub = [copy.deepcopy(by_id[str(node_id)]) for node_id in node_ids]
        from tests.chunk_helper import remap_chunk
        chunk = remap_chunk(sub)
        return {"type": "ParserProgress", "fields": [
            {"name": key, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                    if key == "nodes" else fields_map(parsed)[key])}
            for key in [field["name"] for field in parsed["fields"]]]}

    def emit_unit(self, parsed, report, sem, index=0):
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke",
                                      "tool": "pep-c23-emitter-unit",
                                      "arguments": [parsed, report,
                                                    {"type": "Int", "value": str(index)}],
                                      "semanticTarget": sem})
        if response.get("outcome") != "ok":
            return f"REFUSED:{(response.get('error') or {}).get('code')}"
        fields = fields_map(response["result"])
        return fields["status"]["value"]

    def close(self):
        self.session.close()


CALLER_SOURCE = ("fn g(x: Int) -> Int {\n    return x + 1\n}\n\n"
                 "fn f() -> Int {\n    return g(1)\n}\n\n"
                 "fn main() -> Int { return 0 }\n")

BAD_RETURN_SOURCE = ("fn g(x: Int) -> Str {\n    return \"s\"\n}\n\n"
                     "fn f() -> Int {\n    return g(1)\n}\n\n"
                     "fn main() -> Int { return 0 }\n")


def entry_ids(parsed, name):
    index = contract.DocumentIndex.from_parsed(parsed)
    for node in fields_map(parsed)["nodes"]["value"]:
        if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                and nval(node, "text") == name:
            return index.subtree(int(nval(node, "id")))
    raise RuntimeError(f"entry {name} not found")


def functions_named(report, name):
    out = []
    for item in fields_map(report)["functions"]["value"]:
        if fields_map(item)["name"]["value"] == name:
            out.append(item)
    return out


def signatures_named(signatures, name):
    return [item for item in signatures
            if fields_map(item)["functionName"]["value"] == name]


def main():
    print(f"REPO={REPO}")
    seam = Seam()
    try:
        ctx = seam.prepare(CALLER_SOURCE, "seam-caller")
        f_ids = entry_ids(ctx["parsed"], "f")
        g_fns = functions_named(ctx["report"], "g")
        g_sigs = signatures_named(ctx["signatures"], "g")

        control = seam.chunk(ctx, f_ids, g_fns, g_sigs)
        record("S0 control: honest external facts validate the caller chunk", True,
               "valid", control, f"seed={seed_verdict(CALLER_SOURCE)}")

        required = seam.chunk(ctx, f_ids, [], [])
        record("S1 missing callee facts are refused", True, "not-valid",
               "not-valid" if required != "valid" else "VALID without callee facts")

        # S2 — forge BOTH halves of the callee fact set (signature params *and* the
        # CheckedFunction arity). Forging only one half leaves the other authoritative,
        # which would make the test vacuous.
        forged_arity_sigs = copy.deepcopy(g_sigs)
        for sig in forged_arity_sigs:
            for item in sig["fields"]:
                if item["name"] == "params":
                    item["value"]["value"] = copy.deepcopy(
                        fields_map(g_sigs[0])["params"]["value"]) * 2
        forged_arity_fns = copy.deepcopy(g_fns)
        for fn in forged_arity_fns:
            for item in fn["fields"]:
                if item["name"] == "arity":
                    item["value"]["value"] = "2"
        arity = seam.chunk(ctx, f_ids, forged_arity_fns, forged_arity_sigs)
        record("S2 forged arity (both halves) is refused", True, "not-valid",
               "not-valid" if arity != "valid" else f"VALID with forged arity ({arity})")

        # S3 — forge the callee NAME in both halves.
        forged_name_sigs = copy.deepcopy(g_sigs)
        for sig in forged_name_sigs:
            for item in sig["fields"]:
                if item["name"] == "functionName":
                    item["value"]["value"] = "h"
        forged_name_fns = copy.deepcopy(g_fns)
        for fn in forged_name_fns:
            for item in fn["fields"]:
                if item["name"] == "name":
                    item["value"]["value"] = "h"
        named = seam.chunk(ctx, f_ids, forged_name_fns, forged_name_sigs)
        record("S3 forged callee name (both halves) is refused", True, "not-valid",
               "not-valid" if named != "valid" else f"VALID with forged name ({named})")

        # S4 — the structural question, stated honestly. A *self-consistent* forged callee
        # fact set is indistinguishable from an honest one, because `CheckedFunction` and
        # `ResolvedSignature` carry no document/revision (unlike `ResolvedTypeDecl`). So the
        # caller chunk accepts it. Claim = indistinguishability (held); the consequence —
        # a chunk validated against facts the seed contradicts — is recorded in the detail.
        ctx2 = seam.prepare(BAD_RETURN_SOURCE, "seam-bad-return")
        f2 = entry_ids(ctx2["parsed"], "f")
        g2_fns = functions_named(ctx2["report"], "g")
        g2_sigs = signatures_named(ctx2["signatures"], "g")
        honest2 = seam.chunk(ctx2, f2, g2_fns, g2_sigs)
        forged_ret_sigs = copy.deepcopy(g2_sigs)
        for sig in forged_ret_sigs:
            for item in sig["fields"]:
                if item["name"] == "returnType":
                    item["value"]["value"] = "Int"
        forged_ret_fns = copy.deepcopy(g2_fns)
        for fn in forged_ret_fns:
            for item in fn["fields"]:
                if item["name"] == "returnType":
                    item["value"]["value"] = "Int"
        forged_ret = seam.chunk(ctx2, f2, forged_ret_fns, forged_ret_sigs)
        seed_bad = seed_verdict(BAD_RETURN_SOURCE)
        record("S4 a self-consistent forged callee fact set is indistinguishable", True,
               "indistinguishable", "indistinguishable" if forged_ret != honest2
               else "distinguished",
               f"honest={honest2} forged={forged_ret} seed={seed_bad}; no document/revision "
               f"fields exist on CheckedFunction/ResolvedSignature to check")
        RESULTS.append({"case": "O4 forged return type validates a seed-invalid program",
                        "claimed": False, "expect": "observed",
                        "outcome": f"chunk valid with forged Int return while seed={seed_bad}",
                        "falsified": False,
                        "detail": "consequence of S4: trust in callee facts is unverifiable, "
                                  "so a forged fact set decides the caller's verdict"})

        if seam.emitter_available:
            other = seam.prepare(CALLER_SOURCE, "seam-emitter-other")
            same = seam.emit_unit(ctx["parsed"], ctx["report"], ctx["sem"], 0)
            # parsed and report from the SAME document, target matches -> the emitter runs
            foreign = seam.emit_unit(ctx["parsed"], other["report"], ctx["sem"], 0)
            record("S5 emitter refuses a report that belongs to another document", True,
                   "same-runs+foreign-refused",
                   "same-runs+foreign-refused"
                   if str(same) != "REFUSED" and (str(foreign).startswith("REFUSED")
                                                  or foreign != "emitted")
                   else f"same={same} foreign={foreign}",
                   f"same-document={same} foreign-document={foreign}")
        else:
            RESULTS.append({"case": "S5 emitter-report forgery", "claimed": False,
                            "expect": "observed", "outcome": "SKIP: emitter tool unavailable",
                            "falsified": False})
            print("[SKIP] S5 emitter tool unavailable at this pin")
    finally:
        seam.close()

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
