"""Agent 3 independent probe: the `open_bytes` source-byte cap, re-pinned at
the current revision (LUCY-20261102-005 first-target list item).

Reference: `docs/SESSION_PROTOCOL.md` / `pep_ocaml.ml` (`maxOpenByteInput`,
`PEP_SOURCE_BYTE_LIMIT`), previously measured at base `805062b` (corpus case
R3 in REVISION_AND_LIMITS.md). This probe re-pins the same boundary against
the pinned checkout passed as argv[1].

Claims:
  L1  exactly 65,536 bytes open successfully (outcome ok).
  L2  65,537 bytes are refused with error code PEP_SOURCE_BYTE_LIMIT.

Pure session protocol: no compiler emission, no native build, no execution.

Exit code: 0 = both claims observed as claimed, 1 = a claim falsified.

Usage: python open_bytes_limit.py <repo-root-at-pin>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session  # noqa: E402

LIMIT = 65_536
RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def attempt(session, size):
    """Open `size` bytes with metadataOnly; return (kind, detail)."""
    response = session.send({"schemaVersion": 3, "op": "open_bytes",
                             "name": f"limit-{size}",
                             "bytes": [97] * size, "metadataOnly": True})
    if response.get("outcome") == "ok":
        return "ok", json.dumps({key: response.get(key)
                                 for key in ("document", "revision", "status")})[:200]
    error = response.get("error") or {}
    return error.get("code", "UNKNOWN_ERROR"), json.dumps(error)[:300]


def main():
    session = Session()
    try:
        kind, detail = attempt(session, LIMIT)
        record("L1 open_bytes at exactly 65,536 bytes succeeds", True, "ok", kind, detail)

        kind, detail = attempt(session, LIMIT + 1)
        record("L2 open_bytes at 65,537 refused with PEP_SOURCE_BYTE_LIMIT",
               True, "PEP_SOURCE_BYTE_LIMIT", kind, detail)
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
