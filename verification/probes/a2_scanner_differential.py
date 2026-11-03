"""Adversarial differential: A2's Pep-written scanner (`stdlib/scan.pep`) against
the OCaml seed, at a pinned A2 worktree (LUCY-20261103-012: "adversarially
differential-test A2 scanner latest 9d4ab42 (Int64 max/MAX+1, negative offsets,
escapes incl escaped-NUL position, comments/operator boundaries when ready)").

Method: every claim is measured on BOTH sides.
  * scanner side  — `stdlib/scan.pep` functions invoked as registered v2 tools
    with the payload bytes as the host-authorised semanticTarget (the route the
    project's own tests use).
  * seed side     — `pep.ps1 check <file> --json` on an equivalent Pep source;
    ground truth is the seed's `status`, diagnostic codes and decoded literal
    bytes, never an assumption about what the language "should" do.

Claims:
  S1  Int64 max `9223372036854775807` accepted by the scanner with the exact
      value, matching the seed's acceptance.
  S2  `9223372036854775808` refused by the scanner, matching the seed's
      `PEP_INT_LITERAL_RANGE` refusal (an unsigned scanner is consistent with
      the seed refusing the literal, so no signed-max special case is owed).
  S3  Negative offsets are refused as a diagnostic (status != ok, no escaped
      host exception), rather than raising from the underlying `byte_at`.
  S4  Escape-set parity: the scanner accepts exactly the escapes the seed
      accepts (\n \t \\ \" \0 \r) and refuses the escapes the seed refuses
      (\a \x41), and its decoded byte length matches the seed's decoded bytes.
  S5  (disclosed gap, A2 BOOT-A2-20261103-013) escaped-NUL POSITION: the
      scanner's output must distinguish `"\0ab"` from `"ab\0"`; the seed's
      decoded bytes do. A2 has already declared it counts NUL without emitting
      a fragment, so a falsification here CONFIRMS the disclosure rather than
      discovering a new defect — it is reported as `DISCLOSED_GAP`.
  O1  (observation) a leading `-` is not consumed: `scan_int_at` is unsigned and
      the sign belongs to the caller. Recorded, not claimed.

Exit codes: 0 = no claim falsified, 1 = at least one claim falsified,
2 = harness error (never reads as a verdict).

Usage: python a2_scanner_differential.py <a2-worktree-at-pin>
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
fn a3_probe_int(offset: Int) -> ScanInt {
  return scan_int_at(source_bytes(), offset)
}

fn a3_probe_string(offset: Int) -> ScanString {
  return scan_string_at(source_bytes(), offset)
}
"""

RESULTS = []


def scan_int_record(status, diagnostic, value, next_offset):
    return typed_record_value("ScanInt", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("value", typed("Int", str(value))),
        ("nextOffset", typed("Int", str(next_offset))),
    ])


def scan_string_record(status, diagnostic, parts, byte_length, next_offset, nul_count):
    return typed_record_value("ScanString", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("parts", {"type": "List[Str]", "value": [{"type": "Str", "value": part}
                                                  for part in parts]}),
        ("byteLength", typed("Int", str(byte_length))),
        ("nextOffset", typed("Int", str(next_offset))),
        ("nulCount", typed("Int", str(nul_count))),
    ])


def record(case, claim, expect, outcome, detail="", label=None):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified,
                    "verdict": label or ("FALSIFIED" if falsified else "HELD")})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


# ---------------------------------------------------------------- seed side
def seed_check(source_text):
    """Ground truth from the OCaml seed: status, diagnostic codes, decoded
    string byte sequences (hex) found anywhere in the AST."""
    with tempfile.TemporaryDirectory(prefix="a3-seed-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_text(source_text, encoding="utf-8", newline="\n")
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8")
    raw = done.stdout.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"seed check returned non-JSON (exit {done.returncode}): "
                           f"{raw[:200]}{done.stderr[:200]}")
    strings = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("kind") == "string" and isinstance(node.get("value"), str):
                strings.append(node["value"].encode("utf-8").hex(" "))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload.get("ast"))
    return {"status": payload.get("status"),
            "codes": [item.get("code") for item in payload.get("diagnostics") or []],
            "string_bytes": strings}


def seed_int_source(literal):
    return f"fn main() -> Int {{\n  let x: Int = {literal}\n  return 0\n}}\n"


def seed_string_source(body):
    return f'fn main() -> Int {{\n  say("{body}")\n  return 0\n}}\n'


# ------------------------------------------------------------- scanner side
class Scanner:
    def __init__(self):
        self.session = Session()
        opened = self.session.send({"schemaVersion": 3, "op": "open",
                                    "source": SCAN.read_text(encoding="utf-8") + PROBES,
                                    "name": "a3-scan-diff", "metadataOnly": True})
        require(opened, "outcome", "ok", "open scan module")
        require(opened, "status", "valid", "check scan module")
        self.document, self.revision = opened["document"], opened["revision"]
        sample = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "a3-scan-vectors", "bytes": []})
        require(sample, "outcome", "ok", "open validation sample")
        self.target_spec = {"document": sample["document"], "revision": sample["revision"],
                            "entryFunctions": []}
        self.register("a3-scan-int", "a3_probe_int", [typed("Int", 0)],
                      scan_int_record("unsupported",
                                      "Pep scan found no digits at the end of the source",
                                      0, 0))
        self.register("a3-scan-string", "a3_probe_string", [typed("Int", 0)],
                      scan_string_record("unsupported",
                                         "Pep scan found no string literal at the end of the source",
                                         [], 0, 0, 0))

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

    def invoke(self, tool, payload, arguments):
        raw = payload.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": f"a3-payload-{len(raw)}", "bytes": list(raw)})
        require(target, "outcome", "ok", "open payload")
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": tool,
                                      "arguments": arguments,
                                      "semanticTarget": {"document": target["document"],
                                                         "revision": target["revision"],
                                                         "entryFunctions": []}})
        require(response, "outcome", "ok", f"invoke {tool} (host refused the call)")
        return {item["name"]: item["value"] for item in response["result"]["fields"]}

    def int_at(self, payload, offset=0):
        fields = self.invoke("a3-scan-int", payload, [typed("Int", offset)])
        return {"status": fields["status"]["value"],
                "diagnostic": fields["diagnostic"]["value"],
                "value": int(fields["value"]["value"]),
                "next_offset": int(fields["nextOffset"]["value"])}

    def string_at(self, payload, offset=0):
        fields = self.invoke("a3-scan-string", payload, [typed("Int", offset)])
        parts = [item["value"] for item in fields["parts"]["value"]]
        return {"status": fields["status"]["value"],
                "diagnostic": fields["diagnostic"]["value"],
                "parts": parts,
                "byte_length": int(fields["byteLength"]["value"]),
                "next_offset": int(fields["nextOffset"]["value"]),
                "nul_count": int(fields["nulCount"]["value"])}

    def close(self):
        self.session.close()


def main():
    print(f"REPO={REPO}")
    print(f"SCAN={SCAN}")
    scanner = Scanner()
    try:
        # ---- S1 / S2 / O1: integer boundary parity with the seed ----------
        max_literal = "9223372036854775807"
        over_literal = "9223372036854775808"
        seed_max = seed_check(seed_int_source(max_literal))
        scanned_max = scanner.int_at(max_literal)
        outcome = (f"scan status={scanned_max['status']} value={scanned_max['value']} "
                   f"nextOffset={scanned_max['next_offset']}; "
                   f"seed status={seed_max['status']} codes={seed_max['codes']}")
        record("S1 Int64 max accepted and equal", True,
               "scan ok+max; seed valid",
               "scan ok+max; seed valid"
               if (scanned_max["status"] == "ok"
                   and scanned_max["value"] == 9223372036854775807
                   and scanned_max["next_offset"] == len(max_literal)
                   and seed_max["status"] == "valid") else "mismatch",
               outcome)

        seed_over = seed_check(seed_int_source(over_literal))
        scanned_over = scanner.int_at(over_literal)
        seed_refuses = seed_over["status"] == "invalid" and bool(seed_over["codes"])
        record("S2 Int64 max+1 refused on both sides", True,
               "scan refused; seed invalid",
               "scan refused; seed invalid"
               if (scanned_over["status"] != "ok" and seed_refuses) else "mismatch",
               f"scan status={scanned_over['status']} diagnostic={scanned_over['diagnostic']!r}; "
               f"seed codes={seed_over['codes']}")

        seed_min = seed_check(seed_int_source("-9223372036854775808"))
        scan_min = scanner.int_at("-9223372036854775808")
        print(f"[O1] observation (not claimed): scan status={scan_min['status']} on a leading '-' "
              f"(unsigned scanner); seed on literal -9223372036854775808: "
              f"status={seed_min['status']} codes={seed_min['codes']}")
        RESULTS.append({"case": "O1 leading '-' not consumed (observation)", "claimed": False,
                        "expect": "observed", "outcome": scan_min["status"],
                        "detail": f"seed codes={seed_min['codes']}", "falsified": False,
                        "verdict": "OBSERVED"})

        # ---- S3: negative offsets refuse instead of raising ----------------
        negatives = []
        for offset in (-1, -19):
            try:
                result = scanner.int_at("42", offset)
                negatives.append((offset, result["status"], result["diagnostic"]))
            except BaseException as error:  # a raise here is the defect
                negatives.append((offset, "RAISED", f"{type(error).__name__}: {error}"))
        held = all(status not in ("ok", "RAISED") for _, status, _ in negatives)
        record("S3 negative offsets refuse without raising", True,
               "refused",
               "refused" if held else "mismatch",
               "; ".join(f"offset={o} status={s} diagnostic={d!r}" for o, s, d in negatives))

        # ---- S4: escape-set parity with the seed ---------------------------
        accepted = ["n", "t", "\\", '"', "0", "r"]
        refused = ["a", "x41"]
        rows, mismatches = [], []
        for letter in accepted:
            body = "\\" + letter
            payload = '"' + body + '"'
            seed = seed_check(seed_string_source(body))
            scan = scanner.string_at(payload)
            decoded = bytes(int(pair, 16) for pair in (seed["string_bytes"][0].split()
                                                       if seed["string_bytes"] else []))
            expected_text = decoded.replace(b"\x00", b"")
            nul_expected = decoded.count(b"\x00")
            joined = "".join(scan["parts"]).encode("utf-8")
            rows.append({"escape": body, "seed_status": seed["status"],
                         "seed_bytes": seed["string_bytes"], "scan_status": scan["status"],
                         "scan_parts": scan["parts"], "scan_byte_length": scan["byte_length"],
                         "scan_nul": scan["nul_count"]})
            if seed["status"] != "valid":
                mismatches.append(f"{body}: seed refused an escape it is expected to accept")
            elif scan["status"] != "ok":
                mismatches.append(f"{body}: seed valid, scan {scan['status']} "
                                  f"({scan['diagnostic']})")
            elif joined != expected_text:
                mismatches.append(f"{body}: parts {joined.hex(' ')} != seed "
                                  f"{expected_text.hex(' ')}")
            elif scan["byte_length"] != len(payload):
                mismatches.append(f"{body}: width {scan['byte_length']} != literal width "
                                  f"{len(payload)}")
            elif scan["nul_count"] != nul_expected:
                mismatches.append(f"{body}: nulCount {scan['nul_count']} != seed NULs "
                                  f"{nul_expected}")
        for letter in refused:
            body = "\\" + letter
            payload = '"' + body + '"'
            seed = seed_check(seed_string_source(body))
            scan = scanner.string_at(payload)
            rows.append({"escape": body, "seed_status": seed["status"],
                         "seed_codes": seed["codes"], "scan_status": scan["status"],
                         "scan_diagnostic": scan["diagnostic"]})
            if "PEP_INVALID_ESCAPE" in seed["codes"] and scan["status"] == "ok":
                mismatches.append(f"{body}: seed PEP_INVALID_ESCAPE, scan accepted")
        record("S4 escape set parity with the seed", True,
               "parity",
               "parity" if not mismatches else "mismatch",
               "; ".join(mismatches) or
               f"{len(accepted)} accepted + {len(refused)} refused")

        # ---- S5: escaped-NUL position (disclosed gap) ---------------------
        positions = {}
        for body in ("\\0ab", "ab\\0"):
            payload = f'"{body}"'
            seed = seed_check(seed_string_source(body))
            scan = scanner.string_at(payload)
            positions[body] = {
                "seed_status": seed["status"], "seed_bytes": seed["string_bytes"],
                "scan_parts": scan["parts"], "scan_byte_length": scan["byte_length"],
                "scan_nul": scan["nul_count"], "scan_next": scan["next_offset"]}
        distinct = (positions["\\0ab"]["scan_parts"] != positions["ab\\0"]["scan_parts"]
                    or positions["\\0ab"]["scan_next"] != positions["ab\\0"]["scan_next"])
        record("S5 escaped-NUL position distinguishable", True,
               "distinct scanner output for leading vs trailing NUL",
               "distinguishable" if distinct else "INDISTINGUISHABLE",
               json.dumps(positions, sort_keys=True),
               label="HELD" if distinct else "DISCLOSED_GAP")
    finally:
        scanner.close()

    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)} "
          f"disclosed_gaps={sum(1 for i in RESULTS if i['verdict'] == 'DISCLOSED_GAP')}")
    for item in RESULTS:
        if item["verdict"] != "HELD" and item["claimed"]:
            print(f"NOT HELD: {item['case']} -> {item['verdict']} ({item['outcome']})")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # harness failure must not read as a verdict
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
