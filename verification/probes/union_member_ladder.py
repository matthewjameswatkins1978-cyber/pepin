"""A3-023: union-member structural ladder for the Pep-written parser (packet fallback item).

Packet fallback (A3): "Measure one real parser >25-union-member failure plus a negative
malformed variant source as A1's first structural parser test; retain source size, tool
steps and exact parser stage."

Two independent observations per rung, deliberately kept apart:
  seed      OCaml 5.5.2 semantic authority: `pep.ps1 check` verdict + codes
  pepParser the Pep-written parser driven through the JSONL session by pep_c23.parse_target
            (one `pep-c23-parser-step` per source byte): complete AST, or the exact stage
            that refused
A rung where the seed is `valid` but the Pep parser cannot produce a complete AST is a
bootstrap gap, not a language defect -- the distinction is the point of the table.

Usage: python union_member_ladder.py <candidate-worktree>
Exit codes: 0 = ladder completed (any outcome), 2 = harness error.
"""
import pathlib
import sys
import time

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("staged_typed_attacks",
                                              HERE / "staged_typed_attacks.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

# First pass measured 5/15 complete and 25/26/30 refused, so the ceiling sits in
# between: the ladder bisects that interval instead of assuming the >25 boundary.
RUNG_ARMS = (5, 15, 16, 18, 19, 20, 22, 24, 25, 30)
MALFORMED_ARMS = 5


def union_source(arms):
    """A union with `arms` variants, a match with `arms` arms, and a main.

    Arm bodies are plain expressions: the seed's arm grammar is `pat => expr`
    (a `{ return ... }` block per arm is PEP_PARSE_EXPRESSION -- measured, first
    ladder shape was wrong for that reason, not for a union-size reason).
    """
    variants = " | ".join(f"V{i}(Int)" for i in range(arms))
    arm_text = " ".join(f"V{i}(x) => x" for i in range(arms))
    return (f"type Expr = {variants}\n\n"
            f"fn describe(value: Expr) -> Int {{\n    return match value {{ {arm_text} }}\n}}\n\n"
            f"fn main() -> Int {{\n    return describe(V0(1))\n}}\n")


def malformed_source(arms):
    """Same shape, one variant missing its payload type -> a structural negative."""
    variants = " | ".join(f"V{i}(Int)" for i in range(arms - 1)) + " | Vlast("
    return (f"type Expr = {variants}\n\n"
            f"fn main() -> Int {{\n    return 0\n}}\n")


def seed_probe(source):
    verdict = base.seed_verdict(source.encode("utf-8"))
    return verdict


def parser_probe(harness, source, name):
    started = time.perf_counter()
    try:
        sem, parsed = harness.prepare(source, name)
    except Exception as error:  # noqa: BLE001 - the stage label is the evidence
        text = str(error)
        code = ""
        if "'code': '" in text:
            code = text.split("'code': '")[1].split("'")[0]
        return f"REFUSED@{time.perf_counter() - started:.1f}s code={code or 'none'} {text[:150]}"
    nodes = len(base.fields_map(parsed)["nodes"]["value"])
    return f"complete: {nodes} nodes in {time.perf_counter() - started:.1f}s"


def main():
    print(f"REPO={REPO}")
    harness = base.Harness()
    rows = []
    try:
        for arms in RUNG_ARMS:
            source = union_source(arms)
            seed = seed_probe(source)
            pep = parser_probe(harness, source, f"union-{arms}")
            row = {"arms": arms, "bytes": len(source.encode("utf-8")),
                   "seed": seed, "pep_parser": pep}
            rows.append(row)
            print(f"arms={arms:<3} bytes={row['bytes']:<5} seed={seed:<30} pep={pep}")

        malformed = malformed_source(MALFORMED_ARMS)
        seed = seed_probe(malformed)
        pep = parser_probe(harness, malformed, "union-malformed")
        rows.append({"arms": f"{RUNG_ARMS[-1]}-malformed",
                     "bytes": len(malformed.encode("utf-8")), "seed": seed,
                     "pep_parser": pep})
        print(f"malformed   bytes={rows[-1]['bytes']:<5} seed={seed:<30} pep={pep}")
        # A 0-node parse is not a syntax oracle: the checker's parse-progress path is what
        # refuses the malformed source. Measure it here so the claim is in the driver.
        try:
            sem_m, parsed_m = harness.prepare(malformed, "union-malformed-check")
            nodes = base.fields_map(parsed_m)["nodes"]["value"]
            ids = [int(base.nval(node, "id")) for node in nodes]
            raw = harness.analyze_typed(harness.sliced(parsed_m, ids),
                                        {"type": "List[CheckedFunction]", "value": []},
                                        {"type": "List[ResolvedSignature]", "value": []},
                                        {"type": "List[ResolvedTypeDecl]", "value": []}, sem_m)
            print(f"  parsed nodes={len(nodes)} checker={raw['status']} {raw['diagnostics']}")
        except Exception as error:  # noqa: BLE001
            print(f"  malformed checker probe refused: {error}")
    finally:
        harness.close()

    print()
    for row in rows:
        print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
