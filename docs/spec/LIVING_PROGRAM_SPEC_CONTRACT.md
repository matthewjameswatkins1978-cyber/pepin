# Living Program Specification Contract
**Standard:** PEP-SPEC-LIVING-001  
**Status:** Canonical Living Specification Contract  
**Purpose:** Formalise program-level intent, requirements, and evidence linkage in Pepin projects.

---

## 1. Motivation

In traditional software development, specifications drift from code, and agent-assisted workflows frequently suffer from "hallucinated compliance" where an LLM rewrites the intent to match broken code.

Pepin introduces **Living Program Specifications**:
1. Specifications are machine-readable, versioned artifacts stored alongside code (e.g. `spec.json` or `.spec.md`).
2. Every requirement has an immutable, unique ID (`REQ-<DOMAIN>-<NUM>`).
3. The compiler's **Semantic Map** verifies the integrity of links between:
   $$\text{Requirement ID} \longleftrightarrow \text{Code Symbols} \longleftrightarrow \text{Test Assertions}$$
4. Natural language intent remains authored by humans or AI planners, but link integrity and verification status are mechanically proved.

---

## 2. Specification Schema

A Living Program Specification is represented as a structured JSON object (or companion Markdown frontmatter):

```json
{
  "$schema": "https://pepin.lang/schemas/living-spec-v1.json",
  "project": "pepin",
  "specVersion": "1.0.0",
  "title": "Module Title",
  "purpose": "Precise summary of the problem this software solves.",
  "nonGoals": [
    "Explicitly excluded capabilities or responsibilities."
  ],
  "requirements": [
    {
      "id": "REQ-CALC-001",
      "title": "Integer Factorial Calculation",
      "description": "Compute the factorial of a non-negative 64-bit integer.",
      "level": "MUST",
      "status": "VERIFIED",
      "symbols": ["factorial", "factorial_iter"],
      "tests": ["tests/test_calc.py::test_factorial_positive", "tests/test_calc.py::test_factorial_zero"],
      "invariants": [
        "factorial(0) == 1",
        "factorial(n) == n * factorial(n - 1) for n > 0"
      ],
      "failureModes": [
        {
          "condition": "n < 0",
          "behavior": "Panic or return error code PEP_INVALID_ARGUMENT"
        },
        {
          "condition": "n > 20",
          "behavior": "Integer overflow diagnostic or error"
        }
      ]
    }
  ],
  "dataContracts": [
    {
      "typeName": "CalcResult",
      "description": "Result structure carrying computed value or error."
    }
  ],
  "epistemicStatus": {
    "verifiedCount": 1,
    "unimplementedCount": 0,
    "staleCount": 0
  }
}
```

---

## 3. Requirement Lifecycle

A requirement progresses through strict, observable states:

| State | Definition | Preconditions |
|---|---|---|
| `DRAFT` | Proposed requirement under active framing. | Assigned unique ID; description complete. |
| `ACCEPTED` | Normatively approved by project authority. | Matthew / human acceptance; non-goals defined. |
| `IMPLEMENTED` | Code symbols exist in the AST satisfying the contract. | Compiler verifies symbol names and types exist. |
| `TESTED` | Concrete automated tests exist and pass against the symbols. | Test runner reports green on specific revision SHA. |
| `VERIFIED` | Both positive and negative boundary tests verified by independent oracle. | Verified against regressions; epistemic verdict `ESTABLISHED`. |
| `STALE` | Implementing symbols or tests modified since last verification. | Semantic Map detects code hash or symbol signature change. |
| `SUPERSEDED` | Replaced by a newer requirement ID. | Pointer to replacement requirement ID. |

---

## 4. Semantic Map Linkage Rules

1. **Link Completeness:** The Semantic Map must flag any requirement whose declared `symbols` do not exist in the checked AST.
2. **Orphan Symbol Detection:** The Semantic Map can report public functions or types that have no associated requirement ID.
3. **Conservative Invalidation:** If symbol $S$ is edited in revision $R_2$, all requirements referencing $S$ transition from `VERIFIED` to `STALE` until tests are re-run.
4. **Oracle Integrity:** Modifying a test file is treated as an oracle revision. Test modifications cannot silently manufacture a pass without explicit notice in the test receipt.
