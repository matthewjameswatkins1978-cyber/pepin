import unittest

from tests.test_a13 import fields, scalar


class A13NestedRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_a13 import A13FunctionResolutionTests
        cls.harness_type = A13FunctionResolutionTests
        cls.harness_type.setUpClass()

    def setUp(self):
        self.harness = self.harness_type("test_empty_program_is_consumed_through_the_owned_parser_chain")
        self.harness.setUp()

    def tearDown(self):
        self.harness.tearDown()

    def _assert_matches_reference(self, name, source):
        reference = self.harness._reference_check("nested-record-" + name, source)
        _, report = self.harness._analyze(source)
        actual_status = scalar(report["status"])
        self.assertEqual(actual_status, reference["status"], report)
        expected = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        actual = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        self.assertEqual(actual, expected)
        return report

    def test_union_payload_can_hold_a_named_record(self):
        source = (
            "type Inner { value: Int }\n"
            "type Outcome = Success(Inner) | Failure()\n"
            "fn success() -> Outcome { return Success(Inner { value: 42 }) }"
        )
        report = self._assert_matches_reference("union-payload", source)
        self.assertEqual(scalar(report["status"]), "valid")

    def test_nested_record_fields_construction_and_mismatch_match_ocaml(self):
        valid_read = (
            "type Inner { value: Int }\n"
            "type Outer { inner: Inner }\n"
            "fn read(outer: Outer) -> Int { return outer.inner.value }"
        )
        read_report = self._assert_matches_reference("valid-read", valid_read)
        self.assertEqual(scalar(read_report["status"]), "valid")
        read_types = [scalar(fields(item)["typeName"]) for item in read_report["expressionTypes"]["value"]]
        self.assertIn("Inner", read_types)
        self.assertIn("Int", read_types)

        valid_build = (
            "type Inner { value: Int }\n"
            "type Outer { inner: Inner }\n"
            "fn build() -> Outer { return Outer { inner: Inner { value: 42 } } }"
        )
        build_report = self._assert_matches_reference("valid-build", valid_build)
        self.assertEqual(scalar(build_report["status"]), "valid")
        build_types = [scalar(fields(item)["typeName"]) for item in build_report["expressionTypes"]["value"]]
        self.assertIn("Inner", build_types)
        self.assertIn("Outer", build_types)
        self.assertIn("Int", build_types)

        invalid = (
            "type Inner { value: Int }\n"
            "type Outer { inner: Inner }\n"
            "fn build() -> Outer { return Outer { inner: Inner { value: true } } }"
        )
        report = self._assert_matches_reference("invalid", invalid)
        self.assertEqual(scalar(report["status"]), "invalid")
        self.assertIn("PEP_TYPE_MISMATCH", [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]])


if __name__ == "__main__":
    unittest.main()
