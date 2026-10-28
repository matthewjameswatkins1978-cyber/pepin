"""First-party Pep test runner — Road 2 V8, slice 1.

Uses Pep's actual compiler and interpreter (never interprets Pep itself):
discovers explicitly declared fixtures from an external JSON manifest,
runs each through `pep.ps1 check --json` / `pep.ps1 run`, classifies the
outcome and records human-readable plus machine-readable (`--json`) results.

Outcome taxonomy (mirrors Terror Bats execution splits, unit-test scale):
  pass            behaved exactly as the fixture specifies
  fail            assertion mismatch, or a negative that did not reject exactly
  compile_error   unexpected check failure on a run/check fixture
  runtime_error   nonzero run exit / runtime diagnostic where success expected
  timeout         bounded execution limit exceeded (never a pass)
  infra_error     missing fixture, malformed manifest, CLI crash, non-JSON
                  output, transport failure (never a pass, never a negative pass)
  skip            fixture explicitly marked skipped

A crash, timeout or transport failure NEVER counts as a successful negative
test: kind=reject passes only when `check --json` parses AND reports
status=invalid with exactly the expected diagnostic code (and span, if given).
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

SCHEMA_VERSION = 1
STATUSES = ("pass", "fail", "compile_error", "runtime_error", "timeout",
            "infra_error", "skip")
EXIT_OK = 0
EXIT_TESTS_FAILED = 1
EXIT_INFRA = 2


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def invoke(cli, args, timeout):
    """Run the Pep CLI. Returns (rc, stdout, stderr, elapsed_s, timed_out)."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            list(cli) + [str(a) for a in args],
            text=True, capture_output=True, timeout=timeout, check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr, \
            time.monotonic() - start, False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return None, out, err, time.monotonic() - start, True
    except OSError as exc:
        return None, "", "transport: %s" % exc, time.monotonic() - start, False


def check_fixture(cli, pep_file, timeout):
    """Run `check --json`. Returns (doc, error_detail)."""
    rc, out, err, elapsed, timed_out = invoke(
        cli, ["check", str(pep_file), "--json"], timeout)
    if timed_out:
        return None, {"kind": "timeout", "detail": "check exceeded %ss" % timeout,
                      "elapsed_s": round(elapsed, 3)}
    if rc is None:
        return None, {"kind": "transport", "detail": err, "elapsed_s": round(elapsed, 3)}
    try:
        doc = json.loads(out)
    except json.JSONDecodeError:
        return None, {"kind": "malformed",
                      "detail": "check output was not JSON (rc=%s)" % rc,
                      "stdout": out[-2000:], "stderr": err[-2000:],
                      "elapsed_s": round(elapsed, 3)}
    return {"rc": rc, "doc": doc, "stderr": err,
            "elapsed_s": round(elapsed, 3)}, None


def slugify(value):
    import hashlib as _hashlib
    text = str(value)
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "test"
    return "%s-%s" % (stem[:48], _hashlib.sha1(text.encode("utf-8")).hexdigest()[:8])


def write_evidence(evidence_dir, fixture_id, name, text):
    """Persist one artifact file; return its path, never raise."""
    try:
        target_dir = pathlib.Path(evidence_dir) / slugify(fixture_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / name
        path.write_text(text if isinstance(text, str) else json.dumps(text, indent=2),
                        encoding="utf-8")
        return str(path)
    except OSError:
        return None


def span_matches(actual, expected):
    if not isinstance(actual, dict):
        return False
    for key, value in expected.items():
        if key == "start":
            if not isinstance(actual.get("start"), dict):
                return False
            for sk, sv in value.items():
                if actual["start"].get(sk) != sv:
                    return False
        elif actual.get(key) != value:
            return False
    return True


def run_fixture(cli, repo_root, fx, manifest_dir, timeout_default,
                evidence_dir=None):
    """Execute one manifest fixture. Returns a result dict (never raises)."""
    fid = fx.get("id", "<missing-id>")
    rel = fx.get("file", "")
    kind = fx.get("kind", "run")
    expect = fx.get("expect", {}) or {}
    timeout = fx.get("timeoutSeconds") or timeout_default
    base = {"id": fid, "file": rel, "kind": kind}
    pep_file = manifest_dir / rel if rel else None
    if fx.get("skip"):
        skipped = {"status": "skip", "detail": str(fx["skip"])}
        if pep_file is not None and pep_file.is_file():
            skipped["source_sha256"] = sha256_file(pep_file)
        base.update(skipped)
        return base
    if not rel:
        base.update(status="infra_error", detail="fixture has no file")
        return base
    if not pep_file.is_file():
        base.update(status="infra_error",
                    detail="fixture file missing: %s" % rel)
        return base
    base["source_sha256"] = sha256_file(pep_file)
    if kind not in ("run", "reject", "check"):
        base.update(status="infra_error",
                    detail="unknown kind %r (want run|reject|check)" % kind)
        return base

    checked, err = check_fixture(cli, pep_file, timeout)
    if err is not None:
        base["phase"] = "check"
        if err["kind"] == "timeout":
            base.update(status="timeout", detail=err["detail"],
                        elapsed_s=err["elapsed_s"])
        else:
            base.update(status="infra_error", detail=err)
        return base
    base["check_elapsed_s"] = checked["elapsed_s"]
    doc = checked["doc"]
    diags = doc.get("diagnostics", []) if isinstance(doc, dict) else []
    status = doc.get("status") if isinstance(doc, dict) else None
    if evidence_dir is not None:
        path = write_evidence(evidence_dir, fid, "check.json", doc)
        if path:
            base["evidence"] = {"check.json": path}

    if kind == "reject":
        # Negative passes ONLY on parsed proof of the exact rejection.
        if status != "invalid" or not diags:
            base.update(status="fail",
                        detail="expected rejection but program checked valid",
                        check_rc=checked["rc"])
            return base
        actual_code = diags[0].get("code")
        if actual_code != expect.get("code"):
            base.update(status="fail",
                        detail="rejected with %r, expected %r" % (
                            actual_code, expect.get("code")),
                        diagnostics=diags)
            return base
        if "span" in expect and not span_matches(diags[0].get("span"), expect["span"]):
            base.update(status="fail",
                        detail="code matched but span did not",
                        diagnostics=diags)
            return base
        base.update(status="pass", detail="rejected with %s as specified" % actual_code,
                    diagnostics=diags)
        return base

    # kind run|check: the program must check valid first.
    if status != "valid":
        base.update(status="compile_error",
                    detail="check reported %r" % status,
                    check_rc=checked["rc"], diagnostics=diags)
        return base
    if kind == "check":
        base.update(status="pass", detail="checked valid as specified")
        return base

    rc, out, err_text, elapsed, timed_out = invoke(
        cli, ["run", str(pep_file)], timeout)
    base["run_elapsed_s"] = round(elapsed, 3)
    base["command"] = "pep run %s" % rel
    if timed_out:
        if evidence_dir is not None:
            artifacts = base.get("evidence", {})
            for name, content in (("stdout.txt", out), ("stderr.txt", err_text)):
                path = write_evidence(evidence_dir, fid, name, content)
                if path:
                    artifacts[name] = path
            if artifacts:
                base["evidence"] = artifacts
            base["evidence_note"] = "partial output; process killed at timeout"
        base.update(status="timeout",
                    detail="run exceeded %ss" % timeout)
        return base
    if rc is None:
        base.update(status="infra_error", detail="run transport failure: %s" % err_text)
        return base
    base["exit"] = rc
    base["stdout"] = out
    base["stderr"] = err_text
    if evidence_dir is not None:
        artifacts = base.get("evidence", {})
        for name, content in (("stdout.txt", out), ("stderr.txt", err_text)):
            path = write_evidence(evidence_dir, fid, name, content)
            if path:
                artifacts[name] = path
        if artifacts:
            base["evidence"] = artifacts
    want_exit = expect.get("exit", 0)
    want_code = expect.get("diagnosticCode")
    if want_code is None:
        code_ok = True
    else:
        # Observed CLI contract: runtime diagnostics print as `line:col: CODE: message`.
        # A bare code word in program output must NOT satisfy an expected diagnostic.
        code_ok = re.search(r"(?m)^\d+:\d+:\s*" + re.escape(want_code) + r"\b",
                            out + err_text) is not None
    if rc == want_exit and out == expect.get("stdout", out) and code_ok:
        if rc == 0:
            base.update(status="pass", detail="exit 0 and stdout matched")
        else:
            base.update(status="pass",
                        detail="failed exactly as specified (exit %s, %s observed)" % (
                            rc, want_code or "output matched"))
        return base
    if rc != 0:
        base.update(status="runtime_error",
                    detail="exit %s, expected %s" % (rc, want_exit))
        return base
    base.update(status="fail",
                detail="stdout mismatch: got %r, expected %r" % (
                    out, expect.get("stdout")))
    return base


def summarize(results):
    counts = {s: 0 for s in STATUSES}
    for r in results:
        counts[r.get("status", "infra_error")] = counts.get(r.get("status"), 0) + 1
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description="First-party Pep test runner (V8 slice 1)")
    ap.add_argument("--manifest", default=None,
                    help="manifest JSON (default: test-runner/manifest.json under repo root)")
    ap.add_argument("--filter", default=None,
                    help="run only fixtures whose id contains this substring")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON document")
    ap.add_argument("--list", action="store_true",
                    help="list declared fixtures without executing them")
    ap.add_argument("--timeout", type=float, default=None,
                    help="per-phase seconds override")
    ap.add_argument("--pep", default=None,
                    help="Pep CLI entry (default: pep.ps1 next to this script's repo root)")
    ap.add_argument("--repo", default=None,
                    help="repository root (default: parent of test-runner/)")
    ap.add_argument("--evidence-dir", default=None,
                    help="artifact directory (default: _build/pep-test-evidence/<UTC timestamp> under repo root)")
    args = ap.parse_args(argv)

    here = pathlib.Path(__file__).resolve()
    repo_root = pathlib.Path(args.repo).resolve() if args.repo else here.parents[1]
    manifest_path = pathlib.Path(args.manifest).resolve() if args.manifest \
        else repo_root / "test-runner" / "manifest.json"
    manifest_dir = manifest_path.parent
    # CLI invocation: pep.ps1 via pwsh, or a python stub in tests.
    pep_entry = args.pep or (repo_root / "pep.ps1")
    if str(pep_entry).endswith(".py"):
        cli_base = [sys.executable, str(pep_entry)]
    else:
        cli_base = ["pwsh", "-NoProfile", "-File", str(pep_entry)]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return finish(None, {"status": "infra_error",
                             "detail": "manifest not found: %s" % manifest_path},
                      args)
    except json.JSONDecodeError as exc:
        return finish(None, {"status": "infra_error",
                             "detail": "manifest is not JSON: %s" % exc}, args)
    fixtures = manifest.get("fixtures", [])
    if not isinstance(fixtures, list):
        return finish(None, {"status": "infra_error",
                             "detail": "manifest.fixtures must be a list"}, args)
    timeout_default = args.timeout or manifest.get("limits", {}).get("timeoutSeconds", 120)

    if args.filter:
        fixtures = [f for f in fixtures if args.filter in str(f.get("id", ""))]

    if args.list:
        listing = [{"id": str(f.get("id", "")), "file": f.get("file", ""),
                    "kind": f.get("kind", "run"),
                    "skip": f.get("skip")} for f in fixtures]
        if args.json:
            print(json.dumps({"schemaVersion": SCHEMA_VERSION,
                              "runner": "pep test v1", "manifest": str(manifest_path),
                              "tests": listing}, indent=2))
        else:
            for entry in listing:
                flag = " (skip: %s)" % entry["skip"] if entry.get("skip") else ""
                print("%-28s %-12s %s%s" % (entry["id"], entry["kind"],
                                            entry["file"], flag))
        return EXIT_OK

    if args.evidence_dir:
        evidence_root = pathlib.Path(args.evidence_dir)
    else:
        evidence_root = repo_root / "_build" / "pep-test-evidence" / \
            datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_root.mkdir(parents=True, exist_ok=True)
    results = [run_fixture(cli_base, repo_root, fx, manifest_dir, timeout_default,
                           evidence_root)
               for fx in fixtures]
    counts = summarize(results)
    try:
        repo_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root),
                                  text=True, capture_output=True,
                                  timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        repo_rev = "unknown"
    try:
        compiler_src = repo_root / "pep_ocaml.ml"
        toolchain = {"pepCli": str(pathlib.Path(pep_entry).name),
                     "compilerSource": sha256_file(compiler_src) if compiler_src.is_file() else "missing"}
    except OSError:
        toolchain = {"pepCli": str(pep_entry), "compilerSource": "unreadable"}
    doc = {"schemaVersion": SCHEMA_VERSION, "runner": "pep test v1",
           "repoRevision": repo_rev, "backend": "interpreter",
           "toolchain": toolchain, "manifest": str(manifest_path),
           "evidence_root": str(evidence_root),
           "counts": counts, "tests": results}
    failed = counts["fail"] + counts["compile_error"] + counts["runtime_error"] + \
        counts["timeout"] + counts["infra_error"]
    return finish(doc, None, args, failed=failed)


def finish(doc, infra, args, failed=0):
    if args.json:
        if doc is None:
            doc = {"schemaVersion": SCHEMA_VERSION, "runner": "pep test v1",
                   "counts": {"infra_error": 1}, "tests": [], "error": infra}
        print(json.dumps(doc, indent=2))
    else:
        if doc is None:
            print("INFRA-ERROR %s" % (infra or {}).get("detail", "?"))
            return EXIT_INFRA
        for t in doc["tests"]:
            print("%-12s %-28s %s" % (t.get("status", "?").upper(),
                                      t.get("id", "?"), t.get("detail", "")))
        c = doc["counts"]
        print("pass=%d fail=%d compile_error=%d runtime_error=%d timeout=%d infra_error=%d skip=%d" % (
            c.get("pass", 0), c.get("fail", 0), c.get("compile_error", 0),
            c.get("runtime_error", 0), c.get("timeout", 0),
            c.get("infra_error", 0), c.get("skip", 0)))
        if doc.get("evidence_root"):
            print("evidence: %s" % doc["evidence_root"])
    if infra is not None:
        return EXIT_INFRA
    return EXIT_OK if failed == 0 else EXIT_TESTS_FAILED


if __name__ == "__main__":
    sys.exit(main())
