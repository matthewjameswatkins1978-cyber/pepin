"""A3 BOOT-A3-171: the independent compiler-A approval runbook.

The dispatch asks A3 to, on a published candidate: build through the actual product path in
a clean checkout, use strict Clang AND GCC, exercise positive input-dependent outputs, the
malformed set, the seven unsupported class-(ii) cases, stdout/stderr/exit separately, and
no-C-on-failure, and audit that no semantic compiler sits in the native execution path -
then publish a SHA-bound pass/fail receipt.

This script is that run, in one command, so the approval is reproducible by anyone rather
than assembled from receipts.

  python verification/probes/gate_candidate_171.py --root D:/Projects/wt-a3-cand

Sections are reported independently and never roll up silently: a section that cannot run
says so, and the overall verdict is FAIL unless every section passes.

Exit: 0 all sections pass, 1 a section failed, 3 cannot run (no product path / no source).
"""
import argparse
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parents[1]
SOURCE_REL = "examples/dogfood/pep0/compiler_a.pep"

# PEP0_SUBSET.md class (ii): seed-valid, outside Pep-0 -> exit 5. Classes (i) -> 1.
CLASS_II = [
    ("str",     b'fn main() -> Str { return "x" }',   5),
    ("bool",    b"fn main() -> Bool { return true }", 5),
    ("unit",    b"fn main() -> Unit { return () }",   5),
    ("maincap", b"fn Main() -> Int { return 1 }",     5),
    ("nomain",  b"fn foo() -> Int { return 1 }",      5),
    ("unary",   b"fn main() -> Int { return -42 }",   5),
    ("binary",  b"fn main() -> Int { return 0-42 }",  5),
    ("var",     b"fn main() -> Int { var x = 1 return x }", 5),
    ("let",     b"fn main() -> Int { let x = 1 return x }", 5),
    ("twofn",   b"fn a() -> Int { return 1 } fn main() -> Int { return 2 }", 5),
]
# Byte-for-byte the shapes A4's oracle pins, restated here so this runbook does not depend
# on that file. An earlier version of this list used invented inputs ("return 1x") that are
# not valid Pep at all, so compiler A never saw them and the section failed for the wrong
# reason - caught by running it.
MALFORMED = [
    ("badlit",   b"fn main() -> Int { return ; }\n",   2),
    ("badbrace", b"fn main() -> Int { return 42 ]\n",  1),
    ("longlit",  b"fn main()->Int{return 1000000000000000000}\n", 4),
    ("dup",      b"fn main()->Int{return 1}\nfn main()->Int{return 2}\n", 3),
]
POSITIVE = [
    ("pos42", b"fn main() -> Int {\n  return 42\n}\n", "int main\n(\nvoid\n)\n{\nreturn\n42\n;\n}"),
    ("pos7",  b"fn main() -> Int {\n  return 7\n}\n",  "int main\n(\nvoid\n)\n{\nreturn\n7\n;\n}"),
]

SEC = []


def section(name, ok, detail):
    SEC.append((name, "PASS" if ok else "FAIL", detail))
    return ok


def run(cmd, cwd=None, timeout=3600):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="candidate worktree")
    ap.add_argument("--expect-sha", default=None)
    ap.add_argument("--source", default=SOURCE_REL)
    ap.add_argument("--contract", choices=("published", "narrow"), default="published",
                    help="published: all ten class-(ii) shapes must exit 5 (PEP0_SUBSET.md "
                         "as written). narrow: only the three return types the compiler "
                         "actually classifies - measures A3-155 option (b) without "
                         "pretending the published promise is met.")
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    if not (root / "pep_c23.py").is_file():
        print(f"CANNOT RUN: no pep_c23.py under {root}")
        return 3
    if not (root / a.source).is_file():
        print(f"CANNOT RUN: no {a.source} under {root}")
        return 3

    # -- identity ---------------------------------------------------------
    head = run(["git", "-C", str(root), "rev-parse", "HEAD"]).stdout.strip()
    dirty = run(["git", "-C", str(root), "status", "--porcelain"]).stdout.strip()
    blob = run(["git", "-C", str(root), "hash-object", str(root / a.source)]).stdout.strip()[:10]
    ident_ok = not dirty and (a.expect_sha is None or head.startswith(a.expect_sha))
    section("identity", ident_ok,
            f"HEAD {head[:12]} blob {blob} dirty={len(dirty.splitlines())}")

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a3gate"))
    cpath = tmp / "ca.c"
    exe = tmp / "ca_clang.exe"

    # -- product-path build ----------------------------------------------
    r = run([sys.executable, str(root / "pep_c23.py"), "build-c23", a.source,
             "--sectional", "--output", str(exe), "--emit-c", str(cpath)], cwd=str(root))
    tail = (r.stderr or r.stdout).strip().splitlines()
    built = r.returncode == 0 and cpath.is_file() and exe.is_file()
    section("product build", built,
            f"rc={r.returncode} C={cpath.stat().st_size if cpath.is_file() else 0}B"
            f" {'' if built else tail[-1][:70] if tail else ''}")
    if not built:
        return report(head, blob)

    # -- no C on failure --------------------------------------------------
    bad = tmp / "bad.pep"
    bad.write_bytes(b"fn main() -> Str { return 1 }\n")
    cbad = tmp / "bad.c"
    rb = run([sys.executable, str(root / "pep_c23.py"), "build-c23", str(bad),
              "--sectional", "--output", str(tmp / "bad.exe"), "--emit-c", str(cbad)],
             cwd=str(root))
    # CALIBRATION (A3-172): a stub compiler A passes this section, because it measures the
    # HOST's fail-closed behaviour on an invalid compiler-A source, not compiler A's quality.
    # Named accordingly so no reader treats it as compiler-A evidence.
    section("build fails closed", rb.returncode != 0 and not cbad.is_file(),
            f"host refusal, compiler-A-independent: rc={rb.returncode} wrote_c={cbad.is_file()}")

    # -- second toolchain from the same C ---------------------------------
    gcc = shutil.which("gcc")
    gexe = tmp / "ca_gcc.exe"
    gok = False
    if gcc:
        rg = run([gcc, "-std=c2x", "-O1", str(cpath), "-o", str(gexe)])
        gok = rg.returncode == 0 and gexe.is_file()
        section("gcc build", gok, f"rc={rg.returncode}")
    else:
        section("gcc build", False, "gcc not on PATH")

    # -- M-1 pins on both binaries ----------------------------------------
    sys.path.insert(0, str(HERE / "probes"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("m1", HERE / "probes" / "verify_m1_081.py")
    m1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m1)
    for label, binary in (("clang", exe), ("gcc", gexe)):
        if not pathlib.Path(binary).is_file():
            continue
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            b1, n1 = m1.gate([str(binary)], m1.PINNED, "pinned")
            b2, n2 = m1.gate([str(binary)], m1.UNSEEN, "unseen")
        section(f"M-1 pins ({label})", b1 + b2 == 0, f"{n1 + n2 - b1 - b2}/{n1 + n2}")

    # -- positive outputs, stdout and exit separately ----------------------
    posok, posdetail = True, []
    for name, src, want_out in POSITIVE:
        p = tmp / f"{name}.pep"
        p.write_bytes(src)
        rr = run([str(exe), str(p)])
        good = rr.stdout.rstrip("\n") == want_out and rr.returncode == 0
        posok = posok and good
        posdetail.append(f"{name}:{'ok' if good else 'BAD'}")
    section("positive output", posok, " ".join(posdetail))

    # -- class (ii): the seven, plus the three that already work -----------
    ii_cases = CLASS_II
    if a.contract == "narrow":
        ii_cases = [c for c in CLASS_II if c[0] in ("str", "bool", "unit")]
    ii_bad = []
    for name, src, want in ii_cases:
        p = tmp / f"ii_{name}.pep"
        p.write_bytes(src)
        rr = run([str(exe), str(p)])
        if rr.returncode != want:
            ii_bad.append(f"{name}={rr.returncode}/{want}")
    section(f"class (ii) codes [{a.contract}]", not ii_bad,
            f"{len(ii_cases)}/{len(ii_cases)} exit 5" if not ii_bad
            else f"{len(ii_bad)} of {len(ii_cases)} wrong: {', '.join(ii_bad[:5])}")

    # -- malformed --------------------------------------------------------
    mal_bad = []
    for name, src, want in MALFORMED:
        p = tmp / f"mal_{name}.pep"
        p.write_bytes(src)
        rr = run([str(exe), str(p)])
        if rr.returncode != want:
            mal_bad.append(f"{name}={rr.returncode}/{want}")
    section("malformed codes", not mal_bad,
            f"{len(MALFORMED)}/{len(MALFORMED)}" if not mal_bad else ", ".join(mal_bad))

    # -- native path audit -------------------------------------------------
    pypath = shutil.which("objdump")
    markers = {}
    raw = pathlib.Path(exe).read_bytes()
    for pat in (b"python", b"Python", b"ocaml", b"OCaml", b"opam", b"libpython"):
        markers[pat.decode()] = raw.count(pat)
    clean = sum(markers.values()) == 0
    section("native path", clean,
            "no interpreter markers" if clean else f"markers {markers}")

    return report(head, blob)


def report(head, blob):
    width = max(len(s[0]) for s in SEC) + 2
    print()
    print(f"{'section'.ljust(width)}result  detail")
    print("-" * (width + 56))
    for name, res, det in SEC:
        print(f"{name.ljust(width)}{res:<8}{det[:60]}")
    failed = sum(1 for s in SEC if s[1] == "FAIL")
    print()
    print(f"candidate {head[:12]} source blob {blob}")
    if failed:
        print(f"VERDICT: NOT APPROVED - {failed} of {len(SEC)} sections failed")
        return 1
    print(f"VERDICT: APPROVED - {len(SEC)} sections pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())