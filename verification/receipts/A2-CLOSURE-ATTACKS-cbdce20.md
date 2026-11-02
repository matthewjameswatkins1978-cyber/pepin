# A2 bounded emission slices 4–5 — independent verification at `cbdce20` (closure attacks + executed native parity)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Assignment:** three-agent job routing (#16, 20:09) — A3 item 2: rerun A2 bounded/sectional
work at `cbdce20` unchanged; challenge closure (self-referential union, forward
declarations, invalid prerequisites); distinguish executed native runs from skips.
**Target:** `codex/a2-bounded-emission` @ `cbdce205e318f618d5507d718c8394f82089e036`
(clean pinned worktree `D:\Projects\wt-a3-a2b-cbdce20`; chain `1f5b86b → eebd5cd → 09cd8f7 → cabe89d → cbdce20`).

## Pickup declaration (A3, this assignment)

Role: independent verification, read-only on builder lanes. Branch
`codex/bootstrap-agent3-verification`, HEAD `037014fb` at pickup (+this slice), owned
paths `verification/**` only. Dependency: A1 fix SHA for the unchanged pack replay
(`agent3-index-gates`, baseline `PROVEN=3`); none blocking my A2 work. Review counter:
slice 1/3 of this assignment.

## 1. Unchanged reruns A2 asked for

| run | result |
|---|---|
| `python -m unittest tests.test_c23_bounded_emission -v` | **8/8 OK, 7.81s, ZERO skips** — includes `test_prerequisite_closure_includes_nested_declaration` **and** `test_reassembled_unit_output_compiles_and_runs_under_clang_and_gcc` |
| `python tests\probe_c23_sections.py --sizes 2,4,8` ×2 | **`byte_identity: match` 6/6**; unit/all bands: N=2 **0.58–0.80**, N=4 **0.39–0.56**, N=8 **0.52–0.68** |

**Native parity — executed, not skipped (assignment requirement):** the Clang+GCC
compile-and-run test returned `ok` on my machine (both compilers present at the scoop
paths), i.e. the reassembled header+units+epilogue was compiled `-std=c23 … -Werror`,
run, and its stdout compared against the Pep interpreter — genuinely executed in my run.
Ratio bands at N=4 (0.39–0.56) sit below the `eebd5cd` bands — further movement toward
bounded; still wall-clock bands (1–5 ms), never claimed as O(1).

## 2. My probes, unchanged, at this SHA

- `per_unit_cost_baseline.py`: exit 0, **ratio 0.67**, `byte_identity=True` (series: 0.98 baseline `c70d5eb` → 0.63–0.74 `eebd5cd` → **0.67** here; all bands).
- `bounded_emitter_attacks.py`: **O1 flipped — `inner_in_prereqs: true`** (prereqs `[Outer=3, Inner=0]`) → **closure independently confirmed**, exactly the gap I pinned at `eebd5cd`.
- **Disclosure (my oracle, not A2's defect):** the first run at `cbdce20` showed `CT3 … claim_falsified=1` — because my bidirectional invariant (`prereq ⊆ text`) was written for *direct-only* facts and the closure now *correctly* makes prereqs exceed the unit's own text. Corrected to one-way **provenance soundness** (`text ⊆ prereq`: every record tag the unit emits must be supplied) via Threadmoth (2 certified edits, docstring updated), rerun → **exit 0, `claim_falsified=0`**.

## 3. The three closure attacks A2 asked for — `verification/probes/prereq_closure_attacks.py`

Final run: **exit 0, `SUMMARY cases=8 claim_falsified=0`** (4 claims + 4 stage-map observations).

| case | result |
|---|---|
| **CL1 self-referential union** (`type Expr = Number(Int) \| Add(Expr, Expr)`) | **HELD** — checker-valid; unit `emitted` with prereqs **`[Expr]` exactly** (self-reference deduplicated; kind `union_declaration`); whole emission also `emitted`. **This is the fixture A2 said they lack — termination demonstrated, not just argued.** |
| **CL2 mutually recursive unions** (`Ping`↔`Pong`) | **HELD** — checker-valid (mutual recursion accepted); unit **`emitted` with prereqs `[Ping, Pong]` exactly** (closure terminates, both, no dupes); **whole-program emission refuses**: `unsupported — "Pep C23 tagged union has an unsupported layout"` (fail-closed at whole level; recorded as observation — a chunked caller sees correct unit facts and meets the refusal when assembling the whole) |
| **CL3 type declared after use, inside the closure chain** (`take` before `Outer`, `Outer` before `Inner`) | **HELD** — unit `emitted` with prereqs **`[Outer=8, Inner=11]` both** (Inner never silently omitted — the "refuse, not omitted" contract held *and* the complete set arrived). Whole refuses with `"record fields require Int, Bool, or a preceding record declaration"` — the declaration-**order** constraint (C needs the field's struct complete first), accurate message; observation only |
| **CL4 declaration whose field references an undeclared name** (`Outer { i: Nope }`) | **HELD** — refused at the **checker** (`PEP_UNKNOWN_TYPE: Unknown type 'Nope'`); closure never reached, nothing omitted |

**Disclosures:** my first CL2 fixture was buggy (`take(WrapQ(WrapP(1)))` → `Expected Pong but found Int` was *my* type error, not the compiler's) — fixed by dropping the construction; the original falsification is reclassified by the corrected fixture and claim framing (both edits Threadmoth-certified, visible in the probe file).

## 4. Not executed / out of scope this slice

- `tests.test_a14_c23` not re-run at this SHA (its 2-failure stale pair was verified at `05add76`; A2 reproduced the same pair in a `c70d5eb` control — their statement accepted as consistent with my independent earlier pin, not re-measured here).
- Job item 1 (unchanged pack replay) **awaits A1's fix SHA** — A1 still at `05add76` at this slice boundary; baseline `PROVEN=3` armed.
- Job item 3 (integrated discriminating case) — no A1/A2 pinned integrated candidate exists yet.

## Honest scope

Pure checker/session emit layer + executed native compile/run via A2's own test (no
builder files touched; `verification/**` only). Bands not points for wall-clock. Verdict
labels: probes exit 0 = claims held at this commit; `PROVEN`/`NOT OBSERVED` semantics
per receipt layers. All probe edits this slice: 4 Threadmoth-certified mutations
(`unrelated_bytes_changed=false`, `lf→lf`, budget PASS).

## Reproduction

```powershell
git worktree add --detach <wt> cbdce20
python -m unittest tests.test_c23_bounded_emission -v                 # 8/8, 0 skips
python tests\probe_c23_sections.py --sizes 2,4,8                      # byte_identity match
python verification\probes\bounded_emitter_attacks.py <wt>            # exit 0
python verification\probes\prereq_closure_attacks.py <wt>             # exit 0, 8/0
python verification\probes\per_unit_cost_baseline.py <wt>             # ratio ~0.67
```
