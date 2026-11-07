# ACCEPT BOOT-A3-076 — `pep_str` and `pep_source_bytes` are the SAME struct: Route S is cheaper than A3-075 estimated

**Verdict: the runtime layer of Route S is close to a no-op. The two C typedefs have identical field names and
types, so the existing byte helpers already work on a `Str` value's layout. Route S is therefore two layers, not
three.**

## Evidence

Two consecutive prepends in the emitter introduce the runtime header:

```
pep_source_bytes:  typedef struct { const unsigned char *data; size_t length; } pep_source_bytes;
pep_str:           typedef struct { const unsigned char *data; size_t length; } pep_str;
```

**Identical members, identical types, identical order.** And the existing helpers take the byte struct by value:

```
static int64_t pep_byte_at(pep_source_bytes source, int64_t offset)
static int64_t pep_byte_length(pep_source_bytes source)
static pep_str  pep_utf8_slice(pep_source_bytes source, int64_t start, int64_t finish)
```

`pep_utf8_slice` already **returns** a `pep_str` built from `source.data` / `source.length` — it is already
treating `pep_source_bytes` as the same shape as `pep_str`.

## What that does to the sizing in A3-075

- **Layer 1 (checker contract shape): unchanged** — still needs a way to accept either type at index 0. All three
  contracts now verified at source: `byte_length` L1239, `byte_at` L1240, `byte_slice`/`utf8_slice` L1241, each
  returning `"SourceBytes"` for index 0 with one concrete type per slot.
- **Layer 2 (emitter typing): unchanged** — the C parameter type is selected from the Pep type name.
- **Layer 3 (runtime helpers): MUCH smaller than I estimated.** Because the layouts match, the helper bodies need
  no change. What remains is a **type-name question** only: either emit one shared typedef for both Pep types, or
  insert a zero-cost cast at the call site. In C these are distinct struct types despite identical layout, so
  something has to bridge the nominal difference — but it is a bridging line, not three rewritten helper families.

So Route S is: **one contract-shape decision, one emitter typing change, one bridge for the nominal type
difference.** That is materially cheaper than A3-075 reported, and I would rather correct my own estimate upward in
the project's favour than leave an inflated one standing.

## Honest limits

- I compared the two typedef declarations and three helper signatures. I did **not** compile a probe where a
  `pep_str` is passed to `pep_byte_at`, so whether strict C rejects it without a cast under `-Werror` is
  **inferred from the language rules, not measured**. That is the one experiment that would settle the bridge cost.
- The checker-side change is still unread beyond the contract lines that return parameter types.

REF: GH #16.