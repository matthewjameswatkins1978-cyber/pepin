"""Small, grammar-aware Pep corpus generator and integer reference model.

This module deliberately does not parse Pep.  It builds only a reviewed subset
of the public seed grammar, then records enough structure to make each case
replayable without relying on the compiler's own AST.  The reference integer
model is also intentionally independent: Python's unbounded integers are
constrained to Pep's signed 64-bit contract here.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Callable, Iterable


INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1


class ArithmeticFault(Exception):
    """A checked Pep integer operation failed."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def checked_int(value: int) -> int:
    if value < INT_MIN or value > INT_MAX:
        raise ArithmeticFault("PEP_RUNTIME_OVERFLOW")
    return value


def checked_add(left: int, right: int) -> int:
    return checked_int(left + right)


def checked_sub(left: int, right: int) -> int:
    return checked_int(left - right)


def checked_mul(left: int, right: int) -> int:
    return checked_int(left * right)


def checked_neg(value: int) -> int:
    return checked_int(-value)


def checked_div(left: int, right: int) -> int:
    if right == 0:
        raise ArithmeticFault("PEP_RUNTIME_DIVISION_BY_ZERO")
    if left == INT_MIN and right == -1:
        raise ArithmeticFault("PEP_RUNTIME_OVERFLOW")
    # Pep division truncates toward zero, unlike Python's // for negatives.
    quotient = abs(left) // abs(right)
    return -quotient if (left < 0) != (right < 0) else quotient


@dataclass(frozen=True)
class GeneratedCase:
    case_id: str
    seed: int
    index: int
    family: str
    validity: str
    source: bytes
    expected_output: str | None = None
    expected_statuses: tuple[str, ...] = ("valid",)
    expected_reason: str | None = None
    depth: int = 0
    node_count: int = 0

    def as_record(self) -> dict[str, object]:
        """Stable machine-readable case metadata for results and replay."""
        return {
            "caseId": self.case_id,
            "seed": self.seed,
            "index": self.index,
            "family": self.family,
            "validity": self.validity,
            "sourceBytes": len(self.source),
            "expectedOutput": self.expected_output,
            "expectedStatuses": list(self.expected_statuses),
            "expectedReason": self.expected_reason,
            "depth": self.depth,
            "nodeCount": self.node_count,
        }


@dataclass(frozen=True)
class BoundaryVector:
    name: str
    operation: str
    left: int
    right: int | None
    value: int | None
    error_code: str | None


def boundary_vectors() -> tuple[BoundaryVector, ...]:
    """Return fixed edge vectors used by both unit tests and reports."""
    vectors: list[BoundaryVector] = []
    operations: tuple[tuple[str, Callable[..., int], int, int | None], ...] = (
        ("add-max", checked_add, INT_MAX, 0),
        ("add-overflow", checked_add, INT_MAX, 1),
        ("sub-min", checked_sub, INT_MIN, 0),
        ("sub-overflow", checked_sub, INT_MIN, 1),
        ("mul-min", checked_mul, INT_MIN, 1),
        ("mul-overflow", checked_mul, INT_MAX, 2),
        ("div-min", checked_div, INT_MIN, 1),
        ("div-overflow", checked_div, INT_MIN, -1),
        ("div-zero", checked_div, 1, 0),
        ("neg-min", checked_neg, INT_MIN, None),
    )
    for name, operation, left, right in operations:
        try:
            value = operation(left) if right is None else operation(left, right)
        except ArithmeticFault as fault:
            vectors.append(BoundaryVector(name, operation.__name__, left, right, None, fault.code))
        else:
            vectors.append(BoundaryVector(name, operation.__name__, left, right, value, None))
    return tuple(vectors)


def _int_expr(rng: random.Random, depth: int) -> tuple[str, int, int]:
    """Build a bounded arithmetic expression, returning source/value/node count."""
    if depth <= 0:
        value = rng.randint(-12, 12)
        return str(value), value, 1
    left_source, left_value, left_nodes = _int_expr(rng, depth - 1)
    right_source, right_value, right_nodes = _int_expr(rng, depth - 1)
    operator = rng.choice(("+", "-", "*", "/"))
    if operator == "/" and right_value == 0:
        right_source, right_value, right_nodes = "1", 1, 1
    operation = {"+": checked_add, "-": checked_sub, "*": checked_mul, "/": checked_div}[operator]
    value = operation(left_value, right_value)
    return f"({left_source} {operator} {right_source})", value, left_nodes + right_nodes + 1


def _bool_expr(rng: random.Random, depth: int) -> tuple[str, bool, int]:
    if depth <= 0:
        left = rng.randint(-5, 5)
        right = rng.randint(-5, 5)
        # The seed grammar exposes only the two-character ordered operators;
        # bare < and > are deliberately not lexer tokens.
        op = rng.choice(("==", "!=", "<=", ">="))
        value = {"==": left == right, "!=": left != right,
                 "<=": left <= right, ">=": left >= right}[op]
        return f"{left} {op} {right}", value, 1
    left_source, left_value, left_nodes = _bool_expr(rng, depth - 1)
    right_source, right_value, right_nodes = _bool_expr(rng, depth - 1)
    op = rng.choice(("&&", "||"))
    value = left_value and right_value if op == "&&" else left_value or right_value
    return f"({left_source} {op} {right_source})", value, left_nodes + right_nodes + 1


def _valid_source(rng: random.Random, index: int, depth: int) -> tuple[str, str, str, int]:
    family = index % 6
    if family == 0:
        expression, value, nodes = _int_expr(rng, depth)
        return "arithmetic", f"say(int_text({expression}))\n", f"{value}\n", nodes
    if family == 1:
        condition, value, nodes = _bool_expr(rng, max(0, depth - 1))
        chosen = rng.randint(-20, 20)
        other = rng.randint(-20, 20)
        expected = chosen if value else other
        return "boolean-control", f"say(int_text(if {condition} {{ {chosen} }} else {{ {other} }}))\n", f"{expected}\n", nodes + 2
    if family == 2:
        left, right = rng.randint(-20, 20), rng.randint(-20, 20)
        source = (
            "type Point { x: Int y: Int }\n"
            "fn sum(point: Point) -> Int { return point.x + point.y }\n"
            f"say(int_text(sum(Point {{ x: {left}, y: {right} }})))\n"
        )
        return "records", source, f"{left + right}\n", 8
    if family == 3:
        left, right = rng.randint(-20, 20), rng.randint(-20, 20)
        source = (
            "type Expr = Number(Int) | Add(Expr, Expr)\n"
            "fn evaluate(expr: Expr) -> Int {\n"
            "    return match expr {\n"
            "        Number(n) => n\n"
            "        Add(a, b) => evaluate(a) + evaluate(b)\n"
            "    }\n"
            "}\n"
            f"say(int_text(evaluate(Add(Number({left}), Number({right})))))\n"
        )
        return "recursive-union-match", source, f"{left + right}\n", 12
    if family == 4:
        values = [rng.randint(-5, 9) for _ in range(1 + rng.randrange(3))]
        text = ", ".join(map(str, values))
        source = (
            "fn sum(values: List[Int]) -> Int {\n"
            "    var total = 0\n"
            "    for value in values { total = total + value }\n"
            "    return total\n"
            "}\n"
            f"say(int_text(sum([{text}])))\n"
        )
        return "lists-for-in", source, f"{sum(values)}\n", 7 + len(values)
    value = rng.randint(-20, 20)
    source = (
        "fn shadow(value: Int) -> Int {\n"
        "    let inner: Int = value + 1\n"
        "    { let inner: Int = inner + 1; return inner }\n"
        "}\n"
        f"say(int_text(shadow({value})))\n"
    )
    return "lexical-shadowing", source, f"{value + 2}\n", 9


def _invalid_source(valid_source: str, index: int) -> tuple[str, str, str]:
    line_end = "\r\n" if valid_source.endswith("\r\n") else "\n"
    complete = valid_source[:-len(line_end)] if valid_source.endswith(line_end) else valid_source
    truncated = complete[:-1] + line_end
    variants = (
        ("say(int_text(1)]\n", "malformed delimiter"),
        ("let value: Int = \"wrong\"\n", "type mismatch"),
        ("say(missing_name)\n", "unknown name"),
        ("say(int_text(?answer))\n", "typed hole"),
        ("say(int_text(9223372036854775808))\n", "integer literal range"),
        (truncated, "unexpected EOF"),
    )
    source, reason = variants[index % len(variants)]
    return "invalid-" + reason.replace(" ", "-"), source, reason


def generate_cases(seed: int, count: int, depth: int = 2) -> tuple[GeneratedCase, ...]:
    """Generate ``count`` valid and ``count`` malformed grammar cases.

    The order is stable: valid then its paired invalid variation.  This makes
    a single case ID sufficient to reproduce a result without hidden global
    RNG state.
    """
    if count < 0:
        raise ValueError("count must be nonnegative")
    if depth < 0 or depth > 5:
        raise ValueError("depth must be between 0 and 5")
    rng = random.Random(seed)
    cases: list[GeneratedCase] = []
    for index in range(count):
        family, source, output, nodes = _valid_source(rng, index, depth)
        newline = "\r\n" if index % 3 == 2 else "\n"
        source = source.replace("\n", newline)
        valid_id = f"grammar-valid-{seed}-{index:04d}"
        cases.append(GeneratedCase(valid_id, seed, index, family, "valid",
                                   source.encode("utf-8"), output, ("valid",),
                                   depth=depth, node_count=nodes))
        invalid_family, invalid, reason = _invalid_source(source, index)
        invalid_id = f"grammar-invalid-{seed}-{index:04d}"
        cases.append(GeneratedCase(invalid_id, seed, index, invalid_family, "invalid",
                                   invalid.encode("utf-8"), None, ("invalid", "incomplete"),
                                   reason, depth=depth, node_count=nodes))
    return tuple(cases)


def describe_corpus(seeds: Iterable[int], count: int, depth: int) -> dict[str, object]:
    cases = [case for seed in seeds for case in generate_cases(seed, count, depth)]
    return {
        "seeds": list(seeds),
        "countPerSeed": count,
        "depth": depth,
        "total": len(cases),
        "valid": sum(case.validity == "valid" for case in cases),
        "invalid": sum(case.validity == "invalid" for case in cases),
        "families": sorted({case.family for case in cases}),
    }
