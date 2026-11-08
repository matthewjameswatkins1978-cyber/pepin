# FINDING BOOT-A3-178 — the emitter difference is real: A2's emits UTF-8 slice support that A1's does not

**A3-177 flagged the emitter as the larger untested unknown and declined to claim anything. Tested: the two emitters produce
different C for the same valid program, and the difference is substantive — the candidate's emitter emits a `pep_utf8_slice`
helper with full UTF-8 validation that A1's does not.**

Seed blob `f8f476198f`. A1's tip `333c5805` (emitter `efedda39`) versus candidate `b039fc5` (emitter `32bc253d`, which is A2's tip).

## The measurement

| program | A1 emitter `efedda39` | candidate `32bc253d` | same |
|---|---|---|---|
| arithmetic (`a * b + 1`) | rc 0, C sha `49d2cd61f9e8` | rc 0, C sha `7fccbf241c9b` | **NO** |
| `str_concat` say | rc 0, `4b2f19f7b55d` | rc 0, `51f15efa6d18` | **NO** |
| byte builtins | rc 2, no C | rc 2, no C | yes |
| conditional chain | rc 2, no C | rc 2, no C | yes |

Two of four differ — and the two that differ are the two that emit.

## What actually differs

47 lines, **all present only in the candidate's output**. The additions are the `pep_utf8_slice` runtime helper and its validation:

```
[[maybe_unused]] static pep_str pep_utf8_slice(pep_source_bytes source, int64_t start, int64_t finish, …)
if (source.length != 0 && source.data == NULL) { fputs("PEP_RUNTIME_INVALID_SOURCE_BYTES\n", stderr); …
if (start < 0 || finish < start || (uintmax_t)finish > (uintmax_t)source.length) { fputs("PEP_RUNTIME_…
if (pep_lead < 0x80) { pep_seq = 1; } else if (pep_lead >= 0xC2 && pep_lead <= 0xDF) { pep_seq = 2; } …
else { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); }
```

So the candidate's emitter is a **strict superset** for these programs: it carries UTF-8 slice support — overlong-encoding and
surrogate-range checks included — that A1's does not.

## Why this matters

**A1's reported results were measured on an emitter that is not in the candidate.** Their 30/31 fragment figure, their assembled-`main`
compile check, their step figures — all run against `efedda39`. The candidate runs `32bc253d`. Those results describe a program
nobody is shipping.

This is not a defect claim in either direction. It is a warning: **do not carry A1's numbers over to the candidate without
re-measuring**, and do not assume the candidate regressed them either.

It also means the candidate has *more* runtime capability than A1's branch — if anything the candidate is the better base, provided
the extra helper does not itself breach a step budget or a compile-warning gate.

## What I did not establish

- Whether the UTF-8 helper changes compiler A's emitted C at all, or by how much. That needs a buildable compiler A, and the
  candidate's source is blocked (A3-163).
- Whether `32bc253d`'s extra helper costs steps. It is emitted unconditionally in these programs, so it is worth A1 checking on a
  near-ceiling unit.
- Which emitter is *intended*. A1's own reports suggest theirs; the merge took A2's. That is an integration decision, not mine.

## Method note

A3-177 ended by saying the emitter difference was "the larger unknown of the two" and listing it under limits rather than testing
it. It took four small programs and about a minute. The same failure mode as A3-175 — I named the gap instead of closing it, and
closing it was cheap.

## Limits

- Four programs, two of which emit. Emission-only comparison of C bytes; no execution, no step measurement.
- One merge topology, one seed.
- The two `rc=2` cases refuse before emission on both trees, so they say nothing about the difference.

REF GH #16. Completes the open question in `6728939253` (A3-177).