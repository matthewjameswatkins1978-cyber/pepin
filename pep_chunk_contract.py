"""Versioned checked-chunk facts contract, host/protocol side (v1).

Why this module exists: compiler-sized Pep source does not fit one JSONL
invocation, so the host must hand the emitter *bounded, already checked*
pieces. A2's emitter fails closed, and a fail-closed consumer is only as
safe as the provenance of what it receives. This module is the host half
of that boundary and nothing more:

- one authoritative parse of one document revision;
- disjoint chunk ownership with explicitly declared shared declarations;
- host-held ordering, replay and coverage state;
- refusal of any chunk that does not match its plan exactly.

It performs no type checking, inference or signature derivation. Every
semantic fact in a chunk comes from the Pep checker's own ``analyze_chunk``
/ ``chunk_signatures`` results; the host transports and verifies them.

Measured reason for the shared-declaration rule: the existing chunked
prototype (tests/chunk_helper.py) sends each function's subtree *plus* the
declaration subtrees it textually references, so declaration nodes repeat
across chunks. A contract that silently forbade that would not describe the
pipeline that exists. Repetition is therefore allowed only for ids inside a
declared shared root, and only when that shared root is itself one of the
planned chunks, so the repeated facts are certified once and can be checked.

Stage-0 note (LUCY-20261101-006 decision 5): partition arithmetic and
ordering state here are bootstrap orchestration, not semantics. They are
meant to move into Pep-written Lucy; until then they must not grow any
type, scope or signature logic.
"""

import re

CONTRACT_VERSION = "pep-checked-chunk-v1"

CONTRACT = {
    "version": CONTRACT_VERSION,
    "chunk": {
        "version": "contract tag; any other value is refused",
        "document": "the open target document the chunk was cut from",
        "revision": "the open target revision; a stale revision is refused",
        "index": "0-based position in the plan; accepted only in order, once each",
        "coveredNodeIds": "ascending unique original node ids in this chunk",
        "nodes": "FlatAstNode values, exactly the covered ids, original ids kept",
        "report": "the Pep checker's own CheckerReport for this chunk",
        "suppliedSignatures": "functionIds the host supplied as external signatures",
    },
    "invariants": (
        "every document node is in at least one planned chunk",
        "a node repeats across chunks only inside a declared shared root",
        "each declared shared root is whole inside at least one planned chunk",
        "each chunk is parent-closed: a parent is -1 or in the same chunk",
        "parentId < id and childIndex >= 0 for every node",
        "a chunk's nodes are exactly its covered ids: no extras, no gaps",
        "the report's document, revision and syntaxNodeCount match the chunk",
        "external signatures must come from this document's checker provenance",
        "chunks are accepted in plan order, once each, and all must arrive",
    ),
    "refusals": (
        "CHUNK_VERSION_UNKNOWN", "CHUNK_STALE_REVISION", "CHUNK_INDEX_OUT_OF_RANGE",
        "CHUNK_OUT_OF_ORDER", "CHUNK_REPEATED", "CHUNK_COVERAGE_MISMATCH",
        "CHUNK_UNKNOWN_NODE", "CHUNK_DUPLICATE_NODE", "CHUNK_DUPLICATE_EDGE", "CHUNK_MISSING_NODE",
        "CHUNK_OPEN_PARENT", "CHUNK_INVALID_PARENT_ORDER", "CHUNK_NEGATIVE_CHILD_INDEX",
        "CHUNK_REPORT_MISMATCH", "CHUNK_REPORT_COUNT_MISMATCH", "CHUNK_REPORT_STATUS_UNKNOWN",
        "CHUNK_UNSUPPLIED_SIGNATURE", "CHUNK_INCOMPLETE",
        "CHUNK_PLAN_OVERLAP", "CHUNK_PLAN_INCOMPLETE", "CHUNK_PLAN_OPEN_PARENT",
        "CHUNK_PLAN_EMPTY", "CHUNK_PLAN_SHARED_NOT_PLANNED",
        "CHUNK_TYPE_MISMATCH", "CHUNK_SCALAR_TYPE", "CHUNK_SCALAR_FORMAT",
    ),
}

REPORT_STATUSES = ("valid", "invalid", "incomplete")


class ContractRefusal(RuntimeError):
    """A chunk or plan violated the contract. ``code`` is the stable reason."""

    def __init__(self, code, detail):
        if code not in CONTRACT["refusals"]:
            raise ValueError(f"unknown contract refusal code {code!r}")
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _fields(value, type_name):
    if not isinstance(value, dict) or value.get("type") != type_name:
        raise ContractRefusal("CHUNK_TYPE_MISMATCH",
                              f"expected a {type_name} value, got {type(value).__name__}")
    return {field["name"]: field["value"] for field in value.get("fields", [])}


def _scalar(value, type_name, label):
    if not isinstance(value, dict) or value.get("type") != type_name:
        raise ContractRefusal("CHUNK_SCALAR_TYPE", f"{label} is not a {type_name} value")
    return value.get("value")


def _str_scalar(value, label):
    raw = _scalar(value, "Str", label)
    if not isinstance(raw, str):
        raise ContractRefusal("CHUNK_SCALAR_TYPE", f"{label} is not a string")
    return raw


_INT_TEXT = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")


def _int_scalar(value, label):
    """Return an exact typed integer, or refuse. Never coerce a lossy value.

    Measured hazard this replaces: the old code called int() on whatever the
    envelope carried, so 3.7, True and "12" all became integers and "abc"
    escaped as a bare ValueError instead of a contract refusal. The Pep JSONL
    wire format does carry Int as a canonical decimal string, so that shape is
    accepted exactly; every other shape is refused.
    """
    return _exact_int(_scalar(value, "Int", label), label)


def _exact_int(raw, label):
    if isinstance(raw, bool) or isinstance(raw, float):
        raise ContractRefusal("CHUNK_SCALAR_TYPE", f"{label} is not an integer")
    if isinstance(raw, int):
        return raw
    # Pep's JSONL transport encodes Int as a canonical decimal string.
    if isinstance(raw, str) and _INT_TEXT.match(raw):
        return int(raw)
    raise ContractRefusal("CHUNK_SCALAR_FORMAT", f"{label} is not a canonical integer")


def _chunk_int(raw, label):
    """Envelope integers are exact: no bools, floats, strings or coercions."""
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ContractRefusal("CHUNK_SCALAR_TYPE", f"{label} is not an integer")
    return raw


def _node_fields(node):
    fields = _fields(node, "FlatAstNode")
    return {
        "id": _int_scalar(fields["id"], "node id"),
        "parentId": _int_scalar(fields["parentId"], "node parentId"),
        "childIndex": _int_scalar(fields["childIndex"], "node childIndex"),
        "role": _str_scalar(fields["role"], "node role"),
    }


class DocumentIndex:
    """One authoritative parse of one document revision: ids plus structure.

    Construction re-checks the transport invariants the staged parser host
    already depends on, so no plan can be built over a tampered or
    non-contiguous node list.
    """

    def __init__(self, document, revision, nodes):
        self.document = document
        self.revision = revision
        self.nodes = list(nodes)
        self.parents = {}
        self.children = {}
        edge_seen = set()
        for node in self.nodes:
            fields = _node_fields(node)
            node_id = fields["id"]
            if node_id in self.parents:
                raise ContractRefusal("CHUNK_DUPLICATE_NODE",
                                      f"document lists node {node_id} twice")
            self.parents[node_id] = fields["parentId"]
            self.children.setdefault(fields["parentId"], []).append(node_id)
            if fields["parentId"] != -1:
                edge = (fields["parentId"], fields["role"], fields["childIndex"])
                if edge in edge_seen:
                    raise ContractRefusal("CHUNK_DUPLICATE_EDGE",
                                          f"document has two children with parent {edge[0]}, role {edge[1]!r}, childIndex {edge[2]}")
                edge_seen.add(edge)
        self.ids = tuple(sorted(self.parents))
        if self.ids and self.ids != tuple(range(self.ids[0], self.ids[0] + len(self.ids))):
            raise ContractRefusal("CHUNK_COVERAGE_MISMATCH",
                                  "document node ids are not contiguous")
        for node_id, parent_id in self.parents.items():
            if parent_id != -1 and parent_id not in self.parents:
                raise ContractRefusal("CHUNK_PLAN_OPEN_PARENT",
                                      f"document node {node_id} names missing parent {parent_id}")
            if parent_id >= node_id:
                raise ContractRefusal("CHUNK_INVALID_PARENT_ORDER",
                                      f"document node {node_id} has parent {parent_id} at or after it")

    @classmethod
    def from_parsed(cls, parsed):
        """Build an index from a staged ParserProgress value."""
        fields = _fields(parsed, "ParserProgress")
        document = _str_scalar(fields["document"], "parser document")
        revision = _str_scalar(fields["revision"], "parser revision")
        status = _str_scalar(fields["status"], "parser status")
        if status != "complete":
            raise ContractRefusal("CHUNK_COVERAGE_MISMATCH",
                                  f"an incomplete parse cannot be planned over (status {status!r})")
        return cls(document, revision, fields["nodes"].get("value", []))

    def node_ids(self):
        return self.ids

    def subtree(self, root_id):
        """All ids in the subtree rooted at ``root_id``, ascending."""
        if root_id not in self.parents:
            raise ContractRefusal("CHUNK_UNKNOWN_NODE",
                                  f"root {root_id} is not a node of this document")
        keep, stack = set(), [root_id]
        while stack:
            current = stack.pop()
            if current in keep:
                continue
            keep.add(current)
            stack.extend(self.children.get(current, ()))
        return tuple(sorted(keep))

    def nodes_for(self, ids):
        wanted = set(ids)
        return [node for node in self.nodes if _node_fields(node)["id"] in wanted]

    def referenced_names(self, chunk_ids):
        """Every name text appearing on a node of this chunk.

        Deliberately over-approximate: any node text that coincides with a
        declaration name is reported, whatever the node's role.
        """
        wanted = set(chunk_ids)
        names = set()
        for node in self.nodes:
            fields = _fields(node, "FlatAstNode")
            if _int_scalar(fields["id"], "node id") not in wanted:
                continue
            names.add(_str_scalar(fields["text"], "node text"))
        return names

    def fact_closure(self, chunk_ids, candidate_names):
        """External declarations this chunk can actually reference.

        Index-only and conservative. A declaration whose name never appears
        on a node of the chunk cannot affect the chunk's meaning, so dropping
        it from the external fact set cannot weaken the check; it only stops
        the chunk paying to re-derive facts about the rest of the program.
        Measured on stdlib/collections.pep (107 top-level functions):
        passing all 106 external signatures exceeds the step budget, while
        the same bodies check valid with their closure (often none).
        """
        names = self.referenced_names(chunk_ids)
        return frozenset(name for name in candidate_names if name in names)


class ChunkPlan:
    """Covering chunk plan for one revision, with declared shared roots."""

    def __init__(self, index, chunk_ids, shared_roots=(), signatures=()):
        self.index = index
        self.document = index.document
        self.revision = index.revision
        self.shared_roots = tuple(sorted(_chunk_int(root, "shared root") for root in shared_roots))
        self.chunk_ids = tuple(tuple(ids) for ids in chunk_ids)
        self.signatures = frozenset(_exact_int(value, "signature id") for value in signatures)

    @property
    def chunk_count(self):
        return len(self.chunk_ids)

    def node_ids(self, position):
        if not 0 <= position < len(self.chunk_ids):
            raise ContractRefusal("CHUNK_INDEX_OUT_OF_RANGE",
                                  f"chunk {position} is outside this plan")
        return self.chunk_ids[position]

    def is_shared(self, node_id):
        return node_id in self._shared_ids

    @property
    def shared_ids(self):
        return frozenset(self._shared_ids)

    def describe(self):
        return {
            "version": CONTRACT_VERSION,
            "document": self.document,
            "revision": self.revision,
            "chunkCount": self.chunk_count,
            "nodeCount": sum(len(ids) for ids in self.chunk_ids),
            "chunks": [list(ids) for ids in self.chunk_ids],
            "sharedRoots": list(self.shared_roots),
            "signatures": sorted(self.signatures),
        }


def plan_chunks(index, chunk_roots, shared_roots=(), signatures=()):
    """Plan one chunk per listed root node, in the order given.

    ``shared_roots`` are declarations a body chunk may also carry; each one
    must be planned as its own chunk.
    """
    if not chunk_roots:
        raise ContractRefusal("CHUNK_PLAN_EMPTY", "a plan needs at least one chunk root")
    chunk_ids = [index.subtree(root) for root in chunk_roots]
    return _plan(index, chunk_ids, shared_roots, signatures)


def plan_ids(index, chunk_ids, shared_roots=(), signatures=()):
    """Plan explicit id lists (for dynamic or sub-function partitions later)."""
    if not chunk_ids:
        raise ContractRefusal("CHUNK_PLAN_EMPTY", "a plan needs at least one chunk")
    return _plan(index, chunk_ids, shared_roots, signatures)


def _plan(index, chunk_ids, shared_roots, signatures):
    roots = tuple(_exact_int(root, "shared root") for root in shared_roots)
    for root in roots:
        if root not in index.parents:
            raise ContractRefusal("CHUNK_UNKNOWN_NODE",
                                  f"shared root {root} is not a node of this document")
    shared_ids = set()
    for root in roots:
        shared_ids.update(index.subtree(root))

    owned, ordered = {}, []
    for ids in chunk_ids:
        if not ids:
            raise ContractRefusal("CHUNK_PLAN_EMPTY", "a planned chunk covers no nodes")
        previous = None
        chunk_set = set()
        chunk_values = [_exact_int(value, "planned node id") for value in ids]
        for node_id in chunk_values:
            if node_id not in index.parents:
                raise ContractRefusal("CHUNK_UNKNOWN_NODE",
                                      f"planned node {node_id} is not in this document")
            if previous is not None and node_id <= previous:
                raise ContractRefusal("CHUNK_COVERAGE_MISMATCH", "planned chunk ids must ascend")
            parent_id = index.parents[node_id]
            if parent_id != -1 and parent_id not in set(chunk_values):
                raise ContractRefusal("CHUNK_PLAN_OPEN_PARENT",
                                      f"planned node {node_id} needs parent {parent_id} in its chunk")
            if node_id in owned and node_id not in shared_ids:
                raise ContractRefusal("CHUNK_PLAN_OVERLAP",
                                      f"node {node_id} is owned by more than one chunk "
                                      f"and is not inside a declared shared root")
            if node_id in chunk_set:
                raise ContractRefusal("CHUNK_PLAN_OVERLAP",
                                      f"node {node_id} appears twice in one chunk")
            chunk_set.add(node_id)
            previous = node_id
        for node_id in chunk_set:
            owned.setdefault(node_id, []).append(len(ordered))
        ordered.append(tuple(sorted(chunk_set)))

    for root in roots:
        members = set(index.subtree(root))
        if not any(members <= set(ids) for ids in ordered):
            raise ContractRefusal("CHUNK_PLAN_SHARED_NOT_PLANNED",
                                  f"shared root {root} is not whole inside any planned chunk")
    missing = [node_id for node_id in index.ids if node_id not in owned]
    if missing:
        raise ContractRefusal("CHUNK_PLAN_INCOMPLETE",
                              f"{len(missing)} document node(s) are in no chunk, first {missing[0]}")
    signature_ids = frozenset(_exact_int(value, "signature provenance id")
                              for value in signatures)
    for value in signature_ids:
        if value not in index.parents:
            raise ContractRefusal("CHUNK_COVERAGE_MISMATCH",
                                  f"signature provenance names unknown node {value}")

    plan = ChunkPlan.__new__(ChunkPlan)
    plan.index = index
    plan.document = index.document
    plan.revision = index.revision
    plan.shared_roots = roots
    plan.chunk_ids = tuple(ordered)
    plan.signatures = signature_ids
    plan._shared_ids = frozenset(shared_ids)
    return plan


def chunk_record(plan, position, nodes, report, supplied_signatures=()):
    """Build the versioned envelope the host hands on.

    ``nodes`` and ``report`` are values the host already holds; this binder
    never re-derives their contents, it only binds them to the plan.
    """
    covered = plan.node_ids(position)
    return {
        "version": CONTRACT_VERSION,
        "document": plan.document,
        "revision": plan.revision,
        "index": position,
        "coveredNodeIds": list(covered),
        "nodes": list(nodes),
        "report": report,
        "suppliedSignatures": list(supplied_signatures),
    }


def validate_chunk(plan, chunk):
    """Refuse a chunk that is not exactly the planned piece of this revision."""
    if not isinstance(chunk, dict):
        raise ContractRefusal("CHUNK_COVERAGE_MISMATCH", "chunk is not a mapping")
    if chunk.get("version") != CONTRACT_VERSION:
        raise ContractRefusal("CHUNK_VERSION_UNKNOWN",
                              f"chunk version {chunk.get('version')!r} is not {CONTRACT_VERSION}")
    if chunk.get("document") != plan.document or chunk.get("revision") != plan.revision:
        raise ContractRefusal("CHUNK_STALE_REVISION",
                              "chunk document or revision is not the planned target")
    position = _chunk_int(chunk.get("index"), "chunk index")
    planned = plan.node_ids(position)

    covered = chunk.get("coveredNodeIds")
    if not isinstance(covered, list):
        raise ContractRefusal("CHUNK_COVERAGE_MISMATCH", "coveredNodeIds is not a list")
    covered = [_chunk_int(value, "covered node id") for value in covered]
    if covered != list(planned):
        raise ContractRefusal("CHUNK_COVERAGE_MISMATCH",
                              f"chunk {position} claims {len(covered)} ids, plan says {len(planned)}")

    actual, seen = [], set()
    for node in chunk.get("nodes") or []:
        node_id = _node_fields(node)["id"]
        if node_id in seen:
            raise ContractRefusal("CHUNK_DUPLICATE_NODE", f"chunk repeats node {node_id}")
        if node_id not in plan.index.parents:
            raise ContractRefusal("CHUNK_UNKNOWN_NODE",
                                  f"chunk node {node_id} is not in this document")
        seen.add(node_id)
        actual.append(node_id)
    if sorted(actual) != list(planned):
        missing = [node_id for node_id in planned if node_id not in seen]
        unplanned = [node_id for node_id in actual if node_id not in set(planned)]
        raise ContractRefusal("CHUNK_MISSING_NODE" if missing else "CHUNK_COVERAGE_MISMATCH",
                              f"chunk {position} missing {missing[:4]}, unplanned {unplanned[:4]}")

    planned_set = set(planned)
    for node in chunk["nodes"]:
        fields = _node_fields(node)
        parent_id = fields["parentId"]
        if parent_id != -1 and parent_id not in planned_set:
            raise ContractRefusal("CHUNK_OPEN_PARENT",
                                  f"chunk {position} node {fields['id']} needs parent {parent_id}")
        if parent_id >= fields["id"]:
            raise ContractRefusal("CHUNK_INVALID_PARENT_ORDER",
                                  f"chunk {position} node {fields['id']} has parent {parent_id} at or after it")
        if plan.index.parents[fields["id"]] != parent_id:
            raise ContractRefusal("CHUNK_INVALID_PARENT_ORDER",
                                  f"chunk {position} node {fields['id']} rewrote its parent")
        if fields["childIndex"] < 0:
            raise ContractRefusal("CHUNK_NEGATIVE_CHILD_INDEX",
                                  f"chunk {position} node {fields['id']} has childIndex {fields['childIndex']}")

    report = _fields(chunk.get("report"), "CheckerReport")
    if (_str_scalar(report["document"], "report document") != plan.document or
            _str_scalar(report["revision"], "report revision") != plan.revision):
        raise ContractRefusal("CHUNK_REPORT_MISMATCH",
                              f"chunk {position} report belongs to another revision")
    node_count = _int_scalar(report["syntaxNodeCount"], "report syntaxNodeCount")
    if node_count != len(planned):
        raise ContractRefusal("CHUNK_REPORT_COUNT_MISMATCH",
                              f"chunk {position} report covers {node_count} nodes, "
                              f"plan has {len(planned)}")
    status = _str_scalar(report["status"], "report status")
    if status not in REPORT_STATUSES:
        raise ContractRefusal("CHUNK_REPORT_STATUS_UNKNOWN",
                              f"chunk {position} report status {status!r} is unknown")

    supplied = chunk.get("suppliedSignatures") or []
    if not isinstance(supplied, list):
        raise ContractRefusal("CHUNK_COVERAGE_MISMATCH", "suppliedSignatures is not a list")
    supplied_ids = [_chunk_int(value, "supplied signature id") for value in supplied]
    if len(set(supplied_ids)) != len(supplied_ids):
        raise ContractRefusal("CHUNK_COVERAGE_MISMATCH", "suppliedSignatures contains duplicates")
    for value in supplied_ids:
        if value not in plan.signatures:
            raise ContractRefusal("CHUNK_UNSUPPLIED_SIGNATURE",
                                  f"chunk {position} cites signature {value} the checker never certified")
    return status


class ChunkLedger:
    """Host-held ordering, replay and coverage state for one plan.

    A stateless Pep function cannot remember what it already emitted, so the
    protocol layer holds the sequence. Nothing here inspects types; it only
    decides whether the sequence is complete, ordered and non-repeating.
    """

    def __init__(self, plan):
        self.plan = plan
        self.next_index = 0
        self.statuses = {}

    def accept(self, chunk):
        position = chunk.get("index") if isinstance(chunk, dict) else None
        if not isinstance(position, int) or not 0 <= position < self.plan.chunk_count:
            raise ContractRefusal("CHUNK_INDEX_OUT_OF_RANGE",
                                  f"chunk {position!r} is outside this plan")
        if position in self.statuses:
            raise ContractRefusal("CHUNK_REPEATED", f"chunk {position} was already accepted")
        if position != self.next_index:
            raise ContractRefusal("CHUNK_OUT_OF_ORDER",
                                  f"expected chunk {self.next_index}, received {position}")
        status = validate_chunk(self.plan, chunk)
        self.statuses[position] = status
        self.next_index += 1
        return status

    def complete(self):
        if self.next_index != self.plan.chunk_count:
            missing = [position for position in range(self.plan.chunk_count)
                       if position not in self.statuses]
            raise ContractRefusal("CHUNK_INCOMPLETE",
                                  f"{len(missing)} chunk(s) never arrived, first {missing[0]}")
        statuses = [self.statuses[position] for position in range(self.plan.chunk_count)]
        if "invalid" in statuses:
            overall = "invalid"
        elif "incomplete" in statuses:
            overall = "incomplete"
        else:
            overall = "valid"
        return {"version": CONTRACT_VERSION, "document": self.plan.document,
                "revision": self.plan.revision, "chunkCount": self.plan.chunk_count,
                "nodeCount": sum(len(ids) for ids in self.plan.chunk_ids),
                "status": overall, "chunks": dict(sorted(self.statuses.items()))}
