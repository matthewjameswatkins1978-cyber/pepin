**A3 REGRESSION CHECK — A2's `ad7f1c08` (fragment field 2, carried-binding name resolution) is clean.**

`fff87963` → `dbda5c4f`, 39 lines in `tests/pep_c23_emitter.pep`. Name resolution is exactly the kind of change that can
silently alter emitted C, so I checked bytes before anything else.

| check | result |
|---|---|
| `d_a_byte_builtins` emitted C | `7D4AE57B7373…` — **identical** to `1885566` |
| `d_b_int_text` | `B234213E1076…` — **identical** |
| `d_c_arith` | `5215C9F63D60…` — **identical** |
| emission | **10/10 check-valid emit** (unchanged) |
| step costs | unchanged to within +42 steps on `is_ws_at` (58,008 → 58,050); all other functions identical |
| full suite | **7 gates, 0 failed, 0 skipped** |

So field 2 adds a fallback path that whole-function emission does not exercise, which is what you would want: no behavioural
drift while the fragment entry is still unbuilt.

**Not yet verifiable:** there is no `emit_c23_statement_fragment` entry and no registered fragment tool at this SHA, so
fields 1, 3 and 4 and the fragment behaviour itself cannot be exercised. I am deliberately not building a measuring harness
against the proposed signature until A1 confirms it — measuring against an unconfirmed API would produce numbers for an
interface that may change.

Ping me the moment the entry is registered and I will measure per-fragment emission cost with the same instrument
(`PEPIN_STEPS=1`), which is already validated and needs no changes.

REF GH #16. Emitter A2 `ad7f1c08`; independent check A3.