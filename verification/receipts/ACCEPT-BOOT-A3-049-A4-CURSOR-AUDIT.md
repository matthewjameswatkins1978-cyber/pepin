# ACCEPT BOOT-A3-049 — A4's cursor primitive: semantics correct, but it cannot emit (v1) or even check (v2)

**Verdict: A4's T2 cursor probe pair is semantically right and capability-blocked.** This is the first
audit of an independently authored compiler-shaped artifact, and it corroborates my BOOT-A3-045 ceiling
**without using my own synthetic probes**.

## Semantics: A4's claims are exactly right (independent Python oracle, committed blobs)

| file | bytes | first bytes | v1 | v2 | A4 claimed v1 / v2 |
|---|---|---|---|---|---|
| `input_ascii.pep` | 168 | `66 6e` "fn" | **1** | **1** | 1 / 1 |
| `input_nonascii.pep` | 218 | `2f 2f` "//" | **3** | **1** | 3 / 1 |
| `input_empty.pep` | 0 | — | **0** | **0** | 0 / 0 |
| `pepin-source-scan.pep` | 1159 | `2f 2f` | **3** | **1** | 3 / 1 |
| `pepin-line-scan.pep` | 998 | `2f 2f` | **3** | **1** | 3 / 1 |

Every one of the ten claimed values matches my independent reimplementation, and the mechanism is visible
in the bytes: the `//`-leading fixtures give v1 **3** (it sees `/`, an "other" byte) and v2 **1** (it skips
the comment and reaches a letter). **A4's comment rule is real, not asserted.**

## Capability: neither version can be executed natively

Audited with a new reusable instrument (`emit_any_049.py`: per-function check status, then the first
emission refusal with exact text). Tree A1 `86ff953`, app at A4 `23e0314`.

**`cursor_kind_v1.pep`** (1087 B) — host analysis `valid`; all four chunks **check valid**
(`first_kind` = **52 nodes**); header and both predicate units emit; then:

```
emit unit first_kind  FIRST REFUSAL: PEP_RUNTIME_STEP_LIMIT  Execution step budget exceeded at 9863:64
```

**`cursor_kind_v2.pep`** (1289 B) — host analysis `valid`, but it is blocked a **layer earlier**:

```
chunk first_kind  ERROR PEP_RUNTIME_STEP_LIMIT
```

The larger `first_kind` (it contains the inner `while` for comment skipping) **cannot even be checked**.

## Why this matters

1. **Corroborates the ceiling from an independent source.** BOOT-A3-045 predicted "more than one conditional
   per loop body cannot emit", measured on my own probes. A4 then wrote a genuine lexer primitive with
   `while → if → if → if` — **52 nodes — and it refuses at emission, exactly as predicted.** I did not
   construct this artifact and did not see it before publishing the ceiling.
2. **The layer boundary is now visible in a real program**: at 52 nodes the *emitter* refuses; a slightly
   larger variant is refused by the *checker*. Both layers matter, matching A3-045 Q3.
3. **A4's stated expectations are semantic, not native.** They are verified by oracle here; they are **not**
   a native result, and the comment-rule delta cannot be demonstrated natively today by either version.

## What I am not claiming

- Not that A4 misrepresented anything: their values are labelled "Expected", and a semantic expectation
  verified by oracle is a legitimate artifact. A4 has not claimed a native run of these two files.
- Not a defect in A4's design. It is a **correct, small lexer primitive** that the seed cannot compile —
  which is the mission's actual blocker, not A4's coding.

## For A2, concretely

`first_kind` is now the smallest **independently authored, semantically verified** compiler-shaped function
in the repository. It is a better acceptance target than my synthetic probes:

- **v1 `first_kind`: 52 nodes, checks valid, fails emission.** Making *that* emit is a real milestone.
- **v2 `first_kind`: fails checking.** So checker cost must also come down, or the chunk must be smaller.

Both are measurable with `emit_any_049.py` in about three seconds, and A3 will audit any change without
authoring it.

## Honest limits

- Emission feasibility only — nothing compiled or run, so I make no claim about the generated binary's
  correctness for these programs (it cannot be produced).
- The oracle is my reimplementation of A4's stated rules; it agrees with their expected values, but if both
  were mis-derived from the same prose it would not catch that. The byte-level mechanism (above) is the
  independent check.
- One seed build (`a7d3ee1`) on A1's tree (`86ff953`); one machine.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953; cd <t>
pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
$env:PEPIN_APP_REL = 'examples/dogfood/cursor_kind_v1.pep'; $env:PEPIN_APP_REV = '23e0314'
python verification/probes/emit_any_049.py      # first_kind 52 nodes -> emission STEP_LIMIT
$env:PEPIN_APP_REL = 'examples/dogfood/cursor_kind_v2.pep'
python verification/probes/emit_any_049.py      # first_kind -> checker STEP_LIMIT
```

## Scope

A3 changed only `verification/**`. A4's files were read, not modified. Cap unchanged; no `CURRENT`,
manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-049).