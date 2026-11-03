"""A2 symbol/punctuation scanner differential against the OCaml seed's lexer
(missions PEP-A3-SUSTAINED-013 slice 3: ambiguous operators, comments, named
holes, EOF, CRLF, Unicode boundaries).

Target: `stdlib/scan.pep` @ the pinned A2 commit — `scan_sym_at`,
`scan_sym_count` (maximal munch over the seven two-byte forms and the seed's
single-byte list).

Oracle: the seed's own lexer, read through `pep.ps1 check --json`. The seed
lexes before it parses, so a single unexpected byte is reported as
`PEP_UNEXPECTED_CHARACTER` regardless of grammar context, while a genuine token
produces a parse/checker/type error (or a valid/incomplete result) instead. That
gives a context-free per-byte verdict without rebuilding the reference lexer:

  UNEXPECTED  any diagnostic is PEP_UNEXPECTED_CHARACTER -> not a token
  HOLE        status "incomplete" (a bare `?` opens a typed hole)
  COMMENT     the byte starts a comment (`#`, `//`) and lexes clean
  TOKEN       anything else that lexes

Claims:
  P1  Per-byte acceptance parity: `scan_sym_at` accepts a byte exactly when the
      seed lexes it as a TOKEN, and refuses UNEXPECTED bytes. HOLE/COMMENT bytes
      must be refused by this scanner (other scanners own them) — asserted as a
      boundary, not as an omission.
  P2  The seven two-byte forms (`<= == != && || -> =>`) are single tokens in the
      seed (each used in a real program position, no PEP_UNEXPECTED_CHARACTER)
      and `scan_sym_at` reports exactly those two bytes.
  P3  No over-munch across a separator: `- >` must yield `-` (width 1), while
      the seed refuses the lone `>` — i.e. maximal munch is pair-exact, not
      greedy over whitespace or prefixes.
  P4  A refused multi-byte character is named whole, not sliced: `é` (2 bytes),
      `€` (3), an emoji (4) each come back as text with byteLength 0, and a
      truncated sequence refuses with empty text instead of raising.
  P5  EOF and CRLF: an offset at end-of-source refuses (no symbol, no byte
      consumed); `scan_sym_count` treats CR and LF as separators.

Exit codes: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.
Usage: python a2_symbol_differential.py <a2-worktree-at-pin>
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

SCAN = REPO / "stdlib" / "scan.pep"
PEP_PS1 = REPO / "pep.ps1"

PROBES = """
fn a3_sym_at(offset: Int) -> ScanSym {
  return scan_sym_at(source_bytes(), offset)
}

fn a3_sym_count() -> ScanSymCount {
  return scan_sym_count(source_bytes())
}
"""

RESULTS = []

# Printable ASCII that is not a letter, a digit or whitespace.
SYMBOL_BYTES = [code for code in range(33, 127)
                if not (65 <= code <= 90 or 97 <= code <= 122 or 48 <= code <= 57)]

TWO_BYTE_FORMS = ["<=", "==", "!=", "&&", "||", "->", "=>"]

CONTEXT_PROGRAMS = {
    "<=": "fn main() -> Int {\n  if 1 <= 2 { return 0 } else { return 1 }\n}\n",
    "==": "fn main() -> Int {\n  if 1 == 2 { return 0 } else { return 1 }\n}\n",
    "!=": "fn main() -> Int {\n  if 1 != 2 { return 0 } else { return 1 }\n}\n",
    "&&": "fn main() -> Bool {\n  return true && false\n}\n",
    "||": "fn main() -> Bool {\n  return true || false\n}\n",
    "->": "fn f(x: Int) -> Int {\n  return x\n}\nfn main() -> Int {\n  return f(1)\n}\n",
    "=>": ("type Expr = Number(Int) | Add(Expr, Expr)\n"
           "fn evaluate(expr: Expr) -> Int {\n"
           "  return match expr {\n"
           "    Number(n) => n\n"
           "    Add(a, b) => evaluate(a) + evaluate(b)\n"
           "  }\n"
           "}\n"),
}

SPLIT_PROGRAM = ("fn f(x: Int) - > Int {\n  return x\n}\n"
                 "fn main() -> Int {\n  return 0\n}\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def sym_record(status, diagnostic, text, byte_length, next_offset):
    return typed_record_value("ScanSym", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("text", typed("Str", text)),
        ("byteLength", typed("Int", str(byte_length))),
        ("nextOffset", typed("Int", str(next_offset))),
    ])


def sym_count_record(status, diagnostic, count, offset):
    return typed_record_value("ScanSymCount", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("count", typed("Int", str(count))),
        ("offset", typed("Int", str(offset))),
    ])


def seed_class(payload_bytes):
    """Classify a payload with the seed lexer: UNEXPECTED / HOLE / CLEAN / LEXED."""
    with tempfile.TemporaryDirectory(prefix="a3-sym-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(payload_bytes)
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    raw = done.stdout.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"seed check returned non-JSON (exit {done.returncode}): "
                           f"{raw[:160]}{done.stderr[:160]}")
    codes = [item.get("code") for item in payload.get("diagnostics") or []]
    if "PEP_UNEXPECTED_CHARACTER" in codes:
        return "UNEXPECTED", codes
    if any("STRING" in (code or "") for code in codes):
        # `"` starts a string literal, which the string scanner owns.
        return "STRING", codes
    if payload.get("status") == "incomplete":
        # A bare `?` (or `_`) opens a typed hole, which the hole scanner owns.
        return "HOLE", codes
    if payload.get("status") == "valid":
        # A clean single-byte lex: only `#` does this (to end of line),
        # which the comment scanner owns.
        return "CLEAN", codes
    return "TOKEN", codes


class Scanner:
    def __init__(self):
        self.session = Session()
        opened = self.session.send({"schemaVersion": 3, "op": "open",
                                    "source": SCAN.read_text(encoding="utf-8") + PROBES,
                                    "name": "a3-sym-diff", "metadataOnly": True})
        require(opened, "outcome", "ok", "open scan module")
        require(opened, "status", "valid", "check scan module")
        self.document, self.revision = opened["document"], opened["revision"]
        sample = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "a3-sym-vectors", "bytes": []})
        require(sample, "outcome", "ok", "open validation sample")
        self.target_spec = {"document": sample["document"], "revision": sample["revision"],
                            "entryFunctions": []}
        self.register("a3-sym-at", "a3_sym_at", [typed("Int", 0)],
                      sym_record("unsupported",
                                 "Pep scan found no symbol at the end of the source",
                                 "", 0, 0))
        self.register("a3-sym-count", "a3_sym_count", [],
                      sym_count_record("ok", "", 0, 0))

    def register(self, tool, function, arguments, expect):
        registered = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_register", "tool": tool,
                                        "document": self.document,
                                        "revision": self.revision, "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_validate", "tool": tool,
                                       "document": self.document,
                                       "revision": self.revision,
                                       "testVectors": [{"arguments": arguments,
                                                        "expect": expect,
                                                        "semanticTarget": self.target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        activated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_activate", "tool": tool,
                                       "document": self.document,
                                       "revision": self.revision})
        require(activated, "status", "Active", f"activate {tool}")

    def invoke(self, tool, payload_bytes, arguments):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": f"a3-sym-{len(payload_bytes)}",
                                    "bytes": list(payload_bytes)})
        require(target, "outcome", "ok", "open payload")
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": tool,
                                      "arguments": arguments,
                                      "semanticTarget": {"document": target["document"],
                                                         "revision": target["revision"],
                                                         "entryFunctions": []}})
        require(response, "outcome", "ok", f"invoke {tool} (host refused the call)")
        return {item["name"]: item["value"] for item in response["result"]["fields"]}

    def sym_at(self, payload_bytes, offset=0):
        fields = self.invoke("a3-sym-at", payload_bytes, [typed("Int", offset)])
        return {"status": fields["status"]["value"],
                "diagnostic": fields["diagnostic"]["value"],
                "text": fields["text"]["value"],
                "byte_length": int(fields["byteLength"]["value"]),
                "next_offset": int(fields["nextOffset"]["value"])}

    def sym_count(self, payload_bytes):
        fields = self.invoke("a3-sym-count", payload_bytes, [])
        return {"status": fields["status"]["value"],
                "diagnostic": fields["diagnostic"]["value"],
                "count": int(fields["count"]["value"]),
                "offset": int(fields["offset"]["value"])}

    def close(self):
        self.session.close()


def main():
    print(f"REPO={REPO}")
    print(f"SCAN={SCAN}")
    scanner = Scanner()
    try:
        # ---- P1: per-byte acceptance parity with the seed lexer ---------------
        rows, mismatches = [], []
        for code in SYMBOL_BYTES:
            payload = bytes([code])
            label = chr(code)
            seed_classification, codes = seed_class(payload)
            verdict = scanner.sym_at(payload)
            accepted = verdict["status"] == "ok"
            if seed_classification == "UNEXPECTED":
                if accepted:
                    mismatches.append(f"{label!r} (0x{code:02x}): seed refuses "
                                      f"PEP_UNEXPECTED_CHARACTER, scanner accepted "
                                      f"{verdict['text']!r}")
            elif seed_classification in ("HOLE", "COMMENT", "STRING", "CLEAN"):
                # `?`/`_` open a hole, `#` starts a comment, `"` starts a string:
                # this scanner must refuse and leave the byte to the owner.
                if accepted:
                    mismatches.append(f"{label!r}: seed treats it as "
                                      f"{seed_classification}, scanner claimed it as a "
                                      f"symbol {verdict['text']!r}")
            else:  # TOKEN -> a real symbol byte
                if not accepted:
                    mismatches.append(f"{label!r} (0x{code:02x}): seed lexes it as a "
                                      f"token, scanner refused ({verdict['diagnostic']})")
                elif verdict["text"] != label or verdict["byte_length"] != 1:
                    mismatches.append(f"{label!r}: scanner text="
                                      f"{verdict['text']!r} width={verdict['byte_length']}")
            rows.append({"byte": label, "seed": seed_classification,
                         "scanner": verdict["status"], "codes": codes})
        record("P1 per-byte acceptance parity with the seed lexer", True,
               "parity", "parity" if not mismatches else "mismatch",
               "; ".join(mismatches) or f"{len(SYMBOL_BYTES)} bytes classified")

        # ---- P2: the seven two-byte forms ------------------------------------
        form_rows, form_mismatches = [], []
        for form in TWO_BYTE_FORMS:
            seed_classification, codes = seed_class(payload_ok := form.encode("utf-8"))
            program_class, program_codes = seed_class(
                CONTEXT_PROGRAMS[form].encode("utf-8"))
            verdict = scanner.sym_at(payload_ok)
            form_rows.append({"form": form, "seed_pair": seed_classification,
                              "seed_program": program_class,
                              "scanner_text": verdict["text"],
                              "scanner_width": verdict["byte_length"]})
            if program_class == "UNEXPECTED":
                form_mismatches.append(f"{form}: seed reports PEP_UNEXPECTED_CHARACTER "
                                       f"inside a real program ({program_codes})")
            if verdict["status"] != "ok" or verdict["text"] != form or \
                    verdict["byte_length"] != 2:
                form_mismatches.append(f"{form}: scanner gave status={verdict['status']} "
                                       f"text={verdict['text']!r} "
                                       f"width={verdict['byte_length']}")
        record("P2 seven two-byte forms are single tokens on both sides", True,
               "parity", "parity" if not form_mismatches else "mismatch",
               "; ".join(form_mismatches) or json.dumps(form_rows))

        # ---- P3: no over-munch across a separator ----------------------------
        split = scanner.sym_at(b"- >")
        split_seed, split_codes = seed_class(SPLIT_PROGRAM.encode("utf-8"))
        p3_bad = []
        if split["text"] != "-" or split["byte_length"] != 1:
            p3_bad.append(f"scanner consumed {split['text']!r} width "
                          f"{split['byte_length']} for '- >'")
        if split_seed != "UNEXPECTED":
            p3_bad.append(f"seed did not refuse the separated form (got {split_seed} "
                          f"{split_codes})")
        record("P3 no over-munch across a separator ('- >')", True, "pair-exact",
               "pair-exact" if not p3_bad else "mismatch",
               "; ".join(p3_bad) or "scanner width 1 ('-'); seed refuses lone '>'")

        # ---- P4: refused multi-byte characters are named whole --------------
        unicode_cases = {"é": "é".encode("utf-8"),
                         "€": "€".encode("utf-8"),
                         "😀": "😀".encode("utf-8"),
                         "truncated-€": "€".encode("utf-8")[:2]}
        unicode_rows, unicode_bad = [], []
        for name, payload in unicode_cases.items():
            verdict = scanner.sym_at(payload)
            unicode_rows.append({"case": name, **verdict})
            if verdict["status"] == "ok":
                unicode_bad.append(f"{name}: accepted as a symbol {verdict['text']!r}")
            elif name == "truncated-€":
                if verdict["text"] != "":
                    unicode_bad.append(f"{name}: expected empty text, got "
                                       f"{verdict['text']!r}")
            elif verdict["text"] != name:
                unicode_bad.append(f"{name}: text {verdict['text']!r} does not name the "
                                   f"whole character")
            if verdict["byte_length"] != 0:
                unicode_bad.append(f"{name}: byteLength {verdict['byte_length']} != 0")
        record("P4 refused multi-byte characters named whole, truncated refused", True,
               "whole-or-empty", "whole-or-empty" if not unicode_bad else "mismatch",
               "; ".join(unicode_bad) or json.dumps(unicode_rows))

        # ---- P5: EOF and CRLF -------------------------------------------------
        eof = scanner.sym_at(b"(", offset=1)
        count = scanner.sym_count(b"(\r\n)\t{\n}")
        p5_bad = []
        if eof["status"] == "ok":
            p5_bad.append(f"offset at end-of-source accepted {eof['text']!r}")
        if eof["byte_length"] != 0 or eof["next_offset"] != 1:
            p5_bad.append(f"end-of-source refusal consumed bytes "
                          f"(width={eof['byte_length']}, next={eof['next_offset']})")
        if count["status"] != "ok" or count["count"] != 4 or count["offset"] != 8:
            p5_bad.append(f"CRLF-separated count gave status={count['status']} "
                          f"count={count['count']} offset={count['offset']} "
                          f"(expected ok/4/8) {count['diagnostic']}")
        record("P5 EOF refusal and CRLF separators", True, "refused+4",
               "refused+4" if not p5_bad else "mismatch",
               "; ".join(p5_bad) or f"eof={eof['diagnostic']!r}; count=4 offset=8")
    finally:
        scanner.close()

    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
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
