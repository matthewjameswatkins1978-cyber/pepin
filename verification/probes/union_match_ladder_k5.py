"""Campaign K / A3 K5: checker/emitter ceiling on a structurally DIFFERENT shape (union + match).

H-V4 measured a Str guard-chain cliff (408 B ok -> 454 B refused) and an Int guard-chain ceiling.
This probe deliberately uses a different structure so the result is not a restatement of the
66-node fixture or of the guard ladder: a recursive-ish tagged union with a `match` whose arm
count grows per rung.

Rungs grow the ARM COUNT (and the union's variant count) from 2 to 8. Each rung reports:
  seed validity + value (the oracle), then the pipeline stage and code at refusal.
Stages: CHECKER / EMITTER / UNSUPPORTED / C-BUILD / OK.

Usage: python union_match_ladder_k5.py <a2-or-a1-tree-with-seed>
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-k5"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402


def program(arms):
    """Union with `arms` variants, a match with `arms` arms, and a main constructing the last."""
    variants = " | ".join(f"V{i}(Int)" for i in range(arms))
    body = "\n".join(f"    V{i}(n) => n + {i}" for i in range(arms))
    return (f"type Expr = {variants}\n"
            "fn evaluate(e: Expr) -> Int {\n"
            "  return match e {\n"
            f"{body}\n"
            "  }\n"
            "}\n"
            "fn main() -> Int {\n"
            f"  return evaluate(V{arms - 1}(41))\n"
            "}\n")


def seed(source, stem):
    path = OUT / f"{stem}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    done = subprocess.run(["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
                           "check", str(path), "--json"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(ROOT), check=False)
    try:
        payload = json.loads(done.stdout.strip())
        return payload.get("status"), [d.get("code") for d in payload.get("diagnostics") or []]
    except ValueError:
        return "NON-JSON", []


def stage_of(text):
    for marker, stage in (("check parsed source", "CHECKER"),
                          ("emit checked source", "EMITTER")):
        if marker in text:
            return stage
    return "EMITTER?"


def main():
    print(f"TREE {ROOT}")
    rows = []
    for arms in (2, 3, 4, 6, 8):
        source = program(arms)
        status, codes = seed(source, f"u{arms}")
        line = f"arms={arms} bytes={len(source):4d} seed={status}"
        if status != "valid":
            print(f"{line} codes={codes}  (ladder would be invalid: stop)")
            break
        try:
            c_source = pep_c23.emit(source.encode("utf-8"))
        except Exception as err:  # noqa: BLE001
            text = str(err)
            code = next((c for c in ("PEP_RUNTIME_STEP_LIMIT", "PEP_PARSE_STEP_LIMIT",
                                     "PEP_TYPE_MISMATCH", "PEP_UNKNOWN_TYPE") if c in text), "?")
            marker = text.find("budget exceeded")
            detail = text[marker:marker + 26] if marker >= 0 else text[:110]
            print(f"{line} -> REFUSED {stage_of(text)} {code} :: {detail}")
            rows.append((arms, "REFUSED", code))
            continue
        c_path = OUT / f"u{arms}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        exe = OUT / f"u{arms}.exe"
        built = subprocess.run([str(pep_c23.compiler_path("clang")), "-std=c23", "-Wall",
                                "-Wextra", "-Wpedantic", "-Werror", "-O2", str(c_path),
                                "-o", str(exe)], capture_output=True, text=True,
                               check=False, cwd=str(ROOT))
        if built.returncode:
            first = next((ln for ln in built.stderr.split("\n") if "error" in ln.lower()), "")
            print(f"{line} -> EMITTED {len(c_source)}B but C-BUILD refused: {first.strip()[:110]}")
            rows.append((arms, "C-BUILD", "?"))
            continue
        done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
        out = done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
        print(f"{line} -> OK {len(c_source)}B native={out!r}")
        rows.append((arms, "OK", ""))
    print(f"SUMMARY {rows}")


if __name__ == "__main__":
    sys.exit(main())

