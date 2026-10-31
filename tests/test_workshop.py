"""Persistent Workshop W1: project workspace model (no compiler needed)."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def workshop(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "pep_workshop.py"), *map(str, args)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )


class WorkshopProjectTests(unittest.TestCase):
    def test_create_list_open_active_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            created = workshop("create", "--root", root, "--name", "alpha")
            self.assertEqual(created.returncode, 0, created.stderr)
            payload = json.loads(created.stdout)
            self.assertEqual(payload["project"], "alpha")
            self.assertFalse(payload["adopted"])
            meta = json.loads((pathlib.Path(payload["dir"]) / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["schema"], 1)
            self.assertEqual(meta["name"], "alpha")

            listed = workshop("list", "--root", root)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            names = [p["name"] for p in json.loads(listed.stdout)["projects"]]
            self.assertEqual(names, ["alpha"])

            opened = workshop("open", "--root", root, "--name", "alpha")
            self.assertEqual(opened.returncode, 0, opened.stderr)
            self.assertEqual(json.loads(opened.stdout)["active"], "alpha")

            active = workshop("active", "--root", root)
            self.assertEqual(json.loads(active.stdout)["active"], "alpha")

            direct = workshop("dir", "--root", root)
            self.assertEqual(json.loads(direct.stdout)["dir"], payload["dir"])

    def test_two_projects_are_independent_across_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "ws"
            for name in ("one", "two"):
                proc = workshop("create", "--root", str(root), "--name", name)
                self.assertEqual(proc.returncode, 0, proc.stderr)
            (root / "one" / "definitions.pep").write_text(
                "fn answer() -> Int { return 1 }\n", encoding="utf-8")
            (root / "two" / "definitions.pep").write_text(
                "fn answer() -> Int { return 2 }\n", encoding="utf-8")
            # Fresh process per call simulates exiting and reopening Pep Lab.
            workshop("open", "--root", str(root), "--name", "one")
            first = workshop("dir", "--root", str(root))
            self.assertTrue(json.loads(first.stdout)["dir"].endswith("one"))
            workshop("open", "--root", str(root), "--name", "two")
            second = workshop("dir", "--root", str(root))
            self.assertTrue(json.loads(second.stdout)["dir"].endswith("two"))
            body = (pathlib.Path(json.loads(second.stdout)["dir"])
                    / "definitions.pep").read_text(encoding="utf-8")
            self.assertIn("return 2", body)

    def test_legacy_store_adopted_with_contents_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "ws"
            legacy = root / "old"
            legacy.mkdir(parents=True)
            (legacy / "definitions.pep").write_text(
                "fn keep() -> Int { return 7 }\n", encoding="utf-8")
            (legacy / "buffers").mkdir()
            listed = workshop("list", "--root", str(root))
            statuses = {p["name"]: p["status"]
                        for p in json.loads(listed.stdout)["projects"]}
            self.assertEqual(statuses, {"old": "legacy"})
            opened = workshop("open", "--root", str(root), "--name", "old")
            self.assertEqual(opened.returncode, 0, opened.stderr)
            self.assertTrue(json.loads(opened.stdout)["adopted"])
            kept = (legacy / "definitions.pep").read_text(encoding="utf-8")
            self.assertIn("return 7", kept)
            self.assertTrue((legacy / "project.json").exists())
            meta = json.loads((legacy / "project.json").read_text(encoding="utf-8"))
            self.assertTrue(meta["adopted"])

    def test_repl_resolves_active_project_and_switches(self):
        # W1 acceptance: two independent projects, exit, reopen either,
        # find the correct source and working state.
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            for name in ("one", "two"):
                self.assertEqual(
                    workshop("create", "--root", root, "--name", name).returncode, 0)
            (pathlib.Path(root) / "one" / "definitions.pep").write_text(
                "fn alpha() -> Int { return 1 }\n", encoding="utf-8")
            (pathlib.Path(root) / "two" / "definitions.pep").write_text(
                "fn beta() -> Int { return 2 }\n", encoding="utf-8")
            self.assertEqual(
                workshop("open", "--root", root, "--name", "two").returncode, 0)
            resumed = subprocess.run(
                [sys.executable, str(ROOT / "pep_workshop.py"),
                 "repl", "--root", root],
                cwd=ROOT, text=True, capture_output=True, check=False,
                input=":show\n:info\n:quit\n",
            )
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertIn("beta", resumed.stdout)
            self.assertIn("fn beta() -> Int", resumed.stdout)
            self.assertNotIn("alpha", resumed.stdout)
            self.assertEqual(
                workshop("open", "--root", root, "--name", "one").returncode, 0)
            switched = subprocess.run(
                [sys.executable, str(ROOT / "pep_workshop.py"),
                 "repl", "--root", root],
                cwd=ROOT, text=True, capture_output=True, check=False,
                input=":show\n:quit\n",
            )
            self.assertEqual(switched.returncode, 0, switched.stderr)
            self.assertIn("alpha", switched.stdout)
            self.assertNotIn("beta", switched.stdout)

    def test_checkpoint_save_list_show_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            with open(pathlib.Path(root) / "p" / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write("fn v() -> Int { return 1 }\n")
            saved = workshop("checkpoint", "save", "--root", root,
                             "--project", "p", "--label", "first")
            self.assertEqual(saved.returncode, 0, saved.stderr)
            meta = json.loads(saved.stdout)
            self.assertEqual(meta["id"], "cp-001")
            self.assertEqual(meta["label"], "first")
            self.assertEqual(meta["revision_kind"], "workshop-file-sha256")
            snap = (pathlib.Path(root) / "p" / "checkpoints" / "cp-001.pep").read_bytes()
            self.assertEqual(snap, b"fn v() -> Int { return 1 }\n")
            import hashlib as _hl
            self.assertEqual(meta["digest"], "sha256:" + _hl.sha256(snap).hexdigest())
            second = workshop("checkpoint", "save", "--root", root, "--project", "p")
            self.assertEqual(json.loads(second.stdout)["id"], "cp-002")
            listed = workshop("checkpoint", "list", "--root", root, "--project", "p")
            ids = [c["id"] for c in json.loads(listed.stdout)["checkpoints"]]
            self.assertEqual(ids, ["cp-001", "cp-002"])
            shown = workshop("checkpoint", "show", "--root", root,
                             "--project", "p", "--id", "cp-001")
            self.assertEqual(json.loads(shown.stdout)["label"], "first")

    def test_checkpoint_empty_project_and_bad_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "e").returncode, 0)
            saved = workshop("checkpoint", "save", "--root", root, "--project", "e")
            meta = json.loads(saved.stdout)
            self.assertEqual(meta["bytes"], 0)
            self.assertTrue(meta["digest"].startswith("sha256:"))
            bad = workshop("checkpoint", "show", "--root", root,
                           "--project", "e", "--id", "cp-999")
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("error", bad.stderr)
            evil = workshop("checkpoint", "show", "--root", root,
                            "--project", "e", "--id", "../active")
            self.assertNotEqual(evil.returncode, 0)
            unknown = workshop("checkpoint", "save", "--root", root,
                               "--project", "ghost")
            self.assertNotEqual(unknown.returncode, 0)
            self.assertIn("error", unknown.stderr)

    def test_checkpoint_index_rebuilt_when_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            (pathlib.Path(root) / "p" / "definitions.pep").write_text(
                "fn v() -> Int { return 1 }\n", encoding="utf-8")
            self.assertEqual(
                workshop("checkpoint", "save", "--root", root,
                         "--project", "p", "--label", "a").returncode, 0)
            (pathlib.Path(root) / "p" / "checkpoints" / "index.json").write_bytes(b"{x")
            listed = workshop("checkpoint", "list", "--root", root, "--project", "p")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            entries = json.loads(listed.stdout)["checkpoints"]
            self.assertEqual([e["id"] for e in entries], ["cp-001"])
            self.assertEqual(entries[0]["label"], "a")

    def test_bad_names_and_missing_projects_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            for bad in ("../evil", "", "active.json", "a/b", "x" * 65):
                proc = workshop("create", "--root", root, "--name", bad)
                self.assertNotEqual(proc.returncode, 0, bad)
                self.assertIn("error", proc.stderr)
            missing = workshop("open", "--root", root, "--name", "ghost")
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("error", missing.stderr)
            dup = workshop("create", "--root", root, "--name", "dup")
            self.assertEqual(dup.returncode, 0, dup.stderr)
            again = workshop("create", "--root", root, "--name", "dup")
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("already exists", again.stderr)

    def test_corrupt_metadata_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "ws"
            self.assertEqual(
                workshop("create", "--root", str(root), "--name", "p").returncode, 0)
            (root / "p" / "project.json").write_bytes(b"{nope")
            listed = workshop("list", "--root", str(root))
            statuses = {p["name"]: p["status"]
                        for p in json.loads(listed.stdout)["projects"]}
            self.assertEqual(statuses["p"], "corrupt")
            opened = workshop("open", "--root", str(root), "--name", "p")
            self.assertNotEqual(opened.returncode, 0)
            self.assertIn("error", opened.stderr)
            (root / "active.json").write_bytes(b"\xff\xfe")
            active = workshop("active", "--root", str(root))
            self.assertNotEqual(active.returncode, 0)
            self.assertIn("error", active.stderr)

    def test_active_pointer_absent_initially(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            active = workshop("active", "--root", root)
            self.assertEqual(active.returncode, 0, active.stderr)
            self.assertIsNone(json.loads(active.stdout)["active"])
            listed = workshop("list", "--root", root)
            self.assertEqual(json.loads(listed.stdout)["projects"], [])


if __name__ == "__main__":
    unittest.main()
