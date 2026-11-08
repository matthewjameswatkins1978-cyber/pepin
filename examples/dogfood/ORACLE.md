# T2 + arity oracle pin (A4 lane, reserve-2 durable record)

Probes: `examples/dogfood/t2_names_probe.pep` (v3, trailing-return
classifiers) and `examples/dogfood/arity_probe.pep` (same repair applied;
single nested-return site fixed, re-checked valid).

## Expected native exit codes (checked-tree semantics)

| input | seed check | probe exit | meaning |
|---|---|---|---|
| `t2_valid.pep` | valid | 0 | def + call present |
| `t2_nodef.pep` | invalid (1 diag) | 1 | no definition |
| `t2_nocall.pep` | invalid (1 diag) | 2 | no call |
| `arity_ok.pep` | valid | 0 | arity agrees (1 param / 1 arg) |
| `arity_bad.pep` | invalid (1 diag) | 2 | arity mismatch (2 params / 1 arg) |
| `arity_nodef.pep` | invalid (1 diag) | 1 | no definition |
| `arity_nocall.pep` | valid | 2 | no call (0 args vs 1 param) |

Seed-invalid inputs are the POINT: the probes detect at runtime what the
seed rejects at check. `arity_nocall` is seed-valid (a defined-but-unused
`id` is legal Pep) yet probe-exit 2 (use-count zero).

## Run status

- T2 trio: independently run NATIVE 12/12 by A1 (trailing-return-fixed v2
  shape = committed v3; fixtures valid/nodef/nocall → 0/1/2; Clang+GCC ×
  docorder+protofirst; receipts 6708466158, patch proposal re-run).
- Arity quartet: seed-check VALID (probe) + statuses above; native run
  PENDING — next A2/A3 emitter pass uses this sheet. No native claims made.

## How to run (for A2/A3)

1. Seed: `pep.ps1 check <probe> --json` → expect `valid`, 0 diags.
2. Native: chunk-emit probe through the C23 pipeline with argv file grant
   (`main(source: SourceBytes)` entry), run against each fixture, compare
   exit codes to the table. Both C compilers; both assembly orders for T2.
