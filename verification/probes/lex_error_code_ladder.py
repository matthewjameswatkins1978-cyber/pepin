"""H-V2 slice 2 / H-V4: guard-count ladder on the REAL lex_error_code shape.

The function body is stdlib/scan.pep:730-741 @58fc9bf. Rungs are PREFIX subsets of its
guards (guard 1..5, in source order) plus the always-present final fallthrough. No guard is
rewritten; rungs are measured prefixes, so "first failing rung" is a boundary on real source
structure, not a synthetic knob.

Two argument shapes, because A2's pinned test uses record-field arguments and the source's own
call site (scan.pep:845) does the same, while literal arguments are what a caller may also write:
  REC  -> let i = Info{...}; let code = lex_error_code(i.kind, i.diagnostic); say(code)
  LIT  -> let code = lex_error_code("integer", ""); say(code)

Stages: seed-parse (pep.exe run) / emitter (pep_c23.emit: checker, then emitter function) /
clang / gcc.

Usage: python lex_error_code_ladder.py <a2-tree>
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

GUARDS = [
    '  if kind == "unexpected" { return "PEP_UNEXPECTED_CHARACTER" } else {}\n',
    '  if kind == "integer" { return "PEP_INT_LITERAL_RANGE" } else {}\n',
    '  if kind == "string" {\n'
    '    if diagnostic == "Pep scan found an unescaped newline in a string literal" {\n'
    '      return "PEP_NEWLINE_IN_STRING"\n'
    '    } else {}\n'
    '    if diagnostic == "Pep scan found an unsupported string escape" { return "PEP_INVALID_ESCAPE" } else {}\n'
    '    return "PEP_UNTERMINATED_STRING"\n'
    '  } else {}\n',
    '  if kind == "escape" { return "PEP_INVALID_ESCAPE" } else {}\n',
    '  if kind == "newline" { return "PEP_NEWLINE_IN_STRING" } else {}\n',
]
REC_TYPE = 'type Info { kind: Str, diagnostic: Str }\n'


def fn_with(count):
    return ('fn lex_error_code(kind: Str, diagnostic: Str) -> Str {\n'
            + "".join(GUARDS[:count])
            + '  return "PEP_LEXER_INPUT"\n'
            '}\n')


def program(count, shape):
    call = ('  let i = Info { kind: "integer", diagnostic: "" }\n'
            '  let code = lex_error_code(i.kind, i.diagnostic)\n'
            if shape == "REC" else
            '  let code = lex_error_code("integer", "")\n')
    body = (REC_TYPE if shape == "REC" else "") + fn_with(count)
    return body + ('fn main() -> Int {\n' + call + '  say(code)\n  return 0\n}\n')


def seed_run(source, stem):
    path = OUT / f"ladder_{stem}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    done = subprocess.run([str(SEED), "run", str(path)], capture_output=True,
                          cwd=str(ROOT), check=False)
    return (done.returncode,
            done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip(),
            done.stderr.decode("utf-8", "replace").strip().split("\n")[0][:120])


def stage_of_error(text):
    """Which pipeline stage refused, and the exact diagnostic code if present."""
    for marker, stage in (("check parsed source", "CHECKER"),
                          ("emit checked source", "EMITTER"),
                          ("parse", "PARSER")):
        if marker in text:
            for code in ("PEP_RUNTIME_STEP_LIMIT", "PEP_PARSE_STEP_LIMIT",
                         "PEP_TYPE_MISMATCH", "PEP_UNKNOWN_TYPE"):
                if code in text:
                    return stage, code, text[text.index(code):][:90]
            return stage, "?", text[:120]
    return "?", "?", text[:120]


def emit(source, stem):
    try:
        return pep_c23.emit(source.encode("utf-8")), None
    except Exception as err:  # noqa: BLE001
        return None, stage_of_error(str(err))


def compile_run(compiler, c_source, stem):
    compiler_path = pep_c23.compiler_path(compiler)
    c_path = OUT / f"ladder_{stem}.c"
    exe = OUT / f"ladder_{stem}_{compiler}.exe"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    built = subprocess.run([str(compiler_path), "-std=c23", "-Wall", "-Wextra",
                            "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
                           capture_output=True, text=True, check=False, cwd=str(ROOT))
    if built.returncode:
        return None, f"C-BUILD {built.stderr.strip()[:120]}"
    done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
    return (done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip(),
            done.returncode), None


def main():
    print(f"GUARD_SET_SHA256 {hashlib.sha256(''.join(GUARDS).encode()).hexdigest()}")
    for shape in ("REC", "LIT"):
        print(f"\n=== argument shape {shape} ===")
        for count in range(1, 6):
            label = f"g{count}-{shape}"
            source = program(count, shape)
            rc, out, err = seed_run(source, label)
            seed_txt = f"seed rc={rc} {'OK ' + out if rc == 0 else 'ERR ' + err}"
            c_source, failure = emit(source, label)
            if failure:
                stage, code, detail = failure
                print(f"g{count} {seed_txt:38s} -> {stage} {code} :: {detail}")
                continue
            results = []
            for compiler in ("clang", "gcc"):
                got, build_err = compile_run(compiler, c_source, label)
                if build_err:
                    results.append(f"{compiler.upper()}-{build_err}")
                else:
                    stdout, exit_code = got
                    results.append(f"{compiler.upper()} rc={exit_code} {stdout!r}")
            print(f"g{count} {seed_txt:38s} -> EMITTED {len(c_source)}B :: {' | '.join(results)}")


if __name__ == "__main__":
    sys.exit(main())
