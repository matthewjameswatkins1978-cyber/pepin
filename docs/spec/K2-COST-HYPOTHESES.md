# K2 — Checker-budget hypotheses (INFERRED, sited, falsifiable)

Constraint (inherited, not repeated): A1's ablation (BOOT-A1-20261103-009)
exonerated expression inference as the sole driver — stubbing
infer_expression_type_and_shape to trivial still STEP_LIMITs at 66n;
scope_chain→trivial no movement; tree_is_valid→true moves the offset
but still fails. Cost spreads ~130k steps over ~9 phases. Any hypothesis
below that names a single dominant pass contradicts that measurement
and is already falsified. No step numbers are claimed here; A1 per-phase
counters (their K2) do not exist yet.

## H1 — The spread IS the finding (66n one-shot)

Claim: no single-pass optimisation closes ~25%; the 62-pass/64-fail
cliff is the sum of per-phase linear costs crossing a fixed budget,
not one quadratic blowup. Sited: resolve_names nests functions × nodes
× scopes × bindings (checker_a13.pep ~560-580); resolve_all_signatures
walks all nodes (~600); resolve_all_records full-scans for duplicates
(chunk_type_declarations). Each is linear-ish alone; stacked per
declaration they sum past 100k.
Falsifier: per-phase counters (A1 K2) showing one phase >50% of steps
on 62n–66n — that kills H1 and names the real target. If no phase
dominates, H1 stands and the implication is architectural (staged
checking making one-shot irrelevant, which is A1's already-chosen
direction), not another micro-tune.
Actionable observation for A1 (the one this card allows): the three
exonerated stubs bound where NOT to look — do not spend K3 on infer,
scope_chain, or tree_is_valid in isolation.

## H2 — Str cliff is per-declaration shape derivation, not bytes (408→454 B)

Claim: A3's H-V4 already established the cliff is per-declaration and
shape-dependent (Str costliest, Int twin survives 3 fillers). Candidate
site: per-use shape fallback chains — record_field_shape_ext tries
local then scans external records per field per use; call checking
derives expectedShape/actualShape plus list_mismatch_node recursion
per argument (~2188-2210). Each Str declaration adds shape-derivation
work its Int twin skips.
Falsifier (owned by A3 K5 — coordination, not duplication): minimal
single-declaration pairs varying ONLY shape kind (Int vs Str vs
record) measuring first-failing rung. If rung order does not follow
shape-derivation depth, H2 is wrong. My prediction is on record before
their measurement.

## H3 — Wall-clock vs step-limit are different ceilings

Claim: A1 measured 208M request bytes / 37.8s wall for 227 declarations
at 046 — transport is material. Step budget decides verdicts; transport
+ session overhead decides wall-clock. On near-ceiling shapes the two
can diverge: a slice can be step-green but operationally unusable, or
transport-bound while steps look healthy.
Falsifier: paired step-count vs wall-time across rungs (A1 already
records both). Steps tracking failures → checker-bound (H1 regime).
Wall time superlinear while steps plateau → transport-bound, and K3
must target representation (fewer/bigger chunks, compact facts), not
checker passes.
No fixture change proposed; uses A1's existing probes.

## Status

All three INFERRED, all pre-registered before A1-K2/A3-K5 measurements
land. When counters arrive: H1 dies or stands on the >50% rule; H2 is
decided by A3's rungs; H3 by paired step/wall data. No G-A4-2 E7
revisit — A1 per-phase measurements do not exist yet, so E7 stays parked.
