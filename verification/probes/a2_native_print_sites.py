"""Count the printf sites in the generated C for both programs (attribution of native stdout)."""
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO))
import pep_c23

PROGRAMS = {
    "canonical": ("fn answer() -> Int {\n    return 20 + 22\n}\n\n"
                  "fn main() -> Int {\n    return answer()\n}\n\n"
                  "say(int_text(main()))\n"),
    "in_body_say": 'fn main() -> Int {\n    say("in-main")\n    return 0\n}\n',
}

for name, source in PROGRAMS.items():
    c = pep_c23.emit(source.encode("utf-8"))
    prints = [line.strip() for line in c.splitlines()
              if 'printf("%lld' in line or "fputs(" in line and "PEP_RUNTIME" not in line]
    print(f"== {name}: {len(c)} bytes, {len(prints)} numeric/estring print sites ==")
    for line in prints:
        print("   ", line[:160])
    wrapper = [line.strip() for line in c.splitlines() if line.startswith("int main(")]
    after = c.split("int main(void) {")
    if len(after) > 1:
        print("    wrapper:", " ".join(after[1].splitlines()[:2])[:200])
