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

    def test_nested_primitive_lists_match_ocaml(self):
        valid = "fn values() -> List[List[Int]] { return [[1, 2], [3]] }"
        report = self._assert_matches_reference("nested-list", valid)
        self.assertEqual(scalar(report["status"]), "valid")
        types = [scalar(fields(item)["typeName"]) for item in report["expressionTypes"]["value"]]
        self.assertIn("List[Int]", types)
        self.assertIn("List[List[Int]]", types)

        invalid = "fn values() -> List[List[Int]] { return [[1], [true]] }"
        report = self._assert_matches_reference("nested-list-mismatch", invalid)
        self.assertEqual(scalar(report["status"]), "invalid")
        self.assertIn("PEP_TYPE_MISMATCH", [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]])

        for name, source in (
            ("nested-all-mismatch", "fn values() -> List[List[Int]] { return [[true, false]] }"),
            ("nested-first-mismatch", "fn values() -> List[List[Int]] { return [[true, 1]] }"),
            ("nested-append-mismatch", "fn add() -> List[List[Int]] { return append([[1]], [true, false]) }"),
        ):
            with self.subTest(name=name):
                report = self._assert_matches_reference(name, source)
                self.assertEqual(scalar(report["status"]), "invalid")
                self.assertIn("PEP_TYPE_MISMATCH", [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]])

        unsupported_contains = "fn has() -> Bool { return contains([[1]], [1]) }"
        report = self._assert_matches_reference("nested-list-contains", unsupported_contains)
        self.assertEqual(scalar(report["status"]), "invalid")

    def test_structural_type_shapes_accept_nested_nominal_declarations(self):
        source = (
            "type Point { x: Int }\n"
            "type Box { points: List[Point] }\n"
            "fn identity(points: List[Point]) -> List[Point] { return points }"
        )
        report = self._assert_matches_reference("structural-nominal-list-shapes", source)
        self.assertEqual(scalar(report["status"]), "valid")
        function = fields(report["functions"]["value"][0])
        returned = fields(function["returnShape"])
        self.assertEqual((scalar(returned["kind"]), scalar(returned["name"]), scalar(returned["listDepth"])), ("nominal", "Point", 1))
        parameter = next(fields(item) for item in report["bindings"]["value"] if scalar(fields(item)["name"]) == "points")
        shape = fields(parameter["typeShape"])
        self.assertEqual((scalar(shape["kind"]), scalar(shape["name"]), scalar(shape["listDepth"])), ("nominal", "Point", 1))
        expression_shapes = [fields(item)["typeShape"] for item in report["expressionTypes"]["value"] if scalar(fields(item)["typeShape"]["fields"][0]["value"]) == "nominal"]
        self.assertTrue(any(scalar(fields(item)["name"]) == "Point" and scalar(fields(item)["listDepth"]) == 1 for item in expression_shapes))

    def test_if_expression_preserves_nominal_list_shapes_and_rejects_mismatch(self):
        valid = (
            "type Point { x: Int }\n"
            "fn choose(flag: Bool, left: List[Point], right: List[Point]) -> List[Point] { "
            "return if flag { left } else { right } }"
        )
        report = self._assert_matches_reference("if-expression-nominal-list-shape", valid)
        self.assertEqual(scalar(report["status"]), "valid")
        self.assertTrue(any(
            scalar(fields(fields(item)["typeShape"])["kind"]) == "nominal"
            and scalar(fields(fields(item)["typeShape"])["name"]) == "Point"
            and scalar(fields(fields(item)["typeShape"])["listDepth"]) == 1
            for item in report["expressionTypes"]["value"]
        ))

        invalid = (
            "type Point { x: Int }\n"
            "fn choose(flag: Bool, left: List[Point], right: Point) -> List[Point] { "
            "return if flag { left } else { right } }"
        )
        report = self._assert_matches_reference("if-expression-nominal-list-mismatch", invalid)
        self.assertEqual(scalar(report["status"]), "invalid")

    def test_unknown_nominal_leaf_in_nested_list_matches_reference_diagnostic(self):
        source = "fn accept(values: List[List[Missing]]) -> Unit {}"
        report = self._assert_matches_reference("unknown-nested-list-leaf", source)
        self.assertEqual(scalar(report["status"]), "invalid")
        self.assertIn("PEP_UNKNOWN_TYPE", [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]])

    def test_deep_builtin_list_declaration_stays_within_runtime_budget(self):
        nested = "List[" * 16 + "Int" + "]" * 16
        source = "fn accept(values: " + nested + ") -> Unit {}"
        report = self._assert_matches_reference("deep-nominal-list", source)
        self.assertEqual(scalar(report["status"]), "valid")
        parameter = next(fields(item) for item in report["bindings"]["value"] if scalar(fields(item)["name"]) == "values")
        shape = fields(parameter["typeShape"])
        self.assertEqual((scalar(shape["name"]), scalar(shape["listDepth"])), ("Int", 16))

    def test_triple_nested_lists_round_trip_through_structural_shapes(self):
        source = (
            "fn values() -> List[List[List[Int]]] { "
            "return [[[1]], [[2, 3]]] }"
        )
        report = self._assert_matches_reference("triple-nested-list", source)
        self.assertEqual(scalar(report["status"]), "valid")
        expression_types = report["expressionTypes"]["value"]
        self.assertTrue(any(
            scalar(fields(fields(item)["typeShape"])["kind"]) == "builtin"
            and scalar(fields(fields(item)["typeShape"])["name"]) == "Int"
            and scalar(fields(fields(item)["typeShape"])["listDepth"]) == 3
            for item in expression_types
        ))

        mismatch = (
            "fn values() -> List[List[List[Int]]] { "
            "return [[[true]]] }"
        )
        mismatch_report = self._assert_matches_reference("triple-nested-list-mismatch", mismatch)
        self.assertEqual(scalar(mismatch_report["status"]), "invalid")

        nominal_mismatch = (
            "type Point { x: Int }\n"
            "fn wrong(value: List[List[List[Point]]]) "
            "-> List[List[List[Int]]] { return value }"
        )
        nominal_report = self._assert_matches_reference("triple-nested-nominal-mismatch", nominal_mismatch)
        self.assertEqual(scalar(nominal_report["status"]), "invalid")

        nested_append = (
            "fn add(values: List[List[List[Int]]], item: List[List[Int]]) "
            "-> List[List[List[Int]]] { return append(values, item) }"
        )
        append_report = self._assert_matches_reference("triple-nested-append", nested_append)
        self.assertEqual(scalar(append_report["status"]), "valid")

        nested_append_mismatch = (
            "fn add(values: List[List[List[Int]]], item: List[List[Bool]]) "
            "-> List[List[List[Int]]] { return append(values, item) }"
        )
        append_mismatch_report = self._assert_matches_reference(
            "triple-nested-append-mismatch", nested_append_mismatch
        )
        self.assertEqual(scalar(append_mismatch_report["status"]), "invalid")

    def test_structural_list_types_flow_through_calls_returns_and_inferred_bindings(self):
        cases = (
            (
                "nominal-list-call-mismatch",
                "type P { x: Int }\ntype Q { x: Int }\n"
                "fn take(values: List[P]) -> Unit {}\n"
                "fn main(values: List[Q]) -> Unit { take(values) }",
                "invalid",
            ),
            (
                "nominal-list-return-mismatch",
                "type P { x: Int }\ntype Q { x: Int }\n"
                "fn wrong(value: List[Q]) -> List[P] { return value }",
                "invalid",
            ),
            (
                "mixed-representation-call-mismatch",
                "type P { x: Int }\n"
                "fn take(values: List[Int]) -> Unit {}\n"
                "fn main(values: List[P]) -> Unit { take(values) }",
                "invalid",
            ),
            (
                "mixed-representation-return-mismatch",
                "type P { x: Int }\n"
                "fn wrong(value: List[P]) -> List[Int] { return value }",
                "invalid",
            ),
            (
                "nominal-list-inferred-local",
                "type P { x: Int }\ntype Box { values: List[P] }\n"
                "fn count(box: Box) -> Int { let values = box.values; return length(values) }",
                "valid",
            ),
            (
                "nested-nominal-list-literal",
                "type P { x: Int }\n"
                "fn values() -> List[List[P]] { return [[P { x: 1 }]] }",
                "valid",
            ),
            (
                "nested-nominal-list-element-mismatch",
                "type P { x: Int }\ntype Q { x: Int }\n"
                "fn values() -> List[List[P]] { return [[Q { x: 1 }]] }",
                "invalid",
            ),
            (
                "annotated-nominal-list-element-mismatch",
                "type P { x: Int }\ntype Q { x: Int }\n"
                "fn values() -> Unit { let values: List[P] = [Q { x: 1 }] }",
                "invalid",
            ),
            (
                "record-field-nominal-list-element-mismatch",
                "type P { x: Int }\ntype Q { x: Int }\ntype Box { values: List[P] }\n"
                "fn values() -> Box { return Box { values: [Q { x: 1 }] } }",
                "invalid",
            ),
        )
        for name, source, expected_status in cases:
            with self.subTest(name=name):
                report = self._assert_matches_reference(name, source)
                self.assertEqual(scalar(report["status"]), expected_status)

    def test_structural_nominal_list_builtins_preserve_and_check_shapes(self):
        cases = (
            (
                "append-nominal",
                "type Point { x: Int }\n"
                "fn add(points: List[Point], point: Point) -> List[Point] { return append(points, point) }",
                "valid",
                1,
            ),
            (
                "reverse-nominal",
                "type Point { x: Int }\n"
                "fn reversePoints(points: List[Point]) -> List[Point] { return reverse(points) }",
                "valid",
                1,
            ),
            (
                "append-nested-nominal",
                "type Point { x: Int }\n"
                "fn add(points: List[List[Point]], point: List[Point]) -> List[List[Point]] { return append(points, point) }",
                "valid",
                2,
            ),
            (
                "append-nominal-mismatch",
                "type Point { x: Int }\n"
                "type Other { x: Int }\n"
                "fn add(points: List[Point], point: Other) -> List[Point] { return append(points, point) }",
                "invalid",
                1,
            ),
            (
                "contains-nominal-unsupported-equality",
                "type Point { x: Int }\n"
                "fn has(points: List[Point], point: Point) -> Bool { return contains(points, point) }",
                "invalid",
                1,
            ),
        )
        for name, source, expected_status, expected_depth in cases:
            with self.subTest(name=name):
                report = self._assert_matches_reference(name, source)
                self.assertEqual(scalar(report["status"]), expected_status)
                shapes = [
                    fields(item)["typeShape"]
                    for item in report["expressionTypes"]["value"]
                    if scalar(fields(item)["typeShape"]["fields"][0]["value"]) != ""
                ]
                if name in ("append-nominal", "reverse-nominal", "append-nested-nominal"):
                    self.assertTrue(any(
                        scalar(fields(shape)["kind"]) == "nominal"
                        and scalar(fields(shape)["name"]) == "Point"
                        and scalar(fields(shape)["listDepth"]) == expected_depth
                        for shape in shapes
                    ))

    def test_length_accepts_a_list_with_a_nominal_element_type(self):
        source = (
            "type Point { x: Int }\n"
            "fn count(points: List[Point]) -> Int { return length(points) }"
        )
        report = self._assert_matches_reference("length-nominal-list", source)
        self.assertEqual(scalar(report["status"]), "valid")

        field_source = (
            "type Point { x: Int }\n"
            "type Box { points: List[Point] }\n"
            "fn countBox(box: Box) -> Int { return length(box.points) }"
        )
        field_report = self._assert_matches_reference("length-nominal-list-field", field_source)
        self.assertEqual(scalar(field_report["status"]), "valid")

    def test_union_payload_can_hold_a_named_record(self):
        source = (
            "type Inner { value: Int }\n"
            "type Outcome = Success(Inner) | Failure()\n"
            "fn success() -> Outcome { return Success(Inner { value: 42 }) }"
        )
        report = self._assert_matches_reference("union-payload", source)
        self.assertEqual(scalar(report["status"]), "valid")

    def test_union_pattern_binding_retains_named_record_payload_type(self):
        source = (
            "type Point { x: Int }\n"
            "type Message = At(Point) | Missing()\n"
            "fn read(message: Message) -> Int { return match message { At(point) => 0 Missing() => 1 } }"
        )
        report = self._assert_matches_reference("union-record-pattern", source)
        self.assertEqual(scalar(report["status"]), "valid")
        binding_types = [scalar(fields(item)["typeName"]) for item in report["bindings"]["value"]]
        self.assertIn("Point", binding_types)
        expression_types = [scalar(fields(item)["typeName"]) for item in report["expressionTypes"]["value"]]
        self.assertIn("Int", expression_types)

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
