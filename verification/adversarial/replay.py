"""Agent 3 adversarial corpus replay lab (interpreter + session only).

Replays every base-tree probe behind verification/adversarial/cases/
(P/N/U/R/S/RECORD sets) and asserts the recorded SPEC/observed outcomes.
Pin-specific suites (str_contains @ A1 tip, A2 emit re-runs) are NOT
replayed here; their receipts state exact detached-worktree commands.

Safe under the Defender hold: only `pep.ps1 check/run/query/session`
(OCaml seed, in-process) and temp files. No C toolchain, no binaries.

Usage (from the agent3 worktree root):
    python verification/adversarial/replay.py
Exit 0 iff every probe reproduces its receipted outcome.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = Path(tempfile.gettempdir())
PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
results = []


def _pwsh(args, inp=None, timeout=120):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-Command", *args],
        input=inp, capture_output=True, text=True, cwd=str(ROOT),
        timeout=timeout)


def check(name, data, exp_status, exp_codes=()):
    p = TMP / ("a3re_%s.pep" % name)
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    try:
        r = _pwsh(["./pep.ps1", "check", str(p), "--json"])
        d = json.loads((r.stdout or "{}"))
        codes = tuple(x.get("code") for x in d.get("diagnostics", []))
        ok = d.get("status") == exp_status and all(
            c in codes for c in exp_codes)
        detail = "status=%s codes=%s" % (d.get("status"), codes)
    except Exception as e:  # noqa: BLE001 - record, don't crash the lab
        ok, detail = False, "error: %r" % e
    finally:
        p.unlink(missing_ok=True)
    results.append((name, PASS if ok else FAIL, detail))
    return ok


def run(name, data, exp_out=None, exp_rc=0, exp_err_contains=()):
    p = TMP / ("a3re_%s.pep" % name)
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    try:
        r = _pwsh(["./pep.ps1", "run", str(p)])
        ok = r.returncode == exp_rc
        if exp_out is not None:
            ok = ok and (r.stdout or "") == exp_out
        ok = ok and all(s in (r.stderr or "") for s in exp_err_contains)
        detail = "rc=%d out=%r err=%r" % (
            r.returncode, (r.stdout or "")[:60], (r.stderr or "")[:80])
    except Exception as e:  # noqa: BLE001
        ok, detail = False, "error: %r" % e
    finally:
        p.unlink(missing_ok=True)
    results.append((name, PASS if ok else FAIL, detail))
    return ok


def query_holes(name, data, exp_identity, exp_type):
    p = TMP / ("a3re_%s.pep" % name)
    p.write_bytes(data.encode("utf-8"))
    try:
        r = _pwsh(["./pep.ps1", "query", str(p), "--holes", "--json"])
        d = json.loads((r.stdout or "{}"))
        holes = d.get("holes", [])
        ok = (d.get("status") == "incomplete" and len(holes) == 1
              and holes[0].get("identity") == exp_identity
              and holes[0].get("expectedType") == exp_type)
        detail = "holes=%s" % [(h.get("identity"), h.get("expectedType"))
                               for h in holes]
    except Exception as e:  # noqa: BLE001
        ok, detail = False, "error: %r" % e
    finally:
        p.unlink(missing_ok=True)
    results.append((name, PASS if ok else FAIL, detail))
    return ok


def session(name, reqs, exp_last):
    """exp_last: (outcome, code-or-status)."""
    try:
        payload = "\n".join(json.dumps(r) for r in reqs) + "\n"
        r = _pwsh(["./pep.ps1", "session", "--jsonl"], inp=payload)
        out = [json.loads(ln) for ln in (r.stdout or "").splitlines()
               if ln.strip()]
        last = out[-1] if out else {}
        want_outcome, want = exp_last
        got_code = ((last.get("error") or {}).get("code")
                    if last.get("outcome") == "error"
                    else last.get("status"))
        ok = last.get("outcome") == want_outcome and got_code == want
        detail = "outcome=%s code/status=%s" % (
            last.get("outcome"), got_code)
    except Exception as e:  # noqa: BLE001
        ok, detail = False, "error: %r" % e
    results.append((name, PASS if ok else FAIL, detail))
    return ok


def main():
    # P: value-copy independence
    run("P1", "let a = [1, 2, 3]\nlet b = a\nlet a2 = append(a, 4)\n"
             "say(int_text(length(a)))\nsay(int_text(length(b)))\n"
             "say(int_text(length(a2)))\n", exp_out="3\n3\n4\n")
    run("P2", "var a = [1]\nlet b = a\na = append(a, 2)\n"
             "say(int_text(length(a)))\nsay(int_text(length(b)))\n",
        exp_out="2\n1\n")
    run("P3", "type Point { x: Int y: Int }\n"
             "let pts = [Point { x: 1, y: 2 }]\nlet alias = pts\n"
             "let grown = append(pts, Point { x: 9, y: 9 })\n"
             "say(int_text(length(alias)))\nsay(int_text(length(grown)))\n",
        exp_out="1\n2\n")
    # N: negatives + edges
    check("N1", "fn main() -> Int { return ?pending }", "incomplete")
    run("N1-run", "fn main() -> Int { return ?pending }", exp_rc=1,
        exp_err_contains=("incomplete",))
    check("N2", "fn bump(edit value: Int) -> Unit { value = value + 1 }\n"
                "fn main() -> Int { return 0 }",
          "invalid", ("PEP_PARSE_EXPECTED",))
    check("N3", "fn has() -> Bool { return contains([[1]], [1]) }",
          "invalid", ("PEP_MEMBERSHIP_UNSUPPORTED",))
    check("N4-check", "say(int_text(1 / 0))", "valid")
    run("N4-run", 'say(int_text(1 / 0))', exp_rc=1,
        exp_err_contains=("PEP_RUNTIME_DIVISION_BY_ZERO",))
    run("E1b", 'fn main() -> Unit { say("from-main") }', exp_out="")
    # U: UTF-8 / CRLF / spans
    check("U1", "fn caf\u00e9() -> Int { return Unknown(1) }\n"
                "fn main() -> Int { return 0 }\n".encode("utf-8"),
          "invalid", ("PEP_UNEXPECTED_CHARACTER",))
    check("U2", b"fn main() -> Int {\r\n  return 1\r\n}\r\n", "valid")
    check("U3", b"fn main() -> Int { return \xff\xfe }\n",
          "invalid", ("PEP_INVALID_UTF8",))
    check("U4", 'say("h\u00e9")\n'.encode("utf-8"), "valid")
    check("U5", "# caf\u00e9 comment\nfn main() -> Int { return Unknown }\n"
                .encode("utf-8"),
          "invalid", ("PEP_UNKNOWN_VARIABLE",))
    # E2: byte-derived columns (offset 12 -> column 13)
    p = TMP / "a3re_E2.pep"
    p.write_bytes('say("h\u00e9"); Unknown\n'.encode("utf-8"))
    try:
        r = _pwsh(["./pep.ps1", "check", str(p), "--json"])
        d = json.loads((r.stdout or "{}"))
        sp = (d.get("diagnostics") or [{}])[0].get("span", {}).get("start",
                                                                   {})
        ok = (sp.get("offset") == 12 and sp.get("column") == 13)
        results.append(("E2", PASS if ok else FAIL, str(sp)))
    finally:
        p.unlink(missing_ok=True)
    # R: revision identity + limits (stateful sessions)
    src = "fn main() -> Int { return 1 }\n"
    session("R0-open", [{"schemaVersion": 3, "op": "open", "name": "r",
                         "source": src}], ("ok", "valid"))
    # R1 needs chaining: open, edit ok, stale edit rejected
    payload = [{"schemaVersion": 3, "op": "open", "name": "r1",
                "source": src}]
    r = _pwsh(["./pep.ps1", "session", "--jsonl"],
              inp="\n".join(json.dumps(x) for x in payload) + "\n")
    o = [json.loads(ln) for ln in (r.stdout or "").splitlines()
         if ln.strip()]
    doc, rev1 = o[0]["document"], o[0]["revision"]
    payload = [
        {"schemaVersion": 3, "op": "open", "name": "r1", "source": src},
        {"schemaVersion": 3, "op": "apply_edit", "document": doc,
         "expected_revision": rev1, "start_byte": 26, "end_byte": 27,
         "replacement": "2"},
        {"schemaVersion": 3, "op": "apply_edit", "document": doc,
         "expected_revision": "REV-STALE", "start_byte": 26,
         "end_byte": 27, "replacement": "3"},
    ]
    # fix the stale step to replay the true rev1
    payload[2]["expected_revision"] = rev1
    r = _pwsh(["./pep.ps1", "session", "--jsonl"],
              inp="\n".join(json.dumps(x) for x in payload) + "\n")
    o = [json.loads(ln) for ln in (r.stdout or "").splitlines()
         if ln.strip()]
    ok = (o[1].get("outcome") == "ok"
          and o[2].get("outcome") == "error"
          and (o[2].get("error") or {}).get("code")
          == "PEP_STALE_REVISION")
    results.append(("R1", PASS if ok else FAIL,
                    "edit=%s stale=%s" % (
                        o[1].get("outcome"),
                        (o[2].get("error") or {}).get("code"))))
    uni = 'say("h\u00e9")\n'
    r = _pwsh(["./pep.ps1", "session", "--jsonl"],
              inp="\n".join(json.dumps(x) for x in [
                  {"schemaVersion": 3, "op": "open", "name": "r2",
                   "source": uni}]) + "\n")
    o = [json.loads(ln) for ln in (r.stdout or "").splitlines()
         if ln.strip()]
    doc2, rev2 = o[0]["document"], o[0]["revision"]
    session("R2", [
        {"schemaVersion": 3, "op": "open", "name": "r2", "source": uni},
        {"schemaVersion": 3, "op": "apply_edit", "document": doc2,
         "expected_revision": rev2, "start_byte": 6, "end_byte": 7,
         "replacement": "X"}],
        ("error", "PEP_UTF8_BOUNDARY"))
    session("R3-over", [
        {"schemaVersion": 3, "op": "open_bytes", "name": "big",
         "bytes": [32] * 65537}], ("error", "PEP_SOURCE_BYTE_LIMIT"))
    session("R3-at", [
        {"schemaVersion": 3, "op": "open_bytes", "name": "ok",
         "bytes": [32] * 65536}], ("ok", "valid"))
    session("R4", [
        {"schemaVersion": 3, "op": "open", "name": "r4", "source": src},
        {"schemaVersion": 3, "op": "query", "document": "doc-NOPE",
         "revision": "sha256:" + "0" * 64}],
        ("error", "PEP_DOCUMENT_NOT_FOUND"))
    # S: evaluation order, errors, holes, fuel
    run("S1-or", 'say(int_text(if true || (1 / 0 == 0) { 1 } else { 2 }))',
        exp_out="1\n")
    run("S1-left", 'say(int_text(if (1 / 0 == 0) || true { 1 } else { 2 }))',
        exp_rc=1, exp_err_contains=("PEP_RUNTIME_DIVISION_BY_ZERO",))
    p = TMP / "a3re_S2.pep"
    p.write_text("fn main() -> Int { return Nope1 + Nope2 }",
                 encoding="utf-8", newline="\n")
    try:
        r = _pwsh(["./pep.ps1", "check", str(p), "--json"])
        d = json.loads((r.stdout or "{}"))
        diags = d.get("diagnostics", [])
        ok = (d.get("status") == "invalid" and len(diags) == 1
              and diags[0].get("code") == "PEP_UNKNOWN_VARIABLE")
        results.append(("S2", PASS if ok else FAIL,
                        "ndiags=%d" % len(diags)))
    finally:
        p.unlink(missing_ok=True)
    query_holes("S3", "type Expr = Number(Int) | Add(Expr, Expr)\n"
                      "fn ev(e: Expr) -> Int {\n return match e {\n"
                      " Number(v) => v\n Add(l, r) => ?calc\n }\n}\n"
                      "fn main() -> Int { return 0 }", "calc", "Int")
    run("S4-100k", "fn count() -> Int {\n var x = 0\n while x != 100000 {\n"
                   " x = x + 1\n }\n return x\n}\n"
                   "say(int_text(count()))\n", exp_out="100000\n")
    run("S4-1M", "fn count() -> Int {\n var x = 0\n while x != 1000000 {\n"
                 " x = x + 1\n }\n return x\n}\n"
                 "say(int_text(count()))\n", exp_rc=1,
        exp_err_contains=("PEP_RUNTIME_STEP_LIMIT",))
    _deep = ("fn down(n: Int) -> Int {\n if n == 0 { return 0 } else { }\n"
             " return down(n - 1)\n}\n")
    run("S5-depth-ok", _deep + "say(int_text(down(100)))\n",
        exp_out="0\n")
    run("S5-depth-trip", _deep + "say(int_text(down(100000)))\n",
        exp_rc=1, exp_err_contains=("PEP_RUNTIME_CALL_DEPTH",))
    _mut = ("fn a(n: Int) -> Int {\n if n == 0 { return 0 } else { }\n"
            " return b(n - 1)\n}\n"
            "fn b(n: Int) -> Int {\n return a(n - 1)\n}\n")
    run("S5-mutual", _mut + "say(int_text(a(100000)))\n",
        exp_rc=1, exp_err_contains=("PEP_RUNTIME_CALL_DEPTH",))
    run("S6-prec", "say(int_text(2 + 3 * 4))\n", exp_out="14\n")
    run("S6-paren", "say(int_text((2 + 3) * 4))\n", exp_out="20\n")
    run("S6-assoc-sub", "say(int_text(10 - 3 - 2))\n", exp_out="5\n")
    run("S6-assoc-div", "say(int_text(100 / 10 / 2))\n", exp_out="5\n")
    check("S6-str-plus", 'say("a" + "b")',
          "invalid", ("PEP_TYPE_MISMATCH",))
    check("M-match-bool",
          "fn main() -> Int { return match true { true => 1 false => 0 } }",
          "invalid", ("PEP_MATCH_NON_UNION",))
    check("M-if-branch-mismatch",
          'fn main() -> Int { return if true { 1 } else { "s" } }',
          "invalid", ("PEP_TYPE_MISMATCH",))
    check("M-empty-record",
          "type E { }\nfn main() -> Int { return 0 }", "valid")
    check("M-fn-type-samename",
          "type Point { x: Int }\nfn Point() -> Int { return 1 }\n"
          "fn main() -> Int { return Point() }", "valid")
    run("M-samename-run",
        "type Point { x: Int }\nfn Point() -> Int { return 1 }\n"
        "fn main() -> Int { return 0 }\nsay(int_text(Point()))",
        exp_out="1\n")
    # Records + unions
    hdr = "type Point { x: Int y: Int }\ntype Expr = Number(Int) | Add(Expr, Expr)\n"
    run("REC-access", hdr + 'say(int_text(Point { x: 1, y: 2 }.x))\n',
        exp_out="1\n")
    run("REC-match", hdr + 'say(int_text(match Number(5) { Number(v) => v '
                           'Add(l, r) => 0 }))\n', exp_out="5\n")
    check("REC-wrong-field",
          hdr + "fn f() -> Int { return Point { x: 1, z: 2 }.x }",
          "invalid", ("PEP_MISSING_FIELD",))
    check("REC-nonexhaust",
          hdr + "fn f() -> Int { return match Number(1) { Number(v) => v } }",
          "invalid", ("PEP_NON_EXHAUSTIVE_MATCH",))
    check("REC-dup", hdr + "fn f() -> Int { return match Number(1) { "
                          "Number(v) => v Number(w) => w } }",
          "invalid", ("PEP_DUPLICATE_MATCH_ARM",))
    check("REC-match-int",
          hdr + "fn f() -> Int { return match 1 { Number(v) => v } }",
          "invalid", ("PEP_MATCH_NON_UNION",))
    check("REC-field-bad",
          hdr + "fn f() -> Int { let p = Point { x: 1, y: 2 } return p.z }",
          "invalid", ("PEP_UNKNOWN_FIELD",))
    check("REC-arity", hdr + "fn f() -> Int { return Number(1, 2) }",
          "invalid", ("PEP_ARGUMENT_COUNT",))
    check("REC-fwdref", "type Box { p: Point }\nfn f() -> Int { return 0 }",
          "invalid", ("PEP_UNKNOWN_TYPE",))
    # Literals, escapes, conditions (set 6)
    run("L-esc-n", b'say("a\\nb")\n', exp_out="a\nb\n")
    run("L-esc-quote", b'say("a\\"b")\n', exp_out='a"b\n')
    run("L-esc-bad", b'say("a\\qb")\n', exp_rc=1,
        exp_err_contains=("PEP_INVALID_ESCAPE",))
    run("L-int-max", b"say(int_text(9223372036854775807))\n",
        exp_out="9223372036854775807\n")
    check("L-int-over",
          b"fn main() -> Int { return 9223372036854775808 }",
          "invalid", ("PEP_INT_LITERAL_RANGE",))
    run("L-add-overflow", b"say(int_text(9223372036854775807 + 1))\n",
        exp_rc=1, exp_err_contains=("PEP_RUNTIME_OVERFLOW",))
    run("L-to-min", b"say(int_text(0 - 9223372036854775807 - 1))\n",
        exp_out="-9223372036854775808\n")
    run("L-unary", b"say(int_text(-1))\n", exp_out="-1\n")
    check("L-while-int", b"fn main() -> Int { while 1 { } return 0 }",
          "invalid", ("PEP_TYPE_MISMATCH",))
    check("L-for-int", b"fn main() -> Int { for x in 5 { } return x }",
          "invalid", ("PEP_FOR_REQUIRES_LIST",))
    run("L-if-noelse", b'if true { say("s") }', exp_rc=1,
        exp_err_contains=("PEP_PARSE_ELSE",))
    run("L-if-empty-else", b'if true { say("s") } else { }',
        exp_out="s\n")
    # Calls and scope (set 7)
    check("C-unknown-fn",
          "fn main() -> Int { return nosuchfn() }",
          "invalid", ("PEP_UNKNOWN_FUNCTION",))
    check("C-arity-many",
          "fn one() -> Int { return 1 }\n"
          "fn main() -> Int { return one(1, 2) }",
          "invalid", ("PEP_ARGUMENT_COUNT",))
    check("C-arity-few",
          "fn two(a: Int, b: Int) -> Int { return a }\n"
          "fn main() -> Int { return two(1) }",
          "invalid", ("PEP_ARGUMENT_COUNT",))
    check("C-dup-fn",
          "fn f() -> Int { return 1 }\nfn f() -> Int { return 2 }\n"
          "fn main() -> Int { return 0 }",
          "invalid", ("PEP_DUPLICATE_FUNCTION",))
    check("C-dup-let", "let x = 1\nlet x = 2\nsay(int_text(x))",
          "invalid", ("PEP_DUPLICATE_BINDING",))
    check("C-top-return", "return 1", "invalid",
          ("PEP_RETURN_OUTSIDE_FUNCTION",))
    check("C-say-int", 'say(42)', "invalid", ("PEP_TYPE_MISMATCH",))
    check("C-arg-type",
          "fn id(x: Int) -> Int { return x }\n"
          "fn main() -> Int { return id(true) }",
          "invalid", ("PEP_TYPE_MISMATCH",))
    # Control flow (set 8)
    run("F-for-sum",
        "var total = 0\nfor v in [1, 2, 3] {\n total = total + v\n}\n"
        'say(int_text(total))\n', exp_out="6\n")
    run("F-for-empty",
        "let e: List[Int] = []\nvar total = 99\nfor v in e {\n total = v\n}\n"
        'say(int_text(total))\n', exp_out="99\n")
    run("F-for-nested",
        "var n = 0\nfor row in [[1], [2, 3]] {\n for v in row {\n"
        " n = n + v\n }\n}\nsay(int_text(n))\n", exp_out="6\n")
    run("F-break",
        "var i = 0\nwhile i != 3 {\n i = i + 1\n"
        " if i == 2 { break } else { }\n}\nsay(int_text(i))\n",
        exp_rc=1, exp_err_contains=("PEP_UNKNOWN_VARIABLE",))
    run("F-continue",
        "var i = 0\nvar s = 0\nwhile i != 4 {\n i = i + 1\n"
        " if i == 2 { continue } else { }\n s = s + i\n}\n"
        'say(int_text(s))\n',
        exp_rc=1, exp_err_contains=("PEP_UNKNOWN_VARIABLE",))
    run("F-not", 'say(int_text(if !true { 1 } else { 2 }))\n',
        exp_out="2\n")
    run("F-wildcard",
        "type E = A(Int) | B()\n"
        'say(int_text(match B() { A(v) => v _ => 7 }))\n',
        exp_out="7\n")
    run("F-wild-only",
        "type E = A(Int) | B()\n"
        "fn f(e: E) -> Int { return match e { _ => 0 } }\n"
        'say(int_text(f(A(5))))\n', exp_out="0\n")
    check("F-bare-B-decl", "type E = A(Int) | B\nsay(int_text(1))",
          "invalid", ("PEP_PARSE_EXPECTED",))
    # Hole lifecycle (set 9) — stateful session sequences
    hsrc = ("fn double(n: Int) -> Int { return ?calc }\n"
            "fn main() -> Int { return 0 }\n")
    def hsess(reqs):
        r = _pwsh(["./pep.ps1", "session", "--jsonl"],
                  inp="\n".join(json.dumps(x) for x in reqs) + "\n")
        return [json.loads(ln) for ln in (r.stdout or "").splitlines()
                if ln.strip()]
    ho = hsess([{"schemaVersion": 3, "op": "open", "name": "h",
                  "source": hsrc}])
    hdoc, hrev = ho[0]["document"], ho[0]["revision"]
    hq = hsess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": hsrc},
        {"schemaVersion": 3, "op": "query", "document": hdoc,
         "revision": hrev}])[1]
    hh = hq.get("holes", [])
    def _hname(h):
        ident = h.get("identity")
        if isinstance(ident, dict):
            return ident.get("name")
        return ident
    ok = (hq.get("status") == "incomplete" and len(hh) == 1
          and _hname(hh[0]) == "calc"
          and hh[0].get("expectedType") == "Int")
    results.append(("H-query", PASS if ok else FAIL,
                    "holes=%s" % [(x.get("identity"),
                                     x.get("expectedType")) for x in hh]))
    hp = hsess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": hsrc},
        {"schemaVersion": 3, "op": "fill_hole", "document": hdoc,
         "expected_revision": hrev, "scope": "double",
         "name": "calc", "replacement": "n + n",
         "mode": "preview"}])[1]
    ok = (hp.get("outcome") == "ok" and hp.get("status") == "valid"
          and hp.get("baseRevision") == hp.get("currentRevision")
          and (hp.get("sourceDiff") or {}).get("removed") == "?calc")
    results.append(("H1-preview", PASS if ok else FAIL,
                    "outcome=%s status=%s" % (hp.get("outcome"),
                                               hp.get("status"))))
    hm = hsess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": hsrc},
        {"schemaVersion": 3, "op": "fill_hole", "document": hdoc,
         "expected_revision": hrev, "scope": "double",
         "name": "calc", "replacement": "true",
         "mode": "preview"}])[1]
    ok = hm.get("outcome") == "rejected"
    results.append(("H2-mismatch", PASS if ok else FAIL,
                    "outcome=%s" % hm.get("outcome")))
    ha = hsess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": hsrc},
        {"schemaVersion": 3, "op": "fill_hole", "document": hdoc,
         "expected_revision": hrev, "scope": "double",
         "name": "calc", "replacement": "n + n", "mode": "apply"}])[1]
    ok = (ha.get("outcome") == "ok" and ha.get("status") == "valid"
          and ha.get("holes") == []
          and ha.get("currentRevision") != ha.get("baseRevision"))
    results.append(("H3-apply", PASS if ok else FAIL,
                    "outcome=%s holes=%s" % (ha.get("outcome"),
                                              ha.get("holes"))))
    hs = hsess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": hsrc},
        {"schemaVersion": 3, "op": "fill_hole", "document": hdoc,
         "expected_revision": "sha256:" + "0" * 64,
         "scope": "double", "name": "calc",
         "replacement": "n + n", "mode": "preview"}])[1]
    ok = ((hs.get("error") or {}).get("code") == "PEP_STALE_REVISION")
    results.append(("H4-stale", PASS if ok else FAIL,
                    "error=%s" % (hs.get("error") or {}).get("code")))
    hu = hsess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": hsrc},
        {"schemaVersion": 3, "op": "fill_hole", "document": hdoc,
         "expected_revision": hrev, "scope": "double",
         "name": "nope", "replacement": "1", "mode": "preview"}])[1]
    ok = ((hu.get("error") or {}).get("code") == "PEP_HOLE_NOT_FOUND")
    results.append(("H5-unknown", PASS if ok else FAIL,
                    "error=%s" % (hu.get("error") or {}).get("code")))
    # Tool registry trust boundary (set 10)
    tsrc = ("fn double(n: Int) -> Int { return n + n }\n"
            "fn main() -> Int { return 0 }\n")
    ssrc = ("fn loud(s: Str) -> Str { say(s) return s }\n"
            "fn main() -> Int { return 0 }\n")
    def tsess(reqs):
        r = _pwsh(["./pep.ps1", "session", "--jsonl"],
                  inp="\n".join(json.dumps(x) for x in reqs) + "\n")
        return [json.loads(ln) for ln in (r.stdout or "").splitlines()
                if ln.strip()]
    def IV(v):
        return {"type": "Int", "value": str(v)}
    to = tsess([{"schemaVersion": 3, "op": "open", "name": "t",
                  "source": tsrc}])
    tdoc, trev = to[0]["document"], to[0]["revision"]
    TB = {"schemaVersion": 3, "toolProtocolVersion": 1, "tool": "dbl",
          "document": tdoc, "revision": trev}
    tr = tsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": tsrc},
        dict(TB, op="tool_register", function="double",
             description="double it"),
        dict(TB, op="tool_validate",
             testVectors=[{"arguments": [IV(21)],
                           "expect": IV(42)}]),
        dict(TB, op="tool_activate"),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "dbl",
         "arguments": [IV(21)]},
    ])[1:]
    ok = (tr[0].get("status") == "Registered"
          and tr[0].get("callable") is False
          and tr[1].get("status") == "Validated"
          and tr[2].get("status") == "Active"
          and tr[2].get("callable") is True
          and tr[3].get("result") == IV(42))
    results.append(("T1-lifecycle", PASS if ok else FAIL,
                    "statuses=%s" % [x.get("status") for x in tr[:3]]))
    _tl = tsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": tsrc},
        dict(TB, op="tool_register", function="double"),
        dict(TB, op="tool_validate",
             testVectors=[{"arguments": [IV(21)],
                           "expect": IV(42)}]),
        dict(TB, op="tool_activate"),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_list"},
    ])
    _lt = _tl[4].get("tools", [])
    ok = any(t.get("tool") == "dbl" and t.get("status") == "Active"
             and t.get("callable") is True for t in _lt)
    results.append(("T1b-list", PASS if ok else FAIL,
                    "tools=%s" % [(t.get("tool"), t.get("status")) for t in _lt]))
    tf = tsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": tsrc},
        dict(TB, op="tool_register", function="double"),
        dict(TB, op="tool_validate",
             testVectors=[{"arguments": [IV(21)],
                           "expect": IV(43)}]),
    ])[2]
    ok = tf.get("outcome") == "rejected"
    results.append(("T2-badvector", PASS if ok else FAIL,
                    "outcome=%s" % tf.get("outcome")))
    tn = tsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": tsrc},
        dict(TB, op="tool_register", function="double"),
        dict(TB, op="tool_validate",
             testVectors=[{"arguments": [IV(21)],
                           "expect": IV(42)}]),
        dict(TB, op="tool_activate"),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "dbl",
         "arguments": [{"type": "Str", "value": "x"}]},
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "dbl",
         "arguments": [IV(1), IV(2)]},
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "nosuch",
         "arguments": [IV(1)]},
    ])[4:]
    want = ("PEP_TOOL_ARGUMENT_TYPE", "PEP_TOOL_ARGUMENT_COUNT",
            "PEP_TOOL_NOT_ACTIVE")
    ok = tuple((x.get("error") or {}).get("code") for x in tn) == want
    results.append(("T3-invoke-errs", PASS if ok else FAIL,
                    "codes=%s" % (want,) if ok else "codes=%s" % (tuple(
                        (x.get("error") or {}).get("code") for x in tn),)))
    ta = tsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": tsrc},
        dict(TB, op="tool_register", function="double"),
        dict(TB, op="tool_activate"),
    ])[2]
    ok = ((ta.get("error") or {}).get("code")
          == "PEP_TOOL_NOT_VALIDATED")
    results.append(("T4-no-validate", PASS if ok else FAIL,
                    "error=%s" % (ta.get("error") or {}).get("code")))
    so = tsess([{"schemaVersion": 3, "op": "open", "name": "s",
                  "source": ssrc}])
    sdoc, srev = so[0]["document"], so[0]["revision"]
    SB = {"schemaVersion": 3, "toolProtocolVersion": 1,
          "tool": "loud", "document": sdoc, "revision": srev}
    ts = tsess([
        {"schemaVersion": 3, "op": "open", "name": "s",
         "source": ssrc},
        dict(SB, op="tool_register", function="loud"),
        dict(SB, op="tool_validate",
             testVectors=[{"arguments": [{"type": "Str",
                                            "value": "hi"}],
                           "expect": {"type": "Str",
                                      "value": "hi"}}]),
    ])[1:]
    ok = (ts[0].get("status") == "Registered"
          and ts[1].get("status") == "Rejected")
    results.append(("T5-say-blocked", PASS if ok else FAIL,
                    "validate=%s" % ts[1].get("status")))
    def sess(reqs):
        r = _pwsh(["./pep.ps1", "session", "--jsonl"],
                  inp="\n".join(json.dumps(x) for x in reqs) + "\n")
        return [json.loads(ln) for ln in (r.stdout or "").splitlines()
                if ln.strip()]
    _LIB = "fn double(n: Int) -> Int { return n + 1 }\nfn main() -> Int { return 0 }\n"
    _BADLIB = "fn bad(n: Int) -> Int { return nosuch + n }\nfn main() -> Int { return 0 }\n"
    _to = sess([{"schemaVersion": 3, "op": "open", "name": "t",
                  "source": _LIB}])[0]
    _td2, _tr2 = _to["document"], _to["revision"]
    _B2 = lambda nm: {"schemaVersion": 3, "toolProtocolVersion": 1,
                       "tool": nm, "document": _td2, "revision": _tr2}
    _IV2 = lambda v: {"type": "Int", "value": str(v)}
    _tr = sess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": _LIB},
        dict(_B2("dt"), op="tool_register", function="double"),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "dt",
         "arguments": [_IV2(21)]},
    ])
    _e6 = _tr[2].get("error") or {}
    ok = (_tr[2].get("outcome") == "error"
          and (_e6.get("code") if isinstance(_e6, dict) else _e6) == "PEP_TOOL_NOT_ACTIVE")
    results.append(("T6-invoke-reg", PASS if ok else FAIL,
                    "invoke=%s" % _tr[2].get("outcome")))
    _bo = sess([{"schemaVersion": 3, "op": "open", "name": "b",
                  "source": _BADLIB}])[0]
    _bd, _br = _bo["document"], _bo["revision"]
    _BB = lambda nm: {"schemaVersion": 3, "toolProtocolVersion": 1,
                       "tool": nm, "document": _bd, "revision": _br}
    _br = sess([
        {"schemaVersion": 3, "op": "open", "name": "b",
         "source": _BADLIB},
        dict(_BB("bad"), op="tool_register", function="bad"),
        dict(_BB("bad"), op="tool_validate",
             testVectors=[{"arguments": [_IV2(21)],
                           "expect": _IV2(42)}]),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "bad",
         "arguments": [_IV2(21)]},
    ])
    _ok7 = (_br[1].get("outcome") == "rejected"
            and _br[2].get("outcome") == "rejected"
            and (_br[3].get("error") or {}).get("code") == "PEP_TOOL_NOT_ACTIVE"
            if isinstance(_br[3].get("error"), dict)
            else _br[3].get("outcome") == "error")
    results.append(("T7-invoke-rejected", PASS if _ok7 else FAIL,
                    "invoke=%s" % _br[3].get("outcome")))
    check("C-say-noarg", "say()\nfn main() -> Int { return 0 }",
          "invalid", ("PEP_ARGUMENT_COUNT",))
    _hs = sess([{"schemaVersion": 3, "op": "open", "name": "h",
                  "source": "fn f(n: Int) -> Int { return n + ?h }\nfn main() -> Int { return 0 }\n"}])[0]
    _hd2, _hr2 = _hs["document"], _hs["revision"]
    _HB2 = lambda nm: {"schemaVersion": 3, "toolProtocolVersion": 1,
                       "tool": nm, "document": _hd2, "revision": _hr2}
    _hr = sess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": "fn f(n: Int) -> Int { return n + ?h }\nfn main() -> Int { return 0 }\n"},
        dict(_HB2("hf"), op="tool_register", function="f"),
        dict(_HB2("hf"), op="tool_validate",
             testVectors=[{"arguments": [{"type": "Int", "value": "21"}],
                           "expect": {"type": "Int", "value": "22"}}]),
    ])
    _he = _hr[2]
    ok = _he.get("outcome") == "rejected"
    results.append(("T-hole-src", PASS if ok else FAIL,
                    "validate=%s" % _he.get("outcome")))
    check("X-assign-immutable", b"let x = 1\nx = 2\nsay(int_text(x))",
          "invalid", ("PEP_ASSIGN_IMMUTABLE",))
    check("X-bare-empty", b"for v in [] {\n say(int_text(v))\n}",
          "invalid", ("PEP_EMPTY_LIST_NEEDS_TYPE",))
    check("X-unterm-eof", b'say("abc',
          "invalid", ("PEP_UNTERMINATED_STRING",))
    _ht = sess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": "fn double(n: Int) -> Int { return n + n }\nfn main() -> Int { return 0 }\n"},
    ])
    _hd4, _hr4 = _ht[0]["document"], _ht[0]["revision"]
    _HB4 = lambda nm: {"schemaVersion": 3, "toolProtocolVersion": 1,
                       "tool": nm, "document": _hd4, "revision": _hr4}
    _hw = sess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": "fn double(n: Int) -> Int { return n + n }\nfn main() -> Int { return 0 }\n"},
        dict(_HB4("w"), op="tool_register", function="double"),
        dict(_HB4("w"), op="tool_validate",
             testVectors=[{"arguments": [{"type": "Int", "value": "21"}],
                           "expect": {"type": "Int", "value": "999"}}]),
    ])[2]
    _we = _hw.get("error") or {}
    ok = (_hw.get("outcome") == "rejected"
          and (isinstance(_we, dict) and _we.get("code") == "PEP_TOOL_TEST_FAILED" or "TEST_FAILED" in str(_we)))
    results.append(("T-wrong-expect", PASS if ok else FAIL,
                    "validate=%s" % _hw.get("outcome")))
    # Session edges (set 11)
    _om = sess([{"schemaVersion": 3, "op": "metrics"}])[0]
    ok = _om.get("outcome") == "ok" and "metrics" in _om
    results.append(("O3-metrics", PASS if ok else FAIL,
                    "outcome=%s" % _om.get("outcome")))
    # Lexical edges (set 15)
    run("X-esc-all", b'say("a\\tb\\\\c")\n',
        exp_out="a\tb\\c\n")
    for _ename, _eb in (("esc-bs", b'say("a\\bb")\n'),
                        ("esc-ff", b'say("a\\fb")\n'),
                        ("esc-sq", b'say("a\\\'b")\n'),
                        ("esc-u", b'say("caf\\u00e9")\n'),
                        ("esc-x", b'say("a\\xb")\n')):
        run("X-" + _ename, _eb, exp_rc=1,
            exp_err_contains=("PEP_INVALID_ESCAPE",))
    check("X-hex", b"fn main() -> Int { return 0x10 }",
          "invalid", ("PEP_UNREACHABLE",))
    check("X-hex-let", b"let v = 0x10\nsay(int_text(0))",
          "invalid", ("PEP_UNKNOWN_VARIABLE",))
    check("X-bin-let", b"let v = 0b101\nsay(int_text(0))",
          "invalid", ("PEP_UNKNOWN_VARIABLE",))
    check("X-uscore-let", b"let v = 1_000\nsay(int_text(0))",
          "invalid", ("PEP_UNKNOWN_VARIABLE",))
    for _nm, _src, _exp in (
            ("X-hash-str", b'say("a#b")\n', "a#b\n"),
            ("X-slash-cmt", b'// line comment\nsay("x")\n', "x\n"),
            ("X-hash-cmt", b'# hash comment\nsay("y")\n', "y\n"),
            ("X-trail-cmt", b'say("a"); // trailing\n', "a\n")):
        run(_nm, _src, exp_out=_exp)
    check("X-unterm-str", b'say("unterminated)\n',
          "invalid", ("PEP_NEWLINE_IN_STRING",))
    _mc = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": "fn main() -> Int { return 1 }\n"},
    ])[0]
    _md, _mr = _mc["document"], _mc["revision"]
    _mq = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": "fn main() -> Int { return 1 }\n"},
        {"schemaVersion": 3, "op": "query", "document": _md,
         "revision": _mr},
        {"schemaVersion": 3, "op": "query", "document": _md,
         "revision": _mr},
        {"schemaVersion": 3, "op": "metrics"},
    ])[-1]
    _mm = _mq.get("metrics", {})
    ok = (_mm.get("parse_count") == 1 and _mm.get("typecheck_count") == 1
          and _mm.get("cache_hits") == 2)
    results.append(("O4-cachereuse", PASS if ok else FAIL,
                    "metrics=%s" % _mm))
    _mx = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": "fn main() -> Int { return 1 }\n"},
        {"schemaVersion": 3, "op": "apply_edit", "document": _md,
         "expected_revision": _mr, "start_byte": 26, "end_byte": 27,
         "replacement": "2"},
    ])
    _mnew = _mx[1]["revision"]
    _my = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": "fn main() -> Int { return 1 }\n"},
        {"schemaVersion": 3, "op": "apply_edit", "document": _md,
         "expected_revision": _mr, "start_byte": 26, "end_byte": 27,
         "replacement": "2"},
        {"schemaVersion": 3, "op": "query", "document": _md,
         "revision": _mnew},
        {"schemaVersion": 3, "op": "query", "document": _md,
         "revision": _mr},
        {"schemaVersion": 3, "op": "query", "document": _md,
         "revision": _mnew},
        {"schemaVersion": 3, "op": "metrics"},
    ])
    _mz = _my[-1].get("metrics", {})
    ok = (_mz.get("parse_count") == 2 and _mz.get("typecheck_count") == 2
          and _mz.get("cache_hits") == 3)
    results.append(("O5-xrev", PASS if ok else FAIL,
                    "metrics=%s" % _mz))
    _ho = sess([{"schemaVersion": 3, "op": "open", "name": "m",
                    "source": "fn main() -> Int { return 1 }\n"}])[0]
    _hd2, _hr2 = _ho["document"], _ho["revision"]
    _he = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": "fn main() -> Int { return 1 }\n"},
        {"schemaVersion": 3, "op": "apply_edit", "document": _hd2,
         "expected_revision": _hr2, "start_byte": 26, "end_byte": 27,
         "replacement": "2"},
        {"schemaVersion": 3, "op": "query", "document": _hd2,
         "revision": _hr2},
    ])
    _hnew = _he[1]["revision"]
    _hq = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": "fn main() -> Int { return 1 }\n"},
        {"schemaVersion": 3, "op": "apply_edit", "document": _hd2,
         "expected_revision": _hr2, "start_byte": 26, "end_byte": 27,
         "replacement": "2"},
        {"schemaVersion": 3, "op": "query", "document": _hd2,
         "revision": _hr2},
        {"schemaVersion": 3, "op": "query", "document": _hd2,
         "revision": _hnew},
    ])
    ok = (_hq[2].get("outcome") == "ok"
          and _hq[2].get("status") == "valid"
          and _hq[3].get("outcome") == "ok"
          and _hq[3].get("status") == "valid")
    results.append(("O6-retained", PASS if ok else FAIL,
                    "old=%s new=%s" % (_hq[2].get("status"),
                                       _hq[3].get("status"))))
    _ip = TMP / "a3_inspect.pep"
    _ip.write_bytes(b"fn main() -> Int { return 1 }\n")
    try:
        _ir = _pwsh(["./pep.ps1", "inspect", str(_ip), "--json"])
        _id = json.loads((_ir.stdout or "{}"))
        ok = (_id.get("status") == "parsed"
              and len(_id.get("ast", [])) == 1
              and "typedTree" not in _id)
        results.append(("O5-inspect", PASS if ok else FAIL,
                        "status=%s" % _id.get("status")))
    finally:
        _ip.unlink(missing_ok=True)
    # SourceBytes + byte builtins via host grant (set 13)
    o = sess([{"schemaVersion": 3, "op": "open_bytes", "name": "bad",
                "bytes": [102, 110, 32, 255, 254]}])[0]
    ok = (o.get("status") == "invalid" and "PEP_INVALID_UTF8" in [
        x.get("code") for x in o.get("diagnostics", [])])
    results.append(("O1-badbytes", PASS if ok else FAIL,
                    "status=%s" % o.get("status")))
    e0 = sess([{"schemaVersion": 3, "op": "open", "name": "e",
                 "source": "fn main() -> Int { return 1 }\n"}])[0]
    edoc, erev = e0["document"], e0["revision"]
    eb = sess([
        {"schemaVersion": 3, "op": "open", "name": "e",
         "source": "fn main() -> Int { return 1 }\n"},
        {"schemaVersion": 3, "op": "apply_edit", "document": edoc,
         "expected_revision": erev, "start_byte": 26, "end_byte": 27,
         "replacement": "@@@"},
    ])[1]
    enew = eb.get("revision")
    oq = sess([
        {"schemaVersion": 3, "op": "open", "name": "e",
         "source": "fn main() -> Int { return 1 }\n"},
        {"schemaVersion": 3, "op": "apply_edit", "document": edoc,
         "expected_revision": erev, "start_byte": 26, "end_byte": 27,
         "replacement": "@@@"},
        {"schemaVersion": 3, "op": "query", "document": edoc,
         "revision": enew},
    ])[2]
    ok = (eb.get("outcome") == "ok" and eb.get("status") == "invalid"
          and enew != erev and oq.get("outcome") == "ok"
          and "PEP_UNEXPECTED_CHARACTER" in [
              x.get("code") for x in oq.get("diagnostics", [])])
    results.append(("O2-repairable", PASS if ok else FAIL,
                    "edit=%s query=%s" % (eb.get("status"),
                                           oq.get("status"))))
    # SourceBytes + byte builtins via host grant (set 13)
    _tlib = ("fn blen() -> Int { return byte_length(source_bytes()) }\n"
             "fn bat(i: Int) -> Int { return byte_at(source_bytes(), i) }\n"
             "fn us(a: Int, b: Int) -> Str { return utf8_slice(source_bytes(), a, b) }\n"
             "fn bsl(a: Int, b: Int) -> Int { return byte_length(byte_slice(source_bytes(), a, b)) }\n"
             "fn main() -> Int { return 0 }\n")
    _tgt = 'fn main() -> Int { say("h\u00e9llo") return 0 }\n'
    def _sess(reqs):
        r = _pwsh(["./pep.ps1", "session", "--jsonl"],
                  inp="\n".join(json.dumps(x) for x in reqs) + "\n")
        return [json.loads(ln) for ln in (r.stdout or "").splitlines()
                if ln.strip()]
    _o = _sess([{"schemaVersion": 3, "op": "open", "name": "t",
                  "source": _tlib},
                 {"schemaVersion": 3, "op": "open", "name": "g",
                  "source": _tgt}])
    _td, _tr = _o[0]["document"], _o[0]["revision"]
    _gd, _gr = _o[1]["document"], _o[1]["revision"]
    _st = {"document": _gd, "revision": _gr,
           "entryFunctions": ["main"]}
    def _IV(v):
        return {"type": "Int", "value": str(v)}
    def _SV(v):
        return {"type": "Str", "value": v}
    def _trial(tool, fn, args, expect):
        _B = {"schemaVersion": 3, "toolProtocolVersion": 2,
              "tool": tool, "document": _td, "revision": _tr}
        _r = _sess([
            {"schemaVersion": 3, "op": "open", "name": "t",
             "source": _tlib},
            {"schemaVersion": 3, "op": "open", "name": "g",
             "source": _tgt},
            dict(_B, op="tool_register", function=fn),
            dict(_B, op="tool_validate",
                 testVectors=[{"arguments": args, "expect": expect,
                               "semanticTarget": _st}]),
            dict(_B, op="tool_activate"),
            {"schemaVersion": 3, "toolProtocolVersion": 2,
             "op": "tool_invoke", "tool": tool, "arguments": args,
             "semanticTarget": _st},
        ])
        return _r[2], _r[3], _r[4], _r[5]
    _tgt_len = str(len(_tgt.encode("utf-8")))
    _rb = _trial("blen", "blen", [], {"type": "Int", "value": _tgt_len})
    ok = (_rb[3].get("result") == {"type": "Int", "value": _tgt_len})
    results.append(("G1-bytelen", PASS if ok else FAIL,
                    "invoke=%s" % _rb[3].get("result")))
    _ok = True
    for _args, _exp in [([_IV(25)], _IV(195)), ([_IV(26)], _IV(169))]:
        _rr = _trial("bat", "bat", _args, _exp)
        _ok = _ok and _rr[3].get("result") == _exp
    _ro = _trial("bat", "bat", [_IV(9999)], _IV(0))
    _e = _ro[1].get("error")
    _ok = (_ok and _ro[1].get("outcome") == "rejected"
           and (isinstance(_e, str) and "BYTE_RANGE" in _e
                or (isinstance(_e, dict)
                    and _e.get("code") == "PEP_RUNTIME_BYTE_RANGE")))
    results.append(("G2-byteat", PASS if _ok else FAIL, "byte-at"))
    _ru = _trial("us", "us", [_IV(25), _IV(27)], _SV("\u00e9"))
    _rs = _trial("us", "us", [_IV(25), _IV(26)], _SV("\u00e9"))
    _es = _rs[1].get("error")
    ok = (_ru[3].get("result") == _SV("\u00e9")
          and _rs[1].get("outcome") == "rejected"
          and ((isinstance(_es, str) and "BYTE_BOUNDARY" in _es)
               or (isinstance(_es, dict)
                   and _es.get("code") == "PEP_RUNTIME_BYTE_BOUNDARY")))
    results.append(("G3-utf8", PASS if ok else FAIL,
                    "slice+split"))
    _rl = _trial("bsl", "bsl", [_IV(25), _IV(26)], _IV(1))
    ok = _rl[3].get("result") == _IV(1)
    results.append(("G4-byteslice", PASS if ok else FAIL,
                    "invoke=%s" % _rl[3].get("result")))
    _pv = TMP / "a3_grant.pep"
    _pv.write_bytes(b"fn probe() -> Int {\n semantic_snapshot()\n return 0\n}\n"
                    b'say(int_text(probe()))\n')
    try:
        _rr = _pwsh(["./pep.ps1", "run", str(_pv)])
        ok = (_rr.returncode == 1
              and "PEP_RUNTIME_SEMANTIC_CONTEXT" in (_rr.stderr or ""))
        results.append(("G5-nogrant", PASS if ok else FAIL,
                        "rc=%d" % _rr.returncode))
    finally:
        _pv.unlink(missing_ok=True)
    # v2 typed transport + host grants (set 12)
    vlib = ("type Point { x: Int y: Int }\n"
            "fn total(xs: List[Int]) -> Int {\n var s = 0\n"
            " for x in xs {\n s = s + x\n }\n return s\n}\n"
            "fn getx(p: Point) -> Int { return p.x }\n"
            "fn main() -> Int { return 0 }\n")
    def vsess(reqs):
        r = _pwsh(["./pep.ps1", "session", "--jsonl"],
                  inp="\n".join(json.dumps(x) for x in reqs) + "\n")
        return [json.loads(ln) for ln in (r.stdout or "").splitlines()
                if ln.strip()]
    vo = vsess([{"schemaVersion": 3, "op": "open", "name": "lib",
                  "source": vlib}])
    vdoc, vrev = vo[0]["document"], vo[0]["revision"]
    VB = lambda tool: {"schemaVersion": 3, "toolProtocolVersion": 2,
                       "tool": tool, "document": vdoc,
                       "revision": vrev}
    def VLV(vals):
        return {"type": "List[Int]",
                "value": [{"type": "Int", "value": str(v)}
                            for v in vals]}
    def VPV(x, y):
        return {"type": "Point", "fields": [
            {"name": "x", "value": {"type": "Int", "value": str(x)}},
            {"name": "y", "value": {"type": "Int",
                                        "value": str(y)}}]}
    vr = vsess([
        {"schemaVersion": 3, "op": "open", "name": "lib",
         "source": vlib},
        dict(VB("total"), op="tool_register", function="total"),
        dict(VB("total"), op="tool_validate",
             testVectors=[{"arguments": [VLV([1, 2, 3])],
                           "expect": {"type": "Int", "value": "6"}}]),
        dict(VB("total"), op="tool_activate"),
        {"schemaVersion": 3, "toolProtocolVersion": 2,
         "op": "tool_invoke", "tool": "total",
         "arguments": [VLV([4, 5])]},
    ])[1:]
    ok = (vr[0].get("status") == "Registered"
          and vr[1].get("status") == "Validated"
          and vr[2].get("status") == "Active"
          and vr[3].get("result") == {"type": "Int", "value": "9"})
    results.append(("V1-list", PASS if ok else FAIL,
                    "invoke=%s" % vr[3].get("result")))
    vg = vsess([
        {"schemaVersion": 3, "op": "open", "name": "lib",
         "source": vlib},
        dict(VB("getx"), op="tool_register", function="getx"),
        dict(VB("getx"), op="tool_validate",
             testVectors=[{"arguments": [VPV(3, 4)],
                           "expect": {"type": "Int", "value": "3"}}]),
        dict(VB("getx"), op="tool_activate"),
        {"schemaVersion": 3, "toolProtocolVersion": 2,
         "op": "tool_invoke", "tool": "getx",
         "arguments": [VPV(7, 8)]},
    ])[1:]
    ok = (vg[3].get("result") == {"type": "Int", "value": "7"})
    results.append(("V2-record", PASS if ok else FAIL,
                    "invoke=%s" % vg[3].get("result")))
    vbad = {"type": "Point", "fields": [
        {"name": "y", "value": {"type": "Int", "value": "4"}},
        {"name": "x", "value": {"type": "Int", "value": "3"}}]}
    vw = vsess([
        {"schemaVersion": 3, "op": "open", "name": "lib",
         "source": vlib},
        dict(VB("getx"), op="tool_register", function="getx"),
        dict(VB("getx"), op="tool_validate",
             testVectors=[{"arguments": [vbad],
                           "expect": {"type": "Int", "value": "3"}}]),
    ])[2]
    _ve3 = vw.get("error")
    _vc3 = _ve3.get("code") if isinstance(_ve3, dict) else _ve3
    ok = _vc3 == "PEP_TOOL_ARGUMENT_FIELDS" or (vw.get("outcome") == "rejected" and "FIELD" in str(_ve3))
    results.append(("V3-order", PASS if ok else FAIL,
                    "outcome=%s" % vw.get("outcome")))
    pv = TMP / "a3_v4.pep"
    pv.write_bytes(b"fn probe() -> Int {\n semantic_snapshot()\n return 0\n}\n"
                   b'say(int_text(probe()))\n')
    try:
        rr = _pwsh(["./pep.ps1", "run", str(pv)])
        ok = (rr.returncode == 1
              and "PEP_RUNTIME_SEMANTIC_CONTEXT" in (rr.stderr or ""))
        results.append(("V4-nogrant", PASS if ok else FAIL,
                        "rc=%d" % rr.returncode))
    finally:
        pv.unlink(missing_ok=True)
    def _deep_type(n):
        t = "Int"
        for _ in range(n):
            t = "List[%s]" % t
        return t
    def _deep_val(n):
        v = {"type": "Int", "value": "1"}
        inner = "Int"
        for _ in range(n):
            inner = "List[%s]" % inner
            v = {"type": inner, "value": [v]}
        return v
    v6ok = True
    for _n, _want in ((16, "ok"), (17, "rejected")):
        _fn = ("fn deep(x: %s) -> Int { return 0 }\n"
               "fn main() -> Int { return 0 }\n" % _deep_type(_n))
        _o = vsess([{"schemaVersion": 3, "op": "open", "name": "d",
                      "source": _fn}])
        if _o[0].get("status") != "valid":
            v6ok = False
            break
        _dd, _dr = _o[0]["document"], _o[0]["revision"]
        _B = {"schemaVersion": 3, "toolProtocolVersion": 2,
              "tool": "deep", "document": _dd, "revision": _dr}
        _r = vsess([
            {"schemaVersion": 3, "op": "open", "name": "d",
             "source": _fn},
            dict(_B, op="tool_register", function="deep"),
            dict(_B, op="tool_validate",
                 testVectors=[{"arguments": [_deep_val(_n)],
                               "expect": {"type": "Int",
                                          "value": "0"}}]),
        ])[2]
        if _want == "ok":
            v6ok = v6ok and _r.get("outcome") == "ok"
        else:
            _e = _r.get("error")
            _code = _e.get("code") if isinstance(_e, dict) else _e
            v6ok = v6ok and (_code == "PEP_TOOL_VALUE_DEPTH"
                             or "PEP_TOOL_VALUE_DEPTH" in str(_e))
    results.append(("V6-depth16-17", PASS if v6ok else FAIL,
                    "boundary-16/17"))
    _snt7 = ("fn nfuncs() -> Int { let p = semantic_snapshot() return length(p.functions) }\n"
             "fn main() -> Int { return 0 }\n")
    _gt = sess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": _snt7},
        {"schemaVersion": 3, "op": "open", "name": "g",
         "source": "fn main() -> Int { return 0 }\n"},
    ])
    _gtd, _gtr = _gt[0]["document"], _gt[0]["revision"]
    _ggd, _ggr = _gt[1]["document"], _gt[1]["revision"]
    _tok = lambda nm: {"schemaVersion": 3, "toolProtocolVersion": 2,
                       "tool": nm, "document": _gtd, "revision": _gtr}
    _IV0 = {"type": "Int", "value": "0"}
    _gid_ok = True
    for _tn, _st in (("forged-rev",
                       {"document": _ggd,
                        "revision": "sha256:" + "f" * 64,
                        "entryFunctions": ["main"]}),
                      ("wrong-doc",
                       {"document": "doc-NOPE", "revision": _ggr,
                        "entryFunctions": ["main"]})):
        _gr = sess([
            {"schemaVersion": 3, "op": "open", "name": "t",
             "source": _snt7},
            {"schemaVersion": 3, "op": "open", "name": "g",
             "source": "fn main() -> Int { return 0 }\n"},
            dict(_tok("nf"), op="tool_register", function="nfuncs"),
            dict(_tok("nf"), op="tool_validate",
                 testVectors=[{"arguments": [], "expect": _IV0,
                               "semanticTarget": _st}]),
        ])
        _ge = _gr[3].get("error")
        _gc = _ge.get("code") if isinstance(_ge, dict) else str(_ge)
        _gid_ok = (_gid_ok and _gr[3].get("outcome") == "rejected"
                   and ("NOT_FOUND" in str(_gc)))
    results.append(("V7-grant-identity", PASS if _gid_ok else FAIL,
                    "both-rejected"))
    # Tool hot-replacement (set 14)
    _hv1 = ("fn f(n: Int) -> Int { return n + 1 }\n"
            "fn main() -> Int { return 0 }\n")
    def _hsess(reqs):
        _r = _pwsh(["./pep.ps1", "session", "--jsonl"],
                   inp="\n".join(json.dumps(x) for x in reqs) + "\n")
        return [json.loads(_ln) for _ln in (_r.stdout or "").splitlines()
                if _ln.strip()]

    def _HIV(v):
        return {"type": "Int", "value": str(v)}
    _ho = _hsess([{"schemaVersion": 3, "op": "open", "name": "t",
                    "source": _hv1}])
    _hd, _hr = _ho[0]["document"], _ho[0]["revision"]
    def _HB(rv):
        return {"schemaVersion": 3, "toolProtocolVersion": 1,
                "tool": "dt", "document": _hd, "revision": rv}
    _hr1 = _hsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": _hv1},
        dict(_HB(_hr), op="tool_register", function="f"),
        dict(_HB(_hr), op="tool_validate",
             testVectors=[{"arguments": [_HIV(21)],
                           "expect": _HIV(22)}]),
        dict(_HB(_hr), op="tool_activate"),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "dt",
         "arguments": [_HIV(21)]},
        {"schemaVersion": 3, "op": "apply_edit", "document": _hd,
         "expected_revision": _hr, "start_byte": 29, "end_byte": 34,
         "replacement": "n + 100"},
    ])
    _newrev = _hr1[5]["revision"]
    _hr2 = _hsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": _hv1},
        dict(_HB(_hr), op="tool_register", function="f"),
        dict(_HB(_hr), op="tool_validate",
             testVectors=[{"arguments": [_HIV(21)],
                           "expect": _HIV(22)}]),
        dict(_HB(_hr), op="tool_activate"),
        {"schemaVersion": 3, "op": "apply_edit", "document": _hd,
         "expected_revision": _hr, "start_byte": 29, "end_byte": 34,
         "replacement": "n + 100"},
        dict(_HB(_newrev), op="tool_register", function="f"),
        dict(_HB(_newrev), op="tool_validate",
             testVectors=[{"arguments": [_HIV(21)],
                           "expect": _HIV(121)}]),
        dict(_HB(_newrev), op="tool_activate"),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "dt",
         "arguments": [_HIV(21)]},
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_list"},
    ])
    _inv = _hr2[8]
    _lst = _hr2[9]
    _states = sorted((t.get("status") or "") for t in _lst.get("tools", []))
    _ok = (_inv.get("result") == _HIV(121)
           and "Active" in _states and "Superseded" in _states)
    results.append(("H1-hotswap", PASS if _ok else FAIL,
                    "invoke=%s states=%s" % (_inv.get("result"),
                                            _states)))
    _hb = _hsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": _hv1},
        dict(_HB(_hr), op="tool_register", function="f"),
        dict(_HB(_hr), op="tool_validate",
             testVectors=[{"arguments": [_HIV(21)],
                           "expect": _HIV(22)}]),
        dict(_HB(_hr), op="tool_activate"),
        {"schemaVersion": 3, "op": "apply_edit", "document": _hd,
         "expected_revision": _hr, "start_byte": 26, "end_byte": 27,
         "replacement": "@@@"},
    ])
    _bad = _hb[4]["revision"]
    _hf = _hsess([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": _hv1},
        dict(_HB(_hr), op="tool_register", function="f"),
        dict(_HB(_hr), op="tool_validate",
             testVectors=[{"arguments": [_HIV(21)],
                           "expect": _HIV(22)}]),
        dict(_HB(_hr), op="tool_activate"),
        {"schemaVersion": 3, "op": "apply_edit", "document": _hd,
         "expected_revision": _hr, "start_byte": 26, "end_byte": 27,
         "replacement": "@@@"},
        dict(_HB(_bad), op="tool_register", function="f"),
        dict(_HB(_bad), op="tool_validate",
             testVectors=[{"arguments": [_HIV(21)],
                           "expect": _HIV(22)}]),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "dt",
         "arguments": [_HIV(21)]},
    ])
    _fi, _fv, _fi2 = _hf[5], _hf[6], _hf[7]
    _ok2 = (_fi.get("outcome") == "rejected"
            and _fv.get("outcome") == "rejected"
            and _fi2.get("result") == _HIV(22))
    results.append(("H2-failedswap", PASS if _ok2 else FAIL,
                    "invoke=%s" % _fi2.get("result")))
    # Platform inventory pin (set 20)
    _pd = _pwsh(["./pep.ps1", "describe", "--json"])
    try:
        _pj = json.loads((_pd.stdout or "{}"))
        _pbn = sorted(b.get("name") for b in _pj.get("builtins", []))
        ok = (_pj.get("language") == "Pep"
              and _pj.get("types") == ["Int", "Bool", "Str",
                                          "SourceBytes", "Unit"]
              and _pbn == ["append", "byte_at", "byte_length",
                           "byte_slice", "contains", "int_text",
                           "length", "prepend", "reverse", "say",
                           "source_bytes", "utf8_slice"]
              and "str_contains" not in _pbn
              and _pj.get("runtime") == {"maxSteps": 1000000,
                                           "maxCallDepth": 512}
              and _pj.get("session", {}).get("toolProtocolVersions") == [1, 2])
        results.append(("PL-platform", PASS if ok else FAIL,
                        "builtins=%d" % len(_pbn)))
    except Exception as e:
        results.append(("PL-platform", FAIL, "error: %r" % e))
    # Declaration edges (set 19)
    check("D-nested-fn",
          "fn outer() -> Int {\n fn inner() -> Int { return 1 }\n return inner()\n}\nfn main() -> Int { return 0 }",
          "invalid", ("PEP_PARSE_EXPRESSION",))
    check("D-if-int",
          "fn main() -> Int { return if 1 { 1 } else { 0 } }",
          "invalid", ("PEP_TYPE_MISMATCH",))
    check("D-dup-field",
          "type P { x: Int }\nfn main() -> Int { let v = P { x: 1, x: 2 } return v.x }",
          "invalid", ("PEP_DUPLICATE_FIELD",))
    check("D-param-builtin",
          "fn f(say: Int) -> Int { return say }\nfn main() -> Int { return 0 }",
          "valid")
    check("D-ctor-arg",
          'type E = Number(Int) | B()\nfn main() -> Int { return match Number("x") { Number(v) => v B() => 0 } }',
          "invalid", ("PEP_TYPE_MISMATCH",))
    check("D-dup-main",
          "fn main() -> Int { return 1 }\nfn main() -> Int { return 2 }",
          "invalid", ("PEP_DUPLICATE_FUNCTION",))
    run("D-shadow-value",
        "fn f(say: Int) -> Int { return say }\nsay(int_text(f(41)))",
        exp_out="41\n")
    run("D-shadow-call",
        'fn f(say: Int) -> Unit { say("x") }\nf(1)',
        exp_out="x\n")
    # Semantic snapshot content (set 17)
    _snt = ("fn nfuncs() -> Int { let p = semantic_snapshot() return length(p.functions) }\n"
            "fn nroots() -> Int { let p = semantic_snapshot() return length(p.roots) }\n"
            "fn nedges() -> Int { let p = semantic_snapshot() return length(p.calls) }\n"
            "fn main() -> Int { return 0 }\n")
    _sng = ("fn a() -> Int { return 1 }\n"
            "fn main() -> Int { return a() }\n")
    def _sness(reqs):
        _rr = _pwsh(["./pep.ps1", "session", "--jsonl"],
                    inp="\n".join(json.dumps(_x) for _x in reqs) + "\n")
        return [json.loads(_ln) for _ln in (_rr.stdout or "").splitlines()
                if _ln.strip()]
    _so = _sness([{"schemaVersion": 3, "op": "open", "name": "t",
                    "source": _snt},
                   {"schemaVersion": 3, "op": "open", "name": "g",
                    "source": _sng}])
    _std, _str = _so[0]["document"], _so[0]["revision"]
    _sgd, _sgr = _so[1]["document"], _so[1]["revision"]
    _sst = {"document": _sgd, "revision": _sgr,
            "entryFunctions": ["main"]}
    def _snv(tool, fn, exp):
        _B = {"schemaVersion": 3, "toolProtocolVersion": 2,
              "tool": tool, "document": _std, "revision": _str}
        return _sness([
            {"schemaVersion": 3, "op": "open", "name": "t",
             "source": _snt},
            {"schemaVersion": 3, "op": "open", "name": "g",
             "source": _sng},
            dict(_B, op="tool_register", function=fn),
            dict(_B, op="tool_validate",
                 testVectors=[{"arguments": [], "expect": exp,
                               "semanticTarget": _sst}]),
        ])[3]
    _IV0 = lambda v: {"type": "Int", "value": str(v)}
    _r1 = _snv("nf", "nfuncs", _IV0(2))
    _r2 = _snv("nr", "nroots", _IV0(1))
    _r3 = _snv("ne", "nedges", _IV0(1))
    ok = (_r1.get("status") == "Validated" and _r2.get("status") == "Validated" and _r3.get("status") == "Validated")
    results.append(("SN-contents", PASS if ok else FAIL,
                    "validated=%s" % [ _r1.get("status"), _r2.get("status"), _r3.get("status") ]))
    _sB = {"schemaVersion": 3, "toolProtocolVersion": 2,
           "tool": "nr", "document": _std, "revision": _str}
    _sBbad = {"document": _sgd, "revision": _sgr,
              "entryFunctions": ["nope"]}
    _rb = _sness([
        {"schemaVersion": 3, "op": "open", "name": "t",
         "source": _snt},
        {"schemaVersion": 3, "op": "open", "name": "g",
         "source": _sng},
        dict(_sB, op="tool_register", function="nroots"),
        dict(_sB, op="tool_validate",
             testVectors=[{"arguments": [], "expect": _IV0(1),
                           "semanticTarget": _sBbad}]),
    ])[3]
    _eb = _rb.get("error")
    ok = (_rb.get("outcome") == "rejected" and
          ((isinstance(_eb, dict) and _eb.get("code") == "PEP_SEMANTIC_ROOT_NOT_FOUND") or "SEMANTIC_ROOT" in str(_eb)))
    results.append(("SN-badentry", PASS if ok else FAIL,
                    "outcome=%s" % _rb.get("outcome")))
    # Hole E2E + offset selection + session inspect
    _hs = "fn double(n: Int) -> Int { return ?calc }\nfn main() -> Int { return 0 }\n"
    _hdone = _hs[:34] + "n + n" + _hs[39:]
    _pe = TMP / "a3_he2e.pep"
    _pe.write_bytes(_hdone.encode("utf-8"))
    try:
        _re = _pwsh(["./pep.ps1", "run", str(_pe)])
        ok = _re.returncode == 0 and "incomplete" not in (_re.stderr or "")
        results.append(("H-e2e", PASS if ok else FAIL,
                        "rc=%d" % _re.returncode))
    finally:
        _pe.unlink(missing_ok=True)
    _po = TMP / "a3_off.pep"
    _po.write_bytes(("fn f(a: Int) -> Int { return ?one }\n"
                      "fn g(b: Int) -> Int { return ?two }\n"
                      "fn main() -> Int { return 0 }\n").encode("utf-8"))
    try:
        for _off, _nm in ((29, "one"), (65, "two")):
            _rq = _pwsh(["./pep.ps1", "query", str(_po), "--holes",
                         "--json", "--offset", str(_off)])
            try:
                _dq = json.loads((_rq.stdout or "{}"))
                _hh = _dq.get("holes", [])
                _okq = (len(_hh) == 1 and _hh[0].get("identity") == _nm)
            except Exception:
                _okq = False
            results.append(("H-off-%s" % _nm, PASS if _okq else FAIL,
                            "offset=%d" % _off))
    finally:
        _po.unlink(missing_ok=True)
    _so = sess([{"schemaVersion": 3, "op": "open", "name": "s",
                    "source": _hs}])
    _sd, _sr = _so[0]["document"], _so[0]["revision"]
    _si = sess([{"schemaVersion": 3, "op": "open", "name": "s",
                  "source": _hs},
                 {"schemaVersion": 3, "op": "inspect",
                  "document": _sd, "revision": _sr}])[1]
    ok = (_si.get("outcome") == "ok"
          and isinstance(_si.get("ast"), list)
          and "typedTree" in _si)
    results.append(("O-inspect", PASS if ok else FAIL,
                    "outcome=%s" % _si.get("outcome")))
    _mlib = ("fn dbl(n: Int) -> Int { return n + n }\n"
             "fn neg(n: Int) -> Int { return 0 - n }\n"
             "fn main() -> Int { return 0 }\n")
    _mo = sess([{"schemaVersion": 3, "op": "open", "name": "m",
                  "source": _mlib}])
    _md2, _mr2 = _mo[0]["document"], _mo[0]["revision"]
    def _MB(nm):
        return {"schemaVersion": 3, "toolProtocolVersion": 1,
                "tool": nm, "document": _md2, "revision": _mr2}
    def _MIV(v):
        return {"type": "Int", "value": str(v)}
    _mm = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": _mlib},
        dict(_MB("a"), op="tool_register", function="dbl"),
        dict(_MB("a"), op="tool_validate",
             testVectors=[{"arguments": [_MIV(21)],
                           "expect": _MIV(42)}]),
        dict(_MB("a"), op="tool_activate"),
        dict(_MB("b"), op="tool_register", function="neg"),
        dict(_MB("b"), op="tool_validate",
             testVectors=[{"arguments": [_MIV(21)],
                           "expect": _MIV(-21)}]),
        dict(_MB("b"), op="tool_activate"),
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "a",
         "arguments": [_MIV(1)]},
        {"schemaVersion": 3, "toolProtocolVersion": 1,
         "op": "tool_invoke", "tool": "b",
         "arguments": [_MIV(1)]},
    ])
    _ia = _mm[7].get("result") == _MIV(2)
    _ib = _mm[8].get("result") == _MIV(-1)
    results.append(("O-multiactive", PASS if (_ia and _ib) else FAIL,
                    "a=%s b=%s" % (_mm[7].get("result"),
                                   _mm[8].get("result"))))
    _rr = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": "fn main() -> Int { return 1 }\n"},
    ])
    _rdoc = _rr[0]["document"]
    _r2 = sess([
        {"schemaVersion": 3, "op": "open", "name": "m",
         "source": "fn main() -> Int { return 1 }\n"},
        {"schemaVersion": 3, "op": "apply_edit", "document": _rdoc,
         "expected_revision": _rr[0]["revision"], "start_byte": 27,
         "end_byte": 26, "replacement": "X"},
    ])[1]
    _re = _r2.get("error") or {}
    ok = (_r2.get("outcome") == "error"
          and (isinstance(_re, dict) and _re.get("code") == "PEP_INVALID_EDIT_RANGE" or "INVALID_EDIT_RANGE" in str(_re)))
    results.append(("O-reversed-range", PASS if ok else FAIL,
                    "outcome=%s" % _r2.get("outcome")))
    _mo2 = sess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": "fn f(n: Int) -> Int { return n + ?h }\nfn main() -> Int { return 0 }\n"},
    ])
    _hd3, _hr3 = _mo2[0]["document"], _mo2[0]["revision"]
    _mf = sess([
        {"schemaVersion": 3, "op": "open", "name": "h",
         "source": "fn f(n: Int) -> Int { return n + ?h }\nfn main() -> Int { return 0 }\n"},
        {"schemaVersion": 3, "op": "fill_hole", "document": _hd3,
         "expected_revision": _hr3, "scope": "f", "name": "h",
         "replacement": "1", "mode": "bogus"},
    ])[1]
    _fe = _mf.get("error") or {}
    ok = (_mf.get("outcome") == "error"
          and (isinstance(_fe, dict) and _fe.get("code") == "PEP_FILL_HOLE_MODE" or "FILL_HOLE_MODE" in str(_fe)))
    results.append(("O-badmode", PASS if ok else FAIL,
                    "outcome=%s" % _mf.get("outcome")))
    # v2 transport exclusions: unions + SourceBytes (set 18)
    _xlib = ("type E = A(Int) | B()\n"
             "fn first(x: E) -> Int { return match x { A(v) => v B() => 1 } }\n"
             "fn grab() -> SourceBytes { return source_bytes() }\n"
             "fn main() -> Int { return 0 }\n")
    _xg = "fn main() -> Int { return 0 }\n"
    def _xsess(reqs):
        _rr = _pwsh(["./pep.ps1", "session", "--jsonl"],
                    inp="\n".join(json.dumps(_x) for _x in reqs) + "\n")
        return [json.loads(_ln) for _ln in (_rr.stdout or "").splitlines()
                if _ln.strip()]
    _xo = _xsess([{"schemaVersion": 3, "op": "open", "name": "t",
                    "source": _xlib},
                   {"schemaVersion": 3, "op": "open", "name": "g",
                    "source": _xg}])
    _xd, _xr = _xo[0]["document"], _xo[0]["revision"]
    _xgd, _xgr = _xo[1]["document"], _xo[1]["revision"]
    _xst = {"document": _xgd, "revision": _xgr,
            "entryFunctions": ["main"]}
    def _xval(tool, fn, args, expect):
        _B = {"schemaVersion": 3, "toolProtocolVersion": 2,
              "tool": tool, "document": _xd, "revision": _xr}
        return _xsess([
            {"schemaVersion": 3, "op": "open", "name": "t",
             "source": _xlib},
            {"schemaVersion": 3, "op": "open", "name": "g",
             "source": _xg},
            dict(_B, op="tool_register", function=fn),
            dict(_B, op="tool_validate",
                 testVectors=[{"arguments": args, "expect": expect,
                               "semanticTarget": _xst}]),
        ])[3]
    _IVX = lambda v: {"type": "Int", "value": str(v)}
    _xok = True
    for _tn, _fn, _args, _exp in (
            ("u1", "first",
             [{"type": "E", "value": 1}], _IVX(1)),
            ("u2", "first",
             [{"type": "E", "fields": [
                 {"name": "A",
                  "value": {"type": "Int", "value": "1"}}]}],
             _IVX(1)),
            ("g", "grab", [], _IVX(0))):
        _xv = _xval(_tn, _fn, _args, _exp)
        _xe = _xv.get("error")
        _xok = (_xok and _xv.get("outcome") == "rejected" and (
            (isinstance(_xe, dict)
             and "scalar, List, and monomorphic record" in str(_xe.get("message", _xe)))
            or "scalar, List, and monomorphic record" in str(_xe)))
    results.append(("X-transport-excl", PASS if _xok else FAIL,
                    "all-rejected"))
    fails = [(n, d) for n, s, d in results if s == FAIL]
    print("=== Agent 3 corpus replay: %d/%d PASS ==="
          % (len(results) - len(fails), len(results)))
    for n, s, d in results:
        print("%-14s %s  %s" % (n, s, d))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
