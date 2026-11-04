"""H1-V1 perturbation P3: malformed/foreign source-fact document + revision.

Question: at the checked-chunk transport gate, what happens when the
semanticTarget carries a MALFORMED or FOREIGN document/revision rather than a
merely STALE one? Layer classification per cell:
  HOST-TRANSPORT (message from the session gate, no tool result)
  CHECKER (tool_invoke returned a report)
  ACCEPTED (report/ok reached us)

Prereq: run from a tree where tests/probe_seam_chunked.py's prepare() has
already executed (so _build/a1_* and _build/a1_seed/pep.exe exist). This
driver does NOT run prepare() itself; it reuses the exact same A1 pin files.

Usage: python p3_document_matrix.py <cold-tree>
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
BUILD = ROOT / "_build"
SEED = BUILD / "a1_seed" / "pep.exe"
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402  (A2 tree, same pin as the seam probe)

# The registered tool function (`chunk_signatures`) must exist as a checked
# function of the opened document, so open the SAME four-source bundle the seam
# probe assembles (A1 lexer + parser + checker, A2 emitter). Measured boundary:
# the checker file ALONE does not open -- PEP_UNKNOWN_TYPE 'FlatAstNode'.
FIXTURE = "\n".join([
    (BUILD / "a1_lexer.pep").read_text(encoding="utf-8"),
    (BUILD / "a1_parser.pep").read_text(encoding="utf-8"),
    (BUILD / "a1_checker.pep").read_text(encoding="utf-8"),
    (ROOT / "tests" / "pep_c23_emitter.pep").read_text(encoding="utf-8"),
])


class Session:
    def __init__(self):
        self.proc = subprocess.Popen(
            [str(SEED), "session", "--jsonl"], cwd=str(ROOT),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)

    def send(self, request):
        self.proc.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            return {"__dead__": self.proc.stderr.read()[:200]}
        return json.loads(line)

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            self.proc.wait(timeout=30)


def classify(response):
    if "__dead__" in response:
        return "HOST-TRANSPORT-DEAD", response["__dead__"]
    if response.get("outcome") != "ok":
        err = response.get("error") or {}
        return "HOST-TRANSPORT", f"{err.get('code')}: {err.get('message')}"[:140]
    result = response.get("result")
    if isinstance(result, dict) and "fields" in result:
        fields = {f["name"]: f["value"] for f in result["fields"]}
        status = fields.get("status", {}).get("value")
        return f"TOOL:{status}", f"keys={sorted(fields)[:6]}"
    if isinstance(result, dict) and "type" in result:
        return f"TOOL-VALUE:{result['type']}", str(result.get('value'))[:80]
    return f"TOOL:{response.get('status')}", ""


def main():
    failures = 0
    session = Session()
    try:
        opened = session.send({"schemaVersion": 3, "op": "open",
                               "source": FIXTURE, "name": "p3",
                               "metadataOnly": True})
        if opened.get("outcome") != "ok":
            print("OPEN-FAILED", json.dumps(opened)[:200])
            return 2
        result = opened["result"] if "result" in opened else opened
        fields = {f["name"]: f["value"] for f in result.get("fields", [])}
        good_doc = result.get("document") or fields.get("document")
        good_rev = result.get("revision") or fields.get("revision")

        # The session requires register -> validate -> activate before tool_invoke
        # (mirrors tests/probe_seam_chunked.py lines 190-215).
        tool = "pep-c23-checker-sigs"
        empty_pp = pep_c23.parser_progress(good_doc, good_rev)
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_register", "tool": tool,
                      "document": good_doc, "revision": good_rev,
                      "function": "chunk_signatures"})
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": tool,
                                  "document": good_doc, "revision": good_rev,
                                  "testVectors": [{"arguments": [empty_pp],
                                                   "expect": empty_sig,
                                                   "semanticTarget": {
                                                       "document": good_doc,
                                                       "revision": good_rev,
                                                       "entryFunctions": []}}]})
        print(f"VALIDATE status={validated.get('status')}")
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_activate", "tool": tool,
                      "document": good_doc, "revision": good_rev})
        print(f"OPEN ok document={good_doc!r} revision={good_rev!r}")

        cells = [
            ("control-correct", good_doc, good_rev),
            ("empty-document", "", good_rev),
            ("foreign-document", "0" * len(str(good_doc)), good_rev),
            ("null-document", None, good_rev),
            ("zero-revision", good_doc, 0),
            ("negative-revision", good_doc, -1),
            ("huge-revision", good_doc, 2**62),
            ("foreign-revision", good_doc, "sha256:" + "0" * 64),
            ("truncated-revision", good_doc, str(good_rev)[:-8]),
        ]
        for label, doc, rev in cells:
            target = {"document": doc, "revision": rev, "entryFunctions": []}
            try:
                response = session.send({
                    "schemaVersion": 3, "toolProtocolVersion": 2,
                    "op": "tool_invoke", "tool": tool,
                    "arguments": [empty_pp],
                    "semanticTarget": target})
                layer, detail = classify(response)
            except Exception as err:  # noqa: BLE001
                layer, detail = "DRIVER-ERROR", f"{type(err).__name__}: {err}"[:160]
            print(f"{label:20s} -> {layer:20s} {detail}")

        # Malformed document at the OPEN layer, for a different layer signature.
        for label, extra in (("open-empty-doc", {"document": ""}),
                             ("open-foreign-doc", {"document": "f" * 32})):
            request = {"schemaVersion": 3, "op": "open", "source": FIXTURE,
                       "name": "p3b", "metadataOnly": True}
            request.update(extra)
            try:
                response = session.send(request)
                layer, detail = classify(response)
            except Exception as err:  # noqa: BLE001
                layer, detail = "DRIVER-ERROR", f"{type(err).__name__}: {err}"[:160]
            print(f"{label:20s} -> {layer:20s} {detail}")
    finally:
        session.close()
    print(f"SUMMARY cells=10 failures={failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
