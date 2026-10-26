# PEPIN: CURRENT IMPLEMENTATION PACKET

This is the **one stable entry URL** for implementation agents. Do not guess the next task from conversation history or the newest commit.

## Campaign status: A8 accepted; paused for review
A8 is the final already-scoped phase of the A6–A8 campaign and is complete at [da244417](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/da244417c45a961728181a17ad31581e4d5a21de). The next action is design and priority review; **no implementation packet is currently authorised**. A9–A15 remain provisional. See the [A8 acceptance receipt](A8-PEP-WRITTEN-ANALYSER.md) for scope, evidence and limitations.

The clean OCaml 5.5.2 build and hello check/run smoke succeeded; **55/55 primary OCaml/A7/A8 tests** and **11/11 historical MoonBit tests** passed. The remote `master` points to the A8 implementation commit above.

## Progression
- A6: completed and published.
- A7: completed and published.
- A8: completed and published.
- Next action: design and priority review; no implementation packet is currently authorised.
- A9–A15: provisional; not authorised without review after A8.

## Agent instructions
Read [roadmap](README.md), [AGENTS.md](../../AGENTS.md), [design status](../DESIGN.md), [session protocol](../SESSION_PROTOCOL.md), [founding design](../FOUNDING_DESIGN_v0.3.md), [TR001](../TECHNICAL_RESOLUTION_001.md), [TR002](../TECHNICAL_RESOLUTION_002.md). Verify current repository and tests, do only the authorised phase, publish only accepted work, and change this pointer **together** with [manifest.json](manifest.json) upon verified acceptance. If blocked, do not advance.

A planned packet is never proof of an implemented capability.
