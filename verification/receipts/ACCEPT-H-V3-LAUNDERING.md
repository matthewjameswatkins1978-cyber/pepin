# H-V3: a forged callee fact launders an INVALID program into a VALID chunk

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-015 / Campaign H, Workstream V3.2 + V3.4 · **Evidence label:** `TESTED`
**PIN:** A3 `codex/bootstrap-agent3-verification@e220db6` (+this commit) · clean · tested A1 `2ad750b` (chunk checker, pinned worktree) · seed `pep.exe` from that pin
**Verdict:** **FALSIFIED** — one new property, first measured here. Not a duplicate of E2b / T-ADM-4 / R-ID-1.
**First next action:** A1 decides whether facts must carry declaration provenance (G-A1-2 stamps) to close this; A3 will then re-run this exact probe against the stamped schema.

## The property

Metamorphic law, forbidden direction only:

> same bytes, whole-source **invalid** ⇒ any chunk decomposition must not be **valid**

The attack supplies, for a callee the chunk does not contain, a **self-consistent but false** external fact set. Nothing about the fact is internally inconsistent — it simply does not describe the callee's real declaration. Family: *type-authority laundering*. Distinct from the pinned attacks: E2b/`2ad750b` refuse **duplicates**; T-ADM-4/T-REC are **record/ghost** facts; R-ID-1 gates **colliding names**. None of them tests whether a fact's *type content* is checked against the declaration it claims to describe.

## Program under test (invalid as written)

```pep
fn scale(v: Int) -> Int {
  return v * 2
}
fn main() -> Int {
  return scale("oops")      // Str argument to an Int parameter
}
```
sha256 of the exact bytes: `61d8a5ea8664a61564f98ab667b74a3410b03f6118e9571088e638be911a2a6f`

## Result — 4 cells, 1 falsified

| cell | facts supplied for `scale` | chunk verdict | expectation |
|---|---|---|---|
| **S0** whole-source oracle | — | `invalid` / `PEP_TYPE_MISMATCH` | baseline |
| **A1** chunk `main`, **honest** facts | `(Int) -> Int` (from `chunk_signatures`) | `invalid` / `PEP_TYPE_MISMATCH` | invalid ✅ **HELD** |
| **A2** chunk `main`, **forged param** | `(Str) -> Int` | **`valid`, no diagnostics** | invalid ❌ **FALSIFIED** |
| **A4** honest positive control | valid program, correct facts | `valid` | valid ✅ **HELD** |
| **A3** forged **return** (`say(label(7))`, callee claims `-> Str`) | `(Int) -> Str` | **`valid`, no diagnostics** (whole-source `invalid`/`PEP_TYPE_MISMATCH`) | measured, same family |

A1 is the load-bearing control: the harness slices `main`'s subtree identically in A1 and A2 and differs **only** in the fact's parameter type — honest facts reproduce the whole-source diagnostic, forged facts erase it. So the divergence is caused by the fact content, not by the slicing.

## What this does and does not prove

**Proven (TESTED):** the chunk checker treats supplied external facts as *type authority*. A caller chunk whose only defect is a type mismatch against a callee it does not contain is reported **valid** when the fact mis-describes that callee. No diagnostic, no warning, no provenance complaint — consistent with the measured E3p schema gap (no `document`/`revision` fields on `CheckedFunction`/`ResolvedSignature`), so nothing in the fact can even claim which declaration it describes.

**INFERRED, not measured (stated as such):** the assembled native path is very likely fail-closed *later* — the emitted prototype for `scale` comes from its own chunk and is typed `int64_t pep_fn_scale(int64_t v)`, so a lowered Str argument cannot compile under strict C23. I did **not** drive unit emission from the forged report (that needs the `pep-c23-unit` path), so this remains an inference, not evidence. Either way, the **compiler's own acceptance decision was wrong before C ever saw it**.

**Not claimed:** that this is exploitable beyond "a batch author can make an invalid program's chunk look valid". Whoever supplies facts already controls the build, and the contract's own framing is *consistency, not authenticity*. The finding is that the guarantee has no type-level bridge between a fact and the declaration it names, and that the metamorphic law therefore FAILS while remaining undetectable by any current diagnostic.

## Why this is worth A1's attention

- It is the first measured case where an **invalid** whole-source program yields an **accepted** chunk with **no diagnostic at all** — the previous admissions (T-ADM-4 ghost, R2 pre-gate, E2b) all produced *something* observable or were exact duplicates.
- G-A1-2 (stamped callee schema) would address it only if the stamp binds a fact to the declaration *content* (a hash of the signature), not merely to a document/revision pair: the forged fact here is same-revision and self-consistent, so a revision-only stamp would not catch it. Stated as a design input, not a demand.
- The cheap partial mitigation already exists in the architecture: check the callee's own chunk before trusting its fact. That ordering is the caller's (A2's) to choose, not A3's to impose.

## Mechanics / reproduce

`verification/probes/fact_laundering.py <tree>`, run against a tree carrying the pin's `pep_chunk_contract.py`, `tests/chunk_helper.py` and an emitter (`D:\Projects\wt-a3-a1-2ad750b` was used). The probe registers `parser-start`, `parser-step`, `checker-sigs`, `checker-chunk-typed` against `pep_c23.SOURCES`, validates each, then drives `analyze_chunk_typed` with hand-built fact lists. Exit code 1 means a claim was falsified — deliberately non-zero here.

## Admitted unknowns / limits

- Emitter/C backstop not measured (needs the unit-emission path); declared INFERRED above.
- One callee, one argument position, two axes (param type, return type). Not a matrix; the claim is that the family exists, not that every shape is affected.
- `sliced()` copies the target function's subtree plus the mapped node ids; the honest-facts control proves the slice is faithful for this program.
- No A1/A2/spec/frozen-gate/budget/master/CURRENT change by A3; `verification/**` only. A1's worktree was read-only and left clean.
