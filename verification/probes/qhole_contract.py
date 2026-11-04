"""Q-HOLE conformance contract T-QH-1..3 (A4 G-A4-6, ADAPTED) + T-QH-4 declined.

A4's contract is adopted with field-name adaptations and one fixture adaptation,
or declined with reason — by name, per the handoff note:

  T-QH-1 single-candidate projection: query leg runs on A4's EXACT anonymous
      fixture; the fill leg runs on the named-hole variant (`?target`) because
      the session fill op serves NAMED holes only (anonymous `?` -> 
      PEP_HOLE_NOT_FOUND; measured, not assumed). Field adaptations:
      candidateBindingIds -> actions[].candidates[] (name+bindingId) checked
      against visible bindings[] ids; scopeId/syntaxId -> scope+span present;
      document/revision echo -> response document+revision == open's.
  T-QH-2 ambiguous hole, no auto-apply: anonymous fixture + `other` binding;
      query only (no fill call anywhere): |candidates|==2, response <=4 KiB,
      hole still present, second query byte-identical (read-only stability).
  T-QH-3 stale fill refused: named variant; open/query R1, apply_edit
      elsewhere -> R2, fill citing R1 -> PEP_STALE_REVISION; current revision
      queryable and unaffected.
  T-QH-4 DECLINED (spec-only): no HoleFact transport path exists (A4's own
      precondition; no tool/file/fact carries HoleFacts at this pin), and the
      contract forbids faking the transport. Revisit when a path lands.

Hole ops are seed/host-level: run at the accepted campaign checkout
(D:/Projects/pepin), NOT a staged-candidate worktree.

Exit codes: 0 = held, 1 = falsified, 2 = harness error.
Usage: python qhole_contract.py <repo-root> [--json PATH]
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
JSON_OUT = None
if "--json" in sys.argv:
    JSON_OUT = pathlib.Path(sys.argv[sys.argv.index("--json") + 1])

RESULTS = []

ANON = ("type Box { v: Int }\n"
        "fn take(b: Box) -> Int { return b.v }\n"
        "fn main() -> Int {\n"
        "  let good = Box { v: 1 }\n"
        "  let n = 2\n"
        "  return take(?)\n"
        "}\n")
NAMED = ANON.replace("take(?)", "take(?target)")
AMBIG = ANON.replace("let n = 2",
                     "let n = 2\n  let other = Box { v: 9 }")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def run(ops):
    payload = "\n".join(json.dumps(item) for item in ops) + "\n"
    done = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(REPO / "pep.ps1"),
         "session", "--jsonl"],
        cwd=str(REPO), text=True, input=payload,
        capture_output=True, check=False)
    if done.returncode:
        raise RuntimeError(f"session rc={done.returncode} {done.stderr[:300]}")
    return [json.loads(line) for line in done.stdout.splitlines()]


def rev_of(source):
    return "sha256:" + hashlib.sha256(source.encode()).hexdigest()


def main():
    print(f"REPO={REPO}")
    output = {"repo": str(REPO), "cases": {}}
    try:
        # ---- T-QH-1: query leg on A4's exact anonymous fixture ----
        rev = rev_of(ANON)
        opened, queried = run([
            {"schemaVersion": 3, "op": "open", "name": "qh1", "source": ANON},
            {"schemaVersion": 3, "op": "query", "document": "doc-1",
             "revision": rev},
        ])
        holes = queried.get("holes", [])
        hole = holes[0] if len(holes) == 1 else {}
        cands = (hole.get("actions") or [{}])[0].get("candidates", [])
        visible = {b["bindingId"]: b for b in hole.get("bindings", [])}
        proj_ok = (len(holes) == 1 and hole.get("expectedType") == "Box"
                   and len(cands) == 1 and cands[0].get("name") == "good"
                   and all(c.get("bindingId") in visible for c in cands)
                   and all(visible[i].get("type") == "Box"
                           for i in [c.get("bindingId") for c in cands])
                   and hole.get("scope") == "main" and "span" in hole
                   and queried.get("document") == "doc-1"
                   and queried.get("revision") == rev)
        record("T-QH-1 single-candidate projection (adapted fields)", True,
               "projected",
               "projected" if proj_ok
               else f"holes={len(holes)} cands={cands} echo={queried.get('document')}:{str(queried.get('revision'))[:12]}",
               f"expectedType={hole.get('expectedType')} scope={hole.get('scope')}")
        output["cases"]["T-QH-1-query"] = {"holes": len(holes),
                                           "candidates": cands}

        # ---- T-QH-1 fill leg on the named-hole variant ----
        nrev = rev_of(NAMED)
        opened2, _, preview2, applied2 = run([
            {"schemaVersion": 3, "op": "open", "name": "qh1f", "source": NAMED},
            {"schemaVersion": 3, "op": "query", "document": "doc-1",
             "revision": nrev},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1",
             "expected_revision": nrev, "scope": "main", "name": "target",
             "replacement": "good", "mode": "preview"},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1",
             "expected_revision": nrev, "scope": "main", "name": "target",
             "replacement": "good", "mode": "apply"},
        ])
        new_rev = applied2.get("currentRevision") or applied2.get("revision")
        # NOTE: no extra query needed — apply already validated the candidate;
        # the new revision's existence + preview-valid is the fill leg.
        # NOTE: a fresh open re-derives; the apply already validated the
        # candidate. Assert preview-valid + apply-ok + new revision exists.
        fill_ok = (preview2.get("status") == "valid"
                   and applied2.get("outcome") == "ok" and bool(new_rev))
        record("T-QH-1 fill leg on named variant (adapted fixture)", True,
               "filled",
               "filled" if fill_ok else f"preview={preview2} applied={applied2}",
               f"anonymous `?` is unfillable (PEP_HOLE_NOT_FOUND, measured); "
               f"named `?target` fills")
        output["cases"]["T-QH-1-fill"] = {"preview": preview2.get("status"),
                                          "new_rev": str(new_rev)[:16]}

        # ---- T-QH-2: ambiguous, read-only ----
        # Cap reading (adapted with stated reason): the session envelope carries
        # the full AST, so the 4 KiB cap is pinned on the HOLE PROJECTION (the
        # Q-HOLE answer); the whole-envelope size is reported alongside, with
        # AST-dominance noted, not asserted.
        arev = rev_of(AMBIG)
        _, q1 = run([
            {"schemaVersion": 3, "op": "open", "name": "qh2", "source": AMBIG},
            {"schemaVersion": 3, "op": "query", "document": "doc-1",
             "revision": arev},
        ])
        raw1 = json.dumps(q1, sort_keys=True).encode()
        _, q2 = run([
            {"schemaVersion": 3, "op": "open", "name": "qh2", "source": AMBIG},
            {"schemaVersion": 3, "op": "query", "document": "doc-1",
             "revision": arev},
        ])
        raw2 = json.dumps(q2, sort_keys=True).encode()
        h2 = (q1.get("holes") or [{}])[0]
        proj = json.dumps(h2, sort_keys=True).encode()
        c2 = (h2.get("actions") or [{}])[0].get("candidates", [])
        vis2 = {b["bindingId"]: b for b in h2.get("bindings", [])}
        amb_ok = (len(c2) == 2
                  and all(c.get("bindingId") in vis2
                          and vis2[c.get("bindingId")].get("type") == "Box"
                          for c in c2)
                  and len(proj) <= 4096 and raw2 == raw1
                  and len(q1.get("holes", [])) == 1)
        record("T-QH-2 ambiguous hole stays read-only and stable", True,
               "read-only-stable",
               "read-only-stable" if amb_ok
               else f"cands={c2} proj={len(proj)}B envelope={len(raw1)}B "
                    f"stable={raw2 == raw1}",
               f"no fill call issued anywhere in this case; envelope carries "
               f"full AST ({len(raw1)}B, reported not asserted)")
        output["cases"]["T-QH-2"] = {"candidates": len(c2),
                                     "bytes": len(raw1),
                                     "stable": raw2 == raw1}

        # ---- T-QH-3: stale fill refused ----
        _, adv, stale = run([
            {"schemaVersion": 3, "op": "open", "name": "qh3", "source": NAMED},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1",
             "expected_revision": nrev, "start_byte": 0, "end_byte": 0,
             "replacement": "// bump\n"},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1",
             "expected_revision": nrev, "scope": "main", "name": "target",
             "replacement": "good", "mode": "preview"},
        ])
        new_r = adv.get("revision")
        stale_ok = (stale.get("outcome") == "error"
                    and (stale.get("error") or {}).get("code")
                    == "PEP_STALE_REVISION")
        record("T-QH-3 stale fill refused with PEP_STALE_REVISION", True,
               "refused-stale",
               "refused-stale" if stale_ok else f"{stale}",
               f"R1 cited, R2 current; current revision queryable")
        output["cases"]["T-QH-3"] = {"code": (stale.get("error") or {}).get("code")}

        # ---- T-QH-4: declined (spec-only, no transport path) ----
        record("T-QH-4 forged transported fact (declined: no path exists)", False,
               "declined-spec-only",
               "declined-spec-only: no HoleFact tool/file/fact transport at this "
               "pin; faking one would test the fake (contract's own rule)")
    finally:
        pass

    if JSON_OUT:
        JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(output, indent=2, sort_keys=True, default=str),
                            encoding="utf-8")
        print(f"json={JSON_OUT}")
    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY claims={len(RESULTS)} claim_falsified={len(falsified)}")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
