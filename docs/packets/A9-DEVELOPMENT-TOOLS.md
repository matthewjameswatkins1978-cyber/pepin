# A9: More Pep-written development tools (deferred)

**PROVISIONAL / NOT AUTHORISED.** A9 is deliberately deprioritised following the accepted A8 demonstration and October 2026 roadmap review. This packet is retained for future evidence-driven use, not a prerequisite for A10–A11 or compiler bootstrapping.

## Why defer

A8 already demonstrates that an ordinary Pep program can consume compiler-resolved semantic facts, perform call-graph reachability, be registered/validated/activated through v2 transport, query retained historical revisions and hot-reload with rollback. More example linters would exercise the same architecture while postponing the stronger test: can Pep express its own lexer efficiently and correctly?

## When to return

Revisit only if an actual Pep project or compiler implementation needs one of these tools:
- Unused-local-binding analysis requiring checker-owned BindingInfo/ReadEdge and shadowing-safe symbol IDs.
- Change-impact analysis over typed, revision-bound call edges with explicitly defined traversal direction.

Reuse the A7/A8 semantic API, exact byte spans, host authority and bounded structured transport. Add only missing checker-owned facts justified by a real client. No name-scanning, duplicate resolver, general AST/refactor framework or automatic deletion.

## Acceptance if separately authorised

A Pep-written tool, independent fixtures (including shadowing, recursion and unreachable cycles), revision-specific outputs, invalid/incomplete status, denied targets, tool validation/activation/hot-replacement rollback and tested budget bounds. Publish SHA-bound evidence with primary and MoonBit counts; distinguish builder reports from independent review.

A9 does not advance automatically, is not needed for A10 or A11, and is not a native-compiler/self-hosting milestone.
