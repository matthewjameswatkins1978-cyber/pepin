"""H-V2 slice 4: second REAL compiler function -- advance_position (examples/pep_lexer.pep:90-94).

Verbatim source, byte-checked against the checkout. Distinct shape from lex_error_code:
record RETURN (SourcePosition), if/else EXPRESSION with record constructors, Int arithmetic.
Observation is numeric (no `say(int_text(..))`, which the emitter refuses): main collapses the
returned record to one Int, so the oracle is an exit/stdout integer rather than a Str.

Vectors (source-grounded: the lexer's own newline byte and an ordinary byte):
  byte=10 ('\n'), line=3 column=7  -> {line:4, column:1} -> 4*100+1 = 401
  byte=65 ('A'),  line=3 column=7  -> {line:3, column:8} -> 3*100+8 = 308
  byte=10, line=0 column=1         -> {line:1, column:1} -> 101   (source start boundary)

Usage: python advance_position_real.py <a2-tree>
"""
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-hv2"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402

SEED = ROOT / "_build" / "a1_seed" / "pep.exe"

REAL_FN = (
    'fn advance_position(line: Int, column: Int, byte: Int) -> SourcePosition {\n'
    '  if byte == 10 { return SourcePosition { line: line + 1, column: 1 } } else {\n'
    '    return SourcePosition { line: line, column: column + 1 }\n'
    '  }\n'
    '}\n')
# The type declaration this function needs, verbatim from examples/pep_lexer.pep:1.
TYPE_DECL = 'type SourcePosition { line: Int, column: Int }\n'

VECTORS = [(10, 3, 7, 401), (65, 3, 7, 308), (10, 0, 1, 101)]


def collapse():
    return 'pos.line * 100 + pos.column'


def seed_program(byte, line, column):
    return (TYPE_DECL + REAL_FN +
            f'let pos = advance_position({line}, {column}, {byte});\n'
            f'let code = {collapse()};\n'
            'say(int_text(code));\n')


def native_program(byte, line, column):
    return (TYPE_DECL + REAL_FN + 'fn main() -> Int {\n'
            f'  let pos = advance_position({line}, {column}, {byte})\n'
            f'  return {collapse()}\n'
            '}\n')


def main():
    print(f"REAL_FN_SHA256 {hashlib.sha256(REAL_FN.encode()).hexdigest()}")
    checkout = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
    lines = checkout.split("\n")
    extracted = "\n".join(lines[89:94]) + "\n"
    type_line = lines[0] + "\n"
    print(f"CHECKOUT_FN_SHA256 {hashlib.sha256(extracted.encode()).hexdigest()} "
          f"match={extracted == REAL_FN}")
    print(f"CHECKOUT_TYPE_SHA256 {hashlib.sha256(type_line.encode()).hexdigest()} "
          f"match={type_line == TYPE_DECL}")
    for byte, line, column, want in VECTORS:
        stem = f"ap_{byte}_{line}_{column}"
        path = OUT / f"{stem}.pep"
        path.write_text(seed_program(byte, line, column), encoding="utf-8", newline="\n")
        seed = subprocess.run([str(SEED), "run", str(path)], capture_output=True,
                              cwd=str(ROOT), check=False)
        seed_out = seed.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
        label = (f"byte={byte:3d} line={line} col={column} want={want}")
        if seed.returncode != 0 or seed_out != str(want):
            print(f"{label} SEED-MISMATCH rc={seed.returncode} out={seed_out!r}")
            continue
        try:
            c_source = pep_c23.emit(native_program(byte, line, column).encode("utf-8"))
        except Exception as err:  # noqa: BLE001
            print(f"{label} SEED={seed_out} EMIT-REFUSED {str(err)[:110]}")
            continue
        c_path = OUT / f"{stem}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for compiler in ("clang", "gcc"):
            exe = OUT / f"{stem}_{compiler}.exe"
            built = subprocess.run([str(pep_c23.compiler_path(compiler)), "-std=c23",
                                    "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                                    str(c_path), "-o", str(exe)],
                                   capture_output=True, text=True, check=False, cwd=str(ROOT))
            if built.returncode:
                print(f"{label} {compiler.upper()} BUILD-FAIL {built.stderr.strip()[:100]}")
                continue
            done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
            got = done.stdout.decode("utf-8", "replace").strip()
            verdict = "PARITY" if got == str(want) else f"MISMATCH want={want}"
            print(f"{label} seed={seed_out} {compiler.upper()}={got} {verdict}")


if __name__ == "__main__":
    sys.exit(main())
