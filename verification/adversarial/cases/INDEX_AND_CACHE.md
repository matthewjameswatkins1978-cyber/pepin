# Index / cache / staleness adversarial set (prepared for A1's node-ID index)

**Prepared:** 2026-11-02, per Lucy advisory `LUCY-20261102-006` (priority: challenge
A1's proposed revision-local node-ID index/child-range table and keyed memos with
stale revisions, invalid references, duplicate child edges, incorrect cache reuse
and diagnostic preservation).

**Probe:** `verification/probes/index_cache_adversarial.py` — one command, exit 1 iff
a claim case is falsified. **Run now at the current head as the baseline; re-run the
byte-identical probe at A1's index/caching SHA as the regression gate.** Claims are
anchored to existing contracts (the chunk-contract provenance rule, the session
protocol's deterministic-JSON and same-revision-reuse rules), never to an
implementation that does not exist yet.

Measured baseline: A1 `codex/checker-emitter-integration` @ `05add76`
(2026-11-02). See `verification/receipts/INDEX-CACHE-adversarial-05add76.md`.

## Claim cases

| id | theme | expectation | baseline @ `05add76` |
|---|---|---|---|
| IDX1 | invalid reference | `DocumentIndex` refuses a node naming a missing parent → `CHUNK_PLAN_OPEN_PARENT` | HELD |
| IDX2 | invalid reference/order | refuses parent at/after the child → `CHUNK_INVALID_PARENT_ORDER` | HELD |
| IDX3 | **duplicate child edges** | refuses two siblings with identical `(parentId, role, childIndex)` (provable-piece rule: no authoritative parse has two children with the same edge identity, and the checker's `child_at`/`count_children` treat that tuple as a key) | **FALSIFIED — accepted** |
| CACHE1 | cache reuse + determinism | same-revision re-query: parse/typecheck counts do not grow, `cache_hits` does not fall, diagnostics byte-identical | HELD (`cache_hits` 0→1→2, parse/typecheck flat at 3/3) |
| CACHE2 | incorrect cache reuse | inserting 4 bytes before the error site moves the diagnostic span by exactly +4 with the same code/message (a node-id-keyed cross-revision reuse would keep the old span) | HELD (21→25 / 35→39, `PEP_UNKNOWN_TYPE` unchanged) |
| CACHE3 | revision-keyed identity | reverting the insert restores the ORIGINAL content-addressed revision and byte-identical diagnostics | HELD |
| STALE1 | **stale revision / provenance** | the CROSSED pair — rev1-derived arguments under the advanced rev2 `semanticTarget` — is refused; a fresh target still works | **FALSIFIED — accepted with mislabelled report** (below) |

## Observations (recorded, not claimed)

- **IDX4**: a document-level negative `childIndex` is accepted at index construction;
  chunk validation refuses `CHUNK_NEGATIVE_CHILD_INDEX` downstream, so materiality
  is bounded — recorded for the index-attack surface anyway.
- **STALE0**: a *consistent* pre-edit pair (arguments and target both at rev1) stays
  invokable after the document advances — older revisions remain usable by design
  (protocol: revisions stay queryable until session end). Not a finding.

## The two falsified claims (defect detail)

### IDX3 — duplicate child edges accepted

`DocumentIndex.__init__` checks duplicate node ids, contiguity, missing parents and
parent order, but not sibling-edge identity: `[node1(parent=0,role=statement,childIndex=0),
node2(parent=0,role=statement,childIndex=0)]` builds an index without refusal, and a
plan/chunk can be built over it. Downstream, `(parent, role, childIndex)` is a key
(`child_at`, `count_children`, emitter fixed-slot routing), so an ambiguous edge makes
"which child is this?" unanswerable while every identity check still passes — the
provable-piece rule (chunk-contract doc, *Why the split exists*) is violated by
acceptance.

### STALE1 — crossed provenance accepted, report self-labels but not self-content

After the target document advances rev1 → rev2, invoking the checker tool with
`arguments=[parsed@rev1]` and `semanticTarget.revision=rev2` returns
`outcome: ok` with **no refusal code**, and the returned `CheckerReport`:

- **declares `revision = rev2`** (the target's label) — provenance label taken from the
  target, not the analysed data;
- carries **`syntaxNodeCount = 0`**, while a legitimate analysis of *either* revision
  gives **7** (fresh-target control in the same run: `fresh_nodes=7`,
  `fresh_declared==fresh_rev=True`).

So the response is a contentless analysis wearing the wrong revision's label: any
consumer caching by `report.revision` would store a **0-node "rev2" result** — the
incorrect-cache-reuse / stale-index failure mode in one step. A refusal code
(`PEP_TOOL_*`/stale-revision family) is the documented shape for such mismatches;
`ok` + mislabeled empty report is neither refusal nor truth. Mechanism (why 0 nodes;
whether a deliberate blank-on-mismatch) is the owner's to establish.

## Non-vacuity and controls

- Consistent-pair invoke works before (`control_ok`) and after the edit (`STALE0=ok`);
- fresh-target invoke after the edit works (`fresh_ok`, 7 nodes, self-labelling);
- CACHE1/CACHE2/CACHE3 prove the same-reference and edit/revert paths return real,
  position-correct diagnostics — so STALE1's `ok` is not a general "tools broken"
  artifact, and IDX3 sits beside *enforced* sibling invariants (IDX1/IDX2 held).

## Reproduction

```powershell
python verification\probes\index_cache_adversarial.py <worktree-at-pin>   # exit 1 today
terrorbats run verification\bats\index-cache-claims.yaml --repo <worktree>  # PROVEN at 05add76
```

At A1's future index/caching SHA: same two commands; **success = probe exit 0 /
bat `NOT OBSERVED`** (plus the unchanged P1 gate separately).
