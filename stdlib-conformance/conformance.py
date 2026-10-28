"""Standard-library conformance harness for `pep test`.

Purpose
-------
Give the standard library an independent, regression-catching contract without
copying the library, re-implementing its internals, or writing a second test
runner.

How it works
------------
Pep has no imports yet, so a conformance case is *composed*, never duplicated:
the real library source is read from a git object or a working-tree path and
concatenated with a one-line caller. The composed sources and a generated
manifest land under `_build/` (ignored, never committed), and the existing
`test-runner/pep_test.py` runs them — so classification, evidence, JSON shape
and exit codes stay the single implementation in this repository.

The case table is the contract: it names a public helper, the expression to
evaluate and the expected observable result. It says nothing about how the
helper is implemented, so a refactor that preserves behaviour passes and a
regression fails.

Why the Bool shape
------------------
This base has `int_text` but no `bool_text` (measured: `PEP_UNKNOWN_FUNCTION`),
so a Bool result is observed through branching — the smallest honest workaround
that needs no new language surface:

    say(if <expr> { "true" } else { "false" })

Reporting that gap is part of this mission's job; inventing `bool_text` in a
library would silently change observable behaviour, so it is not done here.

Usage
-----
    # against a pinned agent/library revision (no checkout needed)
    git fetch origin codex/native-collections-loop
    python stdlib-conformance/conformance.py --library-rev 872a997 --json

    # against the working tree once the library is merged
    python stdlib-conformance/conformance.py

    # native column where the emitter supports those shapes
    python stdlib-conformance/conformance.py --backend interpreter,clang,gcc
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "test-runner" / "pep_test.py"
DEFAULT_CASES = ROOT / "stdlib-conformance" / "cases.json"
DEFAULT_LIBRARY = "stdlib/collections.pep"

INT_CALL = "say(int_text(%s))"
BOOL_CALL = 'say(if %s { "true" } else { "false" })'
CALL_FORMS = {"Int": INT_CALL, "Bool": BOOL_CALL}


class HarnessError(Exception):
    """A problem with the case table, the library source, or the output dir."""


def load_cases(path):
    try:
        doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HarnessError("case table not found: %s" % path)
    except json.JSONDecodeError as exc:
        raise HarnessError("case table is not JSON: %s" % exc)
    return doc


def validate_cases(doc):
    """Return the validated case list, or raise HarnessError.

    An empty or malformed table is an infrastructure problem, never a green run.
    """
    if not isinstance(doc, dict):
        raise HarnessError("case table must be a JSON object")
    cases = doc.get("cases")
    if not isinstance(cases, list) or not cases:
        raise HarnessError("case table defines no cases")
    seen = set()
    for index, case in enumerate(cases):
        where = "cases[%d]" % index
        if not isinstance(case, dict):
            raise HarnessError("%s must be an object" % where)
        cid = case.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise HarnessError("%s needs a non-empty string id" % where)
        if cid in seen:
            raise HarnessError("duplicate case id: %s" % cid)
        seen.add(cid)
        expr = case.get("expr")
        if not isinstance(expr, str) or not expr.strip():
            raise HarnessError("%s (%s) needs a non-empty expr" % (where, cid))
        result = case.get("result")
        if result not in CALL_FORMS:
            raise HarnessError("%s (%s) result must be one of %s, got %r"
                               % (where, cid, sorted(CALL_FORMS), result))
        expect = case.get("expect")
        if not isinstance(expect, str):
            raise HarnessError("%s (%s) needs a string expect" % (where, cid))
        if result == "Bool" and expect not in ("true", "false"):
            raise HarnessError("%s (%s) Bool expect must be \"true\" or \"false\", got %r"
                               % (where, cid, expect))
    return cases


def read_library_source(repo, library_path, revision=None):
    """Read the library: a git object at `revision`, else the working tree file."""
    repo = pathlib.Path(repo)
    if revision:
        spec = "%s:%s" % (revision, library_path)
        proc = subprocess.run(["git", "show", spec], cwd=str(repo), text=True,
                              capture_output=True, timeout=120)
        if proc.returncode != 0:
            raise HarnessError(
                "cannot read %s from revision %s: %s" % (
                    library_path, revision, (proc.stderr or "").strip()[:300]))
        return proc.stdout, spec
    path = repo / library_path
    if not path.is_file():
        raise HarnessError("library not found in the working tree: %s" % path)
    return path.read_text(encoding="utf-8"), str(path)


FN_START = re.compile(r"(?m)^fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
CALL_SITE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def library_functions(text):
    """Split a library into its top-level `fn` blocks, keyed by name, in order."""
    starts = [(m.start(), m.group(1)) for m in FN_START.finditer(text)]
    blocks, order = {}, []
    for index, (position, name) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        blocks[name] = text[position:end]
        order.append(name)
    return blocks, order


def reachable_functions(text, expression):
    """Library functions the expression needs, including transitive calls.

    Pep has no imports and a composed file pays for everything it contains — the
    staged parser hits its step budget on a whole library plus a caller — so each
    case carries only its own closure.
    """
    blocks, order = library_functions(text)
    needed, pending = set(), [name for name in CALL_SITE.findall(expression)
                              if name in blocks]
    while pending:
        name = pending.pop()
        if name in needed:
            continue
        needed.add(name)
        pending.extend(called for called in CALL_SITE.findall(blocks[name])
                       if called in blocks)
    return [name for name in order if name in needed]


def compose(library_text, case, prune=True):
    """Concatenate the library (or just the case's closure) with one caller."""
    if prune:
        names = reachable_functions(library_text, case["expr"])
        blocks, _order = library_functions(library_text)
        library_text = "".join(blocks[name] for name in names)
    body = library_text if library_text.endswith("\n") else library_text + "\n"
    return body + CALL_FORMS[case["result"]] % case["expr"] + "\n"


def write_workspace(out_dir, cases, library_text, provenance, prune=True):
    """Materialise composed fixtures plus a manifest for the existing runner."""
    out_dir = pathlib.Path(out_dir)
    fixtures = out_dir / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    entries = []
    slug_seen = set()
    pruned = {}
    for case in cases:
        slug = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in case["id"])
        if slug in slug_seen:  # ids are unique, but keep the filename safe anyway
            slug = "%s-%s" % (slug, hashlib.sha1(case["id"].encode()).hexdigest()[:6])
        slug_seen.add(slug)
        names = (reachable_functions(library_text, case["expr"]) if prune
                 else [n for n in library_functions(library_text)[1]])
        pruned[case["id"]] = names
        source = compose(library_text, case, prune=prune)
        (fixtures / (slug + ".pep")).write_text(source, encoding="utf-8", newline="\n")
        entries.append({
            "id": case["id"],
            "file": "fixtures/%s.pep" % slug,
            "kind": "run",
            "expect": {"exit": 0, "stdout": case["expect"] + "\n"},
            "functions": names,
        })
    manifest = {
        "schemaVersion": 1,
        "runner": "stdlib conformance (generated)",
        "fixtures": entries,
        "limits": {"timeoutSeconds": 120},
        "library": provenance,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Run standard-library conformance cases through `pep test`")
    ap.add_argument("--cases", default=str(DEFAULT_CASES),
                    help="case table JSON (default: stdlib-conformance/cases.json)")
    ap.add_argument("--library", default=DEFAULT_LIBRARY,
                    help="library path inside the repository")
    ap.add_argument("--library-rev", default=None,
                    help="read the library from this git revision instead of the working tree")
    ap.add_argument("--repo", default=str(ROOT), help="repository root")
    ap.add_argument("--out", default=None,
                    help="workspace dir (default: _build/stdlib-conformance/<rev-or-tree>)")
    ap.add_argument("--pep", default=None, help="Pep CLI entry override")
    ap.add_argument("--backend", default="interpreter",
                    help="passed through to `pep test --backend`")
    ap.add_argument("--timeout", default=None, help="passed through to `pep test --timeout`")
    ap.add_argument("--filter", default=None, help="passed through to `pep test --filter`")
    ap.add_argument("--evidence-dir", default=None,
                    help="passed through to `pep test --evidence-dir`")
    ap.add_argument("--no-prune", action="store_true",
                    help="compose the whole library instead of each case's closure")
    ap.add_argument("--json", action="store_true",
                    help="emit the runner's JSON document")
    args = ap.parse_args(argv)

    try:
        cases = validate_cases(load_cases(args.cases))
        library_text, spec = read_library_source(args.repo, args.library,
                                                 args.library_rev)
    except HarnessError as exc:
        print("CONFORMANCE-INFRA-ERROR %s" % exc, file=sys.stderr)
        return 2

    provenance = {
        "path": args.library,
        "source": spec,
        "sha256": "sha256:" + hashlib.sha256(library_text.encode("utf-8")).hexdigest(),
        "cases": len(cases),
        "pruned": not args.no_prune,
    }
    out_dir = pathlib.Path(args.out) if args.out else (
        pathlib.Path(args.repo) / "_build" / "stdlib-conformance"
        / (args.library_rev or "worktree"))
    try:
        manifest_path = write_workspace(out_dir, cases, library_text, provenance,
                                        prune=not args.no_prune)
    except OSError as exc:
        print("CONFORMANCE-INFRA-ERROR cannot write workspace: %s" % exc, file=sys.stderr)
        return 2

    cmd = [sys.executable, str(RUNNER), "--manifest", str(manifest_path),
           "--repo", str(args.repo), "--backend", args.backend]
    if args.pep:
        cmd += ["--pep", args.pep]
    if args.timeout:
        cmd += ["--timeout", str(args.timeout)]
    if args.filter:
        cmd += ["--filter", args.filter]
    if args.evidence_dir:
        cmd += ["--evidence-dir", str(args.evidence_dir)]
    if args.json:
        cmd.append("--json")
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=3600)
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if not args.json:
        print("library: %s (%s)" % (spec, provenance["sha256"][:19]))
        print("workspace: %s" % manifest_path.parent)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
