# Landing `text_contains` — LANDED on `pep/text-contains-utf8`

**Status: done, on a separate branch.** `pep/text-contains-utf8` (based on
`codex/continuation-03-nested-helper@4d8ddef`, which carries `str_contains`) implements
`text_contains` fully, with an explicit UTF-8 / arbitrary-bytes distinction. Final
revision: see that branch's head.

This carrier lane (`pep/native-differential-v1`) still does **not** use `str_contains`,
because its compiler does not have the builtin and using it here would break this lane's
own `pep check`. Everything else in this lane is unchanged and green.

Evidence on the landing branch: `pep check` valid; 201 output lines / 95 self-test verdict
cases; differential **65/65 mismatches=0** against The-Terror-Bats `@ d5e6404`, including
six non-empty needle cases that were uncomparable before; mutation check **11/11
detected, 0 survived**. The non-UTF-8 boundary is measured, not assumed: the reference
byte-searches a `FF FE 41 42` capture and answers PROVEN / PROVEN / NOT OBSERVED for
needles `AB` / `A` / `ZZ`, while Pep correctly reports INCONCLUSIVE because `str_contains`
needs a `Str`.

The rest of this file is the historical record of how the patch was prepared and verified
before the primitive reached a branch this lane could build on.

---

Status: **implementation verified and ready; not committed to this branch** because this
branch's compiler does not have the builtin it needs. Applying it here today would make
`pep check` fail on this branch, which is a worse outcome than a documented, verified,
ready-to-land change.

## The primitive

Agent 1 landed it at `codex/continuation-03-nested-helper@4d8ddef`
("feat: add Pep string substring search"):

```
str_contains(haystack: Str, needle: Str) -> Bool      # describe: emptyNeedle: true
```

Measured against `contains_substring` in the reference (`src/oracle.rs`), which is what
`Condition::TextContains` uses:

| `str_contains(h, n)` | Result | Reference rule |
| --- | --- | --- |
| `("abcdef", "")` | true | `n.is_empty() -> true` |
| `("abcdef", "cd")` | true | window match |
| `("abcdef", "abcdef")` | true | whole-string match |
| `("abcdef", "zzz")` | false | no window |
| `("", "")` | true | empty needle |
| `("", "a")` | false | needle longer than haystack |
| `("abc", "abcd")` | false | needle longer than haystack |
| `("aaaa", "aa")` | true | overlap allowed |

Semantics agree on all eight, including the empty-needle rule, so no adaptation layer is
needed.

## The patch (4 hunks, `oracle.pep`)

The model change is small: the source evidence becomes the loaded **text** rather than an
opaque "loaded" flag, and the non-empty branch stops answering `Inconclusive`.

```diff
-  TextContainsCondition(SourceSelector, Str, SourceAvailability)
+  TextContainsCondition(SourceSelector, Str, SourceText)
...
-    TextContainsCondition(selector, needle, availability) =>
-      judge_text_contains(selector, needle, availability)
+    TextContainsCondition(selector, needle, source) =>
+      judge_text_contains(selector, needle, source)
...
-type SourceAvailability = SourceLoaded() | SourceUnavailable(Str)
+type SourceText = SourceLoadedText(Str) | SourceUnavailable(Str)
 
-fn judge_loaded_needle(needle: Str, availability: SourceAvailability) -> Verdict {
-  return match availability {
+fn judge_loaded_needle(needle: Str, source: SourceText) -> Verdict {
+  return match source {
     SourceUnavailable(why) => Inconclusive(why)
-    SourceLoaded() => if needle == "" {
-      Proven("the empty needle is present in every text")
+    SourceLoadedText(text) => if str_contains(text, needle) {
+      Proven("the needle is present in the source")
     } else {
-      Inconclusive("substring search needs str_bytes(Str) -> SourceBytes")
+      NotObserved("the needle is absent from the source")
     }
   }
 }
...
   selector: SourceSelector,
   needle: Str,
-  availability: SourceAvailability
+  source: SourceText
 ) -> Verdict {
   return match validate_source(selector) {
     SourceRejected(reason) => Invalid(reason)
-    SourceShapeValid() => judge_loaded_needle(needle, availability)
+    SourceShapeValid() => judge_loaded_needle(needle, source)
   }
 }
```

`judge_source_only`, `validate_source` and the whole source-selector layer are unchanged,
because validation never needed the bytes.

## Fixture change needed with the patch

`selftest.pep` supplies `SourceLoaded()`, which becomes `SourceLoadedText("<text>")`. Two
expectations then change, and they should change — they were `Inconclusive` only because
the search was unavailable:

| Case | Before | After |
| --- | --- | --- |
| 83 `tc-nonempty-needle` | INCONCLUSIVE | NOT OBSERVED (needle `"ref"` absent from the fixture text) |
| 89 `tree-text-nonempty` | INCONCLUSIVE | NOT OBSERVED |

Cases 82, 84, 85, 86, 87, 88, 90, 91 keep their verdicts.

## Verification already done

Run in a detached worktree of `4d8ddef` (`_build/a1-probe`, since removed), with this
branch's `oracle.pep` + `selftest.pep` and the patch above applied:

- `pep check oracle.pep` → **valid**, 0 diagnostics, using the compiler that has
  `str_contains`.
- The full self-test → **193 lines, 91 verdict cases**, unchanged count; only the two
  rows above differ, exactly as predicted.
- `text_contains` against the real framework over a step source whose stdout is
  `alpha beta gamma`:

| Needle | Rust | Pep + `str_contains` |
| --- | --- | --- |
| `""` | PROVEN | PROVEN |
| `"beta"` | PROVEN | PROVEN |
| `"alpha beta gamma"` | PROVEN | PROVEN |
| `"zzz"` | NOT OBSERVED | NOT OBSERVED |
| `"gamma alpha"` | NOT OBSERVED | NOT OBSERVED |
| `"alpha beta gamma!"` | NOT OBSERVED | NOT OBSERVED |

**6/6 agree**, including the empty-needle rule and three negatives.

## What is needed to land it

1. `str_contains` present in the compiler on the base this branch is rebuilt on (i.e.
   Agent 1's `4d8ddef` merged to the integration branch, which is the integrator's job —
   not something this lane should force by rebasing onto another agent's branch).
2. Apply the four hunks above.
3. Update the `SourceLoaded()` fixtures to `SourceLoadedText(...)` and the two case
   expectations.
4. Add `text_contains` cases to `differential.py` (the empty-needle cases are already
   there; the non-empty ones become comparable for the first time).

After that the coverage table moves `text_contains` from "decided except the search" to
**implemented**, and `text_matches` / `json_value_equals` inherit the same load path and
need only regex / a JSON parser on top.
