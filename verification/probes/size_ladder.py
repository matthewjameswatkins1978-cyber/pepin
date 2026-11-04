"""H-V4: where does a VALID compiler-shaped program first become unexecutable?

The frozen Candidate6 gate measures a 66-node fixture (62 ok / 64 refuse) and is A1's to fix.
This ladder is a different shape entirely: the REAL two-guard lex_error_code prefix (the largest
emittable share of stdlib/scan.pep:730, see ACCEPT-H-V2) plus N trivial filler functions, grown
until the pipeline refuses. Filler functions are valid, unused, and identical in shape, so the
only variable is program size.

Stages reported: seed-check / checker tool / emitter tool / C build / native run.
Seed validity is asserted for EVERY rung, so a refusal can only come from the native pipeline's
budget, never from source invalidity.

Usage: python size_ladder.py <a2-tree-with-a1_seed>
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

REAL_PREFIX = (
    'fn lex_error_code(kind: Str, diagnostic: Str) -> Str {\n'
    '  if kind == "unexpected" { return "PEP_UNEXPECTED_CHARACTER" } else {}\n'
    '  if kind == "integer" { return "PEP_INT_LITERAL_RANGE" } else {}\n'
    '  return "PEP_LEXER_INPUT"\n'
    '}\n')
RECORD = 'type Info { kind: Str, diagnostic: Str }\n'
MAIN = ('fn main() -> Int {\n'
        '  let i = Info { kind: "integer", diagnostic: "" }\n'
        '  let code = lex_error_code(i.kind, i.diagnostic)\n'
        '  say(code)\n  return 0\n}\n')


def filler(index):
    return f'fn filler_{index}(v: Int) -> Int {{\n  return v + {index}\n}}\n'


def program(count):
    return RECORD + REAL_PREFIX + "".join(filler(i) for i in range(count)) + MAIN


def stage_of(text):
    for marker, stage in (("check parsed source", "CHECKER"),
                          ("emit checked source", "EMITTER")):
        if marker in text:
            return stage
    return "OTHER"


def main():
    print(f"PREFIX_SHA256 {__import__('hashlib').sha256(REAL_PREFIX.encode()).hexdigest()}")
    first_failure = None
    for count in (0, 1, 2, 3, 4, 5, 6):
        source = program(count)
        nodes = source.count("\n")
        path = OUT / f"size_{count}.pep"
        path.write_text(source, encoding="utf-8", newline="\n")
        seed = subprocess.run([str(SEED), "run", str(path)], capture_output=True,
                              cwd=str(ROOT), check=False)
        seed_ok = seed.returncode == 0
        line = (f"fillers={count:3d} lines={nodes:4d} bytes={len(source):5d} "
                f"seed={'valid' if seed_ok else 'INVALID rc=' + str(seed.returncode)}")
        if not seed_ok:
            print(f"{line} SEED-REJECTED (ladder invalid at this rung)")
            break
        try:
            c_source = pep_c23.emit(source.encode("utf-8"))
        except Exception as err:  # noqa: BLE001
            text = str(err)
            code = next((c for c in ("PEP_RUNTIME_STEP_LIMIT", "PEP_PARSE_STEP_LIMIT",
                                     "PEP_TYPE_MISMATCH", "PEP_UNKNOWN_TYPE") if c in text), "?")
            marker = text.find("budget exceeded")
            detail = text[marker:marker + 26] if marker >= 0 else text[:80]
            print(f"{line} -> REFUSED {stage_of(text)} {code} :: {detail}")
            if first_failure is None:
                first_failure = count
            continue
        c_path = OUT / f"size_{count}.c"
        exe = OUT / f"size_{count}.exe"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        built = subprocess.run([str(pep_c23.compiler_path("clang")), "-std=c23", "-Wall",
                                "-Wextra", "-Wpedantic", "-Werror", "-O2", str(c_path),
                                "-o", str(exe)], capture_output=True, text=True,
                               check=False, cwd=str(ROOT))
        if built.returncode:
            print(f"{line} -> C-BUILD-FAIL {built.stderr.strip()[:90]}")
            if first_failure is None:
                first_failure = count
            continue
        done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
        out = done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
        print(f"{line} -> OK {len(c_source)}B native={out!r}")
    print(f"SUMMARY first_failing_filler_count={first_failure}")


if __name__ == "__main__":
    sys.exit(main())
