# FINDING — A1 `d64ea2a` breaks the compiler bundle for every emit path (`PEP_TYPE_MISMATCH`: `FlatAstNode` vs `CheckerNode`)

**Severity: first-order — it supersedes Wall A as the immediate
integration blocker** (Wall A becomes unmeasurable until this is fixed:
no state using A1's checker can open the bundle at all).

## The failure

| state | bundle check (lexer+parser+checker+emitter concatenated) | a14 | classifier |
|---|---|---|---|
| A1 `e0d1f89` (control, last round) | **valid** | 2 known | 1/1 |
| **A1 `d64ea2a` clean** | **invalid** — `PEP_TYPE_MISMATCH: Expected FlatAstNode but found CheckerNode @ line 5041` (emitter region) | **11 failures** (every test; 12.6s — fails at setup) | **5 errors** |
| **combined** `d64ea2a` checker + A2 `ba0e325` emitter | **invalid — same diagnostic, same line 5041** | (moot — bundle never opens) | (moot) |
| A2 `ba0e325` own (their older checker) | **valid** | 3 (known set) | n/a |

Every emit-path test registers the tool against the *bundle document*;
with the bundle invalid, `open` returns `status: invalid` and all emit
tests fail instantly — which is why a14 went 2 → 11 in 12.6 seconds.

## Cause and attribution

`d64ea2a` "Compact checker AST transport" rewrites the checker's
transport to an 8-field `CheckerNode` (243 lines changed in
`pep_checker_a13.pep`, +38 in `pep_c23.py`). The **emitter** — on
A1's line and on A2's — still declares/consumes `FlatAstNode` at the
call sites, so the concatenated document fails type checking at bundle
line 5041. A1's own slice note already says **"No emitter integration"**
— the integration is not optional follow-up: it is required for the
bundle to typecheck at all on any state using the new checker.

Nothing else changed: A1's claims are **true where made** — the a13 +
nested suites really are 97/97 (verified), because those suites do not
exercise the emitter. The gap is that no claimed suite covers bundle
validity/emit on their line; a14 and the classifier do, and they are
now fully red for a *different* reason than the open emit-cost finding.

## What this does to the blocker map

1. **First-order:** bundle typecheck (`CheckerNode` ↔ `FlatAstNode`
   integration) — blocks a14, classifier, and the whole combined lane.
2. **Second-order (Wall A, still open but now unmeasurable):** staged
   emit cost for classifier/`ascii_continue` closures.
3. **Wall B (a14 all-in-one contract)** — owner decision still open,
   unaffected by this round.

## Verified this round (sequential, detached, no builder file edited)

- A1 `d64ea2a` claims: a13+nested **97/97 ✓** (checker suites green —
  but see above for scope).
- A2 `ba0e325` own: a14 **3** (unchanged known set), nested **44
  tests OK** (new continuation-helper composition test passes), bundle
  **valid** — A2's lane unaffected.
- Control re-run: bundle at `e0d1f89` **valid** — the breakage window
  is exactly `e0d1f89..d64ea2a`.

Replay: corpus/`replay.py`/base untouched — **161/161** current.
