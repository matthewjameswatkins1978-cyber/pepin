"""Pep Lab Persistent Workshop: project workspaces over ordinary files.

A workshop *root* is a plain directory. Each subdirectory holding a
``project.json`` is a project; a subdirectory with ``definitions.pep`` or
``buffers/`` but no ``project.json`` is a legacy Pep Lab store and is
adopted seamlessly on first open (contents preserved, ``project.json``
added). There is no database and no second source representation: a
project directory *is* a Pep Lab store directory, so every existing
``--store DIR`` workflow keeps working unchanged.

Layout::

    <root>/
      active.json            -- {"active": "<name>"}; absent means none
      <name>/
        project.json         -- {"schema": 1, "name": ..., ...}
        definitions.pep      -- persisted definitions (as before)
        buffers/             -- named experiment buffers (as before)
        checkpoints/         -- W2 source revisions
        experiments/         -- W3 repeatable experiment records

``active.json`` records the last opened project so a developer can leave
Pep Lab and resume where they were.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile

WORKSHOP_SCHEMA = 1
PROJECT_FILENAME = "project.json"
ACTIVE_FILENAME = "active.json"
STORE_FILENAME = "definitions.pep"
BUFFERS_DIRNAME = "buffers"

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
RESERVED_NAMES = {"active.json", PROJECT_FILENAME}


def check_name(kind: str, name: str | None) -> str:
    if not name or not NAME_RE.match(name) or name in RESERVED_NAMES:
        raise ValueError(
            f"bad {kind} name {name!r}: use 1-64 letters/digits/_/-, starting alphanumeric")
    return name


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".tmp", delete=False, encoding="utf-8",
        newline="\n", dir=str(path.parent),
    ) as tmp:
        tmp.write(text)
        tmp_path = pathlib.Path(tmp.name)
    os.replace(tmp_path, path)


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def project_dir(root: pathlib.Path, name: str) -> pathlib.Path:
    return root / check_name("project", name)


def project_meta_file(proj: pathlib.Path) -> pathlib.Path:
    return proj / PROJECT_FILENAME


def read_project_meta(proj: pathlib.Path) -> dict:
    meta_file = project_meta_file(proj)
    try:
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"not a project: {proj}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"project metadata is corrupt: {meta_file} ({exc})") from exc
    if not isinstance(payload, dict) or payload.get("schema") != WORKSHOP_SCHEMA:
        raise ValueError(f"project metadata is corrupt or unsupported: {meta_file}")
    return payload


def is_legacy_store(proj: pathlib.Path) -> bool:
    return proj.is_dir() and not project_meta_file(proj).exists() and (
        (proj / STORE_FILENAME).exists() or (proj / BUFFERS_DIRNAME).is_dir())


def adopt_legacy_store(proj: pathlib.Path, name: str) -> dict:
    """Write project.json for a pre-existing store dir; contents untouched."""
    meta = {"name": name, "schema": WORKSHOP_SCHEMA, "created_utc": _utcnow(),
            "tool": "pep_workshop/1", "adopted": True}
    _atomic_write_text(project_meta_file(proj),
                       json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def create_project(root: pathlib.Path, name: str) -> dict:
    name = check_name("project", name)
    proj = root / name
    if project_meta_file(proj).exists():
        raise ValueError(f"project already exists: {name!r}")
    if proj.is_file() or (proj.exists() and not proj.is_dir()):
        raise ValueError(f"cannot create project over a non-directory: {proj}")
    if is_legacy_store(proj):
        meta = adopt_legacy_store(proj, name)
        return {"project": name, "dir": str(proj), "adopted": True, "meta": meta}
    proj.mkdir(parents=True, exist_ok=True)
    meta = {"name": name, "schema": WORKSHOP_SCHEMA, "created_utc": _utcnow(),
            "tool": "pep_workshop/1"}
    _atomic_write_text(project_meta_file(proj),
                       json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return {"project": name, "dir": str(proj), "adopted": False, "meta": meta}


def list_projects(root: pathlib.Path) -> dict:
    entries = []
    if root.is_dir():
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if not child.is_dir() or child.is_symlink():
                continue
            name = child.name
            if not NAME_RE.match(name) or name in RESERVED_NAMES:
                continue
            if project_meta_file(child).exists():
                try:
                    meta = read_project_meta(child)
                    entries.append({"name": name, "status": "ok",
                                    "created_utc": meta.get("created_utc"),
                                    "adopted": bool(meta.get("adopted"))})
                except ValueError:
                    entries.append({"name": name, "status": "corrupt"})
            elif is_legacy_store(child):
                entries.append({"name": name, "status": "legacy"})
    return {"root": str(root), "active": read_active(root), "projects": entries}


def _active_file(root: pathlib.Path) -> pathlib.Path:
    return root / ACTIVE_FILENAME


def read_active(root: pathlib.Path) -> str | None:
    active_file = _active_file(root)
    if not active_file.exists():
        return None
    try:
        payload = json.loads(active_file.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"active pointer is corrupt: {active_file} ({exc})") from exc
    active = payload.get("active") if isinstance(payload, dict) else None
    if not isinstance(active, str) or not active:
        raise ValueError(f"active pointer is corrupt: {active_file}")
    return active


def write_active(root: pathlib.Path, name: str) -> None:
    _atomic_write_text(_active_file(root),
                       json.dumps({"active": name}, indent=2, sort_keys=True) + "\n")


def open_project(root: pathlib.Path, name: str) -> dict:
    """Open (and adopt if legacy) a project; records it as active."""
    name = check_name("project", name)
    proj = root / name
    if not proj.is_dir():
        raise FileNotFoundError(f"no such project: {name!r}")
    adopted = False
    if not project_meta_file(proj).exists():
        if not is_legacy_store(proj):
            raise FileNotFoundError(f"not a project: {name!r}")
        adopt_legacy_store(proj, name)
        adopted = True
    else:
        read_project_meta(proj)  # fail cleanly on corruption
    root.mkdir(parents=True, exist_ok=True)
    write_active(root, name)
    return {"project": name, "dir": str(proj), "adopted": adopted, "active": name}


def resolve_project_dir(root: pathlib.Path, name: str | None) -> pathlib.Path:
    """Resolve a project directory: named, else the active pointer."""
    if name is not None:
        check_name("project", name)
        proj = root / name
        if not proj.is_dir() or not project_meta_file(proj).exists():
            raise FileNotFoundError(f"no such project: {name!r}")
        return proj
    active = read_active(root)
    if active is None:
        raise FileNotFoundError(f"no active project in {root}; open one first")
    return resolve_project_dir(root, active)


def project_source_digest(proj: pathlib.Path) -> str:
    """SHA-256 of the project's current definitions source (may be empty)."""
    store = proj / STORE_FILENAME
    data = store.read_bytes() if store.exists() else b""
    return "sha256:" + hashlib.sha256(data).hexdigest()


CHECKPOINTS_DIRNAME = "checkpoints"
CHECKPOINT_ID_RE = re.compile(r"^cp-(\d{3})$")


def checkpoints_dir(proj: pathlib.Path) -> pathlib.Path:
    return proj / CHECKPOINTS_DIRNAME


def _checkpoint_index_file(proj: pathlib.Path) -> pathlib.Path:
    return checkpoints_dir(proj) / "index.json"


def _scan_checkpoint_ids(proj: pathlib.Path) -> list[str]:
    cdir = checkpoints_dir(proj)
    if not cdir.is_dir():
        return []
    ids = []
    for child in cdir.iterdir():
        if child.is_file() and child.suffix == ".pep" and CHECKPOINT_ID_RE.match(child.stem):
            ids.append(child.stem)
    return sorted(ids)


def _read_checkpoint_index(proj: pathlib.Path) -> list[dict]:
    index_file = _checkpoint_index_file(proj)
    if not index_file.exists():
        return []
    try:
        payload = json.loads(index_file.read_text(encoding="utf-8"))
        entries = payload.get("checkpoints")
        if isinstance(payload, dict) and isinstance(entries, list):
            return entries
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        pass
    # Corrupt index: rebuild from the immutable snapshot files on disk.
    rebuilt = []
    for cid in _scan_checkpoint_ids(proj):
        try:
            meta = read_checkpoint_meta(proj, cid)
            rebuilt.append({k: meta[k] for k in
                            ("id", "label", "created_utc", "digest", "bytes")})
        except (ValueError, FileNotFoundError, OSError):
            continue
    return rebuilt


def _write_checkpoint_index(proj: pathlib.Path, entries: list[dict]) -> None:
    _atomic_write_text(_checkpoint_index_file(proj),
                       json.dumps({"schema": WORKSHOP_SCHEMA, "checkpoints": entries},
                                  indent=2, sort_keys=True) + "\n")


def read_checkpoint_meta(proj: pathlib.Path, cid: str) -> dict:
    if not CHECKPOINT_ID_RE.match(cid or ""):
        raise ValueError(f"bad checkpoint id {cid!r}: expected cp-NNN")
    meta_file = checkpoints_dir(proj) / f"{cid}.json"
    src_file = checkpoints_dir(proj) / f"{cid}.pep"
    try:
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"no such checkpoint: {cid!r}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"checkpoint metadata is corrupt: {meta_file} ({exc})") from exc
    if not isinstance(payload, dict) or payload.get("id") != cid:
        raise ValueError(f"checkpoint metadata is corrupt: {meta_file}")
    if not src_file.exists():
        raise ValueError(f"checkpoint source is missing: {src_file}")
    return payload


def save_checkpoint(root: pathlib.Path, name: str, label: str | None = None) -> dict:
    """Snapshot the project's current definitions source immutably."""
    proj = resolve_project_dir(root, name)
    store = proj / STORE_FILENAME
    try:
        data = store.read_bytes() if store.exists() else b""
    except OSError as exc:
        raise ValueError(f"cannot read project source: {exc}") from exc
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"project source is not valid UTF-8: {store}") from exc
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    existing = _read_checkpoint_index(proj)
    taken = {e.get("id") for e in existing if isinstance(e, dict)}
    n = 1
    while f"cp-{n:03d}" in taken:
        n += 1
    cid = f"cp-{n:03d}"
    cdir = checkpoints_dir(proj)
    cdir.mkdir(parents=True, exist_ok=True)
    meta = {"schema": WORKSHOP_SCHEMA, "id": cid, "project": proj.name,
            "label": label or "", "created_utc": _utcnow(),
            "digest": digest, "bytes": len(data), "tool": "pep_workshop/1",
            "revision_kind": "workshop-file-sha256"}
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".pep", delete=False, dir=str(cdir)) as tmp:
        tmp.write(data)
        tmp_path = pathlib.Path(tmp.name)
    os.replace(tmp_path, cdir / f"{cid}.pep")
    _atomic_write_text(cdir / f"{cid}.json",
                       json.dumps(meta, indent=2, sort_keys=True) + "\n")
    _write_checkpoint_index(proj, existing + [
        {k: meta[k] for k in ("id", "label", "created_utc", "digest", "bytes")}])
    return meta


def list_checkpoints(root: pathlib.Path, name: str) -> dict:
    proj = resolve_project_dir(root, name)
    return {"project": proj.name, "checkpoints": _read_checkpoint_index(proj)}


def show_checkpoint(root: pathlib.Path, name: str, cid: str) -> dict:
    proj = resolve_project_dir(root, name)
    return read_checkpoint_meta(proj, cid)


def _snapshot_source(proj: pathlib.Path, cid: str) -> bytes:
    read_checkpoint_meta(proj, cid)  # validates id + integrity
    return (checkpoints_dir(proj) / f"{cid}.pep").read_bytes()


def diff_checkpoints(root: pathlib.Path, name: str, a: str, b: str) -> dict:
    """Unified line diff between two snapshots (or a snapshot and current)."""
    import difflib
    proj = resolve_project_dir(root, name)
    if a == "current":
        store = proj / STORE_FILENAME
        a_bytes = store.read_bytes() if store.exists() else b""
        a_label = "current"
    else:
        a_bytes = _snapshot_source(proj, a)
        a_label = a
    if b == "current":
        store = proj / STORE_FILENAME
        b_bytes = store.read_bytes() if store.exists() else b""
        b_label = "current"
    else:
        b_bytes = _snapshot_source(proj, b)
        b_label = b
    a_text = a_bytes.decode("utf-8", errors="replace").splitlines()
    b_text = b_bytes.decode("utf-8", errors="replace").splitlines()
    diff = "\n".join(difflib.unified_diff(
        a_text, b_text, fromfile=a_label, tofile=b_label, lineterm=""))
    return {"project": proj.name, "a": a_label, "b": b_label,
            "identical": not diff, "diff": diff}


def restore_checkpoint(root: pathlib.Path, name: str, cid: str,
                       apply: bool = False,
                       expect: str | None = None) -> dict:
    """Restore a snapshot to the project's live source (file op only).

    Without ``apply`` this only previews the current-vs-target diff and
    changes nothing. With ``apply`` the live ``definitions.pep`` is
    replaced atomically. ``expect`` refuses when the current digest
    differs (conflict protection). Nothing is ever executed.
    """
    proj = resolve_project_dir(root, name)
    target_bytes = _snapshot_source(proj, cid)
    target_digest = "sha256:" + hashlib.sha256(target_bytes).hexdigest()
    store = proj / STORE_FILENAME
    current_bytes = store.read_bytes() if store.exists() else b""
    current_digest = "sha256:" + hashlib.sha256(current_bytes).hexdigest()
    if current_digest == target_digest:
        return {"project": proj.name, "id": cid, "restored": False,
                "reason": f"already at {target_digest}",
                "current_digest": current_digest, "target_digest": target_digest}
    import difflib
    preview = "\n".join(difflib.unified_diff(
        current_bytes.decode("utf-8", errors="replace").splitlines(),
        target_bytes.decode("utf-8", errors="replace").splitlines(),
        fromfile="current", tofile=cid, lineterm=""))
    if expect is not None and current_digest != expect:
        raise ValueError(
            f"refusing restore: current {current_digest} != expected {expect}")
    if not apply:
        return {"project": proj.name, "id": cid, "restored": False,
                "preview": preview,
                "current_digest": current_digest, "target_digest": target_digest}
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".pep", delete=False, dir=str(proj)) as tmp:
        tmp.write(target_bytes)
        tmp_path = pathlib.Path(tmp.name)
    os.replace(tmp_path, store)
    return {"project": proj.name, "id": cid, "restored": True,
            "preview": preview,
            "current_digest": current_digest, "target_digest": target_digest}


EXPERIMENTS_DIRNAME = "experiments"
EXPERIMENT_ID_RE = re.compile(r"^exp-(\d{3})$")
EXPERIMENT_KINDS = ("check", "inspect", "holes")


def experiments_dir(proj: pathlib.Path) -> pathlib.Path:
    return proj / EXPERIMENTS_DIRNAME


def _compiler_identity() -> dict:
    from pep_lab import cmd_describe
    info = cmd_describe()
    canonical = json.dumps(info, sort_keys=True)
    return {"language": info.get("language"),
            "schemaVersion": info.get("schemaVersion"),
            "digest": "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()}


def _next_experiment_id(proj: pathlib.Path) -> str:
    taken = {p.stem for p in experiments_dir(proj).glob("exp-*.json")
             if p.is_file() and EXPERIMENT_ID_RE.match(p.stem)}
    n = 1
    while f"exp-{n:03d}" in taken:
        n += 1
    return f"exp-{n:03d}"


def _read_experiment(proj: pathlib.Path, eid: str) -> dict:
    if not EXPERIMENT_ID_RE.match(eid or ""):
        raise ValueError(f"bad experiment id {eid!r}: expected exp-NNN")
    exp_file = experiments_dir(proj) / f"{eid}.json"
    try:
        payload = json.loads(exp_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"no such experiment: {eid!r}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"experiment record is corrupt: {exp_file} ({exc})") from exc
    if not isinstance(payload, dict) or payload.get("id") != eid:
        raise ValueError(f"experiment record is corrupt: {exp_file}")
    return payload


def record_experiment(root: pathlib.Path, name: str, kind: str,
                      label: str | None = None, run: bool = False) -> dict:
    """Run one compiler flow against the current source and record it.

    check/inspect/holes never execute code. ``run=True`` additionally
    executes the current source once as an explicitly requested
    observation (stdout/stderr/return code), tagged as observation -- not
    as proof of anything beyond that run.
    """
    if kind not in EXPERIMENT_KINDS:
        raise ValueError(f"bad experiment kind {kind!r}: {', '.join(EXPERIMENT_KINDS)}")
    from pep_lab import cmd_check, cmd_holes, cmd_inspect, cmd_eval
    proj = resolve_project_dir(root, name)
    store = proj / STORE_FILENAME
    source_digest = project_source_digest(proj)
    source_bytes = store.read_bytes() if store.exists() else b""
    runner = {"check": cmd_check, "inspect": cmd_inspect, "holes": cmd_holes}[kind]
    result = runner(store)
    record_result = {"status": result.get("status")}
    if result.get("status") == "invalid":
        record_result["diagnostics"] = result.get("diagnostics", [])
    if result.get("status") == "incomplete":
        record_result["holes"] = [
            {"name": h.get("name", h.get("identity")),
             "expectedType": h.get("expectedType"), "scope": h.get("scope")}
            for h in result.get("holes", [])]
    observation = None
    if run:
        proc = cmd_eval(store)
        observation = {"stdout": proc.stdout, "stderr": proc.stderr,
                       "returncode": proc.returncode}
    eid = _next_experiment_id(proj)
    record = {"schema": WORKSHOP_SCHEMA, "id": eid, "project": proj.name,
              "label": label or "", "kind": kind, "created_utc": _utcnow(),
              "tool": "pep_workshop/1", "source_digest": source_digest,
              "source_bytes": len(source_bytes),
              "compiler": _compiler_identity(),
              "result": record_result, "observation": observation}
    edir = experiments_dir(proj)
    edir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(edir / f"{eid}.json",
                       json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def list_experiments(root: pathlib.Path, name: str) -> dict:
    proj = resolve_project_dir(root, name)
    current_digest = project_source_digest(proj)
    current_compiler = _compiler_identity()["digest"]
    entries = []
    for exp_file in sorted(experiments_dir(proj).glob("exp-*.json")):
        try:
            record = json.loads(exp_file.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            entries.append({"id": exp_file.stem, "status": "corrupt"})
            continue
        entries.append({
            "id": record.get("id"), "kind": record.get("kind"),
            "label": record.get("label", ""),
            "created_utc": record.get("created_utc"),
            "result_status": (record.get("result") or {}).get("status"),
            "observed_run": record.get("observation") is not None,
            "stale": record.get("source_digest") != current_digest,
            "compiler_changed": (record.get("compiler") or {}).get("digest") != current_compiler,
        })
    return {"project": proj.name, "current_digest": current_digest, "experiments": entries}


def show_experiment(root: pathlib.Path, name: str, eid: str) -> dict:
    return _read_experiment(resolve_project_dir(root, name), eid)


def rerun_experiment(root: pathlib.Path, name: str, eid: str) -> dict:
    """Re-run a recorded flow against the CURRENT source; record untouched."""
    from pep_lab import cmd_check, cmd_holes, cmd_inspect
    proj = resolve_project_dir(root, name)
    record = _read_experiment(proj, eid)
    runner = {"check": cmd_check, "inspect": cmd_inspect, "holes": cmd_holes}[record["kind"]]
    current = runner(proj / STORE_FILENAME)
    recorded_status = (record.get("result") or {}).get("status")
    return {"project": proj.name, "id": eid, "kind": record["kind"],
            "recorded_status": recorded_status,
            "recorded_digest": record.get("source_digest"),
            "current_digest": project_source_digest(proj),
            "current_status": current.get("status"),
            "same_status": current.get("status") == recorded_status,
            "stale": record.get("source_digest") != project_source_digest(proj)}


def run_project_repl(root: pathlib.Path, name: str | None) -> int:
    """Open the interactive prompt on a project's store directory."""
    try:
        from pep_lab import run_repl
    except ImportError as exc:
        raise RuntimeError(f"pep_lab.py is required next to pep_workshop.py: {exc}") from exc
    return run_repl(resolve_project_dir(root, name))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pep Lab Persistent Workshop")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="create (or adopt) a project")
    p_create.add_argument("--root", required=True)
    p_create.add_argument("--name", required=True)

    p_list = sub.add_parser("list", help="list projects in a root")
    p_list.add_argument("--root", required=True)

    p_open = sub.add_parser("open", help="open a project and mark it active")
    p_open.add_argument("--root", required=True)
    p_open.add_argument("--name", required=True)

    p_active = sub.add_parser("active", help="show the active project")
    p_active.add_argument("--root", required=True)

    p_dir = sub.add_parser("dir", help="print a project directory (default: active)")
    p_dir.add_argument("--root", required=True)
    p_dir.add_argument("--name", default=None)

    p_repl = sub.add_parser("repl", help="interactive prompt on a project")
    p_repl.add_argument("--root", required=True)
    p_repl.add_argument("--project", default=None)

    p_exp = sub.add_parser("experiment", help="repeatable experiment records")
    exp = p_exp.add_subparsers(dest="exp", required=True)
    e_record = exp.add_parser("record", help="run a flow and record it")
    e_record.add_argument("--root", required=True)
    e_record.add_argument("--project", required=True)
    e_record.add_argument("--kind", required=True,
                          help="check|inspect|holes")
    e_record.add_argument("--label", default=None)
    e_record.add_argument("--run", action="store_true",
                          help="also execute the source once as an observation")
    e_list = exp.add_parser("list", help="list experiments with staleness")
    e_list.add_argument("--root", required=True)
    e_list.add_argument("--project", required=True)
    e_show = exp.add_parser("show", help="show an experiment record")
    e_show.add_argument("--root", required=True)
    e_show.add_argument("--project", required=True)
    e_show.add_argument("--id", required=True)
    e_rerun = exp.add_parser("rerun", help="re-run a flow against current source")
    e_rerun.add_argument("--root", required=True)
    e_rerun.add_argument("--project", required=True)
    e_rerun.add_argument("--id", required=True)

    p_ckpt = sub.add_parser("checkpoint", help="source revisions")
    ckpt = p_ckpt.add_subparsers(dest="ckpt", required=True)
    c_save = ckpt.add_parser("save", help="snapshot current source")
    c_save.add_argument("--root", required=True)
    c_save.add_argument("--project", required=True)
    c_save.add_argument("--label", default=None)
    c_list = ckpt.add_parser("list", help="list checkpoints")
    c_list.add_argument("--root", required=True)
    c_list.add_argument("--project", required=True)
    c_show = ckpt.add_parser("show", help="show checkpoint metadata")
    c_show.add_argument("--root", required=True)
    c_show.add_argument("--project", required=True)
    c_show.add_argument("--id", required=True)
    c_diff = ckpt.add_parser("diff", help="diff two revisions (id or 'current')")
    c_diff.add_argument("--root", required=True)
    c_diff.add_argument("--project", required=True)
    c_diff.add_argument("--a", required=True)
    c_diff.add_argument("--b", required=True)
    c_restore = ckpt.add_parser("restore", help="preview or apply a restore")
    c_restore.add_argument("--root", required=True)
    c_restore.add_argument("--project", required=True)
    c_restore.add_argument("--id", required=True)
    c_restore.add_argument("--apply", action="store_true",
                           help="perform the restore; without it, preview only")
    c_restore.add_argument("--expect", default=None,
                           help="refuse unless current digest matches")

    args = parser.parse_args(argv)
    try:
        root = pathlib.Path(args.root)
        if args.command == "create":
            print(json.dumps(create_project(root, args.name), indent=2))
        elif args.command == "list":
            print(json.dumps(list_projects(root), indent=2))
        elif args.command == "open":
            print(json.dumps(open_project(root, args.name), indent=2))
        elif args.command == "active":
            print(json.dumps({"root": str(root), "active": read_active(root)}, indent=2))
        elif args.command == "dir":
            print(json.dumps({"dir": str(resolve_project_dir(root, args.name))}, indent=2))
        elif args.command == "repl":
            return run_project_repl(root, args.project)
        elif args.command == "experiment":
            if args.exp == "record":
                print(json.dumps(
                    record_experiment(root, args.project, args.kind,
                                      label=args.label, run=args.run), indent=2))
            elif args.exp == "list":
                print(json.dumps(
                    list_experiments(root, args.project), indent=2))
            elif args.exp == "show":
                print(json.dumps(
                    show_experiment(root, args.project, args.id), indent=2))
            elif args.exp == "rerun":
                print(json.dumps(
                    rerun_experiment(root, args.project, args.id), indent=2))
        elif args.command == "checkpoint":
            if args.ckpt == "save":
                print(json.dumps(
                    save_checkpoint(root, args.project, args.label), indent=2))
            elif args.ckpt == "list":
                print(json.dumps(
                    list_checkpoints(root, args.project), indent=2))
            elif args.ckpt == "show":
                print(json.dumps(
                    show_checkpoint(root, args.project, args.id), indent=2))
            elif args.ckpt == "diff":
                print(json.dumps(
                    diff_checkpoints(root, args.project, args.a, args.b), indent=2))
            elif args.ckpt == "restore":
                print(json.dumps(
                    restore_checkpoint(root, args.project, args.id,
                                       apply=args.apply, expect=args.expect), indent=2))
        return 0
    except (RuntimeError, ValueError, FileNotFoundError, OSError,
            UnicodeDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
