"""H-V2 slice 3: 14-vector discriminating matrix over the REAL lex_error_code semantics.

Source: stdlib/scan.pep:730-741 @ A2 58fc9bf, used verbatim as the SEED-side program (the seed
checks and runs it). The native side can only emit the 2-guard prefix at this revision, so each
vector reports three columns and the difference is the measured capability gap -- the native
prefix is NEVER presented as the real function's behaviour.

Columns: REAL(seed) | PREFIX(native Clang+GCC) | verdict
  PARITY     real == prefix (vector cannot distinguish them)
  GAP:<code> real returns <code>, prefix returns PEP_LEXER_INPUT (string branch not emittable)
  NATIVE-NOT-RUN  native refused this vector's shape

Vector axes (matching the real function's own decision structure):
  kind: unexpected / integer / string / bogus        (4 branches)
  diagnostic: the two exact messages scan_string_at emits, plus an unrelated one (3)

Usage: python lex_error_code_matrix.py <a2-tree>
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
    'fn lex_error_code(kind: Str, diagnostic: Str) -> Str {\n'
    '  if kind == "unexpected" { return "PEP_UNEXPECTED_CHARACTER" } else {}\n'
    '  if kind == "integer" { return "PEP_INT_LITERAL_RANGE" } else {}\n'
    '  if kind == "string" {\n'
    '    if diagnostic == "Pep scan found an unescaped newline in a string literal" {\n'
    '      return "PEP_NEWLINE_IN_STRING"\n'
    '    } else {}\n'
    '    if diagnostic == "Pep scan found an unsupported string escape" { return "PEP_INVALID_ESCAPE" } else {}\n'
    '    return "PEP_UNTERMINATED_STRING"\n'
    '  } else {}\n'
    '  return "PEP_LEXER_INPUT"\n'
    '}\n')

PREFIX_FN = (
    'fn lex_error_code(kind: Str, diagnostic: Str) -> Str {\n'
    '  if kind == "unexpected" { return "PEP_UNEXPECTED_CHARACTER" } else {}\n'
    '  if kind == "integer" { return "PEP_INT_LITERAL_RANGE" } else {}\n'
    '  return "PEP_LEXER_INPUT"\n'
    '}\n')

NEWLINE = "Pep scan found an unescaped newline in a string literal"
ESCAPE = "Pep scan found an unsupported string escape"
OTHER = "Pep scan found something else"

VECTORS = [
    ("unexpected", OTHER),
    ("unexpected", NEWLINE),
    ("integer", OTHER),
    ("integer", ESCAPE),
    ("string", NEWLINE),
    ("string", ESCAPE),
    ("string", OTHER),
    ("string", ""),
    ("bogus", OTHER),
    ("bogus", NEWLINE),
    ("", OTHER),
    ("unexpected", ""),
    ("integer", NEWLINE),
    ("bogus", ""),
]


RECORD = 'type Info { kind: Str, diagnostic: Str }\n'


def seed_program(kind, diagnostic):
    # The source's own call site (scan.pep:845) passes RECORD FIELDS, not literals; literal Str
    # arguments are refused by the emitter's two-fallible-argument rule (measured separately).
    return (RECORD + REAL_FN +
            f'let i = Info {{ kind: "{kind}", diagnostic: "{diagnostic}" }};\n'
            'let code = lex_error_code(i.kind, i.diagnostic);\n'
            'say(code);\n')


def native_program(kind, diagnostic):
    return (RECORD + PREFIX_FN + 'fn main() -> Int {\n'
            f'  let i = Info {{ kind: "{kind}", diagnostic: "{diagnostic}" }}\n'
            '  let code = lex_error_code(i.kind, i.diagnostic)\n'
            '  say(code)\n  return 0\n}\n')


def run_seed(source, stem):
    path = OUT / f"mx_{stem}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    done = subprocess.run([str(SEED), "run", str(path)], capture_output=True,
                          cwd=str(ROOT), check=False)
    return (done.returncode,
            done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip(),
            done.stderr.decode("utf-8", "replace").strip().split("\n")[0][:100])


def run_native(source, stem, compiler):
    try:
        c_source = pep_c23.emit(source.encode("utf-8"))
    except Exception as err:  # noqa: BLE001
        return None, f"EMIT-REFUSED {str(err)[:80]}"
    c_path = OUT / f"mx_{stem}.c"
    exe = OUT / f"mx_{stem}_{compiler}.exe"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    built = subprocess.run([str(pep_c23.compiler_path(compiler)), "-std=c23", "-Wall",
                            "-Wextra", "-Wpedantic", "-Werror", "-O2", str(c_path),
                            "-o", str(exe)], capture_output=True, text=True,
                           check=False, cwd=str(ROOT))
    if built.returncode:
        return None, f"C-BUILD {built.stderr.strip()[:80]}"
    done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
    lines = done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip().split("\n")
    return (lines[0] if lines else ""), None


def main():
    print(f"REAL_FN_SHA256 {hashlib.sha256(REAL_FN.encode()).hexdigest()}")
    print(f"PREFIX_FN_SHA256 {hashlib.sha256(PREFIX_FN.encode()).hexdigest()}")
    counts = {"PARITY": 0, "GAP": 0, "NATIVE-NOT-RUN": 0}
    for index, (kind, diagnostic) in enumerate(VECTORS, 1):
        rc, real, seed_err = run_seed(seed_program(kind, diagnostic), f"v{index}")
        if rc != 0:
            print(f"v{index:02d} kind={kind!r:14s} SEED-FAIL rc={rc} {seed_err}")
            counts["NATIVE-NOT-RUN"] += 1
            continue
        outputs = {}
        failure = None
        for compiler in ("clang", "gcc"):
            value, err = run_native(native_program(kind, diagnostic), f"v{index}", compiler)
            if err:
                failure = f"{compiler.upper()}: {err}"
                break
            outputs[compiler] = value
        if failure:
            print(f"v{index:02d} kind={kind!r:14s} real={real:24s} NATIVE-NOT-RUN {failure}")
            counts["NATIVE-NOT-RUN"] += 1
            continue
        if outputs["clang"] != outputs["gcc"]:
            print(f"v{index:02d} kind={kind!r:14s} COMPILER-DIVERGENCE "
                  f"clang={outputs['clang']!r} gcc={outputs['gcc']!r}")
            counts["NATIVE-NOT-RUN"] += 1
            continue
        native = outputs["clang"]
        if native == real:
            verdict = "PARITY-on-runnable-prefix"
            counts["PARITY"] += 1
        else:
            # NOT a native misbehaviour: the real function has no native execution at all, so
            # the substituted prefix cannot stand in for the string branch.
            verdict = f"UNAVAILABLE:string-branch real={real}"
            counts["GAP"] += 1
        print(f"v{index:02d} kind={kind!r:14s} real={real:24s} native={native:24s} {verdict[:60]}")
    print(f"SUMMARY vectors={len(VECTORS)} {counts}")
    print("NOTE: GAP rows are NOT native misbehaviour -- the real function is refused "
          "entirely at this revision; the prefix is the largest emittable share of it.")


if __name__ == "__main__":
    sys.exit(main())
