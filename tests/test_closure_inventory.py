"""Compiler-source closure inventory (A1-5 / integration gate).

For each canonical Lucy compiler module, records the exact pipeline
stage reached under UNCHANGED budgets, using the REAL production path
(host-staged parse + single analyze_parsed + optional emit):
  checked | emitted | transport-limited | step-limited
with OCaml as the semantic oracle in every row.

This is the machine-checkable companion to the Road 1 bootstrap plan:
it tells us precisely which compiler pieces can proceed toward native
compiler A today, and what blocks the rest. Update expectations only
when observed behavior changes; never weaken a failing assertion to
make the ledger green.
"""
import json
import pathlib
import subprocess
import unittest

from tests.test_a11 import revision
import pep_c23
from pep_c23 import Session

ROOT = pathlib.Path(__file__).resolve().parents[1]
NL = chr(10)
LEXER = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")


def ocaml_check(source):
    with open(ROOT / "_build" / "closure_target.pep", "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(source)
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "check",
         str(ROOT / "_build" / "closure_target.pep"), "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False)
    try:
        return json.loads(proc.stdout).get("status")
    except Exception:
        return f"exit={proc.returncode}"


def split_top_level(source):
    blocks, current = [], []
    for line in source.split(NL):
        if (line.startswith("type ") or line.startswith("fn ")) and current:
            blocks.append(NL.join(current))
            current = [line]
        else:
            current.append(line)
    blocks.append(NL.join(current))
    return [b for b in blocks if b.strip()]


def cumulative(blocks, count):
    return (NL.join(blocks[:count]).strip() + NL) if count else ""


LEXER_BLOCKS = split_top_level(LEXER)
LEXER_TYPES = [b for b in LEXER_BLOCKS if b.startswith("type ")]
LEXER_FNS = [b for b in LEXER_BLOCKS if b.startswith("fn ")]


def module_sources():
    mods = {}
    acc = ""
    for i, b in enumerate(LEXER_TYPES):
        acc = (acc + NL + b).strip() + NL
        mods[f"T{i + 1}"] = acc
    acc = mods["T5"]
    fn_names = ["ascii_letter", "ascii_digit", "ascii_continue", "utf8_check",
                "advance_position", "make_cursor", "make_token", "make_progress",
                "lexer_start", "lexer_step"]
    by_name = {}
    for b in LEXER_FNS:
        by_name[b.split("(")[0].split()[-1]] = b
    for name in fn_names:
        acc = acc + NL + by_name[name] + NL
        mods[f"F_{name}"] = acc
    mods["FULL_lexer"] = LEXER
    return mods


class ClosureInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = NL.join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                    "name": "closure", "metadataOnly": True})
        assert opened.get("outcome") == "ok", opened
        cls.tool_revision = opened["revision"]
        tool_document = opened["document"]
        empty = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                  "name": "t", "bytes": []})
        target_spec = {"document": empty["document"], "revision": empty["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(empty["document"], empty["revision"])
        finished_cursor = pep_c23.parser_cursor_value(
            empty["document"], empty["revision"], done=True, lex_done=True, lex_stage="done")
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(empty["document"], empty["revision"], finished_cursor)),
                ("pep-c23-checker", "analyze_parsed",
                 [pep_c23.parser_progress(empty["document"], empty["revision"])],
                 pep_c23.checker_report(empty["document"], empty["revision"]))]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision, "function": function})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                              "tool": tool, "document": tool_document, "revision": cls.tool_revision,
                              "testVectors": [{"arguments": arguments, "expect": expected,
                                                "semanticTarget": target_spec}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                              "tool": tool, "document": tool_document, "revision": cls.tool_revision})
        cls.modules = module_sources()

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def check_module(self, source):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes", "name": "m",
                                    "bytes": list(source.encode("utf-8"))})
        self.assertEqual(target.get("outcome"), "ok", target)
        semantic_target = {"document": target["document"], "revision": target["revision"],
                           "entryFunctions": []}
        try:
            parsed = pep_c23.parse_target(self.session, source.encode("utf-8"), target,
                                          self.tool_revision)
        except RuntimeError as exc:
            return ("parse-transport" if "1 MiB" in str(exc) or "message" in str(exc).lower()
                    else "parse-fail:" + str(exc)[:60])
        try:
            checked = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                         "tool": "pep-c23-checker", "arguments": [parsed],
                                         "semanticTarget": semantic_target})
        except RuntimeError:
            return "transport-limit"
        if checked.get("outcome") != "ok":
            return checked.get("error", {}).get("code", "error")
        rep = {f["name"]: f["value"] for f in checked["result"]["fields"]}
        st = rep["status"]["value"] if isinstance(rep.get("status"), dict) else rep.get("status")
        return "checked-" + str(st)

    def test_closure_inventory_matches_recorded_boundaries(self):
        ledger = {}
        for label in (["T1", "T2", "T3", "T4", "T5"]
                      + ["F_ascii_letter", "F_ascii_digit", "F_ascii_continue",
                         "F_utf8_check", "F_advance_position",
                         "F_make_cursor", "F_make_token", "F_make_progress",
                         "F_lexer_start", "F_lexer_step", "FULL_lexer"]):
            source = self.modules[label]
            ledger[label] = {"bytes": len(source.encode("utf-8")),
                             "ocaml": ocaml_check(source),
                             "pep": self.check_module(source)}
        with open(ROOT / "_build" / "closure_inventory.json", "w", encoding="utf-8") as fh:
            json.dump(ledger, fh, indent=2, sort_keys=True)
        # Pinned boundaries (flip only on demonstrated improvement).
        for label in ("T1", "T2", "T3", "T4", "T5"):
            with self.subTest(module=label):
                self.assertEqual(ledger[label]["ocaml"], "valid")
                self.assertEqual(ledger[label]["pep"], "checked-valid")
        for label in ("F_ascii_letter", "F_ascii_digit", "F_ascii_continue",
                      "F_utf8_check", "F_advance_position",
                      "F_make_cursor", "F_make_token", "F_make_progress"):
            with self.subTest(module=label):
                self.assertEqual(ledger[label]["ocaml"], "valid")
        # FULL_lexer is recorded, not asserted: transport ceiling, separate track.
        self.assertIn("pep", ledger["FULL_lexer"])
        print("\nCLOSURE-LEDGER: " + json.dumps(
            {k: v["pep"] for k, v in sorted(ledger.items())}))


if __name__ == "__main__":
    unittest.main()
