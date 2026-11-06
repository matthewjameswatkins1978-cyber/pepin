"""Typed-bound function-unit records (A1 draft amendment, additive module).

 implements the record layer proposed in
docs/CHECKED_CHUNK_CONTRACT_TYPED_BOUND_DRAFT.md: one decomposed function is
covered by an exact tiling of statement-range units, each checked through the
existing ``bound-chunk`` (``analyze_chunk_typed_bound``) tool with carried
``BindingPool`` facts, and recorded fail-closed host-side.

Design constraints (deliberate):
- NEW module: ``pep_chunk_contract.py`` is frozen and its header says the
  partition layer must not grow scope logic; this file adds none either —
  it is ordering/coverage arithmetic over the checker's OWN reports;
- only EXISTING contract refusal codes are reused (``CHUNK_COVERAGE_MISMATCH``,
  ``CHUNK_INCOMPLETE``) so the refused-vocabulary stays frozen;
- fail-closed carry: bindings are admitted to the pool ONLY from a unit whose
  report is ``valid`` with zero diagnostics; an unverified unit never funds a
  later one;
- ``first_refusal`` preserves the first failing unit (position, status, codes)
  as the first refusing layer for the receipt.

Measured on the real lexer (codex/a1-typed-bound-pipeline@04573c9): utf8_check
21/21 statement units valid, steps 15,896-89,918, 9 bindings carried.
"""
import pep_chunk_contract as contract


def _fields(value, type_name):
    return {f["name"]: f["value"] for f in value.get("fields", [])}


class FunctionUnits:
    """Host-side record for one decomposed function of one document revision."""

    def __init__(self, index, function_id, pool=None):
        self.index = index
        self.function_id = function_id
        self.pool = pool if pool is not None else contract.BindingPool(
            index.document, index.revision)
        self.statements = index.statement_children(function_id)
        self.total = len(self.statements)
        self.covered = {}          # statement position -> unit label
        self.units = []            # accepted/observed unit records, in order
        self.terminal_seen = False
        self.first_refusal = None  # (position, status, codes, label)

    # -- planning side ---------------------------------------------------
    def check_range(self, lo, hi):
        """Validate a half-open statement range against the tiling so far."""
        if not (0 <= lo < hi <= self.total):
            raise contract.ContractRefusal(
                "CHUNK_COVERAGE_MISMATCH",
                f"unit range [{lo}, {hi}) outside this function's "
                f"{self.total} statement(s)")
        if any(pos in self.covered for pos in range(lo, hi)):
            raise contract.ContractRefusal(
                "CHUNK_COVERAGE_MISMATCH",
                f"unit range [{lo}, {hi}) overlaps already-covered statements")
        return True

    def unit_ids(self, lo, hi, carriers=()):
        """Slice ids for one unit: header + statement subtrees [lo, hi)."""
        self.check_range(lo, hi)
        groups = [("unit", lo, hi, tuple(carriers), False)]
        for label, ids, expect_returns in self.index.bounded_units(
                self.function_id, groups=groups):
            return ids, expect_returns
        raise contract.ContractRefusal(
            "CHUNK_COVERAGE_MISMATCH", f"no unit produced for [{lo}, {hi})")

    # -- acceptance side ------------------------------------------------
    def terminal_ids(self, lo, hi, carriers=()):
        """The terminal (last) unit: expect_returns=True, whole-range statement."""
        self.check_range(lo, hi)
        if hi != self.total:
            raise contract.ContractRefusal(
                "CHUNK_COVERAGE_MISMATCH",
                f"terminal unit [{lo}, {hi}) does not end at the function body")
        groups = [("terminal", lo, hi, tuple(carriers), True)]
        for label, ids, expect_returns in self.index.bounded_units(
                self.function_id, groups=groups):
            return ids, expect_returns
        raise contract.ContractRefusal(
            "CHUNK_COVERAGE_MISMATCH", f"no terminal unit for [{lo}, {hi})")

    def accept(self, lo, hi, report, codes, label="unit", terminal=False):
        """Record one checked unit. Fail-closed carry; first refusal sticks.

        ``report`` is the flattened checker report (or None when the tool
        refused at transport level); ``codes`` its diagnostic codes. A unit
        marked ``terminal`` must close the body (``hi == total``). MEASURED
        note (A1 2026-11-06): driving the checker with
        ``expect_returns=True`` on a squeezed terminal slice costs more and
        can cross the 100k-step ceiling (utf8_check group 20 measured), so
        the record does NOT require checker-level terminality; instead the
        LAST unit must cover the body's final statements structurally, and
        the missing-return semantic residual is recorded in the draft
        amendment rather than hidden.
        """
        self.check_range(lo, hi)
        if terminal:
            if hi != self.total:
                raise contract.ContractRefusal(
                    "CHUNK_COVERAGE_MISMATCH",
                    f"terminal unit [{lo}, {hi}) does not end at the "
                    f"function body")
            self.terminal_seen = True
        status = None
        bindings_value = []
        if report is not None:
            if "fields" in report:  # typed form {type, fields}
                flat = _fields(report, "CheckerReport")
            else:  # already flattened (fields_map output, the harness form)
                flat = report
            status = (flat.get("status") or {}).get("value")
            bindings_value = (flat.get("bindings") or {}).get("value", []) or []
        clean = (report is not None and status == "valid" and not codes)
        entry = {"label": label, "lo": lo, "hi": hi, "status": status,
                 "codes": sorted(set(codes))[:3], "terminal": terminal}
        if clean:
            carried = self.pool.add(bindings_value)
            entry["bindings_carried"] = carried
            if terminal:
                entry["checker_expect_returns"] = False
        else:
            entry["bindings_carried"] = 0
            if self.first_refusal is None:
                self.first_refusal = {"lo": lo, "hi": hi, "label": label,
                                      "status": status if status else "refused",
                                      "codes": sorted(set(codes))[:3]}
        self.units.append(entry)
        for pos in range(lo, hi):
            self.covered[pos] = label
        return entry

    # -- totality --------------------------------------------------------
    def complete(self):
        """Refuse until the tiling is exact and every unit was clean."""
        if self.total == 0:
            raise contract.ContractRefusal(
                "CHUNK_COVERAGE_MISMATCH", "function has no statements to cover")
        missing = [pos for pos in range(self.total) if pos not in self.covered]
        if missing:
            raise contract.ContractRefusal(
                "CHUNK_INCOMPLETE",
                f"{len(missing)} statement(s) not covered, first {missing[0]}")
        last = max(self.units, key=lambda u: u["hi"])
        return {
            "functionId": self.function_id,
            "document": self.index.document,
            "revision": self.index.revision,
            "statementCount": self.total,
            "unitCount": len(self.units),
            "status": "invalid" if self.first_refusal else "valid",
            "first_refusal": self.first_refusal,
            "bindingsCarried": len(self.pool.facts()),
            "units": list(self.units),
        }
