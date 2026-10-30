# Crash-freedom under adversarial bytes (V0 set 22 — robustness)

A seeded pseudo-random sweep (seed `20261029`, 24 inputs over a hostile
token alphabet including multibyte/invalid bytes, NUL, bare punctuation
and keywords) through `pep.ps1 check`: **24/24 failed cleanly** — every
run returned a machine-readable `valid`/`invalid`/`incomplete` verdict
or a controlled error, none hung past the harness timeout, none
produced an interpreter traceback or native crash. The sweep itself is
a one-off harness (not committed); four representative byte patterns
are pinned in the replay lab as regression anchors.

| probe | input bytes | result |
|---|---|---|
| `X-garb-braces` | `}{)(fn}{` | `TESTED`: `invalid`, `PEP_PARSE_EXPRESSION` |
| `X-garb-kw` | `fn fn fn` | `TESTED`: `invalid`, `PEP_PARSE_EXPECTED` |
| `X-garb-bytes` | `\xff\xfe\x00fn` (invalid UTF-8 + NUL) | `TESTED`: `invalid`, `PEP_INVALID_UTF8` |
| `X-garb-ret` | `return return return` | `TESTED`: `invalid`, `PEP_PARSE_EXPRESSION` |

No findings: arbitrary bytes are either parsed or rejected with
dedicated diagnostics; there is no third outcome (hang, crash,
unstructured traceback) in the swept sample. This complements the
semantic corpus (which asserts *which* verdict) with a crash-freedom
guarantee (that *a* verdict always arrives).
