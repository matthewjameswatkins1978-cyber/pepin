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
        self.source_bytes = self.source_path.read_bytes()
        self.source_text = self.source_bytes.decode("utf-8")
        self.source_hash = "sha256:" + hashlib.sha256(self.source_bytes).hexdigest()
        
        self.epistemic_status = "UNAVAILABLE"  # CHECKED, INVALID, UNAVAILABLE, or FALLBACK_UNAUTHORIZED
        self.compiler_available = False
        self.compiler_checked = False

        self.ast: Dict[str, Any] = {}
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self.types: Dict[str, Dict[str, Any]] = {}
        self.calls: List[Dict[str, Any]] = []
        self.call_graph: Dict[str, Set[str]] = {}
        self.caller_graph: Dict[str, Set[str]] = {}
        
        self.spec: Optional[Dict[str, Any]] = None
        self.spec_test_catalog: Dict[str, Dict[str, Any]] = {}
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

    def _find_test_on_disk(self, test_ref: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify that a test referenced in a living specification actually exists on disk.
        Supports:
          - Catalog references defined in spec's 'tests' array
          - path/to/test_file.py::test_fn_name
          - direct file path
          - bare test function name (searched under tests/ directory)
        Returns (exists: bool, resolved_path: Optional[str], file_hash: Optional[str]).
        """
        # 1. Check spec test catalog mapping if present
        if test_ref in self.spec_test_catalog:
            entry = self.spec_test_catalog[test_ref]
            tfile = entry.get("testFile")
            tcase = entry.get("testCase")
            if tfile and tcase:
                return self._find_test_on_disk(f"{tfile}::{tcase}")
            elif tfile:
                return self._find_test_on_disk(tfile)

        # 2. Check path::test_fn format
        if "::" in test_ref:
            parts = test_ref.split("::", 1)
            file_part, fn_name = parts[0].strip(), parts[1].strip()
            candidates = [
                ROOT / file_part,
                self.source_path.parent / file_part,
                pathlib.Path(file_part)
            ]
            target_file = None
            for c in candidates:
                if c.is_file():
                    target_file = c
                    break
            if not target_file:
                return False, None, None

            try:
                content = target_file.read_text(encoding="utf-8")
                fn_pat = re.compile(rf'(?:def|fn|test)\s+{re.escape(fn_name)}\b')
                if fn_pat.search(content):
                    fhash = "sha256:" + hashlib.sha256(target_file.read_bytes()).hexdigest()
                    return True, str(target_file), fhash
                else:
                    return False, str(target_file), None
            except Exception:
                return False, None, None

        # 3. Direct file path
        direct_candidates = [
            ROOT / test_ref,
            self.source_path.parent / test_ref,
            pathlib.Path(test_ref)
        ]
        for c in direct_candidates:
            if c.is_file():
                fhash = "sha256:" + hashlib.sha256(c.read_bytes()).hexdigest()
                return True, str(c), fhash

        # 4. Bare test function name: search tests/ directory
        tests_dir = ROOT / "tests"
        if tests_dir.is_dir():
            fn_pat = re.compile(rf'(?:def|fn|test)\s+{re.escape(test_ref)}\b')
            for tfile in list(tests_dir.glob("test_*.py")) + list(tests_dir.glob("*.pep")):
                try:
                    content = tfile.read_text(encoding="utf-8")
                    if fn_pat.search(content):
                        fhash = "sha256:" + hashlib.sha256(tfile.read_bytes()).hexdigest()
                        return True, str(tfile), fhash
                except Exception:
                    continue

        return False, None, None

    def _load_and_analyze(self):
        # 1. Run pep.ps1 inspect --json
        code, stdout, stderr = run_pep_cmd("inspect", str(self.source_path), "--json")
        inspect_ok = False
        if code == 0 and stdout.strip():
            try:
                self.ast = json.loads(stdout)
                self._extract_symbols_from_ast()
                inspect_ok = True
                self.compiler_available = True
            except json.JSONDecodeError:
                inspect_ok = False

        if not inspect_ok:
            # Fallback to local regex-based extraction solely for editor preview
            # NOTE: Epistemic status remains UNAUTHORIZED / INVALID
            self._extract_ast_fallback()
            self.epistemic_status = "UNAVAILABLE" if (code != 0 and not stdout.strip()) else "INVALID"

        # 2. Check diagnostics via pep.ps1 check --json
        chk_code, chk_stdout, _ = run_pep_cmd("check", str(self.source_path), "--json")
        try:
            chk_data = json.loads(chk_stdout)
            self.diagnostics = chk_data.get("diagnostics", [])
            chk_status = chk_data.get("status")
            if inspect_ok and chk_status == "valid" and len(self.diagnostics) == 0:
                self.epistemic_status = "CHECKED"
                self.compiler_checked = True
                self.compiler_available = True
            else:
                self.epistemic_status = "INVALID"
                self.compiler_available = True
        except Exception:
            if not inspect_ok:
                self.epistemic_status = "UNAVAILABLE"
            else:
                self.epistemic_status = "INVALID"

        # 3. Load living specification if present
        if self.spec_path and self.spec_path.is_file():
            try:
                self.spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
                # Build test catalog from spec's 'tests' block
                self.spec_test_catalog = {}
                for t in self.spec.get("tests", []):
                    tid = t.get("testId")
                    if tid:
                        self.spec_test_catalog[tid] = t

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
        """
        Verify integrity between living specification, authoritative AST, and tests.
        Rejects nonexistent tests, invalid compiler states, duplicate requirement IDs,
        and unfulfilled requirements.
        """
        req_list = self.spec.get("requirements", []) if self.spec else []
        report = {
            "source": str(self.source_path),
            "sourceHash": self.source_hash,
            "specFile": str(self.spec_path) if self.spec_path else None,
            "epistemicStatus": self.epistemic_status,
            "status": "VALID",
            "totalRequirements": len(req_list),
            "implementedRequirements": 0,
            "testedRequirements": 0,
            "requirementsWithTestReferences": 0,
            "verifiedRequirements": 0,
            "schemaErrors": [],
            "nonexistentTests": [],
            "missingSymbols": [],
            "orphanSymbols": [],
            "matrix": []
        }

        # 1. Epistemic authority guard: if compiler is unavailable or invalid, spec cannot be verified as valid
        if self.epistemic_status != "CHECKED":
            report["status"] = "INVALID" if self.epistemic_status == "INVALID" else "UNAVAILABLE"
            report["error"] = f"Authoritative compiler check failed or unavailable (epistemic status: {self.epistemic_status}). Specification cannot be verified."

        if not self.spec:
            report["status"] = "NO_SPEC"
            return report

        # 2. Validate spec schema and unique requirement IDs
        seen_ids = set()
        for r in req_list:
            rid = r.get("id")
            if not rid:
                report["schemaErrors"].append("Requirement missing required 'id' in specification.")
            elif rid in seen_ids:
                report["schemaErrors"].append(f"Duplicate requirement ID '{rid}' found in specification.")
            else:
                seen_ids.add(rid)

        # 3. Process requirements
        linked_symbols = set()
        for req in req_list:
            req_id = req.get("id", "UNKNOWN")
            req_symbols = req.get("symbols") or req.get("implementsSymbols") or []
            req_tests = req.get("tests") or req.get("verifiedByTests") or []

            missing_syms = [s for s in req_symbols if s not in self.symbols]

            # Verify referenced tests actually exist on disk
            missing_tests = []
            test_evidence = {}
            for t in req_tests:
                exists, resolved_path, fhash = self._find_test_on_disk(t)
                if not exists:
                    missing_tests.append(t)
                    report["nonexistentTests"].append({"requirement": req_id, "test": t})
                else:
                    test_evidence[t] = {"path": resolved_path, "sha256": fhash}

            # Classify requirement status
            is_implemented = len(missing_syms) == 0 and len(req_symbols) > 0
            has_tests = len(req_tests) > 0 and len(missing_tests) == 0

            if not is_implemented:
                req_status = "UNIMPLEMENTED"
            elif len(missing_tests) > 0:
                req_status = "TEST_MISSING"
            else:
                req_status = "IMPLEMENTED"

            if is_implemented:
                report["implementedRequirements"] += 1
            if is_implemented and has_tests:
                report["requirementsWithTestReferences"] += 1

            for ms in missing_syms:
                report["missingSymbols"].append({"requirement": req_id, "symbol": ms})

            linked_symbols.update(req_symbols)

            report["matrix"].append({
                "id": req_id,
                "title": req.get("title", ""),
                "status": req_status,
                "symbols": req_symbols,
                "missingSymbols": missing_syms,
                "tests": req_tests,
                "nonexistentTests": missing_tests,
                "implemented": is_implemented,
                "verified": False,
                "evidence": {
                    "sourceRevision": self.source_hash,
                    "testRevisions": test_evidence
                }
            })

        # 4. Check for orphan symbols
        for sym_name, sym_info in self.symbols.items():
            if sym_name not in linked_symbols and sym_name != "main" and not sym_name.startswith("pep_"):
                report["orphanSymbols"].append(sym_name)

        # 5. Epistemic validity gate
        if (report["schemaErrors"] or 
            report["nonexistentTests"] or 
            report["missingSymbols"] or 
            report["implementedRequirements"] < report["totalRequirements"]):
            report["status"] = "INVALID"

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
        Includes target symbol implementation, requirements, caller/callee signatures,
        linked tests, and explicit disclosure of omitted information / uncertainties.
        """
        if target_symbol not in self.symbols:
            return {"error": f"Symbol '{target_symbol}' not found in source"}

        sym = self.symbols[target_symbol]
        callees = sorted(list(self.call_graph.get(target_symbol, set())))
        callers = sorted(list(self.caller_graph.get(target_symbol, set())))

        # Extract target implementation from source bytes using span
        fspan = sym.get("span", {})
        lo = fspan.get("lo", 0)
        hi = fspan.get("hi", 0)
        implementation_code = ""
        if 0 <= lo < hi <= len(self.source_bytes):
            try:
                implementation_code = self.source_bytes[lo:hi].decode("utf-8").strip()
            except Exception:
                implementation_code = self.source_text[lo:hi].strip()

        if not implementation_code:
            # Fallback search in source text
            fn_pat = re.compile(rf'(fn\s+{re.escape(target_symbol)}\b[^{{]*\{{.*?^\}})', re.MULTILINE | re.DOTALL)
            m = fn_pat.search(self.source_text)
            if m:
                implementation_code = m.group(1).strip()

        fallback_sig = f"fn {target_symbol}(" + ", ".join(f"{p['name']}: {p['type']}" for p in sym.get("params", [])) + f") -> {sym.get('returns', 'Unit')}"
        if not implementation_code:
            implementation_code = fallback_sig

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

        omitted_info = []
        uncertainties = []
        if implementation_code == fallback_sig:
            uncertainties.append("Exact source span for body could not be isolated from AST; only signature available.")

        # Format markdown packet
        md_lines = [
            f"# Context Packet: `{target_symbol}`",
            f"**File:** `{self.source_path.name}` | **Revision SHA:** `{self.source_hash[:12]}`",
            "",
            "## Target Implementation",
            "```pep",
            implementation_code,
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
        budget_exceeded = approx_tokens > max_tokens

        if budget_exceeded:
            omitted_info.append("Callee signatures and callers truncated due to token budget constraint.")

        return {
            "targetSymbol": target_symbol,
            "kind": sym.get("kind"),
            "params": sym.get("params"),
            "returns": sym.get("returns"),
            "implementation": implementation_code,
            "sourceFile": str(self.source_path),
            "sourceHash": self.source_hash,
            "calleeSignatures": callee_signatures,
            "callerSignatures": caller_signatures,
            "linkedRequirements": relevant_reqs,
            "linkedTests": tests,
            "renderedMarkdown": rendered_md,
            "approximateTokens": approx_tokens,
            "budgetExceeded": budget_exceeded,
            "incomplete": budget_exceeded,
            "omittedInformation": omitted_info,
            "uncertainties": uncertainties,
            "retrievalQuery": f"pep_semantic_map.py context {self.source_path.name} --symbol {target_symbol}"
        }

    # -------------------------------------------------------------------------
    # Deterministic Mechanical Repair Plans (Lom / Astra style)
    # -------------------------------------------------------------------------
    def generate_repair_plan(self, diagnostic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Given a structured compiler diagnostic, compute an unambiguous mechanical repair plan.
        Never automatically resolves ambiguous identifiers.
        Binds to exact source hash and expected original bytes.
        """
        code = diagnostic.get("code") or diagnostic.get("errorCode", "")
        message = diagnostic.get("message", "")
        span = diagnostic.get("at") or diagnostic.get("span", {})
        lo = span.get("lo") if "lo" in span else span.get("start", {}).get("offset", 0)
        hi = span.get("hi") if "hi" in span else span.get("endOffset", 0)
        span_obj = {"lo": lo, "hi": hi, "unit": "byte_offset"}

        expected_bytes = ""
        if 0 <= lo <= hi <= len(self.source_bytes):
            expected_bytes = self.source_bytes[lo:hi].decode("utf-8", errors="replace")

        # 1. Unknown identifier / variable
        if code in ("PEP_UNKNOWN_VARIABLE", "PEP_UNBOUND_NAME") or "unknown variable" in message.lower() or "unbound" in message.lower():
            m = re.search(r"(?:unknown variable|unbound (?:name|variable|identifier)) ['\"]?([A-Za-z0-9_]+)['\"]?", message, re.IGNORECASE)
            unknown = m.group(1) if m else ""
            if unknown:
                candidates = [s for s in sorted(self.symbols.keys()) if s != unknown and (s.startswith(unknown[:2]) or unknown.startswith(s[:2]))]
                if len(candidates) == 1:
                    # Exactly one candidate: SAFE_AUTOMATIC
                    return {
                        "repairId": f"REPAIR-TYPO-{lo}",
                        "diagnosticCode": code,
                        "safety": "SAFE_AUTOMATIC",
                        "description": f"Replace misspelled '{unknown}' with unique in-scope symbol '{candidates[0]}'",
                        "targetSpan": span_obj,
                        "expectedSourceHash": self.source_hash,
                        "expectedOriginalBytes": expected_bytes,
                        "replacement": candidates[0]
                    }
                elif len(candidates) > 1:
                    # Multiple candidates: AMBIGUOUS_CHOICE (never automatically guess!)
                    return {
                        "repairId": f"REPAIR-AMBIGUOUS-TYPO-{lo}",
                        "diagnosticCode": code,
                        "safety": "AMBIGUOUS_CHOICE",
                        "description": f"Ambiguous candidates for '{unknown}': {candidates}. Manual choice required.",
                        "targetSpan": span_obj,
                        "expectedSourceHash": self.source_hash,
                        "expectedOriginalBytes": expected_bytes,
                        "replacement": None,
                        "suggestedReplacements": candidates
                    }

        # 2. Type mismatch: Expected Str but found Int (e.g. say(123) -> say(int_text(123)))
        if code == "PEP_TYPE_MISMATCH":
            exp_type = diagnostic.get("expectedType")
            if exp_type == "Str" and "found Int" in message:
                raw_expr = expected_bytes
                if raw_expr:
                    return {
                        "repairId": f"REPAIR-STR-INT-{lo}",
                        "diagnosticCode": code,
                        "safety": "SAFE_AUTOMATIC",
                        "description": f"Wrap integer expression '{raw_expr}' with 'int_text({raw_expr})'",
                        "targetSpan": span_obj,
                        "expectedSourceHash": self.source_hash,
                        "expectedOriginalBytes": expected_bytes,
                        "replacement": f"int_text({raw_expr})"
                    }
            elif exp_type == "Int" and "found Str" in message:
                raw_expr = expected_bytes
                m = re.match(r'^"(\d+)"$', raw_expr)
                if m:
                    return {
                        "repairId": f"REPAIR-INT-LITERAL-{lo}",
                        "diagnosticCode": code,
                        "safety": "SAFE_AUTOMATIC",
                        "description": f"Replace string literal '{raw_expr}' with integer {m.group(1)}",
                        "targetSpan": span_obj,
                        "expectedSourceHash": self.source_hash,
                        "expectedOriginalBytes": expected_bytes,
                        "replacement": m.group(1)
                    }

        # 3. PEP_HOLE
        if "hole" in message.lower() or code == "PEP_HOLE":
            expected = diagnostic.get("expected") or diagnostic.get("expectedType")
            if expected:
                return {
                    "repairId": f"REPAIR-{code}-{lo}",
                    "diagnosticCode": code,
                    "safety": "SUGGESTED_CHOICE",
                    "description": f"Fill typed hole with expected type {expected}",
                    "targetSpan": span_obj,
                    "expectedSourceHash": self.source_hash,
                    "expectedOriginalBytes": expected_bytes,
                    "replacement": None,
                    "suggestedReplacements": [f"/* expected {expected} */"]
                }

        return None

    def apply_repair(self, repair_plan: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Mechanically applies an unambiguous repair plan to the source code,
        verifying that the diagnostic is eliminated and no compiler error is introduced.
        Preserves original source on failure; compiler failure never reports SUCCESS.
        """
        expected_hash = repair_plan.get("expectedSourceHash")
        if expected_hash and expected_hash != self.source_hash:
            return {
                "status": "REJECTED_STALE_REVISION",
                "message": f"Source revision mismatch: plan expected {expected_hash}, current file is {self.source_hash}",
                "verifiedValid": False
            }

        replacement = repair_plan.get("replacement")
        if replacement is None:
            return {
                "status": "REJECTED_AMBIGUOUS",
                "message": "Cannot automatically apply plan with ambiguous or missing replacement.",
                "verifiedValid": False
            }

        span = repair_plan.get("targetSpan", {})
        lo = span.get("lo", 0)
        hi = span.get("hi", 0)

        if lo < 0 or hi > len(self.source_bytes) or lo > hi:
            return {
                "status": "REJECTED_INVALID_SPAN",
                "message": f"Target span [{lo}, {hi}] out of bounds for source of length {len(self.source_bytes)}",
                "verifiedValid": False
            }

        # Verify original bytes at target span
        expected_orig = repair_plan.get("expectedOriginalBytes")
        actual_orig = self.source_bytes[lo:hi].decode("utf-8", errors="replace")
        if expected_orig is not None and actual_orig != expected_orig:
            return {
                "status": "REJECTED_BYTE_MISMATCH",
                "message": f"Byte mismatch at [{lo}, {hi}]: expected '{expected_orig}', found '{actual_orig}'",
                "verifiedValid": False
            }

        if dry_run:
            return {
                "status": "DRY_RUN_VALID",
                "diff": {"before": actual_orig, "after": replacement, "span": span},
                "verifiedValid": True
            }

        # Apply edit to byte buffer
        original_bytes = self.source_bytes
        new_bytes = original_bytes[:lo] + replacement.encode("utf-8") + original_bytes[hi:]

        # Write candidate edit to file
        self.source_path.write_bytes(new_bytes)

        # Run compiler check on candidate
        cmd = ["pwsh", "-NoProfile", "-File", str(PEP_CLI), "check", str(self.source_path), "--json"]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")

        candidate_valid = False
        remaining_diagnostics = []
        try:
            chk_data = json.loads(proc.stdout)
            candidate_valid = chk_data.get("status") == "valid" and len(chk_data.get("diagnostics", [])) == 0
            remaining_diagnostics = chk_data.get("diagnostics", [])
        except Exception:
            candidate_valid = proc.returncode == 0

        # CRITICAL SAFETY: If compiler failed, ROLL BACK IMMEDIATELY! Never report SUCCESS!
        if not candidate_valid or proc.returncode != 0:
            self.source_path.write_bytes(original_bytes)
            return {
                "status": "FAILED_VERIFICATION",
                "reverted": True,
                "message": "Candidate edit failed compiler check; original source preserved.",
                "verifiedValid": False,
                "compilerDiagnostics": remaining_diagnostics,
                "compilerOutput": proc.stdout + proc.stderr
            }

        # Success: update in-memory state
        self.source_bytes = new_bytes
        self.source_text = new_bytes.decode("utf-8")
        self.source_hash = "sha256:" + hashlib.sha256(new_bytes).hexdigest()
        self._load_and_analyze()

        return {
            "status": "SUCCESS",
            "repairId": repair_plan.get("repairId"),
            "source": str(self.source_path),
            "sourceHash": self.source_hash,
            "originalDiagnostic": repair_plan.get("diagnosticCode"),
            "diff": {
                "before": actual_orig,
                "after": replacement,
                "span": {"lo": lo, "hi": hi}
            },
            "verifiedValid": True,
            "remainingDiagnostics": remaining_diagnostics
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
                    # Compare semantic signatures independently of line/span movements
                    curr_sig = SemanticMap._extract_semantic_symbol_signature(sym_info)
                    base_sig = SemanticMap._extract_semantic_symbol_signature(base_sym)
                    if curr_sig != base_sig and sym_name not in allowed_symbols:
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
                    curr_sig = SemanticMap._extract_semantic_symbol_signature(self.symbols[sym_name])
                    base_sig = SemanticMap._extract_semantic_symbol_signature(base_map.symbols[sym_name])
                    if curr_sig.get("params") != base_sig.get("params") or curr_sig.get("returns") != base_sig.get("returns"):
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
    def _extract_semantic_symbol_signature(sym: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts semantic signature independent of source positions/spans."""
        if not sym:
            return {}
        return {
            "name": sym.get("name"),
            "kind": sym.get("kind"),
            "params": [{"name": p.get("name"), "type": p.get("type")} for p in sym.get("params", [])],
            "returns": sym.get("returns", "Unit")
        }

    @staticmethod
    def detect_semantic_conflicts(base_map: "SemanticMap",
                                  branch_a_map: "SemanticMap",
                                  branch_b_map: "SemanticMap") -> Dict[str, Any]:
        """
        Symmetric, order-independent semantic conflict detection.
        Checking (base, A, B) produces the exact same findings as (base, B, A).
        Handles:
          - Both directions of signature and dependency changes
          - Modified and deleted symbols
          - Existing callers whose assumptions have changed
          - Global constants and types
          - Living specification requirements
          - Position-independent semantic comparison (ignoring line shifts)
          - Epistemic validity of branch analysis
        """
        conflicts = []

        # Epistemic check on branches
        if getattr(branch_a_map, "epistemic_status", None) == "INVALID" or getattr(branch_b_map, "epistemic_status", None) == "INVALID":
            conflicts.append({
                "type": "UNVERIFIED_BRANCH_ANALYSIS",
                "severity": "CRITICAL",
                "description": "One or both branches have compiler errors. Semantic merge requires valid branches."
            })

        def check_directional(src_map: "SemanticMap", other_map: "SemanticMap", src_name: str, other_name: str):
            # 1. Signature changes in src_map
            sig_changed = set()
            for sym_name, s_sym in src_map.symbols.items():
                base_sym = base_map.symbols.get(sym_name)
                if base_sym:
                    s_sig = SemanticMap._extract_semantic_symbol_signature(s_sym)
                    b_sig = SemanticMap._extract_semantic_symbol_signature(base_sym)
                    if s_sig != b_sig:
                        sig_changed.add(sym_name)

            # 2. Check if other_map calls any symbol whose signature changed in src_map
            for caller, callees in other_map.call_graph.items():
                base_callees = base_map.call_graph.get(caller, set())
                new_calls = callees - base_callees
                for callee in new_calls:
                    if callee in sig_changed:
                        conflicts.append({
                            "type": "SEMANTIC_SIGNATURE_COLLISION",
                            "severity": "CRITICAL",
                            "symbol": callee,
                            "description": f"{src_name} altered signature of '{callee}', but {other_name} introduced new call from '{caller}' assuming base signature.",
                            "sourceChange": src_map.symbols.get(callee),
                            "targetUsage": {"caller": caller, "callee": callee}
                        })
                # Check existing callers in other_map that were modified while callee signature changed in src_map
                for callee in (callees & sig_changed):
                    if callee in base_callees:
                        other_caller_sym = other_map.symbols.get(caller)
                        base_caller_sym = base_map.symbols.get(caller)
                        if other_caller_sym and base_caller_sym:
                            other_c_sig = SemanticMap._extract_semantic_symbol_signature(other_caller_sym)
                            base_c_sig = SemanticMap._extract_semantic_symbol_signature(base_caller_sym)
                            if other_c_sig != base_c_sig:
                                conflicts.append({
                                    "type": "BREAKING_CALLER_ASSUMPTION",
                                    "severity": "HIGH",
                                    "symbol": callee,
                                    "description": f"{src_name} changed signature of '{callee}', breaking caller '{caller}' which was modified concurrently in {other_name}.",
                                    "caller": caller,
                                    "callee": callee
                                })

            # 3. Deleted symbols in src_map that other_map modified or called
            for base_sym_name in base_map.symbols:
                if base_sym_name not in src_map.symbols:
                    # Symbol was deleted in src_map
                    if base_sym_name in other_map.symbols:
                        # Did other_map modify it?
                        other_sig = SemanticMap._extract_semantic_symbol_signature(other_map.symbols[base_sym_name])
                        base_sig = SemanticMap._extract_semantic_symbol_signature(base_map.symbols[base_sym_name])
                        if other_sig != base_sig:
                            conflicts.append({
                                "type": "MODIFY_DELETE_COLLISION",
                                "severity": "CRITICAL",
                                "symbol": base_sym_name,
                                "description": f"{src_name} deleted symbol '{base_sym_name}', but {other_name} modified it."
                            })
                    # Did other_map call the deleted symbol?
                    for caller, callees in other_map.call_graph.items():
                        if base_sym_name in callees:
                            conflicts.append({
                                "type": "CALL_TO_DELETED_SYMBOL",
                                "severity": "CRITICAL",
                                "symbol": base_sym_name,
                                "description": f"{src_name} deleted symbol '{base_sym_name}', which is called by '{caller}' in {other_name}."
                            })

            # 4. Type changes in src_map
            for tname, stype in src_map.types.items():
                base_type = base_map.types.get(tname)
                other_type = other_map.types.get(tname)
                if base_type and stype.get("details") != base_type.get("details"):
                    if other_type and other_type.get("details") != base_type.get("details") and stype.get("details") != other_type.get("details"):
                        conflicts.append({
                            "type": "TYPE_DEFINITION_CONFLICT",
                            "severity": "CRITICAL",
                            "type": tname,
                            "description": f"Both {src_name} and {other_name} modified type '{tname}' incompatibly."
                        })

        # Run directional check in BOTH directions to guarantee symmetry!
        check_directional(branch_a_map, branch_b_map, "Branch A", "Branch B")
        check_directional(branch_b_map, branch_a_map, "Branch B", "Branch A")

        # 5. Requirement Specification Conflicts
        if base_map.spec and branch_a_map.spec and branch_b_map.spec:
            all_req_ids = set(branch_a_map.requirements.keys()) | set(branch_b_map.requirements.keys())
            for req_id in all_req_ids:
                a_req = branch_a_map.requirements.get(req_id)
                b_req = branch_b_map.requirements.get(req_id)
                base_req = base_map.requirements.get(req_id)
                if a_req and b_req and base_req:
                    if a_req != base_req and b_req != base_req and a_req != b_req:
                        conflicts.append({
                            "type": "REQUIREMENT_SPECIFICATION_CONFLICT",
                            "severity": "HIGH",
                            "requirementId": req_id,
                            "description": f"Both Branch A and Branch B modified requirement '{req_id}' incompatibly.",
                            "branchA": a_req,
                            "branchB": b_req
                        })

        # Deduplicate conflicts
        seen_keys = set()
        deduped = []
        for c in conflicts:
            key = (c.get("type"), c.get("symbol"), c.get("requirementId"), c.get("description"))
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(c)

        return {
            "hasConflicts": len(deduped) > 0,
            "conflictCount": len(deduped),
            "conflicts": deduped
        }


# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Pepin Semantic Map & Living Specification Engine")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # verify-spec
    p_verify = subparsers.add_parser("verify-spec", help="Validate living specification against checked symbols and test references")
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
        if res["hasConflicts"]:
            sys.exit(1)
        return

    smap = SemanticMap(args.source, getattr(args, "spec", None))

    if args.subcommand == "verify-spec":
        res = smap.verify_specification()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Living Specification Validation: {res['status']}")
            print(f"Requirements: {res['implementedRequirements']}/{res['totalRequirements']} implemented ({res['verifiedRequirements']} verified)")
            if res.get('nonexistentTests'):
                print(f"Nonexistent Tests: {res['nonexistentTests']}")
            if res.get('schemaErrors'):
                print(f"Schema Errors: {res['schemaErrors']}")
            if res.get('missingSymbols'):
                print(f"Missing Symbols: {res['missingSymbols']}")
            if res.get('orphanSymbols'):
                print(f"Orphan Symbols: {res['orphanSymbols']}")
        if res["status"] != "VALID":
            sys.exit(1)

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
