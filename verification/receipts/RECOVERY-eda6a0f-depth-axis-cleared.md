# Recovery verified — A1 `eda6a0f` clears the depth axis: heavy 26 → 4 (2026-10-30)

A1 acted on the delivered fix directions
(`MECHANISM-ae91bdc-match-chains.md`, direction #1: common-first arm
ordering): commit `eda6a0f` "Prioritize recursive parser AST nodes"
hoists `AstList`/`AstTypeList` (and match/constructor-pattern arms in
`flat_node_fast_1`) into the chain ENTRY functions, removing them from
parts 5/7/8/9/10/11.

## Measured (clean detached, sequential, `-v`)

| head | heavy set (124) | deep-suite failures | a14 |
|---|---|---|---|
| `46bf1c0` (pre-series) | 2 | 0 | 2 known |
| `ae91bdc` (break) | 26 | **22** | 4 |
| `e37218a` (checker work) | 26 | 22 | 4 |
| **`eda6a0f` (arm hoist)** | **4** | **0** ✓ | 4 |

**The depth axis is fully fixed**: all 22 deep/nested failures recover
— the span-chain frame analysis was right, and hoisting the
list/type-list variants to the entry (exactly one frame for the common
deep-target query) removed the extra frames that blew host depth 128.

## What remains (the 4)

The a14 set: `source_backed` + `depth` (the **step-axis** residue of
`ae91bdc` — chain overhead still on the shared all-in-one budget) plus
the two long-known stale expectations. cli 8/8, classifier 1/1, all
a13/nested green. This is the **Wall B** contract/headroom question
plus whatever step residue the hoisting didn't return — separate track
from the now-fixed depth axis.

## Status of the original URGENT finding

- Mechanism: confirmed and acted upon ✓
- Directions: #1 applied and verified effective (22→0) ✓
- Axes: depth closed; step axis (4 a14) open — either more cost work
  or the Wall B contract decision.

Replay **172/172**; INDEX current.
