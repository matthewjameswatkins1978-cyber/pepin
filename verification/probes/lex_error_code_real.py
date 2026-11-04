"""H-V2 slice 1: the REAL stdlib/scan.pep:730 lex_error_code, verbatim, through seed + native.

Source (A2 `58fc9bf`, `stdlib/scan.pep` lines 730-741) is copied byte-for-byte into
`REAL_FN` below -- verified against the checkout by sha256 of the extracted slice, printed
as REAL_FN_SHA256. Nothing is edited: no guard dropped, no literal shortened.

Measurement ladder (each rung its own source, all sharing the verbatim function):
  R0  full five-guard function + record-field call  (A2's claimed parse-stage boundary)
  R1  full five-guard function + literal arguments  (removes the record, keeps every guard)
  R2  full five-guard function, returned and printed directly via say(...)
  R3  three-guard core (A2's pinned slice)          -- the existing claim, for contrast
  N1  verbatim function called with a kind whose guard cannot fire (fallthrough path)

Layers reported: seed-parse / seed-check / emitter / clang / gcc.

Usage: python lex_error_code_real.py <a2-tree>
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-hv2"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402

SEED = ROOT / "_build" / "a1_seed" / "pep.exe"

# VERBATIM stdlib/scan.pep:730-741 @ 58fc9bf (no edits).
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

RECORD_TYPE = 'type Info { kind: Str, diagnostic: Str }\n'
THREE_GUARD = (
    'fn lex_error_code(kind: Str, diagnostic: Str) -> Str {\n'
    '  if kind == "unexpected" { return "PEP_UNEXPECTED_CHARACTER" } else {}\n'
    '  if kind == "integer" { return "PEP_INT_LITERAL_RANGE" } else {}\n'
    '  return "PEP_LEXER_INPUT"\n'
    '}\n')

RUNGS = {
    "R0-record-fields": ((RECORD_TYPE + REAL_FN +
                         'fn main() -> Int {\n'
                         '  let i = Info { kind: "integer", diagnostic: "" }\n'
                         '  let code = lex_error_code(i.kind, i.diagnostic)\n'
                         '  say(code)\n'
                         '  return 0\n'
                         '}\n'), "integer", ""),
    "R1-literal-args": ((REAL_FN +
                        'fn main() -> Int {\n'
                        '  let code = lex_error_code("integer", "")\n'
                        '  say(code)\n'
                        '  return 0\n'
                        '}\n'), "integer", ""),
    "R2-inline-say": ((REAL_FN +
                      'fn main() -> Int {\n'
                      '  say(lex_error_code("string", ""))\n'
                      '  return 0\n'
                      '}\n'), "string", ""),
    "R3-three-guard": ((THREE_GUARD +
                       'fn main() -> Int {\n'
                       '  let code = lex_error_code("integer", "")\n'
                       '  say(code)\n'
                       '  return 0\n'
                       '}\n'), "integer", ""),
    "N1-fallthrough": ((REAL_FN +
                       'fn main() -> Int {\n'
                       '  let code = lex_error_code("bogus", "")\n'
                       '  say(code)\n'
                       '  return 0\n'
                       '}\n'), "bogus", ""),
}


def seed_source(source, kind, diagnostic):
    body = source.split("fn main()")[0]
    return (body + f'let code = lex_error_code("{kind}", "{diagnostic}");\n'
            'say(code);\n')


def run_seed(source, stem):
    path = OUT / f"{stem}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    done = subprocess.run([str(SEED), "run", str(path)], capture_output=True,
                          cwd=str(ROOT), check=False)
    out = done.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    err = done.stderr.decode("utf-8", "replace")
    return done.returncode, out, err


def emit(source, stem):
    try:
        return pep_c23.emit(source.encode("utf-8")), None
    except Exception as err:  # noqa: BLE001
        detail = str(err).replace("\n", " ")
        if "{" in detail:
            start = detail.index("{")
            try:
                payload = json.loads(detail[start:detail.rindex("}") + 1])
                error = payload.get("error") or {}
                detail = f"{error.get('code')}: {error.get('message')}"
            except (ValueError, KeyError):
                pass
        return None, f"{type(err).__name__}: {detail}"[:220]


def compile_and_run(compiler, c_source, stem):
    compiler_path = pep_c23.compiler_path(compiler)
    c_path = OUT / f"{stem}.c"
    exe = OUT / f"{stem}_{compiler}.exe"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    built = subprocess.run([str(compiler_path), "-std=c23", "-Wall", "-Wextra",
                            "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
                           capture_output=True, text=True, check=False, cwd=str(ROOT))
    if built.returncode:
        return None, f"BUILD-FAIL {built.stderr[:160]}"
    done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
    return (done.stdout.decode("utf-8", "replace").replace("\r\n", "\n"),
            done.returncode), None


def main():
    print(f"REAL_FN_SHA256 {hashlib.sha256(REAL_FN.encode()).hexdigest()}")
    src_file = (ROOT / "stdlib" / "scan.pep").read_text(encoding="utf-8")
    extracted = "\n".join(src_file.split("\n")[729:741]) + "\n"
    print(f"CHECKOUT_SLICE_SHA256 {hashlib.sha256(extracted.encode()).hexdigest()} "
          f"match={extracted == REAL_FN}")
    for label, (source, kind, diagnostic) in RUNGS.items():
        rc, out, err = run_seed(seed_source(source, kind, diagnostic), f"seed_{label}")
        if rc != 0:
            first = [ln for ln in err.strip().split("\n") if ln][:2]
            print(f"{label:18s} SEED rc={rc} out={out.strip()[:40]!r} err={' | '.join(first)[:180]}")
        else:
            print(f"{label:18s} SEED rc=0 out={out.strip()!r}")
        c_source, emit_err = emit(source, label)
        if emit_err:
            print(f"{'':18s} EMIT-REFUSED {emit_err[:170]}")
            continue
        for compiler in ("clang", "gcc"):
            got, build_err = compile_and_run(compiler, c_source, label)
            if build_err:
                print(f"{'':18s} {compiler.upper()}-{build_err[:150]}")
                continue
            stdout, exit_code = got
            print(f"{'':18s} {compiler.upper()} rc={exit_code} out={stdout.strip()!r}")


if __name__ == "__main__":
    sys.exit(main())
