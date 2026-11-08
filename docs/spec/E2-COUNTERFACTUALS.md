# E2 — Counterfactual Minimal Architectures, with Falsifiers

**Programme:** PEP-A4-RESEARCH-E-20261104, Phase I slice 2 of 3. Builds on E1
(E1-CLOSURE-MAP) + B2/B3 evidence below. No implementation changed, no probes
run. Labels: ESTABLISHED / INFERRED / UNKNOWN. Nothing here removes anything
from accepted Pep 1.0 — all routes keep the full language as a later stage.

## 0. B2/B3 evidence (ESTABLISHED by source-read at seed `57fe424`)

- **B2 — staged composition EXISTS:** the parser consumes the staged lexer
  directly (`lexer_step` inside `examples/pep_parser.pep`; `ParserStream`
  carries `lexCursor`), and `emit_c23()` in the emitter composes
  `parser_parse_program → analyze_parsed → emit_c23_checked` in one staged
  program. Host-side, `pep_c23.py` bundles all four sources into one session
  `open` and invokes parser/checker through the v2 tool protocol. Full chain
  lexer→parser→checker→emitter is real composed Pep code, not a diagram.
- **B3 — emitter subset tabulated:** types Int→int64_t, Bool→_Bool ONLY (no
  Str/records/unions/lists); 0–2 scalar params; bodies = immutable lets + one
  return, or lets + one final if with direct returns; expressions =
  literals, names, calls (known target, ≤2 args, call-free body, two-fallible
  rejection for C order), if-expressions, `+ - * /` via checked helpers
  (`pep_add/sub/mul/div`, overflow+div0 traps), comparisons, `&& ||`, `!`,
  unary `-`; everything else → `pep_c23_unsupported` (fail-closed). Runtime
  prelude mirrors seed limits (call depth 512). Authority gate on
  document/revision/node-count precedes emission.

## 1. Route (a) — Bootstrap only the compiler-used subset; full Pep later

**Shape:** stage-0 implements and checks ONLY what compiler A uses on itself:
records + `List[T]` + one AST union + first-order fns + match/for/while/var +
the 12 builtins (E1 §3–§4). Holes, tool registry, session ops, `SourceBytes`
authority beyond lexing, and Str-heavy semantics remain accepted language but
are not in the bootstrap stage. The staged checker gains a declared subset
flag; anything outside it is a clean `unsupported`, as the emitter already does.
**Cost comparison (INFERRED):** trusted-code win is in CHECKER RULES (hole
facts, tool validation, Str-shape rules — uncounted, likely a minority of the
103 checker fns), NOT in the interpreter, which must still implement the whole
subset runtime (records, lists, strings, match, loops). Native runtime
unchanged (Clang/GCC already subset-agnostic). A→B→C reproducibility IMPROVES
(smaller stage-0 surface to re-verify); diagnostics parity must be preserved
byte-for-byte on the subset. Maintenance: two subset definitions to keep in
sync (stage-0 + staged flag) — a new sync obligation.
**Falsifier F-A (quantitative, smallest):** count staged-checker lines serving
features compiler A never invokes on its own bundled sources
(hole/tool/`say`/Str-shape paths). If that fraction is <10% of the 2258-line
checker, route (a) saves review surface but no meaningful trust or step cost —
NOT WORTH IT. Measurement needs one instrumented run, not an essay.

## 2. Route (b) — One authoritative semantic checkpoint, no re-derivation

**Shape:** the checker emits ONE annotated tree (stable node identities,
bindings resolved inline, revision stamped once); the emitter consumes it
directly. Kills per-boundary re-walks: scope re-derivation, `BindingPool`
renumbering (`2000000` vs `3000000` id families), repeat admission guards, and
the `emit_c23_checked` node-count reconciliation.
**Cost comparison (INFERRED):** removes the exact machinery that produced the
O1c/A1b aliasing class (renumbering pooled facts) — ESTABLISHED evidence FOR
(b): those bugs cannot exist if identities are never re-minted. Against (b):
the 66-node gate cost (A3: 62/64 row) lives INSIDE analysis, not at seams —
unifying representations does not move the gate. Source-revision stamping gets
simpler (one stamp, not three); A→B→C replay gets stricter (checkpoint bytes
are part of the build artifact). Maintenance: one schema to version instead of
three fact families — but every consumer must upgrade in lockstep.
**Falsifier F-B (smallest program):** a two-chunk program where seam-guard +
renumbering cost is measured against total check steps (A3's harness can emit
this). If seam machinery is <5% of the 66-node row cost, (b) is a purity win
with no performance case — ADOPT ONLY for the bug class, not for speed. If a
single counterexample shows two stages disagreeing on one stable identity,
(b) is NECESSARY regardless of cost. (Matthew's priority — "one
compiler-derived semantic/checkpoint model" — points here; the question is
whether it rides the bug-class argument or the cost argument. F-B decides.)

## 3. Route (c) — Demote builtins to Pep library code where semantics match

**Shape:** re-express selected stage-0 builtins as ordinary Pep over a smaller
native core — e.g. `utf8_slice`/`byte_slice` as loops over `byte_at`;
`int_text` as digit arithmetic; `contains`/`reverse` as recursion. Candidate
core: `byte_at`, `length`, `source_bytes`, control flow, arithmetic (~4–5
primitives instead of 12).
**Cost comparison (INFERRED):** trusted native surface shrinks by half; every
demoted builtin pays staged-step cost on EVERY use — including inside the
compiler's own hot paths (the checker leans on `length/append/prepend/
contains`; the lexer leans on byte builtins). Interpreter step budget is 1M,
tool runtime 100k; the compiler's own sources are the largest inputs the
interpreter ever runs. UTF-8 boundary logic in Pep risks SUBTLE divergence
from the seed's byte-table version — the exact class of bug staged checking
exists to catch. A→B→C reproducibility: library code is revision-stamped like
any source (good); but the library becomes load-bearing for stage-0 itself
(bootstrap circularity must be staged carefully).
**Falsifier F-C (smallest program):** write `utf8_check`-equivalent slicing
purely over `byte_at` and run it on a fixed 1 KiB input both ways; compare
step counts and span outputs. If the library version exceeds ~10× steps of the
builtin OR any span diverges, (c) is REFUTED for byte builtins — keep them
native. `int_text` is the softest target (pure arithmetic, no boundary
subtlety); try that one first if any.

## 4. Standing constraints reused (not re-argued)

B4-R3 (no PKI/second resolver), B4-C4 single namespace, E1 transport cap
(65536) and `trustedLocal/sandboxed:false` bound all three routes. E3 verdict
must respect Matthew's binding priorities: semantic/checkpoint model, Pep
standard library, Road 1 closure — route (b) aligns with the first, route (c)
with the second, route (a) with neither directly.

## 5. Status labels

PROPOSAL space only: three routes + three falsifiers, no recommendation (that
is E3). F-A/F-B/F-C are all executable with existing harnesses (A3 steps, A1
checker, A2 emitter); none requires new infrastructure. Next: E3 — run or
specify the cheapest discriminating measurement, ask practitioners 2–5
questions, deliver the one-page verdict.
