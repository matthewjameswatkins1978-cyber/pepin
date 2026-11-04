"""H-V5c: A4's chosen next vertical -- `known_builtin` @ A1 2ad750b:148-150, verbatim.

A4's H2 flags Str `==` lowering as "the plan's single riskiest assumption". This probe measures
it: the real 13-way `||` chain over Str equality, plus a name matrix of all 13 builtins, a
near-miss, an empty name and a case variant.

  seed   : top-level `say(int_text(known_builtin(x)))` per vector (the oracle)
  native : Clang + GCC, `main` returns a bitmask of the vectors it tested (no say(int_text))

Usage: python known_builtin_real.py <a2-tree-with-a1_seed>
"""
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-hv5"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402

SEED = ROOT / "_build" / "a1_seed" / "pep.exe"

# VERBATIM tests/pep_checker_a13.pep:148-150 @ 2ad750b
REAL_FN = (
    'fn known_builtin(name: Str) -> Bool {\n'
    '  return name == "say" || name == "int_text" || name == "length" || name == "append" || '
    'name == "prepend" || name == "reverse" || name == "source_bytes" || name == "byte_length" '
    '|| name == "byte_at" || name == "byte_slice" || name == "utf8_slice" || '
    'name == "contains" || name == "str_concat"\n'
    '}\n')

NAMES = ["say", "int_text", "length", "append", "prepend", "reverse", "source_bytes",
         "byte_length", "byte_at", "byte_slice", "utf8_slice", "contains", "str_concat"]
VECTORS = NAMES + ["nope", "", "Say", "str_conca", "length "]


def seed_program():
    lines = "".join(f'say(int_text_of(known_builtin("{name}")));\n' for name in VECTORS)
    # int_text on a Bool is not the emitter's surface; the seed can print via if-expression.
    lines = "".join(
        f'let r{index} = if known_builtin("{name}") {{ 1 }} else {{ 0 }};\n'
        f'say(int_text(r{index}));\n'
        for index, name in enumerate(VECTORS))
    return REAL_FN + lines


def native_program():
    lines = "".join(
        f'  let r{index} = if known_builtin("{name}") {{ 1 }} else {{ 0 }}\n'
        for index, name in enumerate(VECTORS))
    terms = " + ".join([f"r{index} * {2 ** index}" for index in range(len(VECTORS))])
    return REAL_FN + 'fn main() -> Int {\n' + lines + f'  return {terms}\n}}\n'


def main():
    print(f"REAL_FN_SHA256 {hashlib.sha256(REAL_FN.encode()).hexdigest()}")
    checkout = pathlib.Path("D:/Projects/wt-a3-gate/_build/chk-2ad750b.pep")
    if checkout.exists():
        lines = checkout.read_text(encoding="utf-8").split("\n")
        extracted = "\n".join(lines[147:150]) + "\n"
        print(f"CHECKOUT_SLICE_SHA256 {hashlib.sha256(extracted.encode()).hexdigest()} "
              f"match={extracted == REAL_FN}")
    path = OUT / "kb_seed.pep"
    path.write_text(seed_program(), encoding="utf-8", newline="\n")
    seed = subprocess.run([str(SEED), "run", str(path)], capture_output=True,
                          cwd=str(ROOT), check=False)
    seed_out = seed.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
    expected = "".join("1" if name in NAMES else "0" for name in VECTORS)
    print(f"SEED rc={seed.returncode} bits={seed_out.replace(chr(10), '')} "
          f"expected={expected} match={seed_out.replace(chr(10), '') == expected}")
    if seed.returncode != 0:
        print("SEED-FAIL", seed.stderr.decode("utf-8", "replace")[:300])
        return 2
    try:
        c_source = pep_c23.emit(native_program().encode("utf-8"))
    except Exception as err:  # noqa: BLE001
        text = str(err)
        code = next((c for c in ("PEP_RUNTIME_STEP_LIMIT", "PEP_PARSE_STEP_LIMIT",
                                 "PEP_TYPE_MISMATCH", "PEP_UNKNOWN_TYPE") if c in text), "?")
        stage = ("CHECKER" if "check parsed source" in text
                 else "EMITTER" if "emit checked source" in text else "OTHER")
        print(f"NATIVE REFUSED {stage} {code} :: {text[:140]}")
        return 0
    print(f"NATIVE EMITTED {len(c_source)}B")
    want = int(expected[::-1], 2)
    c_path = OUT / "kb.c"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    for compiler in ("clang", "gcc"):
        exe = OUT / f"kb_{compiler}.exe"
        built = subprocess.run([str(pep_c23.compiler_path(compiler)), "-std=c23", "-Wall",
                                "-Wextra", "-Wpedantic", "-Werror", "-O2", str(c_path),
                                "-o", str(exe)], capture_output=True, text=True,
                               check=False, cwd=str(ROOT))
        if built.returncode:
            print(f"{compiler.upper()} BUILD-FAIL {built.stderr.strip()[:120]}")
            continue
        done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
        # Epilogue prints pep_fn_main(); the value is stdout, not the exit status.
        got = done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
        print(f"{compiler.upper()} value={got!r} expected={want} "
              f"{'PARITY' if got == str(want) else 'MISMATCH'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
