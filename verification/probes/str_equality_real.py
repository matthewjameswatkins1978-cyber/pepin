"""H-V5c part 2: does Str `==` lower natively at all (A4 H2's flagged risk), below the budget?

Minimal single-comparison program, one Str parameter and one Str literal argument (the
two-fallible-argument rule refuses two literal arguments, measured separately).

Vectors: equal ("say" vs "say") -> 1 ; unequal ("say" vs "nope") -> 0 ;
         prefix ("say" vs "sa") -> 0 ; empty ("say" vs "") -> 0.

Usage: python str_equality_real.py <a2-tree-with-a1_seed>
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-hv5"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402

SEED = ROOT / "_build" / "a1_seed" / "pep.exe"

FN = ('fn is_named(name: Str) -> Bool {\n'
      '  return name == "say"\n'
      '}\n')

VECTORS = [("say", 1), ("nope", 0), ("sa", 0), ("", 0)]

for literal, want in VECTORS:
    seed_src = FN + (f'let r = if is_named("{literal}") {{ 1 }} else {{ 0 }};\n'
                     'say(int_text(r));\n')
    native_src = FN + ('fn main() -> Int {\n'
                       f'  let r = if is_named("{literal}") {{ 1 }} else {{ 0 }}\n'
                       '  return r\n}\n')
    stem = f"seq_{literal or 'empty'}"
    path = OUT / f"{stem}.pep"
    path.write_text(seed_src, encoding="utf-8", newline="\n")
    seed = subprocess.run([str(SEED), "run", str(path)], capture_output=True,
                          cwd=str(ROOT), check=False)
    seed_out = seed.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
    try:
        c_source = pep_c23.emit(native_src.encode("utf-8"))
    except Exception as err:  # noqa: BLE001
        text = str(err)
        code = next((c for c in ("PEP_RUNTIME_STEP_LIMIT", "PEP_PARSE_STEP_LIMIT",
                                 "PEP_TYPE_MISMATCH", "PEP_UNKNOWN_TYPE") if c in text), "?")
        stage = ("CHECKER" if "check parsed source" in text
                 else "EMITTER" if "emit checked source" in text else "OTHER")
        print(f'literal={literal!r:8s} seed={seed_out!r} -> NATIVE REFUSED {stage} {code}')
        continue
    c_path = OUT / f"{stem}.c"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    results = []
    for compiler in ("clang", "gcc"):
        exe = OUT / f"{stem}_{compiler}.exe"
        built = subprocess.run([str(pep_c23.compiler_path(compiler)), "-std=c23", "-Wall",
                                "-Wextra", "-Wpedantic", "-Werror", "-O2", str(c_path),
                                "-o", str(exe)], capture_output=True, text=True,
                               check=False, cwd=str(ROOT))
        if built.returncode:
            results.append(f"{compiler.upper()}-BUILD-FAIL")
            continue
        done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
        # The epilogue PRINTS pep_fn_main() and returns 0, so the value is stdout, not the
        # exit status (measured: int main(void) { printf("%lld\n", pep_fn_main()); return 0; }).
        got = done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
        results.append(f"{compiler.upper()}={got}")
    verdict = "PARITY" if all(r.split("=")[1] == str(want) for r in results) else "MISMATCH"
    print(f'literal={literal!r:8s} seed={seed_out!r} want={want} -> {" ".join(results)} {verdict}')
