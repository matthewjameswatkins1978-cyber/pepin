"""A3 BOOT-A3-162: compiler A's INPUT CLASSIFICATION contract gate.

The M-1 oracle pins one example per input class, so it cannot see whether compiler A
distinguishes "valid Pep I do not support" (exit 5) from "not Pep at all" (exit 1/2/3).
PEP0_SUBSET.md class (ii) names nine seed-valid shapes that must exit 5. A3-153 found
seven of them returning the wrong code, A3-155 traced them to three source sites, and
A3-160 confirmed them on the product-path binary.

This gate makes that a mechanical check instead of a paragraph. It builds compiler A from
the committed product-path C and runs every class-(ii) shape documented in
PEP0_SUBSET.md, plus the controls that must keep working.

Exit: 0 all cases match the documented contract
      1 one or more mismatches (prints each)
      3 no compiler or no fixture (the gate cannot run)

Override the binary with PEPIN_CA_EXE to test a tracked build instead of the fixture.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_C = HERE / "fixtures" / "a3-compilerA-productpath.c"
# A3-212: the tree-relative path this fixture was built from, used for the anti-rot check.
SOURCE_REL = "examples/dogfood/pep0/compiler_a.pep"

# (name, source bytes, expected exit, why)
CASES = [
    # PEP0_SUBSET.md class (ii): seed-valid, outside Pep-0 -> exit 5, no C.
    ("classii_bool",     b"fn main() -> Bool { return true }", 5, "-> Bool return"),
    ("classii_unit",     b"fn main() -> Unit { return () }",   5, "-> Unit return"),
    ("classii_str",      b'fn main() -> Str { return "x" }',   5, "-> Str return"),
    ("classii_maincap",  b"fn Main() -> Int { return 1 }",     5, "fn Main is seed-valid, no main"),
    ("classii_nomain",   b"fn foo() -> Int { return 1 }",      5, "non-main only"),
    ("classii_unary",    b"fn main() -> Int { return -42 }",   5, "unary minus"),
    ("classii_binary",   b"fn main() -> Int { return 0-42 }",  5, "binary arithmetic"),
    ("classii_var",      b"fn main() -> Int { var x = 1 return x }", 5, "var declaration"),
    ("classii_let",      b"fn main() -> Int { let x = 1 return x }", 5, "let declaration"),
    ("classii_twofn",    b"fn a() -> Int { return 1 } fn main() -> Int { return 2 }", 5, "multi-function"),
    # Controls: these must keep their documented codes.
    ("ctl_longlit",      b"fn main() -> Int { return 1000000000000000000 }", 4, "19-digit cap"),
    ("ctl_ok",           b"fn main() -> Int {\n  return 42\n}\n", 0, "the accepted shape"),
    ("ctl_empty",        b"",                                    0, "empty input is vacuous"),
    ("ctl_ws",           b"   \n\t\n  ",                         0, "whitespace only"),
]


def build_binary(tmp):
    exe = os.environ.get("PEPIN_CA_EXE")
    if exe:
        return exe, None
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc:
        return None, "no clang or gcc on PATH"
    if not FIXTURE_C.is_file():
        return None, f"missing fixture {FIXTURE_C}"
    out = pathlib.Path(tmp) / "ca.exe"
    r = subprocess.run([cc, "-std=c23", "-O1", str(FIXTURE_C), "-o", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, f"fixture C did not compile: {r.stderr.strip()[:90]}"
    return str(out), None


def main():
    tmp = tempfile.mkdtemp(prefix="a3contract")
    exe, why = build_binary(tmp)
    if exe is None:
        print(f"CONTRACT: CANNOT RUN - {why}")
        return 3
    # A3-212: anti-rot check. The fixture is a committed copy of compiler A's emitted C,
    # so it silently measures an older artifact whenever A4's source moves - which is
    # exactly what happened between A3-198 and A3-211. Warn loudly rather than rot quietly.
    prov_path = FIXTURE_C.with_suffix(".provenance")
    rounded = str(FIXTURE_C.relative_to(HERE))
    if prov_path.is_file():
        try:
            prov = json.loads(prov_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  NOTE: could not read {prov_path.name}: {exc}")
            prov = {}
        if prov:
            print(f"  fixture built from {prov.get('source_revision')} "
                  f"blob {prov.get('source_blob')} (recipe {prov.get('driver_recipe_sha256')})")
            ca = os.environ.get("PEPIN_CA_ROOT")
            if ca:
                tree_src = pathlib.Path(ca) / SOURCE_REL
                if tree_src.is_file():
                    import hashlib
                    r = subprocess.run(["git", "-C", ca, "hash-object", str(tree_src)],
                                       capture_output=True, text=True)
                    blob = r.stdout.strip()[:10]
                    if blob and blob != prov.get("source_blob"):
                        print(f"  STALE: {rounded} was built from blob {prov.get('source_blob')} "
                              f"but the tree's compiler_a.pep is {blob}.")
                        print("  A gate measuring a stale artifact must not report a verdict. "
                              "Regenerate the fixture (A3-211) or unset PEPIN_CA_ROOT.")
                        return 3
    tmpdir = pathlib.Path(tmp)
    # A3-204: support the narrowed contract so the gate can be run the moment a decision
    # lands. PEP0_SUBSET.md as written promises nine class-(ii) shapes exit 5; only three
    # are implemented. CONTRACT=narrow checks just those three.
    contract = os.environ.get("PEPIN_CONTRACT", "published")
    cases = CASES
    if contract == "narrow":
        cases = [c for c in CASES if not c[0].startswith("classii")
                 or c[0] in ("classii_str", "classii_bool", "classii_unit")]
    bad, rows = 0, []
    for name, src, want, why in cases:
        p = tmpdir / f"{name}.pep"
        p.write_bytes(src)
        r = subprocess.run([exe, str(p)], capture_output=True, text=True, timeout=180)
        ok = r.returncode == want
        bad += 0 if ok else 1
        rows.append((name, want, r.returncode, "ok" if ok else "MISMATCH",
                     r.stdout.strip().replace("\n", "/")[:30], why))
    for name, want, got, verdict, out, why in rows:
        print(f"  {name:<18} want={want:<2} got={got:<2} {verdict:<9} {out:<30} {why}")
    if bad:
        known = [r[0] for r in rows if r[3] == "MISMATCH"]
        print(f"  misclassified: {', '.join(known)}")
        print("  These are seed-valid inputs reported as malformed. Either give compiler A")
        print("  enough parsing to classify, or narrow the published contract (A3-155).")
    # Summary LAST: the gate runner reports the final line, so it must carry the count.
    label = ("PEP0_SUBSET.md as published" if contract == "published"
             else "narrowed contract (3 return types only)")
    print(f"CONTRACT[{contract}]: {len(rows) - bad}/{len(rows)} match {label}"
          f"{'' if bad == 0 else f' - {bad} misclassified'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())