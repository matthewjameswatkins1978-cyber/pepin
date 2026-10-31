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

    def test_checkpoint_diff_restore_with_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            proj = pathlib.Path(root) / "p"
            with open(proj / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write("fn v() -> Int { return 1 }\n")
            self.assertEqual(
                workshop("checkpoint", "save", "--root", root,
                         "--project", "p", "--label", "v1").returncode, 0)
            with open(proj / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write("fn v() -> Int { return 2 }\n")
            self.assertEqual(
                workshop("checkpoint", "save", "--root", root,
                         "--project", "p", "--label", "v2").returncode, 0)
            diffed = workshop("checkpoint", "diff", "--root", root,
                              "--project", "p", "--a", "cp-001", "--b", "cp-002")
            self.assertEqual(diffed.returncode, 0, diffed.stderr)
            payload = json.loads(diffed.stdout)
            self.assertFalse(payload["identical"])
            self.assertIn("-fn v() -> Int { return 1 }", payload["diff"])
            self.assertIn("+fn v() -> Int { return 2 }", payload["diff"])
            # Preview changes nothing.
            preview = workshop("checkpoint", "restore", "--root", root,
                               "--project", "p", "--id", "cp-001")
            self.assertEqual(preview.returncode, 0, preview.stderr)
            pre = json.loads(preview.stdout)
            self.assertFalse(pre["restored"])
            self.assertIn("+fn v() -> Int { return 1 }", pre["preview"])
            self.assertIn("return 2", proj.joinpath("definitions.pep").read_text(encoding="utf-8"))
            # Wrong expectation refuses even with --apply.
            refused = workshop("checkpoint", "restore", "--root", root,
                               "--project", "p", "--id", "cp-001",
                               "--apply", "--expect", "sha256:dead")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("refusing restore", refused.stderr)
            # Apply restores exact bytes; second restore is a no-op.
            applied = workshop("checkpoint", "restore", "--root", root,
                               "--project", "p", "--id", "cp-001", "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertTrue(json.loads(applied.stdout)["restored"])
            self.assertEqual(
                (proj / "definitions.pep").read_bytes(),
                b"fn v() -> Int { return 1 }\n")
            again = workshop("checkpoint", "restore", "--root", root,
                             "--project", "p", "--id", "cp-001", "--apply")
            self.assertIn("already at", json.loads(again.stdout)["reason"])

    def test_experiment_record_list_rerun_with_staleness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            proj = pathlib.Path(root) / "p"
            with open(proj / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write("fn v() -> Int { return 1 }\n")
            recorded = workshop("experiment", "record", "--root", root,
                                "--project", "p", "--kind", "check",
                                "--label", "baseline")
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            rec = json.loads(recorded.stdout)
            self.assertEqual(rec["id"], "exp-001")
            self.assertEqual(rec["result"]["status"], "valid")
            self.assertIsNone(rec["observation"])
            self.assertTrue(rec["source_digest"].startswith("sha256:"))
            listed = workshop("experiment", "list", "--root", root, "--project", "p")
            entries = json.loads(listed.stdout)["experiments"]
            self.assertEqual(len(entries), 1)
            self.assertFalse(entries[0]["stale"])
            self.assertFalse(entries[0]["compiler_changed"])
            self.assertFalse(entries[0]["observed_run"])
            # Change the source: the record goes stale but stays readable.
            with open(proj / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write("fn v() -> Int { return 2 }\n")
            stale = workshop("experiment", "list", "--root", root, "--project", "p")
            self.assertTrue(json.loads(stale.stdout)["experiments"][0]["stale"])
            rerun = workshop("experiment", "rerun", "--root", root,
                             "--project", "p", "--id", "exp-001")
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            rr = json.loads(rerun.stdout)
            self.assertTrue(rr["same_status"])
            self.assertTrue(rr["stale"])
            # The record itself is untouched by rerun: digest still pins v1.
            shown = workshop("experiment", "show", "--root", root,
                             "--project", "p", "--id", "exp-001")
            rec2 = json.loads(shown.stdout)
            self.assertEqual(rec2["result"]["status"], "valid")
            import hashlib as _hl2
            self.assertEqual(
                rec2["source_digest"],
                "sha256:" + _hl2.sha256(b"fn v() -> Int { return 1 }\n").hexdigest())

    def test_experiment_run_observation_is_explicit_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            proj = pathlib.Path(root) / "p"
            with open(proj / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write('say("hi")\n')
            recorded = workshop("experiment", "record", "--root", root,
                                "--project", "p", "--kind", "check", "--run")
            rec = json.loads(recorded.stdout)
            self.assertIsNotNone(rec["observation"])
            self.assertEqual(rec["observation"]["returncode"], 0)
            self.assertEqual(rec["observation"]["stdout"], "hi\n")
            listed = workshop("experiment", "list", "--root", root, "--project", "p")
            self.assertTrue(json.loads(listed.stdout)["experiments"][0]["observed_run"])

    def test_experiment_bad_kind_and_unknown_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            bad = workshop("experiment", "record", "--root", root,
                           "--project", "p", "--kind", "prove")
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("error", bad.stderr)
            missing = workshop("experiment", "show", "--root", root,
                               "--project", "p", "--id", "exp-009")
            self.assertNotEqual(missing.returncode, 0)

    def test_inspect_reports_revision_pinned_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            proj = pathlib.Path(root) / "p"
            with open(proj / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write("fn v() -> Int { return 1 }\n")
            self.assertEqual(
                workshop("checkpoint", "save", "--root", root,
                         "--project", "p", "--label", "v1").returncode, 0)
            with open(proj / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write('fn v() -> Int { return "bad" }\n')
            current = workshop("inspect", "--root", root, "--project", "p")
            self.assertEqual(current.returncode, 0, current.stderr)
            cur = json.loads(current.stdout)
            self.assertEqual(cur["status"], "invalid")
            self.assertEqual(cur["revision"]["kind"], "current")
            self.assertTrue(any(d["code"] == "PEP_TYPE_MISMATCH"
                                for d in cur["diagnostics"]))
            self.assertEqual(cur["functions"], [])
            # The checkpoint revision still reports the OLD facts.
            old = workshop("inspect", "--root", root, "--project", "p",
                           "--revision", "cp-001")
            self.assertEqual(old.returncode, 0, old.stderr)
            pinned = json.loads(old.stdout)
            self.assertEqual(pinned["status"], "valid")
            self.assertEqual(pinned["revision"]["kind"], "checkpoint")
            self.assertEqual(
                pinned["functions"],
                [{"name": "v", "parameters": [], "returns": "Int"}])
            self.assertNotEqual(pinned["revision"]["digest"],
                                cur["revision"]["digest"])

    def test_inspect_holes_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            proj = pathlib.Path(root) / "p"
            with open(proj / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write("fn h(n: Int) -> Int { return ?calc }\n")
            holed = workshop("inspect", "--root", root, "--project", "p")
            holes = json.loads(holed.stdout)["holes"]
            self.assertEqual(len(holes), 1)
            self.assertEqual(holes[0]["name"], "calc")
            self.assertEqual(holes[0]["expectedType"], "Int")
            self.assertIn("n", holes[0]["suggestions"])
            self.assertEqual(
                workshop("checkpoint", "save", "--root", root,
                         "--project", "p").returncode, 0)
            with open(proj / "checkpoints" / "cp-001.pep", "wb") as fh:
                fh.write(b"tampered")
            tampered = workshop("inspect", "--root", root, "--project", "p",
                                "--revision", "cp-001")
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("integrity", tampered.stderr)
            badrev = workshop("inspect", "--root", root, "--project", "p",
                              "--revision", "nope")
            self.assertNotEqual(badrev.returncode, 0)

    def _write_example_source(self, root, project, example):
        src = ROOT / "examples" / example
        data = src.read_bytes()
        (pathlib.Path(root) / project / "definitions.pep").write_bytes(data)
        return data

    def test_workshop_project_full_workflow(self):
        # W5 acceptance: create, develop, check, execute, checkpoint,
        # modify, restore, export -- across processes.
        lab = lambda *a: subprocess.run(
            [sys.executable, str(ROOT / "pep_lab.py"), *map(str, a)],
            cwd=ROOT, text=True, capture_output=True, check=False)
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "shapes").returncode, 0)
            original = self._write_example_source(root, "shapes", "workshop_shapes.pep")
            saved = workshop("checkpoint", "save", "--root", root,
                             "--project", "shapes", "--label", "v1")
            self.assertEqual(saved.returncode, 0, saved.stderr)
            inspected = workshop("inspect", "--root", root, "--project", "shapes")
            facts = json.loads(inspected.stdout)
            self.assertEqual(facts["status"], "valid")
            self.assertEqual(
                sorted(f["name"] for f in facts["functions"]),
                ["area", "count_circles", "is_circle", "perimeter", "total_area"])
            recorded = workshop("experiment", "record", "--root", root,
                                "--project", "shapes", "--kind", "check")
            self.assertEqual(json.loads(recorded.stdout)["result"]["status"], "valid")
            # Modify: Circle(2) -> Circle(5); diff must show it.
            broken = original.replace(b"Circle(2)", b"Circle(5)")
            self.assertNotEqual(broken, original)
            (pathlib.Path(root) / "shapes" / "definitions.pep").write_bytes(broken)
            diffed = workshop("checkpoint", "diff", "--root", root,
                              "--project", "shapes", "--a", "cp-001", "--b", "current")
            self.assertIn("Circle(5)", json.loads(diffed.stdout)["diff"])
            # Restore, re-check, export the portable program, run it.
            restored = workshop("checkpoint", "restore", "--root", root,
                                "--project", "shapes", "--id", "cp-001", "--apply")
            self.assertTrue(json.loads(restored.stdout)["restored"])
            self.assertEqual(
                (pathlib.Path(root) / "shapes" / "definitions.pep").read_bytes(),
                original)
            exported_path = pathlib.Path(tmp) / "shapes_final.pep"
            exported = lab("export", "--store", str(pathlib.Path(root) / "shapes"),
                           "--output", str(exported_path))
            self.assertEqual(exported.returncode, 0, exported.stderr)
            ran = lab("eval", str(exported_path))
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(
                ran.stdout,
                "areas:\n12\n12\n9\nperimeters:\n12\n14\ncircles:\n2\n"
                "gallery area:\n36\n")
            # Second project: ledger, shorter pass with an observed run.
            self.assertEqual(
                workshop("create", "--root", root, "--name", "ledger").returncode, 0)
            self._write_example_source(root, "ledger", "workshop_ledger.pep")
            self.assertEqual(
                workshop("checkpoint", "save", "--root", root,
                         "--project", "ledger").returncode, 0)
            led = workshop("inspect", "--root", root, "--project", "ledger")
            self.assertEqual(json.loads(led.stdout)["status"], "valid")
            rec = workshop("experiment", "record", "--root", root,
                           "--project", "ledger", "--kind", "check", "--run",
                           "--label", "ledger-run")
            obs = json.loads(rec.stdout)["observation"]
            self.assertEqual(obs["returncode"], 0)
            self.assertEqual(obs["stdout"], "total:\n62\nlargest:\n40\nover 10:\n2\n")

    def test_workshop_repl_project_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "p").returncode, 0)
            script = ("fn v() -> Int { return 1 }\n"
                      ":def\n"
                      ":project\n"
                      ":checkpoint save v1\n"
                      ":checkpoint list\n"
                      "fn w() -> Int { return 2 }\n"
                      ":def\n"
                      ":checkpoint save v2\n"
                      ":restore cp-001\n"
                      ":restore cp-001 apply\n"
                      ":show\n"
                      ":restore nope\n"
                      ":quit\n")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "pep_workshop.py"),
                 "repl", "--root", root, "--project", "p"],
                cwd=ROOT, text=True, capture_output=True, check=False,
                input=script,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("workshop project p", proc.stdout)
            self.assertIn("project p", proc.stdout)
            self.assertIn("checkpoint cp-001", proc.stdout)
            self.assertIn("cp-001", proc.stdout)
            self.assertIn("cp-002", proc.stdout)
            self.assertIn("preview cp-001 (not applied):", proc.stdout)
            self.assertIn("-fn w() -> Int { return 2 }", proc.stdout)
            self.assertIn("restored cp-001", proc.stdout)
            self.assertIn("definitions: v", proc.stdout)
            self.assertNotIn("definitions: v, w", proc.stdout)
            self.assertIn("not restored:", proc.stdout)

    def test_no_temp_litter_after_operations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "ws"
            sroot = str(root)
            self.assertEqual(
                workshop("create", "--root", sroot, "--name", "p").returncode, 0)
            with open(root / "p" / "definitions.pep", "w",
                       encoding="utf-8", newline="\n") as fh:
                fh.write("fn v() -> Int { return 1 }\n")
            self.assertEqual(
                workshop("checkpoint", "save", "--root", sroot,
                         "--project", "p").returncode, 0)
            self.assertEqual(
                workshop("experiment", "record", "--root", sroot,
                         "--project", "p", "--kind", "check").returncode, 0)
            self.assertEqual(
                workshop("checkpoint", "restore", "--root", sroot,
                         "--project", "p", "--id", "cp-001",
                         "--apply").returncode, 0)
            self.assertEqual(
                workshop("open", "--root", sroot, "--name", "ghost").returncode, 2)
            litter = [p for p in root.rglob("*")
                      if p.is_file() and (p.suffix == ".tmp" or p.name.startswith("tmp"))]
            self.assertEqual(litter, [])

    def test_root_is_a_file_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            rootfile = str(pathlib.Path(tmp) / "notadir")
            pathlib.Path(rootfile).write_text("x", encoding="utf-8")
            for argv in (["create", "--name", "p"], ["list"],
                          ["open", "--name", "p"], ["active"],
                          ["dir"],
                          ["checkpoint", "save", "--project", "p"],
                          ["checkpoint", "list", "--project", "p"],
                          ["experiment", "record", "--project", "p", "--kind", "check"],
                          ["experiment", "list", "--project", "p"],
                          ["inspect", "--project", "p"]):
                proc = workshop(*argv, "--root", rootfile)
                self.assertNotEqual(proc.returncode, 0, argv)
                self.assertIn("error", proc.stderr, argv)

    def test_experiment_record_on_empty_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(pathlib.Path(tmp) / "ws")
            self.assertEqual(
                workshop("create", "--root", root, "--name", "e").returncode, 0)
            rec = workshop("experiment", "record", "--root", root,
                           "--project", "e", "--kind", "check")
            self.assertNotEqual(rec.returncode, 0)
            self.assertIn("error", rec.stderr)

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
