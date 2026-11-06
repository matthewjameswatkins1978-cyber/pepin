"""A native lexer fragment: the four checkable lexer functions, composed and running.

`probe_single_function_ceiling.py` showed the checker accepts a single function up to
293 bytes, and that the four lexer functions which fit are exactly the four that emit:
ascii_letter, ascii_digit, ascii_continue, advance_position.

Individually they are proven. This probe proves they COMPOSE: each is checked and
emitted in its own invocation (so the per-function ceiling is respected), the units
are assembled into one translation unit, and a driver scans a real file with them.

The driver loop is hand-written C -- the Pep functions are the native part, and the
loop is the substrate that a future `lexer_step` would replace. That boundary is
stated rather than hidden.

What it demonstrates: a native binary that reads a real Pep file and classifies its
bytes with the compiler's own lexer predicates, tracking line and column with the
compiler's own advance_position. That is a real (partial) native lexer, not a
synthetic feature probe.

Run: python tests/probe_native_lexer_fragment.py
"""
import importlib.util
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

BUILD = ROOT / "_build"
A1_SEED = BUILD / "a1_seed" / "pep.exe"
LEXER = ROOT / "examples" / "pep_lexer.pep"

# advance_position FIRST: it is the only unit that declares the SourcePosition record,
# so its preamble carries the `pep_record_0` typedef the other definitions need.
FUNCTIONS = ["advance_position", "ascii_letter", "ascii_digit", "ascii_continue"]

# The driver: scan the granted bytes, classify with the Pep predicates, track position
# with the Pep advance_position. Hand-written C, stated as such.
DRIVER = r"""
#include <stdio.h>
#include <stdlib.h>
#define main pep_program_main
#include "lexer_fragment.c"
#undef main
#if defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable: 4996)
#endif

int main(int argc, char **argv) {
  if (argc < 2) { fputs("PEP_RUNTIME_SOURCE_CONTEXT\n", stderr); return 1; }
  FILE *handle = fopen(argv[1], "rb");
  if (handle == NULL) { fputs("PEP_RUNTIME_SOURCE_OPEN\n", stderr); return 1; }
  if (fseek(handle, 0, SEEK_END) != 0) { return 1; }
  long size = ftell(handle);
  if (size < 0) { return 1; }
  if (fseek(handle, 0, SEEK_SET) != 0) { return 1; }
  unsigned char *data = (unsigned char *)malloc((size_t)size + 1u);
  if (data == NULL) { return 1; }
  if (size > 0 && fread(data, 1, (size_t)size, handle) != (size_t)size) { return 1; }
  (void)fclose(handle);

  int64_t line = 1, column = 1, offset = 0;
  int64_t identifiers = 0, digits = 0;
  while (offset < size) {
    int64_t byte = (int64_t)data[offset];
    if (pep_fn_ascii_continue(byte)) { identifiers += 1; }
    if (pep_fn_ascii_digit(byte)) { digits += 1; }
    pep_record_0 next = pep_fn_advance_position(line, column, byte);
    line = next.pep_field_0;
    column = next.pep_field_1;
    offset += 1;
  }
  printf("%lld %lld %lld %lld\n", (long long)identifiers, (long long)digits,
         (long long)line, (long long)column);
  free(data);
  return 0;
}
#if defined(_MSC_VER)
#pragma warning(pop)
#endif
"""


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def extract_function(text, name):
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(f"fn {name}("):
            start = index
            depth = 0
            opened = False
            while index < len(lines):
                depth += lines[index].count("{") - lines[index].count("}")
                if "{" in lines[index]:
                    opened = True
                index += 1
                if opened and depth == 0:
                    break
            return "\n".join(lines[start:index])
    raise SystemExit(f"function {name} not found")


def emit_unit(session, revision, source, label):
    """Check + emit one function as a whole program; return its C text."""
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    require(target, "outcome", "ok", f"open {label}")
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    parsed = parse_target(session, payload, target, revision)
    checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-checker",
                            "arguments": [parsed], "semanticTarget": semantic})
    require(checked, "outcome", "ok", f"check {label}")
    cfields = fields_map(checked["result"])
    if cfields["status"]["value"] != "valid":
        return None, f"check status={cfields['status']['value']}"
    emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-emitter",
                            "arguments": [parsed, checked["result"]],
                            "semanticTarget": semantic})
    require(emitted, "outcome", "ok", f"emit {label}")
    efields = fields_map(emitted["result"])
    if efields["status"]["value"] != "emitted":
        return None, f"emit status={efields['status']['value']} " \
                     f"{efields['diagnostic']['value'][:140]}"
    return "".join(p["value"] for p in efields["sourceParts"]["value"]), "emitted"


def main():
    if not A1_SEED.is_file():
        print("SKIP: no A1 seed exe at", A1_SEED)
        return 1
    lexer_text = LEXER.read_text(encoding="utf-8")
    failures = 0
    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")

        spec = importlib.util.spec_from_file_location(
            "pic", ROOT / "tests" / "probe_integration_case.py")
        pic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pic)
        pic.register(session, document, revision, sample["document"], sample["revision"])

        # Emit each function in its own invocation, so the per-function ceiling holds.
        # Each unit carries only the declarations and callees that function needs, or
        # the fixture would exceed the 293-byte per-function ceiling on its own.
        closure = importlib.util.spec_from_file_location(
            "pfc", ROOT / "tests" / "probe_function_closure.py")
        pfc = importlib.util.module_from_spec(closure)
        closure.loader.exec_module(pfc)
        declaration_text, all_functions = pfc.split_source(lexer_text)
        declarations = pfc.split_declarations(declaration_text)
        units = []
        for name in FUNCTIONS:
            block = extract_function(lexer_text, name)
            callees = pfc.needed_functions(all_functions, name, block)
            decls = pfc.needed_declarations(declarations, block + "\n" + callees)
            source = (decls + "\n" if decls else "") + callees + \
                ("\n" if callees else "") + block + "\nfn main() -> Int { return 0 }\n"
            csrc, detail = emit_unit(session, revision, source, f"frag-{name}")
            if not csrc:
                print(f"{name:18s} EMIT-REFUSED {detail}")
                failures += 1
                continue
            print(f"{name:18s} emitted ({len(csrc)} bytes of C)")
            units.append(csrc)
        if failures:
            return 1
    finally:
        session.close()

    # Assemble one translation unit. Each emitted unit is a WHOLE program: preamble +
    # declarations + the function + a `pep_fn_main` wrapper. So take the first unit up
    # to (not including) its `pep_fn_main`, then from each later unit take only its own
    # function definition, again stopping before `pep_fn_main`. The driver supplies the
    # real main.
    def body_of(unit, start_marker):
        """The DEFINITION of start_marker, not its prototype.

        A unit contains a prototype line ending in `;` and a definition line ending in
        `{`. Taking the first occurrence picks the prototype, which references types
        the first unit may not declare. Pick the line that opens a body.
        """
        offset = 0
        while True:
            index = unit.find(start_marker, offset)
            if index < 0:
                return None
            line_start = unit.rfind("\n", 0, index) + 1
            line_end = unit.find("\n", index)
            if line_end < 0:
                line_end = len(unit)
            if unit[line_start:line_end].rstrip().endswith("{"):
                end = unit.rfind("int64_t pep_fn_main")
                if end < 0 or end < line_start:
                    end = len(unit)
                return unit[line_start:end]
            offset = line_end

    # The FIRST unit keeps its whole preamble (includes, typedefs, runtime helpers) --
    # its first `pep_fn_` occurrence is a prototype, so start from byte 0 and cut only
    # at the main wrapper.
    # rfind, not find: `int64_t pep_fn_main` also appears as a PROTOTYPE before the
    # definitions, so the first occurrence would cut the definitions off.
    first_end = units[0].rfind("int64_t pep_fn_main")
    assembled = units[0] if first_end < 0 else units[0][:first_end]
    for name, extra in zip(FUNCTIONS[1:], units[1:]):
        piece = body_of(extra, f"pep_fn_{name}")
        if piece is None:
            print(f"assemble FAIL: no definition for {name}")
            return 1
        assembled += "\n" + piece

    c_path = BUILD / "lexer_fragment.c"
    c_path.write_text(assembled, encoding="utf-8", newline="\n")
    d_path = BUILD / "lexer_fragment_driver.c"
    d_path.write_text(DRIVER, encoding="utf-8", newline="\n")

    # A real Pep source file to scan.
    fixture = BUILD / "fragment_input.pep"
    fixture.write_text("fn main() -> Int { return 42 }\n", encoding="utf-8", newline="\n")
    payload = fixture.read_bytes()

    # Seed oracle: the same classification and position tracking, in Pep.
    #
    # It CANNOT use source_bytes(): the seed's `run` has no host grant and refuses with
    # PEP_RUNTIME_SOURCE_CONTEXT (that is the sourceGrant gap on issue #16, measured).
    # So the oracle iterates the SAME byte values as a literal Int list instead. Same
    # bytes, same predicates, same advance_position -- a different source for the bytes,
    # which is exactly the authority boundary that is still A1's to close.
    oracle_decls = pfc.needed_declarations(
        declarations, "".join(extract_function(lexer_text, name) for name in FUNCTIONS))
    byte_list = ", ".join(str(byte) for byte in payload)
    oracle = (oracle_decls + "\n" if oracle_decls else "") + \
        "".join(extract_function(lexer_text, name) + "\n" for name in FUNCTIONS)
    oracle += (
        f"let bytes = [{byte_list}]\n"
        "var line = 1\nvar column = 1\n"
        "var identifiers = 0\nvar digits = 0\n"
        "for byte in bytes {\n"
        "  if ascii_continue(byte) { identifiers = identifiers + 1 } else {}\n"
        "  if ascii_digit(byte) { digits = digits + 1 } else {}\n"
        "  let next = advance_position(line, column, byte)\n"
        "  line = next.line\n  column = next.column\n"
        "}\n"
        'say(int_text(identifiers))\n'
        'say(int_text(digits))\n'
        'say(int_text(line))\n'
        'say(int_text(column))\n')
    oracle_path = BUILD / "lexer_fragment_oracle.pep"
    oracle_path.write_text(oracle, encoding="utf-8", newline="\n")
    seed = subprocess.run([str(A1_SEED), "run", str(oracle_path)],
                          capture_output=True, check=False)
    if seed.returncode:
        print("seed-oracle FAIL", seed.stderr.decode("utf-8", "replace")[:200])
        return 1
    seed_out = seed.stdout.replace(b"\r\n", b"\n")
    expected = b" ".join(seed_out.split()) + b"\n"
    print(f"seed-oracle        OK {expected!r}")

    for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        exe = BUILD / f"lexer_fragment_{compiler_name}.exe"
        built = subprocess.run(
            [str(pep_c23.compiler_path(compiler_name)), *extra, "-Wall", "-Wextra",
             "-Wpedantic", "-Werror", "-O2", str(d_path), "-o", str(exe)],
            capture_output=True, text=True, check=False)
        if built.returncode:
            print(f"build-{compiler_name:8s}  FAIL exit={built.returncode} "
                  f"{built.stderr[:400]}")
            failures += 1
            continue
        ran = subprocess.run([str(exe), str(fixture)], capture_output=True, check=False)
        out = ran.stdout.replace(b"\r\n", b"\n")
        ok = ran.returncode == 0 and out == expected
        print(f"native-{compiler_name:7s}  {'OK' if ok else 'FAIL'} "
              f"seed={expected!r} native={out!r}")
        if not ok:
            failures += 1

    print("\nnative lexer fragment:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
