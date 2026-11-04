# G-A4-3 (E9) — Comparative Minimal Compiler Prior Art (source-backed)

**Campaign G, Agent 4 card 3.** Three systems with inspectable primary
sources (existence ESTABLISHED by web lookup this slice; internals from
documented structure, labeled INFERRED where not line-read). No rewrite
mandate; one transferable technique each, one falsifiable trial each.

## 1. chibicc (rui314/chibicc, MIT) — phase discipline in C

**Source shape (ESTABLISHED):** `tokenize.c / parse.c / codegen.c / main.c` +
`tests/`, single-header `chibicc.h`
([raw `chibicc.h`](https://raw.githubusercontent.com/rui314/chibicc/main/chibicc.h),
verified this slice). ~C11 subset, self-hosting-capable.
**Minimum trusted semantic logic:** tokenizer → recursive-descent parser →
x64 codegen, one process, no IR beyond the C AST; type checking is thin
(C's weak types demand little). **Native/runtime deps:** a C library +
assembler + linker (outsourced, like Pep's Clang reliance — E4-T4).
**AST:** heap C structs, single ownership, freed per compilation — no
revision identity. CORRECTION (2026-11-04, read `chibicc.h` this slice):
tokens DO carry source location (`Token.loc` pointer + `len`, plus
`file`/`filename`/`line_no`), `Node.tok`/`Obj.tok`/`Member.tok` retain
representative tokens, and `error_at`/`error_tok` report them — so "no spans"
overstated the difference. What Pep has that chibicc does not: byte-exact
span CONTRACTS tied to machine-checked diagnostic codes (A3 CD1: code+span
required), revision identity, and cross-chunk span preservation.
**Validation:** `tests/` shell-driven; reproducibility =
deterministic single-pass output.
**What does NOT transfer to Pep:** untyped memory model (Pep's value
semantics + typed holes forbid the casual casts chibicc leans on); no
source-revision concept anywhere; chibicc's line-oriented diagnostics are
not a substitute for Pep's byte-span oracle contract (compare A3 CD1:
code+span required).
**Transferable technique → `tests/pep_c23_emitter.pep`:** chibicc's
*refuse-early-per-phase* discipline — each phase rejects what it cannot
represent before the next phase runs (no half-lowered state crosses a
boundary). Pep's emitter already does this (`pep_c23_unsupported` fail-closed,
E2-B3); the transfer is to the CHECKER: enumerate the exact accepted subset
per checker pass the way chibicc's parser enumerates accepted declarators.
**Falsifiable trial:** pick one checker pass (e.g. match-exhaustiveness),
list its accepted pattern shapes in one comment table, add one negative per
row; if any row cannot be stated precisely, the pass is under-specified —
file as A1 finding, not a refactor.

## 2. JonesForth (public domain, asm + Forth sources)

**Source shape (ESTABLISHED — repo listing verified this slice via
[GitHub API](https://api.github.com/repos/nornagon/jonesforth/contents/),
mirror `nornagon/jonesforth`):** NOT one file (correction 2026-11-04):
`jonesforth.S` (82,783 B literate x86 asm — tutorial + editor + compiler +
runtime) PLUS `jonesforth.f` (59,363 B Forth sources) plus Forth-level tests.
Threaded-code (address-list) execution, no AST at all. The correction
strengthens the negative-pole point: even a typeless stack system needs
~140 KB across two languages to boot and self-extend.
**Minimum trusted semantic logic:** dictionary + two stacks + inner
interpreter (~dozens of primitives); everything else is Forth-defined.
**Native/runtime deps:** Linux i386 syscalls only (`-nostdlib -static`) —
the smallest honest native base of the three (cf. E4's T1–T6).
**AST:** none — words compile to threaded addresses; there is nothing to
span, version, or re-derive. **Validation:** boots and self-extends; no
oracle beyond "it runs."
**What does NOT transfer to Pep:** untyped stacks (Pep's typed holes and
`PEP_TYPE_MISMATCH` are the antithesis); no diagnostics (a Forth stack dump
is not a `CheckDiagnostic`); no revisions, no UTF-8, no source identity.
JonesForth is the purest existence proof that LOC minimalism ≠ Pep's goals —
it keeps ZERO of Pep's safety properties. Valuable precisely as the negative
pole for E2-(a): bootstrap-subset thinking that forgets diagnostics parity
ends here.
**Transferable technique → `examples/pep_lexer.pep`:** JonesForth's
*primitives-then-defined-words* layering with the boundary written down:
each primitive documents exactly what it assumes (stack shape in, stack
shape out). Pep builtins document signatures but not COST or failure modes
beyond one-word complexity tags (E1 §4). Trial: annotate the 12 builtins
with exact failure conditions + step bounds in one table; any builtin whose
bounds cannot be stated (looking at `contains` O(n)-with-early-exit,
`utf8_slice` boundary traps) gets a conformance probe, not a rewrite.
**Falsifiable trial:** write the 12-row table; if ≥3 rows need a probe to
complete, the builtin contract — not the implementations — is the gap.

## 3. OCaml self-hosting (ocaml/ocaml, trunk) — the actually-relevant one

**Source shape (ESTABLISHED):** `driver/` (`main.ml` bytecode / `optmain.ml`
native entry points), `parsing/ typing/ bytecomp/ asmcomp/`, separate
`stdlib/`, `runtime/` (C), `BOOT_OCAMLC` staging in the Makefile.
**Minimum trusted semantic logic:** the *type checker* (`typing/`) is the
irreducible semantic core — parsing and codegen are comparatively
mechanical; soundness arguments cite typing, not the backend. **Native/runtime
deps:** C runtime + (for bootstrap) a previous OCaml binary — the same shape
as Pep's opam `pepin-5.5.2` + `ocamlopt` rebuild (E1 §2).
**AST:** `Parsetree` (syntax) vs `Typedtree` (checked) — TWO trees, the
checked one authoritative (see
[driver/](https://github.com/ocaml/ocaml/tree/trunk/driver) entry points
and [HACKING.adoc](https://github.com/ocaml/ocaml/blob/trunk/HACKING.adoc)
pipeline description, both verified this slice). This is an industry-scale
precedent RELEVANT to E2-(b) — not proof Pep should adopt the same boundary
(correction 2026-11-04: a precedent informs; only a measured seam justifies).
One authoritative semantic representation consumed downstream, with the
syntax tree demoted to ingress. **Validation:** `testsuite/` (thousands of
expect-tests with recorded outputs); reproducibility via Makefile staging.
**What does NOT transfer directly:** OCaml has no source-revision dimension
(files are compiled, not revision-stamped sessions); its diagnostics are
human-text-first, not machine-oracle byte spans; the trusted base (C
runtime + previous compiler) is far larger than anything Pep needs.
**Transferable technique → `tests/pep_checker_a13.pep` + tool protocol:**
OCaml's `Parsetree`-vs-`Typedtree` split with the checked tree as the ONLY
thing backends read. Pep already approximates this (FlatAstNode ingress vs
CheckerReport facts); the transferable move is an explicit rule: NO consumer
may read a syntax field the checked report already adjudicated (today the
emitter re-walks `parsed.nodes` for structure AND reads `checked` for
verdicts — mixed authority). **Falsifiable trial (F-B-adjacent):** pick one
emitter function (`pep_c23_expression`), list every `nodes.*` access that
duplicates a checked-fact lookup; if >30% of accesses are redundant with
`CheckerReport` fields, route (b) has a measured seam to remove — file as a
sized A1/A2 finding with line refs, not a redesign.

## 4. Comparative ledger (why these three)

| property | chibicc | JonesForth | OCaml | Pep compiler A |
|---|---|---|---|---|
| trusted semantic core | thin (C types) | dictionary+stacks | `typing/` | staged checker (2258 lines) |
| AST | C structs, Token loc/len | none | Parsetree vs Typedtree | FlatAstNode vs CheckerReport |
| diagnostics | line-text | stack dump | human text | byte-span codes (strongest) |
| revisions | none | none | none | session document/revision (unique) |
| bootstrap | self-compile | self-extend | BOOT_OCAMLC staging | opam ocamlopt rebuild |
| native deps | libc+as+ld | raw syscalls | C runtime | Clang (unpinned — E4 gap) |

Pep's genuinely differentiating properties: byte-span machine oracles and
revision-stamped sessions. Neither prior art has them; both constrain what
can be borrowed (no technique may weaken spans or revisions — hard filter).

## 5. Status labels

COMPARISON (not adoption): 3 systems, 3 transferable techniques each tied to
one Pep file + one falsifiable trial, 1 hard filter (spans+revisions).
INFERRED where line-reads were not done; `chibicc.h` struct fields and the
JonesForth repo listing were read verbatim this slice (ESTABLISHED);
OCaml internals remain documented-structure (INFERRED). Correction pass
2026-11-04 applied (spans wording, JonesForth files, precedent-vs-proof).
Cheapest next step: the §3 emitter-redundancy count (one read, no code).
Next: G-A4-4 (E10) — smallest real useful app.
