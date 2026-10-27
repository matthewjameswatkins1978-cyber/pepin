from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artifact_lab import FixtureError, canonical_manifest_bytes, load_manifest, render_c, validate_manifest


ROOT = Path(__file__).parent
FIXTURES = sorted((ROOT / "fixtures").glob("*.json"))


class ArtifactLabTests(unittest.TestCase):
    def test_all_fixtures_validate(self):
        self.assertEqual(len(FIXTURES), 5)
        for path in FIXTURES:
            with self.subTest(path=path.name):
                self.assertTrue(load_manifest(path)["fixture_id"])

    def test_canonical_bytes_ignore_object_order(self):
        manifest = json.loads((ROOT / "fixtures" / "function_call.json").read_text())
        reordered = {key: manifest[key] for key in reversed(list(manifest))}
        self.assertEqual(canonical_manifest_bytes(manifest), canonical_manifest_bytes(reordered))

    def test_render_is_deterministic_and_path_free(self):
        manifest = json.loads((ROOT / "fixtures" / "function_call.json").read_text())
        first = render_c(manifest)
        second = render_c(copy.deepcopy(manifest))
        self.assertEqual(first, second)
        self.assertNotIn(str(ROOT), first)
        self.assertNotIn("2026-", first)
        self.assertIn("pep_a05_fn_", first)

    def test_generation_writes_lf_and_stable_bytes(self):
        manifest = json.loads((ROOT / "fixtures" / "primitive_add.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "artifact.c"
            from artifact_lab import generate
            receipt = generate(ROOT / "fixtures" / "primitive_add.json", output)
            self.assertEqual(output.read_bytes(), render_c(manifest).encode())
            self.assertEqual(receipt["bytes"], output.stat().st_size)
            self.assertNotIn(b"\r\n", output.read_bytes())

    def test_invalid_manifests_fail_closed(self):
        original = json.loads((ROOT / "fixtures" / "primitive_add.json").read_text())
        cases = []
        missing_type = copy.deepcopy(original)
        del missing_type["functions"][0]["result"]["type"]
        cases.append((missing_type, "missing_expression_fact"))
        unknown_binding = copy.deepcopy(original)
        unknown_binding["functions"][0]["result"]["left"]["kind"] = "param_ref"
        unknown_binding["functions"][0]["result"]["left"]["binding_id"] = "binding.missing"
        cases.append((unknown_binding, "unknown_binding_identity"))
        unsupported_tag = copy.deepcopy(original)
        unsupported_tag["functions"][0]["result"]["kind"] = "match"
        cases.append((unsupported_tag, "unsupported_expression_tag"))
        duplicate_node = copy.deepcopy(original)
        duplicate_node["functions"][0]["result"]["right"]["node_id"] = "node.left"
        cases.append((duplicate_node, "duplicate_checked_node_id"))
        missing_ownership = copy.deepcopy(original)
        del missing_ownership["ownership"]
        cases.append((missing_ownership, "manifest_keys"))
        bad_schema = copy.deepcopy(original)
        bad_schema["schema_version"] = 99
        cases.append((bad_schema, "unsupported_fixture_schema"))
        bad_revision = copy.deepcopy(original)
        with self.assertRaises(FixtureError) as raised:
            validate_manifest(bad_revision, "sha256:different")
        self.assertEqual(raised.exception.code, "source_revision_conflict")
        for manifest, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(FixtureError) as raised:
                    validate_manifest(manifest)
                self.assertEqual(raised.exception.code, code)

    def test_invalid_manifest_does_not_create_output(self):
        manifest = json.loads((ROOT / "fixtures" / "primitive_add.json").read_text())
        del manifest["ownership"]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "artifact.c"
            with self.assertRaises(FixtureError):
                from artifact_lab import generate
                bad_path = Path(directory) / "bad.json"
                bad_path.write_text(json.dumps(manifest), encoding="utf-8")
                generate(bad_path, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
