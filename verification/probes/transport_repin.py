"""Agent 3 independent probe: session-transport rejections re-pinned at the
current A1 revision (corpus cases R1/R2/R4 from
`verification/adversarial/cases/REVISION_AND_LIMITS.md`, originally measured
at base `805062b`; R3 — the 65,536-byte cap — is re-pinned separately by
`open_bytes_limit.py`).

Claims (all against SESSION_PROTOCOL.md):
  T1 a stale `expected_revision` is rejected with `PEP_STALE_REVISION` and the
     document's CURRENT revision is unchanged afterwards
  T2 an `apply_edit` range splitting a UTF-8 code point is rejected with
     `PEP_UTF8_BOUNDARY`
  T3 a query naming an unknown document/revision is rejected with
     `PEP_DOCUMENT_NOT_FOUND`

Session protocol only (schema v3, one process per probe): no native build,
no execution of generated C.

Exit code: 0 = all claims observed, 1 = a claim falsified.

Usage: python transport_repin.py <repo-root-at-pin>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session  # noqa: E402

RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def error_code(response):
    error = response.get("error") or {}
    return error.get("code", "NO_ERROR"), json.dumps(error)[:240]


def main():
    session = Session()
    try:
        # ---- T1: stale expected_revision --------------------------------
        opened = session.send({"schemaVersion": 3, "op": "open",
                               "source": "fn main() -> Int { return 1 }\n",
                               "name": "t1"})
        rev1 = opened["revision"]
        document = opened["document"]
        first = session.send({"schemaVersion": 3, "op": "apply_edit",
                              "document": document, "expected_revision": rev1,
                              "start_byte": 26, "end_byte": 27, "replacement": "2"})
        rev2 = first.get("revision")
        stale = session.send({"schemaVersion": 3, "op": "apply_edit",
                              "document": document, "expected_revision": rev1,
                              "start_byte": 26, "end_byte": 27, "replacement": "3"})
        code, detail = error_code(stale)
        current = stale.get("currentRevision")
        ok = (stale.get("outcome") == "error" and code == "PEP_STALE_REVISION"
              and current == rev2 and rev2 is not None)
        record("T1 stale expected_revision refused, current revision preserved",
               True, "stale-refused+current-unchanged",
               "stale-refused+current-unchanged" if ok else "mismatch",
               f"code={code} currentRevision_unchanged={current == rev2} detail={detail}")

        # ---- T2: range splits a UTF-8 code point -------------------------
        # 'say("hé")\n' — é occupies bytes 6..7 (half-open [6,7) = one byte)
        opened2 = session.send({"schemaVersion": 3, "op": "open",
                                "source": 'say("hé")' + "\n", "name": "t2"})
        split = session.send({"schemaVersion": 3, "op": "apply_edit",
                              "document": opened2["document"],
                              "expected_revision": opened2["revision"],
                              "start_byte": 6, "end_byte": 7, "replacement": "X"})
        code2, detail2 = error_code(split)
        ok2 = split.get("outcome") == "error" and code2 == "PEP_UTF8_BOUNDARY"
        record("T2 UTF-8 code-point-splitting edit refused", True, "PEP_UTF8_BOUNDARY",
               "PEP_UTF8_BOUNDARY" if ok2 else "mismatch",
               f"code={code2} detail={detail2}")

        # ---- T3: forged document/revision query --------------------------
        forged = session.send({"schemaVersion": 3, "op": "query",
                               "document": "doc-UNKNOWN",
                               "revision": "sha256:" + "0" * 64})
        code3, detail3 = error_code(forged)
        ok3 = forged.get("outcome") == "error" and code3 == "PEP_DOCUMENT_NOT_FOUND"
        record("T3 forged document/revision query refused", True, "PEP_DOCUMENT_NOT_FOUND",
               "PEP_DOCUMENT_NOT_FOUND" if ok3 else "mismatch",
               f"code={code3} detail={detail3}")
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"REPO={REPO}")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


if __name__ == "__main__":
    sys.exit(main())
