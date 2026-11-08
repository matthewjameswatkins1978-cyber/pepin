"""A4 test-only field-range extractor (LUCY-20261106-006, A1 NEEDS).

Reads the seed `check --json` typed tree of mc_seam_oracle.pep, splits the
single make_cursor return record into field groups 0-7 / 8-15, and emits one
slice descriptor per group. Verifies the neg fixture still refuses with the
identical span. No checker/host changes; seed oracle only.

Usage:
  python docs/spec/mc_seam_extract.py --pep-root D:/Projects/pepin [--out DIR]
Exit 0 iff every assertion below holds, else 1 with the first failure.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = HERE / "mc_seam_oracle.pep"
NEG = HERE / "mc_seam_neg.pep"
GROUPS = (("mc_seam_slice_0_7.json", range(0, 8)),
          ("mc_seam_slice_8_15.json", range(8, 16)))


def run_check(pep_ps1, target):
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(pep_ps1),
         "check", str(target), "--json"],
        capture_output=True, text=True, check=False)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.returncode, {"status": "unparseable",
                                 "raw": proc.stdout[:200]}


def fail(msg):
    print(f"FAIL: {msg}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pep-root", default="D:/Projects/pepin")
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    outdir = Path(args.out)
    pep = Path(args.pep_root) / "pep.ps1"
    ok = True

    code, oracle = run_check(pep, ORACLE)
    if code != 0 or oracle.get("status") != "valid":
        return 1 if not fail("oracle fixture must check valid, exit 0") else 1

    typed = oracle.get("typedTree", {})
    fn = next((f for f in typed.get("functions", [])
               if f.get("name") == "make_cursor"), None)
    if fn is None:
        return 1 if not fail("make_cursor missing from typed tree") else 1
    param_type = {p["name"]: (p.get("bindingId"), p.get("type"))
                  for p in fn.get("parameters", [])}
    ret = next((b for b in fn.get("body", [])
                if b.get("kind") == "return"), None)
    retval = (ret or {}).get("value", {})
    rec = retval.get("expression", {})
    rec_span = retval.get("span")
    if rec.get("kind") != "record" or not rec_span:
        return 1 if not fail("return value is not a record node") else 1
    fields = rec.get("fields", [])
    if len(fields) != 16:
        return 1 if not fail(f"expected 16 fields, got {len(fields)}") else 1

    decl = next((t for t in typed.get("types", [])
                 if t.get("name") == "LexCursor"), None)
    if decl is None:
        return 1 if not fail("LexCursor declaration missing") else 1
    decl_fields = {f.get("fieldId"): (f.get("name"), f.get("type"))
                   for f in decl.get("fields", [])}
    if set(decl_fields) != set(range(16)):
        return 1 if not fail("declaration fieldIds are not 0-15") else 1
    adecl = next((n for n in oracle.get("ast", [])
                  if n.get("kind") == "record_declaration" and
                  n.get("name") == "LexCursor"), {})
    decl_span = adecl.get("span")
    if not decl_span:
        return 1 if not fail("LexCursor declaration span missing") else 1

    by_id = {}
    for fld in fields:
        fid = fld.get("fieldId")
        val = fld.get("value", {})
        expr = val.get("expression", {})
        if expr.get("kind") != "binding":
            return 1 if not fail(
                f"field {fid} value is not a bare binding: "
                f"{expr.get('kind')}") else 1
        dname, dtype = decl_fields.get(fid, (None, None))
        if val.get("type") != dtype:
            return 1 if not fail(
                f"field {fid} value type disagrees with declaration") else 1
        by_id[fid] = {"name": dname, "type": val.get("type"),
                      "span": val.get("span"),
                      "bindingId": expr.get("bindingId")}

    # Cross-check binding identity against parameter declarations.
    for fid, info in by_id.items():
        pname = next((n for n, (bid, _) in param_type.items()
                      if bid == info["bindingId"] and n == info["name"]),
                     None)
        if pname is None:
            return 1 if not fail(
                f"field {fid} binding identity mismatch") else 1

    # Revision stamp: source pin the fixture was derived from + fixture bytes.
    rev = {"lexer_source": "pep_lexer.pep @57fe424==a9e9e2f(byte-identical)",
           "oracle_sha256": hashlib.sha256(
               ORACLE.read_bytes()).hexdigest()[:16]}

    seen, slices = set(), {}
    for fname, rng in GROUPS:
        group = [by_id[i] for i in rng]
        carried = sorted({g["bindingId"] for g in group})
        referenced = sorted(param_type[n][0] for n in
                            [g["name"] for g in group])
        if carried != referenced:
            return 1 if not fail(f"{fname}: carried != referenced") else 1
        slices[fname] = {
            "header": {"recordType": "LexCursor",
                       "recordSpan": rec_span,
                       "declSpan": decl_span},
            "fieldIds": list(rng),
            "fields": group,
            "carriedBindings": carried,
            "revision": rev,
        }
        seen.update(rng)
        print(f"{fname}: VALID "
              f"({len(group)} fields, {len(carried)} carried bindings)")
    if seen != set(range(16)):
        return 1 if not fail("groups do not partition all 16 fields") else 1

    for fname, payload in slices.items():
        (outdir / fname).write_text(json.dumps(payload, indent=1),
                                    encoding="utf-8")
        print(f"wrote {fname}")

    ncode, neg = run_check(pep, NEG)
    diags = neg.get("diagnostics", [])
    want_span = by_id[4]["span"]  # offset field in the oracle
    if ncode == 0 or neg.get("status") != "invalid" or not any(
            d.get("code") == "PEP_TYPE_MISMATCH" and
            d.get("span") == want_span for d in diags):
        return 1 if not fail(
            "neg fixture must refuse MISMATCH at the oracle offset span") else 1
    print("neg: VALID (refuses MISMATCH at identical span)")
    print("PASS: both halves sliceable, oracle pair green")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
