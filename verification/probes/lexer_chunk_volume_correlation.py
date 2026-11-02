"""Agent 3 independent probe: real-lexer chunk ledger -> node-volume
correlation, measured at the pinned A1 revision.

What is new here is the ANALYSIS, not a new chunker: the probe reuses the
builder's measuring harness read-only (`tests.test_lexer_chunk_ledger.measure`
+ `tests.chunk_helper`) so the numbers are directly comparable with A1's pin,
then computes the correlation and per-node cost bands A1's headlines rest on.

Claims (all against the pinned ledger at `docs`/test docstring):
  C1  the five pinned-valid chunks are `valid`
      (ascii_letter 24, ascii_digit 12, ascii_continue 10, advance_position 33,
      make_token 55 — plus the declaration chunks)
  C2  the four pinned hot function chunks are `PEP_RUNTIME_STEP_LIMIT`
      (lexer_start 59, make_cursor 103, make_progress 125, utf8_check 268)
  C3  lexer_step (1,513 nodes) hits the host transport limit
  C4  within FUNCTION chunks the outcome is ordered by node count
      (max valid node count < min step-limited node count) — the
      volume-consistency half of A1's "node volume, not construct" thesis

Observations (no claim): per-node cost bands under an explicit
linear-through-origin model (cost/node in (100000/n_fail, 100000/n_valid]),
and whether any universal node ceiling fits across chunk KINDS.

Pure checker-layer: no emission, no native build, no execution.

Exit code: 0 = all claims observed, 1 = a claim falsified.

Usage: python lexer_chunk_volume_correlation.py <repo-root-at-pin>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402

BUDGET = 100_000
RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def main():
    import tests.test_lexer_chunk_ledger as ledger_module  # noqa: E402

    suite_class = ledger_module.RealLexerChunkLedgerTests
    suite_class.setUpClass()
    try:
        instance = suite_class("runTest")
        measured = instance.measure()["results"]
    finally:
        try:
            suite_class.tearDownClass()
        except Exception:  # noqa: BLE001
            pass

    table = {label: data for label, data in measured.items()}
    serialisable = {label: dict(data) for label, data in table.items()}

    pinned_valid = ["ascii_letter", "ascii_digit", "ascii_continue",
                    "advance_position", "make_token"]
    pinned_hot = ["lexer_start", "make_cursor", "make_progress", "utf8_check"]

    bad = [name for name in pinned_valid if table.get(name, {}).get("result") != "valid"]
    record("C1 five pinned-valid function chunks are valid", True, "none-bad",
           "none-bad" if not bad else "bad", ",".join(bad))

    decl_bad = [label for label, data in table.items()
                if label.startswith("declaration:") and data.get("result") != "valid"]
    record("C1b pinned declaration chunks are valid", True, "none-bad",
           "none-bad" if not decl_bad else "bad", ",".join(decl_bad))

    wrong = [name for name in pinned_hot
             if table.get(name, {}).get("result") != "PEP_RUNTIME_STEP_LIMIT"]
    record("C2 four pinned hot function chunks are PEP_RUNTIME_STEP_LIMIT",
           True, "none-wrong", "none-wrong" if not wrong else "wrong", ",".join(wrong))

    step_result = table.get("lexer_step", {}).get("result", "missing")
    record("C3 lexer_step hits the host transport limit", True,
           "host-transport-limit", step_result, str(step_result))

    fn_valid = [data["nodes"] for name, data in table.items()
                if not name.startswith("declaration:") and name != "lexer_step"
                and data.get("result") == "valid"]
    fn_fail = [data["nodes"] for name, data in table.items()
               if not name.startswith("declaration:") and name != "lexer_step"
               and data.get("result") == "PEP_RUNTIME_STEP_LIMIT"]
    ordered = bool(fn_valid and fn_fail) and max(fn_valid) < min(fn_fail)
    record("C4 function-chunk outcomes ordered by node count (volume-consistent)",
           True, "ordered", "ordered" if ordered else "not-ordered",
           f"max_valid={max(fn_valid) if fn_valid else None} "
           f"min_fail={min(fn_fail) if fn_fail else None}")

    # ---- analysis (observations, not claims) ----------------------------
    bands = {}
    if fn_valid and fn_fail:
        bands["function_chunks"] = (
            f"cost/node in ({BUDGET // min(fn_fail)}+, {BUDGET // max(fn_valid)}]"
            f" from pass@{max(fn_valid)} / fail@{min(fn_fail)} (linear model)")
    decl_valid = [data["nodes"] for name, data in table.items()
                  if name.startswith("declaration:") and data.get("result") == "valid"]
    if decl_valid:
        bands["declaration_chunks"] = (
            f"cost/node <= {BUDGET // max(decl_valid)} at pass@{max(decl_valid)} (upper bound only)")
    record("O1 per-node cost bands under linear-through-origin model", False,
           "observed", json.dumps(bands))

    cross = [f"{label}:{data['nodes']}={data.get('result')}"
             for label, data in sorted(table.items(), key=lambda kv: kv[1]["nodes"])]
    record("O2 full ledger table sorted by node count", False, "observed",
           " | ".join(cross))

    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"REPO={REPO}")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


if __name__ == "__main__":
    sys.exit(main())
