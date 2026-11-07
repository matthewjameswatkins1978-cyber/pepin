# PRE-REGISTRATION A3-025: identifier-start-run application, unseen cases

**Seat:** A3 (independent verification / hostile dogfood). Campaign `LUCY-20261107-007`.

**Written and committed BEFORE any run of A4's application and BEFORE reading A2's #16
receipt `6706527165`.** At the time of writing, no native output for this application had been
produced or read on this machine by me. Source-reading of A4's app and SPEC is deliberate: they
*are* the contract under test, not a result.

## Source authority (pinned)

| Item | Value |
|---|---|
| A4 branch/HEAD | `spec/agent4-spec-lab@12e143f` |
| Application | `examples/dogfood/pepin-source-scan.pep` |
| Blob | `4a44dd653e949258a196d247097197d7c24c1da7` |
| SPEC | `examples/dogfood/SPEC.md` @ `12e143f` |

A4 states the source is **frozen for this first gate**. A3 will gate exactly this blob and will
report if the blob measured at test time differs.

## Semantics derived from the pinned source (not from prose alone)

`main(source: SourceBytes) -> Int` is, verbatim in effect:

```
n = 0
for o in 0 .. byte_length(source)-1:
    if ascii_letter(b[o]):
        if o == 0: n += 1
        elif not ascii_continue(b[o-1]): n += 1
return n
```

with the predicates verbatim from `examples/pep_lexer.pep`:

- `ascii_letter(b)`  = `(65<=b<=90) || (97<=b<=122) || b == 95`  → `A-Z a-z _`
- `ascii_digit(b)`   = `48<=b<=57`                                → `0-9`
- `ascii_continue(b)`= `ascii_letter(b) || ascii_digit(b)`

So the value is:

```
count = |{ o : ascii_letter(b[o]) and (o == 0 or not ascii_continue(b[o-1])) }|
```

### Three consequences that are easy to get wrong, and that these fixtures target

1. **A letter preceded by a DIGIT is not a run start.** `9y` contributes 0, and `1_2`
   contributes 0 (because `_` is a *letter*, but it is preceded by `1`, which is
   `ascii_continue`). This is not "count words" and not "count maximal letter runs".
2. **A non-ASCII byte breaks a run but is invisible otherwise.** Every byte `>= 128` is neither
   letter nor continue, so `éa` → 1 and `aé` → 1, and no byte of a multi-byte sequence is ever
   counted.
3. **Text inside comments and string literals counts**, because no lexical state exists.
   Keywords, names, comment words and string words are indistinguishable to this program.

**Vocabulary.** This is an *identifier-start-run count*, still **not** a lexer and **not**
tokenisation. A3 will not accept a receipt that upgrades the label.

## New unseen fixtures (A3-authored, exact bytes, `verification/fixtures/idruns/`)

Predictions below are hand tallies from the hex column, done before execution.

| # | File | Bytes | SHA-256 | Hex | Targets | **Predicted** |
|---|---|---|---|---|---|---|
| G1 | `idruns_digits_underscore.pep` | 19 | `059215ea669d6090…` | `5f 78 39 20 39 79 20 61 31 62 20 5f 5f 7a 20 31 5f 32 0a` | adjacent digits/underscore: `y`, `b`, and the `_` in `1_2` are all suppressed | **3** |
| G2 | `idruns_utf8.pep` | 20 | `2117b3cb6eb5294d…` | `c3 a9 61 20 61 c3 a9 20 f0 9f 8e 89 62 20 5f c3 a9 20 63 0a` | UTF-8 boundaries: 2-byte `é`, 4-byte `🎉` | **5** |
| G3 | `idruns_comments_strings.pep` | 35 | `56a1434654a8a929…` | `23 20 61 6c 70 68 61 20 62 65 74 61 0a 6c 65 74 20 73 20 3d 20 22 67 61 6d 6d 61 20 64 65 6c 74 61 22 0a` | comment words `alpha beta` + string words `gamma delta` all count | **6** |
| G4 | `idruns_nul.pep` | 12 | `4af7734867801e5e…` | `78 31 00 20 30 79 20 5f 7a 00 77 0a` | embedded NUL as separator, plus `0y` suppression | **3** |
| G5 | `idruns_nonempty_zero.pep` | 19 | `b129ce1eb164e863…` | `31 32 33 2d 34 35 36 20 28 29 5b 5d 7b 7d 20 30 30 30 0a` | non-empty, no letter byte → 0 | **0** |
| G6 | `idruns_empty.pep` | 0 | `e3b0c44298fc1c14…` | *(none)* | empty file → 0 | **0** |

### Tallies in full, so a reader can falsify my arithmetic

- **G1** `_x9 9y a1b __z 1_2\n` — `_`@0 (start) **1**; `x` prev `_` cont; `y` prev `9` cont;
  `a`@7 prev space **2**; `b` prev `1` cont; `_`@11 prev space **3**; `_`@12 prev `_` cont;
  `z` prev `_` cont; `_`@16 prev `1` cont. → **3**
- **G2** `éa aé 🎉b _é c\n` — `a`@2 prev `a9` **1**; `a`@4 prev space **2**; `b`@12 prev `89`
  **3**; `_`@14 prev space **4**; `c`@18 prev space **5**. → **5**
- **G3** `# alpha beta\nlet s = "gamma delta"\n` — `alpha` **1**; `beta` **2**; `let` **3**;
  `s` **4**; `gamma` **5**; `delta` **6**. → **6**
- **G4** `x1\0 0y _z\0w\n` — `x`@0 **1**; `y` prev `0` cont; `_`@7 prev space **2**; `z` prev
  `_` cont; `w`@10 prev NUL **3**. → **3**
- **G5** all bytes are digits, punctuation, space, newline → **0**
- **G6** no bytes → **0**

G1, G2 and G4 each contain a case where a naive "count maximal `ascii_continue` runs" or
"count words" implementation gives a **different** number (naive-continue-runs would give
G1 = 4, G2 = 4, G4 = 4). So a wrong-but-plausible implementation is detectable, not merely
"probably fine".

## A4's own four fixtures — to be independently checked, not predicted

A4's SPEC claims these reference values. I record them as **A4's claims to verify**, never as my
predictions, and my Python oracle is independent of A4's:

| file (at `12e143f`) | A4 claims runs |
|---|---|
| `examples/dogfood/input_ascii.pep` (168 B, sha8 `7269de34`) | 23 |
| `examples/dogfood/input_nonascii.pep` (218 B, sha8 `bb82fc6f`) | 30 |
| `examples/dogfood/input_empty.pep` (0 B) | 0 |
| `examples/dogfood/pepin-source-scan.pep` self (1159 B, sha8 `f6e8f942`) | 139 |

A disagreement here is a finding about **A4's reference**, and is reported separately from a
disagreement about the compiler. The two must not be conflated.

## Negative and hostile cases

| # | Case | Requirement | Prediction |
|---|---|---|---|
| N1 | argv path missing | no number on stdout | exit 1, stderr `PEP_RUNTIME_SOURCE_OPEN` |
| N2 | argv path is a directory | no number on stdout | exit 1, stderr `PEP_RUNTIME_SOURCE_OPEN` |
| N3 | no argv path | no number on stdout | exit 1, stderr `PEP_RUNTIME_SOURCE_CONTEXT` |
| N4 | main chunk report with resolved call facts stripped | refuse at emit | `…has no resolved call fact` |
| N5 | call fact `calleeId` severed | refuse at emit | `…target is missing from the checked functions` |
| N6 | checked-callee arity forged | refuse at emit | `…argument count disagrees with the checked arity` |
| N7 | honest report re-invoked on a second valid target | refuse | `PEP_STALE_REVISION` |
| N8 | false-positive control: honest report on its own target | **must emit** | `emitted` — the control that makes N4–N6 meaningful |
| N9 | metamorphic: one binary, six G-files | six distinct answers | `3, 5, 6, 3, 0, 0` |
| N10 | compiled C for the app is assembly-order agnostic where supported | same answers both orders | equal |

N3's contract was **measured** in BOOT-A3-024 from the generated epilogue (`argc < 2` →
`PEP_RUNTIME_SOURCE_CONTEXT`), so it is a prediction carried forward, not a guess.

## Evidence layers, labelled separately

1. **A4 reference** — A4's own numbers. Builder-side. Not evidence about the compiler.
2. **A3 oracle** — `read_bytes()` + the three predicates in plain Python, no Pep, no checker, no
   emitter, no seed. Independent of A4.
3. **Seed interpreter** — the same predicates and the same byte values through the Pep
   interpreter (`run` cannot reach `source_bytes()`; bytes supplied by value, labelled).
4. **Native** — strict Clang (`-std=c23`) and strict GCC (`-std=c2x`), `-Wall -Wextra
   -Wpedantic -Werror -O2`.

A3 certifies only what layers 2–4 agree on. Layer 1 agreeing is convenient, not authoritative.

## Failure vocabulary

`PROVEN` = every row of layers 2–4 agrees and all negatives refuse. `FAIL` = one row differs, a
negative emits, or a number appears where a refusal was required. `NOT TESTED` = named with the
reason. The previous 67/67 (`dfca7d2`) stays attached to the **byte-class counter** and is not
evidence for this application; it must not be quoted as such.

## Scope guard

A3 owns only `verification/**`. No edits to A4's app or fixtures, A1's checker/host, A2's
emitter/runtime, frozen Full-v2, `CURRENT`, manifest, budgets, master or release labels.
Candidate7 is not touched. Peer worktrees are read-only; the merged tree is disposable.
