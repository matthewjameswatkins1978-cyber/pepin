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
        self.source_text = self.source_path.read_bytes().decode("utf-8")
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
        self.diagnostics: List[Dict[str, Any]] = []
        
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

        # 2. Check diagnostics
        chk_code, chk_stdout, _ = run_pep_cmd("check", str(self.source_path), "--json")
        try:
            chk_data = json.loads(chk_stdout)
            self.diagnostics = chk_data.get("diagnostics", [])
        except Exception:
            self.diagnostics = []

        # 3. Load living specification if present
        if self.spec_path and self.spec_path.is_file():
            try:
                self.spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
                for req in self.spec.get("requirements", []):
                    req_id = req.get("id")
                    if req_id:
                        self.requirements[req_id] = req
                        syms = req.get("symbols") or req.get("implementsSymbols") or []
                        tests = req.get("tests") or req.get("verifiedByTests") or []
                        for sym in syms:
                            for test in tests:
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

            elif kind in ("record", "union", "TopType", "record_declaration", "union_declaration"):
                decl = item.get("decl", item)
                tname = decl.get("name", "")
                type_info = {
                    "kind": decl.get("kind", kind),
                    "name": tname,
                    "span": decl.get("span", {}),
                    "details": decl
                }
                self.types[tname] = type_info
                self.symbols[tname] = type_info

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
            req_symbols = req.get("symbols") or req.get("implementsSymbols") or []
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
                "tests": req.get("tests") or req.get("verifiedByTests") or [],
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
            syms = req.get("symbols") or req.get("implementsSymbols") or []
            if target_symbol in syms:
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
        lo = span.get("lo") if "lo" in span else span.get("start", {}).get("offset", 0)
        hi = span.get("hi") if "hi" in span else span.get("endOffset", 0)
        span_obj = {"lo": lo, "hi": hi}

        # 1. Unknown identifier / variable with single close typo
        if code in ("PEP_UNKNOWN_VARIABLE", "PEP_UNBOUND_NAME") or "unknown variable" in message.lower() or "unbound" in message.lower():
            m = re.search(r"(?:unknown variable|unbound (?:name|variable|identifier)) ['\"]?([A-Za-z0-9_]+)['\"]?", message, re.IGNORECASE)
            unknown = m.group(1) if m else ""
            if unknown:
                candidates = [s for s in self.symbols if s != unknown and (s.startswith(unknown[:2]) or unknown.startswith(s[:2]))]
                if candidates:
                    return {
                        "repairId": f"REPAIR-TYPO-{lo}",
                        "diagnosticCode": code,
                        "safety": "SAFE_AUTOMATIC",
                        "description": f"Replace misspelled '{unknown}' with in-scope symbol '{candidates[0]}'",
                        "targetSpan": span_obj,
                        "replacement": candidates[0]
                    }

        # 2. Type mismatch: Expected Str but found Int (e.g. say(123) -> say(int_text(123)))
        if code == "PEP_TYPE_MISMATCH":
            exp_type = diagnostic.get("expectedType")
            if exp_type == "Str" and "found Int" in message:
                content = self.source_path.read_bytes().decode("utf-8")
                raw_expr = content[lo:hi] if lo < hi <= len(content) else ""
                if raw_expr:
                    return {
                        "repairId": f"REPAIR-STR-INT-{lo}",
                        "diagnosticCode": code,
                        "safety": "SAFE_AUTOMATIC",
                        "description": f"Wrap integer expression '{raw_expr}' with 'int_text({raw_expr})'",
                        "targetSpan": span_obj,
                        "replacement": f"int_text({raw_expr})"
                    }
            elif exp_type == "Int" and "found Str" in message:
                content = self.source_path.read_bytes().decode("utf-8")
                raw_expr = content[lo:hi] if lo < hi <= len(content) else ""
                m = re.match(r'^"(\d+)"$', raw_expr)
                if m:
                    return {
                        "repairId": f"REPAIR-INT-LITERAL-{lo}",
                        "diagnosticCode": code,
                        "safety": "SAFE_AUTOMATIC",
                        "description": f"Replace string literal '{raw_expr}' with integer {m.group(1)}",
                        "targetSpan": span_obj,
                        "replacement": m.group(1)
                    }

        # 3. PEP_TYPE_MISMATCH with hole candidate
        if "hole" in message.lower() or code == "PEP_HOLE":
            expected = diagnostic.get("expected") or diagnostic.get("expectedType")
            if expected:
                return {
                    "repairId": f"REPAIR-{code}-{lo}",
                    "diagnosticCode": code,
                    "safety": "SUGGESTED_CHOICE",
                    "description": f"Fill typed hole with expected type {expected}",
                    "targetSpan": span_obj,
                    "suggestedReplacements": [f"/* expected {expected} */"]
                }

        return None

    def apply_repair(self, repair_plan: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Mechanically applies an unambiguous repair plan to the source code,
        verifying that the diagnostic is eliminated.
        """
        span = repair_plan.get("targetSpan", {})
        lo = span.get("lo", 0)
        hi = span.get("hi", 0)
        replacement = repair_plan.get("replacement", "")

        content = self.source_path.read_bytes().decode("utf-8")
        if lo < 0 or hi > len(content) or lo > hi:
            raise ValueError(f"Invalid target span [{lo}, {hi}] for file of length {len(content)}")

        old_slice = content[lo:hi]
        repaired_content = content[:lo] + replacement + content[hi:]

        if not dry_run:
            self.source_path.write_bytes(repaired_content.encode("utf-8"))

        # Re-check via compiler
        cmd = ["pwsh", "-NoProfile", "-File", str(PEP_CLI), "check", str(self.source_path), "--json"]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
        
        try:
            check_data = json.loads(proc.stdout)
            is_valid = check_data.get("status") == "valid"
            remaining = check_data.get("diagnostics", [])
        except Exception:
            is_valid = proc.returncode == 0
            remaining = []

        return {
            "status": "SUCCESS" if (is_valid or len(remaining) < 1) else "PARTIAL",
            "repairId": repair_plan.get("repairId"),
            "source": str(self.source_path),
            "originalDiagnostic": repair_plan.get("diagnosticCode"),
            "diff": {
                "before": old_slice,
                "after": replacement,
                "span": {"lo": lo, "hi": hi}
            },
            "verifiedValid": is_valid,
            "remainingDiagnostics": remaining
        }

    # -------------------------------------------------------------------------
    # Multi-Agent Coordination Lane Verification
    # -------------------------------------------------------------------------
    def verify_lane(self, lane_def: Dict[str, Any], base_map: Optional["SemanticMap"] = None) -> Dict[str, Any]:
        """
        Validates that modifications stay strictly within an agent's designated semantic lane.
        Checks:
        1. Clean compiler status (zero syntax/type errors in lane).
        2. Out-of-lane symbol mutations (if allowNewSymbols is False).
        3. Breaking caller contracts for modified symbols (if base_map provided).
        4. Assigned requirement fulfillment in living specification.
        """
        lane_id = lane_def.get("laneId", "unknown-lane")
        allowed_symbols = set(lane_def.get("allowedSymbols", []))
        allow_new = lane_def.get("allowNewSymbols", False)
        assigned_reqs = set(lane_def.get("assignedRequirements", []))

        violations = []

        # 1. Check compiler health
        if self.diagnostics:
            for diag in self.diagnostics:
                violations.append({
                    "type": "COMPILER_DIAGNOSTIC",
                    "severity": "CRITICAL",
                    "message": f"Compilation error in lane: {diag.get('message', '')} ({diag.get('code', '')})",
                    "diagnostic": diag
                })

        # 2. Check out-of-lane symbols if base_map is present
        if base_map:
            # Check modified existing symbols
            for sym_name, sym_info in self.symbols.items():
                base_sym = base_map.symbols.get(sym_name)
                if base_sym:
                    # Symbol existed in base. Was it modified?
                    if sym_info != base_sym and sym_name not in allowed_symbols:
                        violations.append({
                            "type": "OUT_OF_LANE_MODIFICATION",
                            "severity": "CRITICAL",
                            "symbol": sym_name,
                            "message": f"Symbol '{sym_name}' was modified but is outside lane '{lane_id}' allowed symbols."
                        })
                else:
                    # New symbol added
                    if not allow_new and sym_name not in allowed_symbols:
                        violations.append({
                            "type": "OUT_OF_LANE_ADDITION",
                            "severity": "HIGH",
                            "symbol": sym_name,
                            "message": f"New symbol '{sym_name}' was added but is outside lane '{lane_id}' allowed symbols."
                        })

            # Check deleted symbols
            for base_sym_name in base_map.symbols:
                if base_sym_name not in self.symbols and base_sym_name not in allowed_symbols:
                    violations.append({
                        "type": "OUT_OF_LANE_DELETION",
                        "severity": "CRITICAL",
                        "symbol": base_sym_name,
                        "message": f"Symbol '{base_sym_name}' was removed but is outside lane '{lane_id}' allowed symbols."
                    })

            # 3. Check breaking caller contracts for modified symbols
            for sym_name in allowed_symbols:
                if sym_name in self.symbols and sym_name in base_map.symbols:
                    curr_sym = self.symbols[sym_name]
                    base_sym = base_map.symbols[sym_name]
                    if curr_sym.get("params") != base_sym.get("params") or curr_sym.get("returns") != base_sym.get("returns"):
                        outside_callers = [c for c in base_map.caller_graph.get(sym_name, set()) if c not in allowed_symbols]
                        if outside_callers:
                            violations.append({
                                "type": "BREAKING_CALLER_CONTRACT",
                                "severity": "HIGH",
                                "symbol": sym_name,
                                "message": f"Signature of '{sym_name}' was changed in lane '{lane_id}', breaking outside callers: {outside_callers}",
                                "outsideCallers": outside_callers
                            })

        # 4. Check assigned requirements fulfillment
        if self.spec and assigned_reqs:
            for req_id in assigned_reqs:
                req = self.requirements.get(req_id)
                if not req:
                    violations.append({
                        "type": "REQUIREMENT_MISSING",
                        "severity": "HIGH",
                        "requirementId": req_id,
                        "message": f"Assigned requirement '{req_id}' is not defined in the specification."
                    })
                else:
                    req_symbols = req.get("symbols", [])
                    missing_syms = [s for s in req_symbols if s not in self.symbols]
                    if missing_syms:
                        violations.append({
                            "type": "REQUIREMENT_UNSATISFIED",
                            "severity": "HIGH",
                            "requirementId": req_id,
                            "message": f"Assigned requirement '{req_id}' is missing required symbols: {missing_syms}"
                        })

        valid = len(violations) == 0
        return {
            "laneValid": valid,
            "laneId": lane_id,
            "status": "APPROVED" if valid else "REJECTED",
            "violationCount": len(violations),
            "violations": violations
        }

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

    # repair
    p_repair = subparsers.add_parser("repair", help="Analyze diagnostics and compute mechanical repair plans")
    p_repair.add_argument("source", type=pathlib.Path, help="Target .pep source file")
    p_repair.add_argument("--json", action="store_true", help="Output JSON format")

    # apply-repair
    p_apply = subparsers.add_parser("apply-repair", help="Apply mechanical repair plans and verify validity")
    p_apply.add_argument("source", type=pathlib.Path, help="Target .pep source file")
    p_apply.add_argument("--auto", action="store_true", help="Automatically apply all SAFE_AUTOMATIC repairs")
    p_apply.add_argument("--json", action="store_true", help="Output JSON format")

    # verify-lane
    p_lane = subparsers.add_parser("verify-lane", help="Verify that changes strictly adhere to a designated semantic lane")
    p_lane.add_argument("source", type=pathlib.Path, help="Target .pep source file")
    p_lane.add_argument("--lane-file", type=pathlib.Path, required=True, help="Lane definition JSON file")
    p_lane.add_argument("--base", type=pathlib.Path, default=None, help="Base .pep source file before lane changes")
    p_lane.add_argument("--json", action="store_true", help="Output JSON format")

    # check-merge
    p_merge = subparsers.add_parser("check-merge", help="Check semantic merge safety between base and two branch sources")
    p_merge.add_argument("base", type=pathlib.Path, help="Base .pep source file")
    p_merge.add_argument("branch_a", type=pathlib.Path, help="Branch A .pep source file")
    p_merge.add_argument("branch_b", type=pathlib.Path, help="Branch B .pep source file")
    p_merge.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    if args.subcommand == "check-merge":
        base_map = SemanticMap(args.base)
        a_map = SemanticMap(args.branch_a)
        b_map = SemanticMap(args.branch_b)
        res = SemanticMap.detect_semantic_conflicts(base_map, a_map, b_map)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Semantic Merge Verdict: {'CONFLICTS DETECTED' if res['hasConflicts'] else 'SAFE TO MERGE'}")
            print(f"Conflicts: {res['conflictCount']}")
            for c in res['conflicts']:
                print(f"  [{c['severity']}] {c['type']}: {c['description']}")
        return

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

    elif args.subcommand == "repair":
        cmd = ["pwsh", "-NoProfile", "-File", str(PEP_CLI), "check", str(args.source), "--json"]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
        try:
            data = json.loads(proc.stdout)
            diags = data.get("diagnostics", [])
        except Exception:
            diags = []

        plans = []
        for d in diags:
            plan = smap.generate_repair_plan(d)
            if plan:
                plans.append(plan)

        out = {
            "source": str(args.source),
            "diagnosticCount": len(diags),
            "repairableCount": len(plans),
            "repairs": plans
        }
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"Diagnostics: {len(diags)}, Repairable: {len(plans)}")
            for p in plans:
                print(f"  [{p['safety']}] {p['repairId']}: {p['description']}")

    elif args.subcommand == "apply-repair":
        cmd = ["pwsh", "-NoProfile", "-File", str(PEP_CLI), "check", str(args.source), "--json"]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
        try:
            data = json.loads(proc.stdout)
            diags = data.get("diagnostics", [])
        except Exception:
            diags = []

        applied = []
        plans = []
        for d in diags:
            p = smap.generate_repair_plan(d)
            if p and (p["safety"] == "SAFE_AUTOMATIC" or not args.auto):
                plans.append(p)

        # Sort descending by lo offset so earlier offsets remain intact
        plans.sort(key=lambda p: p["targetSpan"]["lo"], reverse=True)
        for p in plans:
            outcome = smap.apply_repair(p)
            applied.append(outcome)

        out = {
            "source": str(args.source),
            "appliedCount": len(applied),
            "outcomes": applied
        }
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"Applied {len(applied)} mechanical repairs.")
            for o in applied:
                print(f"  {o['repairId']}: {o['status']} (valid: {o['verifiedValid']})")

    elif args.subcommand == "verify-lane":
        with open(args.lane_file, "r", encoding="utf-8") as f:
            lane_def = json.load(f)
        base_map = SemanticMap(args.base) if args.base else None
        res = smap.verify_lane(lane_def, base_map)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Lane Verification for '{res['laneId']}': {res['status']}")
            print(f"Violations: {res['violationCount']}")
            for v in res['violations']:
                print(f"  [{v['severity']}] {v['type']}: {v['message']}")
        if not res["laneValid"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
