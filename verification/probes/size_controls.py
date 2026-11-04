"""H-V4 controls: is the tiny second-function boundary caused by the Str-returning function,
or by any second function at all?

Cells (all programs seed-valid; only the native pipeline verdict is compared):
  S0  Str guard-chain fn + N fillers        (the ladder shape)
  S1  Int guard-chain fn + N fillers        (same shape, Int result)
  S2  no helper fn at all + N fillers       (main only)

Usage: python size_controls.py <a2-tree-with-a1_seed>
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-hv4"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402

SEED = ROOT / "_build" / "a1_seed" / "pep.exe"
RECORD = 'type Info { kind: Str, diagnostic: Str }\n'

STR_FN = (
    'fn lex_error_code(kind: Str, diagnostic: Str) -> Str {\n'
    '  if kind == "unexpected" { return "PEP_UNEXPECTED_CHARACTER" } else {}\n'
    '  if kind == "integer" { return "PEP_INT_LITERAL_RANGE" } else {}\n'
    '  return "PEP_LEXER_INPUT"\n'
    '}\n')
INT_FN = (
    'fn classify(kind: Int) -> Int {\n'
    '  if kind == 1 { return 10 } else {}\n'
    '  if kind == 2 { return 20 } else {}\n'
    '  return 0\n'
    '}\n')
MAIN_STR = ('fn main() -> Int {\n'
            '  let i = Info { kind: "integer", diagnostic: "" }\n'
            '  let code = lex_error_code(i.kind, i.diagnostic)\n'
            '  say(code)\n  return 0\n}\n')
MAIN_INT = ('fn main() -> Int {\n'
            '  let code = classify(2)\n  return code\n}\n')
MAIN_PLAIN = 'fn main() -> Int {\n  return 42\n}\n'


def filler(index):
    return f'fn filler_{index}(v: Int) -> Int {{\n  return v + {index}\n}}\n'


CELLS = {
    "S0-Str-chain": lambda n: RECORD + STR_FN + "".join(filler(i) for i in range(n)) + MAIN_STR,
    "S1-Int-chain": lambda n: INT_FN + "".join(filler(i) for i in range(n)) + MAIN_INT,
    "S2-main-only": lambda n: "".join(filler(i) for i in range(n)) + MAIN_PLAIN,
}

for label, build in CELLS.items():
    for count in (0, 1, 3, 8):
        source = build(count)
        path = OUT / f"ctl_{label}_{count}.pep"
        path.write_text(source, encoding="utf-8", newline="\n")
        seed = subprocess.run([str(SEED), "run", str(path)], capture_output=True,
                              cwd=str(ROOT), check=False)
        line = f"{label:14s} fillers={count} bytes={len(source):4d} seed_rc={seed.returncode}"
        if seed.returncode != 0:
            print(f"{line} SEED-REJECTED")
            continue
        try:
            c_source = pep_c23.emit(source.encode("utf-8"))
        except Exception as err:  # noqa: BLE001
            text = str(err)
            code = next((c for c in ("PEP_RUNTIME_STEP_LIMIT", "PEP_PARSE_STEP_LIMIT")
                         if c in text), "?")
            stage = ("CHECKER" if "check parsed source" in text
                     else "EMITTER" if "emit checked source" in text else "OTHER")
            marker = text.find("budget exceeded")
            print(f"{line} -> REFUSED {stage} {code} :: "
                  f"{text[marker:marker + 26] if marker >= 0 else text[:60]}")
            continue
        c_path = OUT / f"ctl_{label}_{count}.c"
        exe = OUT / f"ctl_{label}_{count}.exe"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        built = subprocess.run([str(pep_c23.compiler_path("clang")), "-std=c23", "-Wall",
                                "-Wextra", "-Wpedantic", "-Werror", "-O2", str(c_path),
                                "-o", str(exe)], capture_output=True, text=True,
                               check=False, cwd=str(ROOT))
        if built.returncode:
            print(f"{line} -> C-BUILD-FAIL {built.stderr.strip()[:70]}")
            continue
        done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
        print(f"{line} -> OK {len(c_source)}B native_rc={done.returncode} "
              f"out={done.stdout.decode('utf-8', 'replace').strip()[:16]!r}")
