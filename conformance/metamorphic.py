"""Validated source-level metamorphic relations for the conformance lab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

try:
    from .generator import GeneratedCase
except ImportError:  # Running the harness as a direct repository script.
    from generator import GeneratedCase


@dataclass(frozen=True)
class MetamorphicPair:
    pair_id: str
    origin_case_id: str
    relation: str
    original: bytes
    transformed: bytes
    expected_output: str


def _line_ending(raw: bytes) -> bytes:
    return b"\r\n" if b"\r\n" not in raw else b"\n"


def _with_line_ending(raw: bytes, ending: bytes) -> bytes:
    text = raw.replace(b"\r\n", b"\n")
    return ending.join(text.split(b"\n"))


def _with_comments(raw: bytes) -> bytes:
    """Add lexer comments only at line ends; generated sources have no strings."""
    output: list[bytes] = []
    for line in raw.replace(b"\r\n", b"\n").split(b"\n"):
        if line.strip():
            output.append(line + b" # metamorphic-comment")
        else:
            output.append(line)
    ending = b"\r\n" if b"\r\n" in raw else b"\n"
    return ending.join(output)


def pairs_for_case(case: GeneratedCase) -> tuple[MetamorphicPair, ...]:
    """Return only relations with a reviewed validity precondition."""
    if case.validity != "valid" or case.expected_output is None:
        return ()
    pairs: list[MetamorphicPair] = []
    alternate_ending = _line_ending(case.source)
    line_variant = _with_line_ending(case.source, alternate_ending)
    if line_variant != case.source:
        pairs.append(MetamorphicPair(case.case_id + "-crlf", case.case_id,
                                     "line-ending", case.source, line_variant,
                                     case.expected_output))
    comment_variant = _with_comments(case.source)
    if comment_variant != case.source:
        pairs.append(MetamorphicPair(case.case_id + "-comments", case.case_id,
                                     "trailing-comments", case.source, comment_variant,
                                     case.expected_output))
    return tuple(pairs)


def semantic_signature(value: Any) -> Any:
    """Drop source-location and revision identity fields before comparison."""
    if isinstance(value, dict):
        return {key: semantic_signature(item) for key, item in sorted(value.items())
                if key not in {"span", "identity", "revision"}}
    if isinstance(value, list):
        return [semantic_signature(item) for item in value]
    return value


def compare_pair(original: dict[str, Any], transformed: dict[str, Any],
                 original_output: str | None = None,
                 transformed_output: str | None = None,
                 expected_output: str | None = None) -> dict[str, Any]:
    """Pure oracle used by the runner and synthetic mismatch tests."""
    if original.get("status") != "completed" or transformed.get("status") != "completed":
        return {"classification": "infrastructure-failure", "detail": "metamorphic process did not complete"}
    if original.get("returncode") is None or transformed.get("returncode") is None:
        return {"classification": "infrastructure-failure", "detail": "metamorphic process did not return an exit code"}
    if original.get("returncode") != transformed.get("returncode"):
        return {"classification": "confirmed-bug", "detail": "metamorphic return codes differ"}
    if original.get("returncode") != 0:
        return {"classification": "confirmed-bug", "detail": "completed metamorphic process returned a nonzero exit code",
                "originalReturncode": original.get("returncode"),
                "transformedReturncode": transformed.get("returncode")}
    if (expected_output is not None and
            (original_output != expected_output or transformed_output != expected_output)):
        return {"classification": "confirmed-bug", "detail": "metamorphic runtime output disagrees with the independent expected output",
                "expected": expected_output, "originalOutput": original_output,
                "transformedOutput": transformed_output}
    left = semantic_signature(original.get("response"))
    right = semantic_signature(transformed.get("response"))
    if left != right:
        return {"classification": "confirmed-bug", "detail": "metamorphic semantic responses differ",
                "original": left, "transformed": right}
    if original_output is not None and transformed_output is not None and original_output != transformed_output:
        return {"classification": "confirmed-bug", "detail": "metamorphic runtime outputs differ",
                "originalOutput": original_output, "transformedOutput": transformed_output}
    return {"classification": "missing-test", "detail": "metamorphic relation preserved"}


def pairs_for_cases(cases: Iterable[GeneratedCase]) -> tuple[MetamorphicPair, ...]:
    return tuple(pair for case in cases for pair in pairs_for_case(case))
