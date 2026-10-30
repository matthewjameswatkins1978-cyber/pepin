# Wall A hotspot — both failures die inside `pep_c23_child`'s linear scan (`compiler-bundle:5114:8` → emitter L25) (2026-10-30)

Answers A2's stated next step ("profile any exact emitter cap hotspot").

## Measurement

Combined state (A1 `46bf1c0` + A2 `26be4be` files), staged path,
budget labelling from A1's `stage=`/`compiler-bundle:` instrumentation:

| failing test | stage | reported location | maps to |
|---|---|---|---|
| `test_c23_real_lexer_classifiers` (5 subtests) | **emitter** | `compiler-bundle:5114:8` | `tests/pep_c23_emitter.pep` **line 25** |
| `test_lucy_ascii_continue_composes_real_lexer_helpers` (5 subtests) | **emitter** | `compiler-bundle:5114:8` | **same line 25** |

**Two structurally different programs exhaust the step budget at the
identical position** — that position is the closing brace of the scan
loop in:

```pep
fn pep_c23_child(nodes: List[FlatAstNode], parentId: Int, role: Str,
                 wantedIndex: Int) -> PepC23NodeLookup {   -- emitter L20
  for node in nodes {                                     -- full O(N) scan
    if node.parentId == parentId && node.role == role && ...
      return PepC23NodeLookup { found: true, node: node }
    else {}
  }                                                       -- L25:8 = death position
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
```

## Why it is the prime lead (stated with its limit)

- **Fan-out:** `pep_c23_child` has **186 call sites**; the emitter
  contains **72 `for … in nodes` loops** over 3,327 lines. Every call
  re-scans the whole node list → aggregate superlinear in node count,
  with one named center.
- Same death line for classifier and `ascii_continue` despite
  different shapes → shared cost center, not program-specific work.
- This is the same class A2's prior cost rounds attacked piecemeal
  (`cfa88d2` dedup scans, `edbe3b6`/`7b69964` skip-guarded lookups) —
  those shaved other loops; this one remains and is now pinned to an
  exact line.
- **Limit (honest):** the step-limit position is where the budget was
  *exhausted*, not a proof of sole causation — but same-line exhaustion
  across programs plus the call-site density make it the highest-value
  target.

## Direction (builder's call, mirrors their own prior art)

Bucket the node list once by `(parentId, role, childIndex)` (or
precompute per-function child indices) and make `pep_c23_child` an
O(1) lookup — the same dedup/index shape as `cfa88d2`'s variant-scan
reduction, applied to the largest fan-out. It also explains the Wall B
oscillation: every new emitter feature adds more `pep_c23_child`/`for
in nodes` passes over the same list, multiplying the shared cost the
a14 all-in-one path cannot absorb.

Replay: corpus/`replay.py`/base untouched this round — **163/163**
current.
