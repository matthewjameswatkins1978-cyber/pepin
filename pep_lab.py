"""Pep Lab: Living Prompt over the existing OCaml seed.

Thin file-backed wrapper. It does NOT change pep_ocaml.ml, the session
protocol, or any accepted language semantics. All evaluation and
inspection delegate to the existing ``pep.ps1`` CLI:

- evaluation: ``pep.ps1 run FILE``
- compiler inspection: ``describe`` / ``check`` / ``inspect`` / ``query --holes``
- persistent definitions: a ``definitions.pep`` store file validated with
  ``check`` before each atomic update (temp file + replace, so a crash or a
  rejected snippet can never leave a truncated store)
- source export: a plain ``.pep`` file with an explicit dependency header

The in-process ``session --jsonl`` keeps revisions only for its own
lifetime; this wrapper provides persistence by keeping ordinary source
bytes in files, which remain the durable program (Founding Design v0.3).

The ``repl`` command adds an interactive text prompt: type Pep code
(several lines if needed), a blank line checks the buffer, ``:run``
evaluates it once against the stored definitions, and ``:def`` persists it.
The buffer is never re-executed implicitly and quitting never writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
PEP = ROOT / "pep.ps1"
STORE_FILENAME = "definitions.pep"

FN_RE = re.compile(r"^\s*fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)

# Bounded execution: the seed compiler answers in seconds; never wait forever
# on a hung subprocess. Missing pwsh/pep.ps1 surfaces as RuntimeError, not a
# traceback, so scripts and the REPL can report it as infrastructure failure.
PEP_TIMEOUT = 120


def _run_pep(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *args],
            cwd=ROOT, text=True, capture_output=True, check=False,
            input=input_text, timeout=PEP_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"cannot launch pep subprocess: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"pep subprocess timed out after {PEP_TIMEOUT}s: {' '.join(args)}"
        ) from exc


def _load_json(proc: subprocess.CompletedProcess[str], what: str) -> dict:
    if proc.returncode != 0:
        raise RuntimeError(f"{what} failed: {proc.stderr.strip()}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{what} returned malformed JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{what} returned a non-object JSON payload")
    return payload


def cmd_describe() -> dict:
    payload = _load_json(_run_pep("describe", "--json"), "describe")
    if payload.get("schemaVersion") != 2 or payload.get("language") != "Pep":
        raise RuntimeError(f"describe returned unexpected identity: {payload!r:.200}")
    return payload


def cmd_check(path: pathlib.Path) -> dict:
    # The file CLI exits nonzero for incomplete/invalid programs but still
    # emits the JSON payload on stdout; prefer that payload over the exit
    # code so callers can distinguish valid/incomplete/invalid from a real
    # transport failure (no usable JSON at all).
    proc = _run_pep("check", str(path), "--json")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"check failed (exit {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()[:200]}"
        ) from exc
    if not isinstance(payload, dict) or "status" not in payload:
        raise RuntimeError("check returned JSON without a status field")
    return payload


def cmd_inspect(path: pathlib.Path) -> dict:
    return _load_json(_run_pep("inspect", str(path), "--json"), "inspect")


def cmd_holes(path: pathlib.Path, offset: int | None = None) -> dict:
    args = ["query", str(path), "--holes", "--json"]
    if offset is not None:
        args += ["--offset", str(offset)]
    return _load_json(_run_pep(*args), "query")


def cmd_eval(path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return _run_pep("run", str(path))


def _read_store(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"store file is not valid UTF-8: {path}") from exc


def store_path(store_dir: pathlib.Path) -> pathlib.Path:
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir / STORE_FILENAME


def list_definitions(store_dir: pathlib.Path) -> list[str]:
    path = store_dir / STORE_FILENAME
    if not path.exists():
        return []
    return FN_RE.findall(_read_store(path))


def define_source(store_dir: pathlib.Path, snippet: str) -> dict:
    """Validate ``existing defs + snippet`` with ``check``, then append.

    Accepts ``valid`` or ``incomplete`` combined status (holes allowed);
    rejects ``invalid`` so one bad definition cannot poison the store.
    Returns the combined check payload plus the stored function names.
    """
    path = store_path(store_dir)
    existing = _read_store(path) if path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    if not snippet.endswith("\n"):
        snippet += "\n"
    combined = existing + snippet
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pep", delete=False, encoding="utf-8",
        newline="\n",  # never let Windows text mode rewrite stored bytes to CRLF
    ) as tmp:
        tmp.write(combined)
        tmp_path = pathlib.Path(tmp.name)
    try:
        payload = cmd_check(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    if payload.get("status") == "invalid":
        raise ValueError(f"definition rejected: {payload.get('diagnostics')!r}")
    # Atomic durable write: temp file in the same directory, then replace, so
    # a crash or failed validation can never leave a truncated store behind.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pep", delete=False, encoding="utf-8",
        newline="\n",  # byte fidelity: stored source keeps LF newlines
        dir=str(path.parent),
    ) as tmp:
        tmp.write(combined)
        tmp_path = pathlib.Path(tmp.name)
    os.replace(tmp_path, path)
    return {"status": payload.get("status"), "functions": FN_RE.findall(snippet)}


def export_store(store_dir: pathlib.Path, output: pathlib.Path) -> dict:
    """Write the stored definitions to ``output`` with an explicit header."""
    src = store_dir / STORE_FILENAME
    if not src.exists():
        raise FileNotFoundError(f"no lab store at {src}")
    body = _read_store(src)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    names = FN_RE.findall(body)
    header = (
        "# Pep Lab export: ordinary source, explicit dependencies only.\n"
        f"# store_sha256: {digest}\n"
        f"# definitions: {', '.join(names) if names else '(none)'}\n"
        "# Common lab modules are NOT implicit; import by pasting this file.\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pep", delete=False, encoding="utf-8",
        newline="\n",  # exported bytes are exactly header + stored body
        dir=str(output.parent),
    ) as tmp:
        tmp.write(header + body)
        tmp_path = pathlib.Path(tmp.name)
    os.replace(tmp_path, output)
    return {"output": str(output), "sha256": digest, "definitions": names}


def eval_with_store(store_dir: pathlib.Path, main_source: str) -> subprocess.CompletedProcess[str]:
    """Evaluate ``stored defs + main_source`` via a temp file with ``run``."""
    src = store_dir / STORE_FILENAME
    defs = _read_store(src) if src.exists() else ""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pep", delete=False, encoding="utf-8",
        newline="\n", dir=ROOT
    ) as tmp:
        # dir=ROOT keeps Resolve-Path simple on Windows; removed afterwards.
        tmp.write(defs + main_source)
        tmp_path = pathlib.Path(tmp.name)
    try:
        return cmd_eval(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _hole_name(hole: dict) -> object:
    # `query --holes` calls it `identity`; `check` calls it `name`.
    return hole.get("name", hole.get("identity"))


def _hole_suggestions(hole: dict) -> str:
    # Prefer the compiler's fill candidates; fall back to visible bindings.
    candidates = []
    for action in hole.get("actions", []) or []:
        candidates.extend(c.get("name") for c in action.get("candidates", []) or [])
    if not candidates:
        candidates = [b.get("name") for b in hole.get("bindings", []) or []]
    seen = [c for c in dict.fromkeys(candidates) if c]
    return f" (try: {', '.join(seen)})" if seen else ""


def _excerpt(source_text: str, line: int | None, column: int | None) -> str:
    if not source_text or not line:
        return ""
    lines = source_text.split("\n")
    if line < 1 or line > len(lines):
        return ""
    text = lines[line - 1]
    caret = " " * max((column or 1) - 1, 0) + "^" if column else ""
    return f"\n  > {text}" + (f"\n    {caret}" if caret else "")


def _format_status(payload: dict, source_text: str | None = None) -> str:
    """One-line human summary of a check payload for the REPL."""
    status = payload.get("status")
    if status == "valid":
        return "valid"
    if status == "incomplete":
        holes = payload.get("holes", [])
        names = ", ".join(
            f"{_hole_name(h)} ({h.get('expectedType')}) in {h.get('scope')}{_hole_suggestions(h)}"
            for h in holes
        )
        return f"incomplete: holes [{names}]" if names else "incomplete"
    if status == "invalid":
        parts = []
        for diag in payload.get("diagnostics", []):
            span = diag.get("span", {}) or {}
            start = span.get("start", {}) or {}
            at = f" @ {start.get('line')}:{start.get('column')}" \
                if start.get("line") is not None else ""
            excerpt = _excerpt(source_text or "", start.get("line"), start.get("column"))
            parts.append(f"{diag.get('code')}: {diag.get('message')}{at}{excerpt}")
        detail = "; ".join(parts) if parts else "no diagnostics"
        return f"invalid: {detail}"
    return f"unknown status: {status!r}"


REPL_HELP = """Pep Lab REPL -- an interactive text prompt over the seed compiler.
Type Pep code, several lines if needed; a blank line checks the buffer.
Commands (prefix with a colon):
  :help          show this help
  :run            evaluate stored definitions + buffer (runs once)
  :def            validate the buffer and persist it as definitions
  :check          re-check stored definitions + buffer
  :holes          list typed holes in stored definitions + buffer
  :show           list persisted definition names
  :info            show checked signatures of stored defs + buffer state
  :export FILE    export definitions to a portable .pep file
  :describe       show the compiler identity
  :pop            drop the last buffered line
  :clear          discard the buffer
  :quit           leave the REPL (also Ctrl-D)"""


class ReplSession:
    """Interactive prompt state: a line buffer over a file-backed store.

    The buffer is ad-hoc experiment text; only ``:def`` persists. Buffers
    are checked and run as ``stored definitions + buffer`` so experiments
    can use persisted functions. Each ``:run`` executes once -- nothing is
    re-executed implicitly -- and quitting never writes the store.
    """

    def __init__(self, store_dir: pathlib.Path):
        self.store_dir = store_dir
        self.buf: list[str] = []

    def buffer_text(self) -> str:
        text = "\n".join(self.buf)
        return text + "\n" if text else ""

    def combined_text(self) -> str:
        src = self.store_dir / STORE_FILENAME
        defs = _read_store(src) if src.exists() else ""
        if defs and not defs.endswith("\n"):
            defs += "\n"
        return defs + self.buffer_text()

    def _check_combined(self) -> dict:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pep", delete=False, encoding="utf-8",
            newline="\n",
        ) as tmp:
            tmp.write(self.combined_text())
            tmp_path = pathlib.Path(tmp.name)
        try:
            return cmd_check(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _holes_combined(self) -> dict:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pep", delete=False, encoding="utf-8",
            newline="\n",
        ) as tmp:
            tmp.write(self.combined_text())
            tmp_path = pathlib.Path(tmp.name)
        try:
            return cmd_holes(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _info(self) -> str:
        """Checked signatures of stored definitions plus buffer state."""
        lines = []
        src = self.store_dir / STORE_FILENAME
        if src.exists():
            try:
                payload = cmd_check(src)
            except (RuntimeError, ValueError) as exc:
                lines.append(f"store: cannot check ({exc})")
            else:
                fns = (payload.get("typedTree") or {}).get("functions", [])
                if not fns:
                    lines.append(f"store: {payload.get('status')} (no functions)")
                for fn in fns:
                    params = ", ".join(
                        f"{p.get('name')}: {p.get('type')}"
                        for p in fn.get("parameters", []))
                    lines.append(f"store: fn {fn.get('name')}({params}) -> {fn.get('returnType')}")
        else:
            lines.append("store: (empty)")
        if self.buf:
            lines.append(f"buffer: {len(self.buf)} line(s):")
            lines.extend(f"  {i + 1}: {text}" for i, text in enumerate(self.buf))
        else:
            lines.append("buffer: (empty)")
        return "\n".join(lines)

    def handle(self, line: str) -> tuple[str, bool]:
        """Handle one input line; returns (output text, quit flag)."""
        stripped = line.strip()
        try:
            if stripped in (":quit", ":exit", ":q"):
                return ("bye", True)
            if stripped == ":help":
                return (REPL_HELP, False)
            if stripped == ":clear":
                self.buf = []
                return ("buffer cleared", False)
            if stripped == ":pop":
                if not self.buf:
                    return ("buffer is already empty", False)
                self.buf.pop()
                return (f"dropped; {len(self.buf)} line(s) buffered", False)
            if stripped == ":show":
                names = list_definitions(self.store_dir)
                return ("definitions: " + (", ".join(names) if names else "(none)"), False)
            if stripped == ":info":
                return (self._info(), False)
            if stripped == ":describe":
                info = cmd_describe()
                builtins = [b["name"] for b in info.get("builtins", [])]
                return (f"Pep with {', '.join(info.get('types', []))}; "
                        f"builtins: {', '.join(builtins)}", False)
            if stripped == ":check":
                if not self.buf:
                    return ("buffer is empty -- type Pep code first", False)
                combined = self.combined_text()
                return (_format_status(self._check_combined(), combined), False)
            if stripped == ":holes":
                payload = self._holes_combined()
                holes = payload.get("holes", [])
                if not holes:
                    return (f"{payload.get('status', 'unknown')}: no holes", False)
                lines = [f"{_hole_name(h)} : {h.get('expectedType')} "
                         f"in {h.get('scope')}{_hole_suggestions(h)}" for h in holes]
                return ("holes:\n" + "\n".join(lines), False)
            if stripped == ":run":
                if not self.buf:
                    return ("buffer is empty -- type Pep code first", False)
                proc = eval_with_store(self.store_dir, self.buffer_text())
                out = proc.stdout
                if proc.returncode != 0:
                    out += f"[exit {proc.returncode}]\n{proc.stderr}"
                return (out.rstrip("\n") or f"[exit {proc.returncode}]", False)
            if stripped == ":def":
                if not self.buf:
                    return ("buffer is empty -- type Pep code first", False)
                try:
                    result = define_source(self.store_dir, self.buffer_text())
                except ValueError as exc:
                    # Keep the buffer so the user can correct and retry.
                    return (f"not persisted: {exc}", False)
                self.buf = []
                names = ", ".join(result["functions"]) or "(no functions)"
                return (f"persisted ({result['status']}): {names}", False)
            if stripped.startswith(":export"):
                target = stripped[len(":export"):].strip()
                if not target:
                    return ("usage: :export FILE", False)
                result = export_store(self.store_dir, pathlib.Path(target))
                names = ", ".join(result["definitions"]) or "(none)"
                return (f"exported {result['output']} [{result['sha256'][:12]}]: {names}", False)
            if stripped.startswith(":"):
                return (f"unknown command {stripped!r} -- try :help", False)
            if stripped == "":
                if not self.buf:
                    return ("", False)
                return (_format_status(self._check_combined(), self.combined_text()), False)
            self.buf.append(line.rstrip("\n"))
            return (f"... ({len(self.buf)} buffered)", False)
        except (RuntimeError, ValueError, FileNotFoundError, OSError,
                UnicodeDecodeError) as exc:
            return (f"error: {exc}", False)


def run_repl(store_dir: pathlib.Path, stdin=None, stdout=None) -> int:
    """Run the interactive loop; ``stdin``/``stdout`` allow scripted use."""
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    session = ReplSession(store_dir)
    stdout.write("Pep Lab REPL -- :help for commands, blank line checks, :quit to leave.\n")
    stdout.flush()
    while True:
        try:
            stdout.write("pep> " if not session.buf else "...+ ")
            stdout.flush()
            line = stdin.readline()
        except KeyboardInterrupt:
            stdout.write("\nbuffer cleared\n")
            session.buf = []
            continue
        if line == "":
            stdout.write("bye\n")
            return 0
        try:
            output, quit = session.handle(line.rstrip("\n"))
        except KeyboardInterrupt:
            stdout.write("\nbuffer cleared\n")
            session.buf = []
            continue
        if output:
            stdout.write(output + "\n")
            stdout.flush()
        if quit:
            return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pep Lab Living Prompt (step 1)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("eval", help="evaluate a .pep file with the seed interpreter")
    p_eval.add_argument("file")

    p_check = sub.add_parser("check", help="compiler check with JSON output")
    p_check.add_argument("file")

    p_inspect = sub.add_parser("inspect", help="compiler inspect with JSON output")
    p_inspect.add_argument("file")

    p_holes = sub.add_parser("holes", help="typed-hole query with JSON output")
    p_holes.add_argument("file")
    p_holes.add_argument("--offset", type=int, default=None)

    sub.add_parser("describe", help="compiler identity with JSON output")

    p_define = sub.add_parser("define", help="validate and persist a definition snippet")
    p_define.add_argument("--store", required=True)
    group = p_define.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", default=None)
    group.add_argument("--file", default=None)

    p_show = sub.add_parser("show", help="list persisted definition names")
    p_show.add_argument("--store", required=True)

    p_export = sub.add_parser("export", help="export store to a plain .pep file")
    p_export.add_argument("--store", required=True)
    p_export.add_argument("--output", required=True)

    p_run = sub.add_parser("eval-store", help="evaluate snippet on top of stored defs")
    p_run.add_argument("--store", required=True)
    p_run.add_argument("--file", required=True)

    p_repl = sub.add_parser("repl", help="interactive text prompt over the seed compiler")
    p_repl.add_argument("--store", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "eval":
            proc = cmd_eval(pathlib.Path(args.file))
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)
            return proc.returncode
        if args.command == "check":
            print(json.dumps(cmd_check(pathlib.Path(args.file)), indent=2))
            return 0
        if args.command == "inspect":
            print(json.dumps(cmd_inspect(pathlib.Path(args.file)), indent=2))
            return 0
        if args.command == "holes":
            print(json.dumps(cmd_holes(pathlib.Path(args.file), args.offset), indent=2))
            return 0
        if args.command == "describe":
            print(json.dumps(cmd_describe(), indent=2))
            return 0
        if args.command == "define":
            snippet = args.source if args.source is not None else pathlib.Path(args.file).read_text(encoding="utf-8")
            print(json.dumps(define_source(pathlib.Path(args.store), snippet), indent=2))
            return 0
        if args.command == "show":
            print(json.dumps({"store": args.store, "definitions": list_definitions(pathlib.Path(args.store))}, indent=2))
            return 0
        if args.command == "export":
            print(json.dumps(export_store(pathlib.Path(args.store), pathlib.Path(args.output)), indent=2))
            return 0
        if args.command == "repl":
            return run_repl(pathlib.Path(args.store))
        if args.command == "eval-store":
            main_source = pathlib.Path(args.file).read_text(encoding="utf-8")
            proc = eval_with_store(pathlib.Path(args.store), main_source)
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)
            return proc.returncode
    except (RuntimeError, ValueError, FileNotFoundError, OSError, UnicodeDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
