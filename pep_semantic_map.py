#!/usr/bin/env python3
"""
Pepin Semantic Map & Living Specification Engine
Standard: PEP-SPEC-LIVING-001 / PEP-AG-20261120-01

Exposes compiler-derived knowledge:
  - Symbol declarations, types, and scopes
  - Call graph and transitive reachability
  - Living Program Specification links (Requirements <-> Symbols <-> Tests)
  - Behavioural Map: Test indexing and conservative affected-test calculation
  - Dependency-Complete Context Packets (token-budgeted for AI agents)
  - Deterministic Mechanical Repair Plans
  - Multi-Agent Semantic Conflict Detection
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = pathlib.Path(__file__).resolve().parent
PEP_CLI = ROOT / "pep.ps1"


def run_pep_cmd(*args: str, cwd: Optional[pathlib.Path] = None) -> Tuple[int, str, str]:
    """Execute pep.ps1 command and capture stdout/stderr."""
    command = ["pwsh", "-NoProfile", "-File", str(PEP_CLI), *args]
    res = subprocess.run(command, cwd=str(cwd or ROOT), capture_output=True, text=True, encoding="utf-8")
    return res.returncode, res.stdout, res.stderr


class SemanticMap:
    def __init__(self, source_path: pathlib.Path, spec_path: Optional[pathlib.Path] = None):
        self.source_path = source_path.resolve()
        self.spec_path = spec_path.resolve() if spec_path else self._find_companion_spec()
        self.source_text = self.source_path.read_text(encoding="utf-8")
        self.source_hash = hashlib.sha256(self.source_text.encode("utf-8")).hexdigest()
        
        self.ast: Dict[str, Any] = {}
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self.types: Dict[str, Dict[str, Any]] = {}
        self.calls: List[Dict[str, Any]] = []
        self.call_graph: Dict[str, Set[str]] = {}
        self.caller_graph: Dict[str, Set[str]] = {}
        
        self.spec: Optional[Dict[str, Any]] = None
        self.requirements: Dict[str, Dict[str, Any]] = {}
        self.test_index: Dict[str, List[Dict[str, Any]]] = {}  # symbol -> list of tests
        
        self._load_and_analyze()

    def _find_companion_spec(self) -> Optional[pathlib.Path]:
        candidates = [
            self.source_path.with_suffix(".spec.json"),
            self.source_path.parent / "spec.json",
            self.source_path.parent / (self.source_path.stem + "_spec.json"),
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    def _load_and_analyze(self):
        # 1. Run pep.ps1 inspect --json
        code, stdout, stderr = run_pep_cmd("inspect", str(self.source_path), "--json")
        if code != 0 or not stdout.strip():
            # Fallback to local regex-based AST extraction if compiler is building or syntax is partial
            self._extract_ast_fallback()
        else:
            try:
                self.ast = json.loads(stdout)
                self._extract_symbols_from_ast()
            except json.JSONDecodeError:
                self._extract_ast_fallback()

        # 2. Load living specification if present
        if self.spec_path and self.spec_path.is_file():
            try:
                self.spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
                for req in self.spec.get("requirements", []):
                    req_id = req.get("id")
                    if req_id:
                        self.requirements[req_id] = req
                        for sym in req.get("symbols", []):
                            for test in req.get("tests", []):
                                self.test_index.setdefault(sym, []).append({
                                    "test": test,
                                    "requirement": req_id
                                })
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to parse spec file {self.spec_path}: {e}\n")

    def _extract_symbols_from_ast(self):
        # Support both 'ast' and 'program' keys
        items = self.ast.get("ast") or self.ast.get("program") or []
        for item in items:
            kind = item.get("kind") or item.get("type")
            if kind in ("function", "TopFun"):
                fn = item.get("func", item)
                name = fn.get("name") or fn.get("fname", "")
                
                params = []
                for p in fn.get("parameters") or fn.get("params") or []:
                    if isinstance(p, dict):
                        params.append({"name": p.get("name", ""), "type": p.get("type", "Int"), "span": p.get("span", {})})
                    elif isinstance(p, (list, tuple)) and len(p) >= 2:
                        params.append({"name": p[0], "type": p[1], "span": p[2] if len(p) > 2 else {}})
                
                ret_type = fn.get("returnType") or fn.get("result", "Unit")
                fspan = fn.get("span") or fn.get("fspan", {})
                body = fn.get("body", [])
                
                self.symbols[name] = {
                    "kind": "function",
                    "name": name,
                    "params": params,
                    "returns": ret_type,
                    "span": fspan,
                    "body": body,
                }
                self.call_graph.setdefault(name, set())
                self.caller_graph.setdefault(name, set())
                self._extract_calls_from_statements(name, body)

            elif kind in ("record", "union", "TopType"):
                decl = item.get("decl", item)
                tname = decl.get("name", "")
                self.types[tname] = {
                    "kind": decl.get("kind", kind),
                    "name": tname,
                    "span": decl.get("span", {}),
                    "details": decl
                }

    def _extract_calls_from_statements(self, caller: str, stmts: List[Dict[str, Any]]):
        def walk_node(node: Any):
            if not isinstance(node, dict):
                return
            kind = node.get("kind") or node.get("type", "")
            if kind in ("call", "ECall"):
                callee = node.get("name") or node.get("fname", "")
                if callee:
                    self.calls.append({"caller": caller, "callee": callee, "span": node.get("span", {})})
                    self.call_graph.setdefault(caller, set()).add(callee)
                    self.caller_graph.setdefault(callee, set()).add(caller)
                for arg in node.get("arguments") or node.get("args") or []:
                    walk_node(arg)
            for k, v in node.items():
                if k in ("name", "kind", "type", "operator"):
                    continue
                if isinstance(v, dict):
                    walk_node(v)
                elif isinstance(v, list):
                    for el in v:
                        if isinstance(el, dict):
                            walk_node(el)

        for stmt in stmts:
            walk_node(stmt)

    def _extract_ast_fallback(self):
        """Robust regex extraction for source files when full compiler check is in flux."""
        # Functions
        fn_pattern = re.compile(r'fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*(?:->\s*([A-Za-z0-9_\[\]]+))?\s*\{', re.MULTILINE)
        for match in fn_pattern.finditer(self.source_text):
            name, params_raw, ret_type = match.groups()
            ret_type = ret_type or "Unit"
            params = []
            if params_raw.strip():
                for p in params_raw.split(","):
                    p = p.strip()
                    if ":" in p:
                        pname, ptype = p.split(":", 1)
                        params.append({"name": pname.strip(), "type": ptype.strip()})
            self.symbols[name] = {
                "kind": "function",
                "name": name,
                "params": params,
                "returns": ret_type,
                "start": match.start(),
            }
            self.call_graph.setdefault(name, set())
            self.caller_graph.setdefault(name, set())

        # Simple call discovery
        call_pattern = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', re.MULTILINE)
        for fn_name, fn_info in self.symbols.items():
            # Scan rough body for calls
            fn_start = fn_info.get("start", 0)
            body_window = self.source_text[fn_start:fn_start + 4000]
            for cm in call_pattern.finditer(body_window):
                cname = cm.group(1)
                if cname != fn_name and cname in self.symbols and cname not in ("if", "while", "for", "say", "return"):
                    self.call_graph.setdefault(fn_name, set()).add(cname)
                    self.caller_graph.setdefault(cname, set()).add(fn_name)

    # -------------------------------------------------------------------------
    # Living Specification & Verification Matrix
    # -------------------------------------------------------------------------
    def verify_specification(self) -> Dict[str, Any]:
        """Verify integrity between specification requirements, AST symbols, and tests."""
        report = {
            "source": str(self.source_path),
            "sourceHash": self.source_hash,
            "specFile": str(self.spec_path) if self.spec_path else None,
            "status": "VALID",
            "totalRequirements": len(self.requirements),
            "implementedRequirements": 0,
            "unimplementedRequirements": [],
            "missingSymbols": [],
            "orphanSymbols": [],
            "matrix": []
        }

        linked_symbols = set()
        for req_id, req in self.requirements.items():
            req_symbols = req.get("symbols", [])
            missing_syms = [s for s in req_symbols if s not in self.symbols]
            
            is_implemented = len(missing_syms) == 0 and len(req_symbols) > 0
            if is_implemented:
                report["implementedRequirements"] += 1
            else:
                report["unimplementedRequirements"].append(req_id)
                for ms in missing_syms:
                    report["missingSymbols"].append({"requirement": req_id, "symbol": ms})

            linked_symbols.update(req_symbols)

            report["matrix"].append({
                "id": req_id,
                "title": req.get("title", ""),
                "status": req.get("status", "DRAFT"),
                "symbols": req_symbols,
                "missingSymbols": missing_syms,
                "tests": req.get("tests", []),
                "implemented": is_implemented
            })

        for sym_name, sym_info in self.symbols.items():
            if sym_name not in linked_symbols and sym_name != "main":
                report["orphanSymbols"].append(sym_name)

        if report["missingSymbols"]:
            report["status"] = "INCOMPLETE"

        return report

    # -------------------------------------------------------------------------
    # Behavioural Map & Affected Test Invalidation
    # -------------------------------------------------------------------------
    def get_affected_tests(self, changed_symbols: List[str]) -> Dict[str, Any]:
        """
        Given a list of modified symbols, calculate direct and transitive impacted tests.
        """
        impacted_symbols = set(changed_symbols)
        # Transitive callers
        to_visit = list(changed_symbols)
        visited = set()
        while to_visit:
            curr = to_visit.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            for caller in self.caller_graph.get(curr, set()):
                impacted_symbols.add(caller)
                to_visit.append(caller)

        affected_tests = []
        for sym in impacted_symbols:
            for test_entry in self.test_index.get(sym, []):
                affected_tests.append({
                    "test": test_entry["test"],
                    "causedBySymbol": sym,
                    "requirement": test_entry["requirement"],
                    "reason": "Direct modification" if sym in changed_symbols else f"Transitive caller of {changed_symbols}"
                })

        return {
            "changedSymbols": changed_symbols,
            "transitiveImpactedSymbols": sorted(list(impacted_symbols)),
            "affectedTestCount": len(affected_tests),
            "affectedTests": affected_tests
        }

    # -------------------------------------------------------------------------
    # Dependency-Complete Context Packet (Aver / Lume style)
    # -------------------------------------------------------------------------
    def get_context_packet(self, target_symbol: str, max_tokens: int = 4000) -> Dict[str, Any]:
        """
        Produce a compact, dependency-complete context packet for an AI agent.
        Includes target symbol definition, requirement, caller/callee signatures, and linked tests.
        """
        if target_symbol not in self.symbols:
            return {"error": f"Symbol '{target_symbol}' not found in source"}

        sym = self.symbols[target_symbol]
        callees = sorted(list(self.call_graph.get(target_symbol, set())))
        callers = sorted(list(self.caller_graph.get(target_symbol, set())))

        # Callee signatures
        callee_signatures = []
        for c in callees:
            if c in self.symbols:
                csym = self.symbols[c]
                params = ", ".join(f"{p['name']}: {p['type']}" for p in csym.get("params", []))
                callee_signatures.append(f"fn {c}({params}) -> {csym.get('returns', 'Unit')}")

        # Caller signatures
        caller_signatures = []
        for c in callers:
            if c in self.symbols:
                csym = self.symbols[c]
                params = ", ".join(f"{p['name']}: {p['type']}" for p in csym.get("params", []))
                caller_signatures.append(f"fn {c}({params}) -> {csym.get('returns', 'Unit')}")

        # Relevant requirements
        relevant_reqs = []
        for req_id, req in self.requirements.items():
            if target_symbol in req.get("symbols", []):
                relevant_reqs.append({
                    "id": req_id,
                    "title": req.get("title", ""),
                    "description": req.get("description", ""),
                    "invariants": req.get("invariants", []),
                    "failureModes": req.get("failureModes", [])
                })

        # Linked tests
        tests = self.test_index.get(target_symbol, [])

        # Approximate token count (~4 chars per token)
        context_data = {
            "targetSymbol": target_symbol,
            "kind": sym.get("kind"),
            "params": sym.get("params"),
            "returns": sym.get("returns"),
            "sourceFile": str(self.source_path),
            "sourceHash": self.source_hash,
            "calleeSignatures": callee_signatures,
            "callerSignatures": caller_signatures,
            "linkedRequirements": relevant_reqs,
            "linkedTests": tests,
        }

        # Format markdown packet
        md_lines = [
            f"# Context Packet: `{target_symbol}`",
            f"**File:** `{self.source_path.name}` | **Revision SHA:** `{self.source_hash[:12]}`",
            "",
            "## Target Signature",
            f"```pep",
            f"fn {target_symbol}(" + ", ".join(f"{p['name']}: {p['type']}" for p in sym.get("params", [])) + f") -> {sym.get('returns', 'Unit')}",
            "```",
            "",
            "## Linked Requirements",
        ]
        if relevant_reqs:
            for r in relevant_reqs:
                md_lines.append(f"- **[{r['id']}] {r['title']}**: {r['description']}")
                for inv in r.get("invariants", []):
                    md_lines.append(f"  - *Invariant:* `{inv}`")
        else:
            md_lines.append("_No requirement linked in Living Spec._")

        md_lines.extend([
            "",
            "## Callee Dependencies (Signatures)",
            "```pep" if callee_signatures else "_No internal callees._",
        ])
        if callee_signatures:
            md_lines.extend(callee_signatures)
            md_lines.append("```")

        md_lines.extend([
            "",
            "## Direct Callers",
            "```pep" if caller_signatures else "_No known callers in file._",
        ])
        if caller_signatures:
            md_lines.extend(caller_signatures)
            md_lines.append("```")

        md_lines.extend([
            "",
            "## Linked Test Contracts",
        ])
        if tests:
            for t in tests:
                md_lines.append(f"- `{t['test']}` (verifies `{t['requirement']}`)")
        else:
            md_lines.append("_No tests registered._")

        rendered_md = "\n".join(md_lines)
        approx_tokens = len(rendered_md) // 4
        context_data["renderedMarkdown"] = rendered_md
        context_data["approximateTokens"] = approx_tokens
        context_data["budgetExceeded"] = approx_tokens > max_tokens

        return context_data

    # -------------------------------------------------------------------------
    # Deterministic Mechanical Repair Plans (Lom / Astra style)
    # -------------------------------------------------------------------------
    def generate_repair_plan(self, diagnostic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Given a structured compiler diagnostic, compute an unambiguous mechanical repair plan.
        """
        code = diagnostic.get("code") or diagnostic.get("errorCode", "")
        message = diagnostic.get("message", "")
        span = diagnostic.get("at") or diagnostic.get("span", {})
        lo = span.get("lo", 0)
        hi = span.get("hi", 0)

        # 1. PEP_TYPE_MISMATCH with hole candidate
        if "hole" in message.lower() or code == "PEP_HOLE":
            expected = diagnostic.get("expected")
            if expected:
                return {
                    "repairId": f"REPAIR-{code}-{lo}",
                    "diagnosticCode": code,
                    "safety": "SUGGESTED_CHOICE",
                    "description": f"Fill typed hole with expected type {expected}",
                    "targetSpan": span,
                    "suggestedReplacements": [f"/* expected {expected} */"]
                }

        # 2. Unknown identifier with single close typo
        if code == "PEP_UNBOUND_NAME" or "unbound" in message.lower():
            m = re.search(r"unbound (?:name|variable|identifier) ['\"]?([A-Za-z0-9_]+)['\"]?", message, re.IGNORECASE)
            unknown = m.group(1) if m else ""
            if unknown:
                # Find closest symbol
                candidates = [s for s in self.symbols if s != unknown and (s.startswith(unknown[:2]) or unknown.startswith(s[:2]))]
                if len(candidates) == 1:
                    return {
                        "repairId": f"REPAIR-TYPO-{lo}",
                        "diagnosticCode": code,
                        "safety": "SAFE_AUTOMATIC",
                        "description": f"Replace misspelled '{unknown}' with in-scope symbol '{candidates[0]}'",
                        "targetSpan": span,
                        "replacement": candidates[0]
                    }

        return None

    # -------------------------------------------------------------------------
    # Multi-Agent Semantic Conflict Detection
    # -------------------------------------------------------------------------
    @staticmethod
    def detect_semantic_conflicts(base_map: "SemanticMap",
                                  branch_a_map: "SemanticMap",
                                  branch_b_map: "SemanticMap") -> Dict[str, Any]:
        """
        Detects semantic conflicts between two branches even if Git merge succeeds with 0 text conflicts!
        Example: Branch A changes function `f`'s signature, Branch B adds a call to `f` using old signature.
        """
        conflicts = []

        # Check signature changes in Branch A
        sig_changed_in_a = set()
        for sym_name, a_sym in branch_a_map.symbols.items():
            base_sym = base_map.symbols.get(sym_name)
            if base_sym:
                if a_sym.get("params") != base_sym.get("params") or a_sym.get("returns") != base_sym.get("returns"):
                    sig_changed_in_a.add(sym_name)

        # Check if Branch B adds new calls to functions whose signature changed in A
        for caller, callees in branch_b_map.call_graph.items():
            base_callees = base_map.call_graph.get(caller, set())
            new_calls_in_b = callees - base_callees
            for callee in new_calls_in_b:
                if callee in sig_changed_in_a:
                    conflicts.append({
                        "type": "SEMANTIC_SIGNATURE_COLLISION",
                        "severity": "CRITICAL",
                        "symbol": callee,
                        "description": f"Branch A altered signature of '{callee}', but Branch B introduced new call from '{caller}' assuming base signature.",
                        "branchAChange": branch_a_map.symbols.get(callee),
                        "branchBUsage": {"caller": caller, "callee": callee}
                    })

        # Check requirement conflict: both branches modified or superseded the same requirement
        if base_map.spec and branch_a_map.spec and branch_b_map.spec:
            for req_id, a_req in branch_a_map.requirements.items():
                b_req = branch_b_map.requirements.get(req_id)
                base_req = base_map.requirements.get(req_id)
                if b_req and base_req:
                    if a_req != base_req and b_req != base_req and a_req != b_req:
                        conflicts.append({
                            "type": "REQUIREMENT_SPECIFICATION_CONFLICT",
                            "severity": "HIGH",
                            "requirementId": req_id,
                            "description": f"Both Branch A and Branch B modified requirement '{req_id}' incompatibly.",
                            "branchA": a_req,
                            "branchB": b_req
                        })

        return {
            "hasConflicts": len(conflicts) > 0,
            "conflictCount": len(conflicts),
            "conflicts": conflicts
        }


# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Pepin Semantic Map & Living Specification Engine")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # verify-spec
    p_verify = subparsers.add_parser("verify-spec", help="Verify living specification against code and tests")
    p_verify.add_argument("source", type=pathlib.Path, help="Target .pep source file")
    p_verify.add_argument("--spec", type=pathlib.Path, default=None, help="Companion .spec.json file")
    p_verify.add_argument("--json", action="store_true", help="Output JSON format")

    # context
    p_context = subparsers.add_parser("context", help="Generate dependency-complete context packet for agent")
    p_context.add_argument("source", type=pathlib.Path, help="Target .pep source file")
    p_context.add_argument("--symbol", required=True, help="Target symbol name")
    p_context.add_argument("--max-tokens", type=int, default=4000, help="Token budget threshold")
    p_context.add_argument("--json", action="store_true", help="Output raw JSON instead of Markdown")

    # affected-tests
    p_tests = subparsers.add_parser("affected-tests", help="Calculate affected tests for modified symbols")
    p_tests.add_argument("source", type=pathlib.Path, help="Target .pep source file")
    p_tests.add_argument("--symbols", required=True, help="Comma-separated list of modified symbols")
    p_tests.add_argument("--json", action="store_true", help="Output JSON format")

    # map
    p_map = subparsers.add_parser("map", help="Display full semantic map (symbols, calls, types)")
    p_map.add_argument("source", type=pathlib.Path, help="Target .pep source file")
    p_map.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    smap = SemanticMap(args.source, getattr(args, "spec", None))

    if args.subcommand == "verify-spec":
        res = smap.verify_specification()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Living Specification Verification: {res['status']}")
            print(f"Requirements: {res['implementedRequirements']}/{res['totalRequirements']} implemented")
            if res['missingSymbols']:
                print(f"Missing Symbols: {res['missingSymbols']}")
            if res['orphanSymbols']:
                print(f"Orphan Symbols: {res['orphanSymbols']}")

    elif args.subcommand == "context":
        res = smap.get_context_packet(args.symbol, args.max_tokens)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(res.get("renderedMarkdown", res.get("error", "")))

    elif args.subcommand == "affected-tests":
        syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
        res = smap.get_affected_tests(syms)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Changed: {res['changedSymbols']}")
            print(f"Transitive impacted: {res['transitiveImpactedSymbols']}")
            print(f"Affected tests count: {res['affectedTestCount']}")
            for t in res['affectedTests']:
                print(f"  - {t['test']} (via {t['causedBySymbol']}, {t['reason']})")

    elif args.subcommand == "map":
        data = {
            "source": str(smap.source_path),
            "hash": smap.source_hash,
            "symbols": list(smap.symbols.keys()),
            "types": list(smap.types.keys()),
            "callEdges": smap.calls
        }
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
