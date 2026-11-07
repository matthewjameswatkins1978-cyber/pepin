# ACCEPT BOOT-A3-066 — `source_bytes` is a host-granted v2 capability, not a plain builtin

**Verdict: my BOOT-A3-065 negative is now explained rather than merely observed, and the campaign's remaining
work is larger than one emitter patch. Input acquisition needs host-grant plumbing that BOOT-A3-041 already
found unreachable through the documented CLI.**

`docs/SEED_LANGUAGE.md` L48 states:

> "The unaccepted A10 review branch adds exact-byte inspection, `open_bytes`, a v2 host-granted
> `source_bytes()`, checked byte slicing … These are candidate branch capabilities, not an accepted full lexer
> or self-hosting milestone."

So `source_bytes()` is **host-granted** — it requires the v2 grant mechanism rather than being callable by an
ordinary program. That is exactly why `source_bytes("Pep")` was refused by **host analysis** rather than by the
emitter: the call is not a normal builtin invocation in the current seed.

## The consolidated blocker list for input-dependent C23

Two independent gates, both now named:

1. **Emitter sites.** `source_bytes`, `utf8_slice`, `byte_slice` and `int_text` each have **0** by-name sites
   (BOOT-A3-062), so an emitted program cannot call them at all. Fix = the three-site pattern that `str_concat`
   already demonstrates.
2. **Host grant plumbing.** Even with sites added, `source_bytes()` is v2 host-granted. BOOT-A3-041 measured
   that the documented user-facing command **does not work** — there is no `--grant-file`, and a one-shot CLI
   check exceeds the 100,000-step budget on both apps.

So the floor is not one patch away: it is **three-site emitter work plus a working grant path**. This corrects
my BOOT-A3-064/065 framing that the emitter patch alone was the remaining item.

## What is already clear and should not be re-litigated

- Emitter capacity is **not** the blocker (BOOT-A3-051/053: decomposition emits and runs).
- List handling is **not** the blocker (BOOT-A3-061/064: List values in `main`, cross-chunk `Int` calls, and
  loop-time call-fact resolution all work, natively, under Clang and GCC).
- Output-proof is **not** blocked by `int_text` (BOOT-A3-064).
- The step budget **is** a hard gate on large single chunks (BOOT-A3-045/049), and the 100k cap is frozen —
  changing it is Matthew's decision, not an emitter patch.

## Honest limits

- I read one documented sentence, not the A10 branch or the host-grant implementation. Whether a grant path
  exists that A3-041 did not exercise is **unverified**.
- The A10 branch is described as *unaccepted*; whether byte capabilities are intended to land in the seed is a
  design decision above my lane.

REF: GH #16.