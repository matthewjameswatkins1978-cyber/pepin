"""Probe the deliberate primitive-shadowing exception in the duplicate-type repair.

`chunk_type_declarations` excludes primitive names from its duplicate scan
(`if !supported_primitive_type(resolved.recordName)` at tests/pep_checker_a13.pep in the
declaration-closure scan), so `type Int { ... }` and a repeated `type Int { ... }` bypass the
duplicate refusal. This probe asks whether the SEED agrees with that exception, using the seed
CLI as oracle only. No harness is involved, so a disagreement is a plain behavioural difference.

Usage: python dup_primitive_shadow.py <candidate-worktree>
Exit: 0 = seed and staged exception agree on every case, 1 = a case differs, 2 = harness error.
"""
import json
import pathlib
import subprocess
import sys
import tempfile

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
PEP_PS1 = REPO / "pep.ps1"
RESULTS = []

CASES = {
    "P1 single record shadowing a primitive name (type Int { a: Int })":
        "type Int {\n    a: Int\n}\nfn f(x: Int) -> Int {\n    return x.a\n}\n",
    "P2 two records both shadowing the same primitive (type Str twice)":
        "type Str {\n    a: Int\n}\ntype Str {\n    b: Int\n}\n"
        "fn f(x: Str) -> Int {\n    return x.a\n}\n",
    "P3 primitive shadow plus a duplicate user record (control that dupes still refuse)":
        "type Int {\n    a: Int\n}\ntype D {\n    a: Int\n}\ntype D {\n    b: Int\n}\n"
        "fn f(d: D) -> Int {\n    return d.a\n}\n",
    "P4 record named Bool, body uses it (no duplication)":
        "type Bool {\n    a: Int\n}\nfn f(x: Bool) -> Int {\n    return x.a\n}\n",
}


def seed_verdict(source):
    with tempfile.TemporaryDirectory(prefix="a3-prim-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(source.encode("utf-8"))
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"], cwd=str(REPO), capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        return "NON_JSON", done.stderr[-200:]
    codes = [item.get("code") for item in payload.get("diagnostics") or []]
    return payload.get("status") + (("/" + "/".join(str(c) for c in codes)) if codes else ""), ""


print(f"REPO={REPO}")
for name, source in CASES.items():
    verdict, note = seed_verdict(source)
    print(f"[seed] {name} -> {verdict}" + (f"  ({note})" if note else ""))
    RESULTS.append({"case": name, "seed": verdict})
print(json.dumps(RESULTS, indent=2))
