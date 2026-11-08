# A3 verification status — index and handoff

**Purpose.** This lane has produced 273 receipts and ~90 probes across several missions. This file is the entry point: what is
verified *now*, by what method, at which pin, and what is not. Historical receipts remain authoritative for their own pins; this
index tells a successor where to look and what not to re-derive.

**Re-run everything in one command:**

```
PEPIN_SEED_ROOT=<worktree with built seed> PEPIN_A1_ROOT=<A1 worktree> PEPIN_A2_ROOT=<A2 worktree> \
  python verification/run_gates.py
```

Seven gates, all green at the pins below. It reports `PARTIAL` (never "green") when any gate is skipped.

## Live pins

| lane | SHA | note |
|---|---|---|
| A1 `codex/a1-typed-bound-pipeline` | `07af079d` | sectional host; bindings carry landed |
| A2 `codex/a2-divergence-spike` | `e07e278f` | emitter; assignment-path fix + str_contains fix landed |
| A4 `spec/agent4-spec-lab` | `e0272977` | `compiler_a.pep` blob **`ca732536`**, unchanged since `5f62e4b` |
| A3 `codex/bootstrap-agent3-verification` | `41b796d9` | this lane |
| campaign base | `bddd3542` | reference for "before" comparisons |

**Two seed blobs are in play and their builtin sets differ by exactly one name.** `f8f476198f` (146,713 B, A1 pipeline + A2) knows
`str_concat`; `c92f9cc4a3` (143,092 B, campaign base + A1 ledger + A4) does not. **Every claim below names its seed.** A receipt
that says "verified against the seed" without a blob is ambiguous — see `FINDING-BOOT-A3-110`.

## What is verified

| claim | method | evidence |
|---|---|---|
| A2's `prepend+reverse` lowerings are semantics-preserving | emitted C byte-identical to `1885566` (`7D4AE57B…`, `B234213E…`, `5215C9F6…`) | A3-078 |
| A2's assignment-path fix is correct and was needed | `calls require a known target` refusals converted to bindings refusals exactly as predicted | A3-123, A3-127 |
| A2's `str_contains` skip-list defect is fixed | union variant named `str_contains` now emits its constructor | A3-134, A3-136 |
| A1's bindings merge works | 13 rank-space bindings, `21/21` chain CHECK, `main` reaches **30/31** fragments | A3-135, A3-133 |
| Fragment contract composes at scale | 19 of 21 functions compile and link from units + fragments | A3-138 |
| Fragment bodies compute correctly | 19 functions executed; `is_ws`/`is_digit` exhaustive against the seed, 17 against source-derived expectations | A3-139–143 |
| Emission is deterministic and stateless | identical across fresh seed processes; identical under forward/reverse/shuffled fragment order | A3-144 |
| Both semantic oracles reproduce | A4's 13 pins + 17 boundary probes; A1's 23-case span-exact oracle | A3-086/088/094 |
| A4's own-source census is exact | 189/189 table cells; totals reconcile 1343 + 44 + 65 = 1452 | A3-087, A3-092 |
| M-1 gate is calibrated | Python stubs **and** a native compiled binary; partial implementations score partially | A3-081, A3-132 |
| **M-1 passes on a modelled build** | full gate 15/15, three fixes modelled in other lanes | A3-150 |
| **A1's parser guard is output-neutral** | d_a/d_b/d_c byte-identical, 7 gates green | A3-152 |
| **Gate is narrower than the contract** | 7 of 9 class-(ii) shapes misclassified, exit 1/2/3 not 5 | A3-153 |
| **build_c23 has no fragment path** | refuses `PEP_RUNTIME_STEP_LIMIT` on the M-1 source | A3-151 |

## What is NOT verified — the honest gaps

1. **The tracked tree has no compiler A yet, but one has been built and it passes M-1.** A complete Pep-authored compiler A
   assembled from all 21 functions (10 whole units + 11 fragment-assembled, zero refusals) **passes `verify_m1_081.py` 15/15** -
   all thirteen pinned oracle cases plus both unseen forms, correct exit codes and stdout, linking under clang and gcc. It needs
   **three modelled fixes in two other lanes**: A4 emitting punctuation as literals rather than `int_text` codes, and an epilogue
   that neither echoes `main`'s return nor hardcodes `exit 0`. See A3-150. **No M-1 claim is made for the tracked tree** until
   those land, and A1's `build_c23` still cannot produce the build at all - it has no fragment path (A3-151).
2. **`find_brace` loses 3 statements, not 7.** The lever was never an emitter optimisation or a `parentId` index — it is the
   size of the node list the host passes. Narrowing per fragment to *function node + parameter subtrees + var/let declaration
   subtrees + target statement* makes **`main` emit 31/31** (#23 at 61,572 steps on 85 nodes instead of 100,001 on 222) and
   `find_brace` 21/24. The three remaining are **5-conjunct `&&` conditions**, while 2- and 3-conjunct ones in the same
   function emit at 25,126 and 36,634 steps — exactly the limit A4's `EXPECTED.md` predicted, whose stated remedy is to
   split long conjunctions. See A3-146, A3-147. **A3-131's 'only the index can help' and A3-137's recommendation are
   superseded**; note Pep has no list indexing, so an index may be inexpressible anyway.
3. **The child-lookup early exit is correct but cannot help a late statement.** Zero differences across 63,954 queries, but it
   only fires for early-positioned parents: −18,131 steps for an early statement, **+11,149** for a late one. See A3-126, A3-135.
4. **19 of 21 functions have only a source-derived oracle.** The seed cannot execute them because `source_bytes()` is host-gated
   in run mode (`PEP_RUNTIME_SOURCE_CONTEXT`). This is the input-access wall (A3-073/074) reaching into verification: it bounds
   how exhaustively the compiler can be checked, not just what it can do.
5. **Whole-function emission is impossible for 11 of 21 functions** — they are step-limited as units and only work when
   fragmented. `main`/`find_brace` excepted, all currently succeed by that route.

## Standing cautions for the next verifier

- **Mixed lanes are not an integration.** Most measurements here drive A1's host against A2's emitter. Both are unmodified, but
  they are not merged. Re-measure on the candidate tree.
- **Three id spaces coexist.** A1's merge emits facts in *rank* space (0..221 for `main`), `remap_chunk` renumbers *0..n−1 by
  position*, and document ids are 1230–1451. Feeding document-id nodes to rank-space facts produces 5 spurious refusals — A3-116
  published that as an emitter gap and A3-117 retracted it.
- **Optimisations keep narrowing correctness silently.** Three so far: arithmetic `may_fail` (A3-078), node-count guard removal
  (A3-118), name-based skip (A3-134). The habit that catches all three: *when an optimisation skips work because of a name or
  shape, test that the language cannot produce that name or shape.*
- **Some of this lane's own conclusions were wrong and are retracted.** A3-061, A3-069, A3-070, A3-083 phrasing, A3-104 scope,
  A3-116, A3-126 magnitudes. Read the correction, not the original.
- **Instrument defects are the main risk.** Eight found so far, all in this lane's harness rather than the code under audit —
  including a PowerShell loop that gave five identical rows from stale variables (A3-110) and `metrics.last_execute_steps` being
  treated as cumulative when it is per-invocation (A3-099). Prefer generating and building over reasoning about what should work.

## Instrument quick reference

| need | probe |
|---|---|
| whole lane | `run_gates.py` |
| emit/execute an app, per-function status, native build+run | `emit_any_049.py` (`PEPIN_GATE_ROOT`, `PEPIN_APP_REL/REV`, `PEPIN_UNITS_ONLY=1`, `PEPIN_STEPS=1`) |
| M-1 acceptance | `verify_m1_081.py --compiler-cmd '["<exe>"]'`, `--selftest` |
| seed vs emitted expression semantics | `seed_differential_106.py` |
| step cost per function / per fragment | `step_cost_099.py`, `emit_any_049.py` with `PEPIN_STEPS=1` |
| A1 sectional merge fail-closed | `sectional_negatives_080.py` |
| A4 oracle, boundary, A1 oracle replay | `pep0_oracle_079.py`, `pep0_boundary_088.py`, `pep0_a1_oracle_093.py` |
| DIVERGENCE-2 input-dependent C | `divergence_2_042.py` |

## Next action for whoever picks this up

Re-run `run_gates.py`, then the 21-function sweep and the execution harness, once A2's `parentId` index lands. When `find_brace`
and `main` both assemble, build the full compiler A and run `verify_m1_081.py` against it — that is the first moment an M-1 claim
becomes possible.