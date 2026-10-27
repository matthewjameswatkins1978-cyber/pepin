from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artifact_lab import FixtureError, canonical_manifest_bytes, load_manifest, render_c, validate_generated_source, validate_manifest


ROOT = Path(__file__).parent
FIXTURES = sorted((ROOT / "fixtures").glob("*.json"))


class ArtifactLabTests(unittest.TestCase):
    def test_all_fixtures_validate(self):
        self.assertEqual(len(FIXTURES), 8)
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
        reordered = copy.deepcopy(manifest)
        reordered["functions"].reverse()
        self.assertEqual(first, render_c(reordered))
        self.assertNotIn(str(ROOT), first)
        self.assertNotIn("2026-", first)
        self.assertIn("pep_a05_fn_", first)

    def test_generation_writes_lf_and_stable_bytes(self):
        manifest = json.loads((ROOT / "fixtures" / "primitive_add.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "artifact.c"
            other = Path(directory) / "other" / "artifact.c"
            from artifact_lab import generate
            receipt = generate(ROOT / "fixtures" / "primitive_add.json", output)
            generate(ROOT / "fixtures" / "primitive_add.json", other)
            self.assertEqual(output.read_bytes(), render_c(manifest).encode())
            self.assertEqual(output.read_bytes(), other.read_bytes())
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
        unsupported_tag["functions"][0]["result"]["kind"] = "while"
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

        record = json.loads((ROOT / "fixtures" / "record_field.json").read_text())
        del record["functions"][0]["result"]["left"]["target"]["fields"]["field.point.y"]
        with self.assertRaises(FixtureError) as raised:
            validate_manifest(record)
        self.assertEqual(raised.exception.code, "incorrect_field_count")
        string = json.loads((ROOT / "fixtures" / "string_bytes.json").read_text())
        string["functions"][0]["result"]["bytes"] = [0xC0, 0x80]
        with self.assertRaises(FixtureError) as raised:
            validate_manifest(string)
        self.assertEqual(raised.exception.code, "invalid_utf8_literal")
        union = copy.deepcopy(original)
        union["types"] = [{"id": "type.expr", "kind": "union", "constructors": [{"id": "ctor.number", "name": "Number", "fields": []}]}]
        union["functions"][0]["return_type"] = "type.expr"
        union["functions"][0]["result"] = {"node_id": "node.constructor", "kind": "constructor", "constructor_id": "ctor.missing", "type": "type.expr", "span": {"start": 0, "end": 1}, "fields": {}}
        union["supported_features"] = ["constructors"]
        with self.assertRaises(FixtureError) as raised:
            validate_manifest(union)
        self.assertEqual(raised.exception.code, "unknown_constructor_identity")
        incomplete_match = copy.deepcopy(original)
        incomplete_match["functions"][0]["result"] = {"node_id": "node.match", "kind": "match", "type": "Int", "span": {"start": 0, "end": 1}, "arms": []}
        incomplete_match["supported_features"] = ["pattern_matching"]
        with self.assertRaises(FixtureError) as raised:
            validate_manifest(incomplete_match)
        self.assertEqual(raised.exception.code, "incomplete_match_information")

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

    def test_generated_output_mutation_is_rejected_by_independent_invariants(self):
        manifest = json.loads((ROOT / "fixtures" / "list_sum.json").read_text())
        source = render_c(manifest)
        validate_generated_source(source, manifest)
        with self.assertRaises(FixtureError) as raised:
            validate_generated_source(source.replace("pep_list_dispose", "pep_omitted"), manifest)
        self.assertEqual(raised.exception.code, "missing_cleanup")


if __name__ == "__main__":
    unittest.main()
