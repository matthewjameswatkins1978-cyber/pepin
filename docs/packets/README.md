# Pepin implementation packets
This is the canonical packet index. For any implementation handoff, **start at [CURRENT.md](CURRENT.md)**, not the most recently discussed packet. Presence of a packet is **not** evidence that its feature exists.

| Stage | Packet | Status | Dependency |
|---|---|---|---|
| A6 | [A6](A6-COLLECTIONS-AND-CONTROL-FLOW.md) | completed | A5 |
| A7 | [A7](A7-TYPED-SEMANTIC-API.md) | completed | A6 |
| A8 | [A8](A8-PEP-WRITTEN-ANALYSER.md) | ready | A7 |
| A9 | [A9](A9-DEVELOPMENT-TOOLS.md) | provisional | A8 |
| A10 | [A10](A10-COMPILER-FOUNDATION-LIBRARY.md) | provisional | A8 |
| A11 | [A11](A11-PEP-WRITTEN-LEXER.md) | provisional | A10 |
| A12 | [A12](A12-PEP-WRITTEN-PARSER.md) | provisional | A11 |
| A13 | [A13](A13-PEP-WRITTEN-CHECKER.md) | provisional | A12 |
| A14 | [A14](A14-PEP-WRITTEN-C23-EMITTER.md) | provisional | A13 |
| A15 | [A15](A15-STAGED-SELF-HOSTING.md) | provisional | A14 |

**Status contract:** ready = currently authorised; queued = within the already scoped A6–A8 campaign, runnable only when the preceding acceptance gate passes; provisional = future design draft, not implementation authorisation; completed = implementation and evidence published. A3–A5 are accepted historical milestones, with the A5 record in [archive](archive/A5-ACCEPTANCE-RECORD.md).

## Working procedure
1. Open [CURRENT.md](CURRENT.md), inspect repository HEAD/status, read linked packet, AGENTS.md, [status](../DESIGN.md), [protocol](../SESSION_PROTOCOL.md), [founding design](../FOUNDING_DESIGN_v0.3.md), [TR001](../TECHNICAL_RESOLUTION_001.md) and [TR002](../TECHNICAL_RESOLUTION_002.md).
2. Work on **one accepted phase**. Check actual implementation before changing code; preserve local branches/unrelated work. Test independently; publish an evidence-backed commit, report exact counts/observed behaviour and limitations.
3. Only after acceptance, advance both [CURRENT.md](CURRENT.md) and [manifest.json](manifest.json) with the same accepted publication. A7/A8 may follow sequentially within existing scope.
4. **Pause after A8.** A9–A15 need explicit review of the real implementation before their provisional contracts become executable.
5. No invented test results, premature claims, force-push or autonomous implementation of provisional phases.

TR002 supersedes old *future* C11 backend plans with **Pep-written C23** (Clang primary, GCC independent check). OCaml remains the seed. Historic MoonBit C11 work remains historical. The extension host remains **trusted local, not a sandbox**.
