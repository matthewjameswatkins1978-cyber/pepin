"""WHICH construct makes the checker expensive?

`probe_staged_budget_ceiling.py` established that the checker, not the parser or the
emitter, is the binding constraint in the staged path: it handles ~335 bytes and then
hits PEP_RUNTIME_STEP_LIMIT.

That is only half the information a staged-descent design needs. "335 bytes" does not
say whether the cost is per function, per statement, per call, per binding or per
type. This probe measures the checker's ceiling for several CONSTRUCT SHAPES at the
same source size, so the dominant term is visible.

Method: for each shape, build programs of increasing size, run parse -> check, and
report the first size at which the checker refuses. Parse alone is known to handle
>=2575 bytes, so a check failure here is the checker's cost, not the parser's.

Run: python tests/probe_checker_cost_shape.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402


def trivial_functions(count):
    body = "".join(f"fn f{index}() -> Int {{ return {index} }}\n" for index in range(count))
    return body + "fn main() -> Int { return f0() }\n"


def let_bindings(count):
    body = "".join(f"  let v{index} = {index}\n" for index in range(count))
    return f"fn main() -> Int {{\n{body}  return v0\n}}\n"


def call_chain(count):
    body = "".join(f"fn g{index}(n: Int) -> Int {{ return n }}\n" for index in range(count))
    calls = "".join(f"  let r{index} = g{index}(1)\n" for index in range(count))
    return body + f"fn main() -> Int {{\n{calls}  return r0\n}}\n"


def if_statements(count):
    body = "".join(f"  if {index} <= {index} {{ }} else {{ }}\n" for index in range(count))
    return f"fn main() -> Int {{\n{body}  return 0\n}}\n"


SHAPES = {
    "trivial-functions": trivial_functions,
    "let-bindings": let_bindings,
    "call-chain": call_chain,
    "if-statements": if_statements,
}

SIZES = [2, 4, 8, 16, 32, 64]


def check_only(session, revision, source, label):
    """parse -> check. Returns a named outcome; never raises."""
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    if target.get("outcome") != "ok":
        return "open:" + str((target.get("error") or {}).get("code"))
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    try:
        parsed = parse_target(session, payload, target, revision)
    except Exception as error:  # noqa: BLE001
        text = str(error)
        for code in ("PEP_RUNTIME_STEP_LIMIT", "PEP_TOOL_VALUE_LIMIT",
                     "PEP_SOURCE_BYTE_LIMIT"):
            if code in text:
                return "parse:" + code
        return "parse-failed"
    try:
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
    except RuntimeError as error:
        return "transport:" + str(error)[:40]
    if checked.get("outcome") != "ok":
        return (checked.get("error") or {}).get("code")
    fields = {f["name"]: f["value"] for f in checked["result"]["fields"]}
    return fields["status"]["value"]


def main():
    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")

        spec = importlib.util.spec_from_file_location(
            "pic", ROOT / "tests" / "probe_integration_case.py")
        pic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pic)
        pic.register(session, document, revision, sample["document"], sample["revision"])

        print(f"{'shape':<20} | {'largest OK':>22} | first refusal")
        for name, builder in SHAPES.items():
            largest_ok = None
            first_refusal = None
            for size in SIZES:
                source = builder(size)
                outcome = check_only(session, revision, source, f"{name}-{size}")
                if outcome == "valid":
                    largest_ok = (size, len(source.encode("utf-8")))
                else:
                    first_refusal = (size, len(source.encode("utf-8")), outcome)
                    break
            ok_text = (f"{largest_ok[0]} units / {largest_ok[1]} bytes"
                       if largest_ok else "none")
            bad_text = (f"{first_refusal[0]} units / {first_refusal[1]} bytes -> "
                        f"{first_refusal[2]}" if first_refusal else "none in range")
            print(f"{name:<20} | {ok_text:>22} | {bad_text}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
