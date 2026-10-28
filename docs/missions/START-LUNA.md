# Luna — Start the Sustained Pepin Campaign

**Main mission:** docs/missions/PEP-SUSTAINED-IMPLEMENTATION-20261027.md on this branch.

**Latest priorities (28 October):** [Pepin priorities and deferrals](../PEPIN-PRIORITIES-2026-10-28.md). Treat compiler knowledge and checkpoints as one semantic system, make bottom-up Pep-written standard-library foundations the practical library priority, and defer rabbit UX, Sartorial/Rust migrations and multiparadigm exploration. This is a prioritisation clarification, not permission to merge, change acceptance markers, or skip correctness work.

## Copy-and-paste starting instruction

Luna, you have Matthew's authorisation to undertake a **sustained multi-milestone Pepin implementation campaign**, not a three-slice job. Begin on branch `campaign/pep-v01-sustained-build-20261027`, whose ancestor is verified A13 checker checkpoint `54a08f311117fe020db916286aa863b42d5151a1`.

Read `docs/missions/PEP-SUSTAINED-IMPLEMENTATION-20261027.md` and the referenced accepted language draft. Inspect the live repository and run the current test baseline. Complete the existing Pep-written A13 checker, including List and nominal typing, then continue autonomously through integration, a genuine Pep-written C23 native compiler vertical slice, standard-library and built-in testing, broader accepted Pep features, safety work and the self-hosting bootstrap whenever dependencies permit.

**Do not stop after three slices, a review, an initial milestone, a PR or a proposal.** After every coherent capability, test, commit and push. Review each three-slice batch independently where possible, log evidence and keep working. Reuse existing work, don't invent truth or claims of correctness, and never auto-merge master, change CURRENT/manifest or publish a release. Escalate only a real irreconcilable product/safety/authority blocker; pivot to independent safe progress wherever possible.

The user intends to leave this active work session for a while. Make substantial actual implementation progress rather than spending it drafting more plans. If the execution environment ultimately stops, leave a clean pushed branch and an exact resumable next-action receipt. Don't claim to be working asynchronously after the session ends.

## This is a start pointer, not a second authority

The longer mission document governs implementation phases, verification, branch ownership, acceptance, exceptions and stop conditions. Use the accepted final draft in design PR #14 as the desired language target, not proof of presently supported semantics. Existing A11/A12/A13 and C23 experimental branches are reuse candidates, not blank-slate invitations. The builder's last 129-full / 14-focused passing results are reported evidence until independently rerun in your environment.
