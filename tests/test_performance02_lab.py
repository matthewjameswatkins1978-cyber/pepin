import json
import unittest

from tests import performance02_lab as lab


class Performance02LabTests(unittest.TestCase):
    def test_profile_totals_keep_internal_wall_clock_ledger(self):
        totals = lab.profile_totals([
            {"decodeCpuUs": 100, "grantCpuUs": 200, "executeCpuUs": 300,
             "encodeCpuUs": 400, "responseCpuUs": 500, "steps": 9,
             "resultValueNodes": 4, "encodedResultBytes": 12},
            {"decodeCpuUs": 300, "grantCpuUs": 0, "executeCpuUs": 100,
             "encodeCpuUs": 0, "responseCpuUs": 100, "steps": 3,
             "resultValueNodes": 2, "encodedResultBytes": 8},
        ])
        self.assertEqual(totals.calls, 2)
        self.assertEqual(totals.execute_ms, 0.4)
        self.assertEqual(totals.steps, 12)
        self.assertEqual(totals.encoded_result_bytes, 20)
        self.assertEqual(totals.internal_ms, 2.0)

    def test_stage_accounting_labels_overlap_and_typed_construction(self):
        row = lab.stage_accounting(
            source={"bytes": 1, "revision": "sha256:x"},
            result={"tokens": [{"kind": "x"}], "error": None},
            metrics={"requests": {"count": 1, "requestBytes": 2, "responseBytes": 3,
                                  "requestEncodeMs": 1.0, "writeMs": 2.0, "readMs": 3.0,
                                  "parseMs": 4.0, "totalMs": 10.0}},
            profiles=[{"decodeCpuUs": 1, "grantCpuUs": 2, "executeCpuUs": 3,
                       "encodeCpuUs": 4, "responseCpuUs": 5, "steps": 6,
                       "resultValueNodes": 7, "encodedResultBytes": 8}],
            process={"spawnMs": 9.0, "readyMs": 10.0, "peakMemory": None},
            trial=1,
        )
        self.assertTrue(row["attribution"]["internalAndHostLedgersOverlap"])
        self.assertTrue(row["attribution"]["typedConstructionIsNotSeparatelyIsolated"])
        self.assertEqual(row["internalProfile"]["interpreterAndTypedConstructionMs"], 0.003)

    def test_representation_variants_round_trip_exactly(self):
        fixture = lab.synthetic_checked_ast_fixture(12)
        rows = lab.measure_representations(fixture)
        self.assertEqual({row["representation"] for row in rows}, {
            "existing-typed-json", "flat-node-array", "compact-interned-array"
        })
        self.assertTrue(all(row["jsonBytes"] > 0 for row in rows))
        compact = next(row for row in rows if row["representation"] == "compact-interned-array")
        typed = next(row for row in rows if row["representation"] == "existing-typed-json")
        self.assertLess(compact["jsonBytes"], typed["jsonBytes"])

    def test_topology_and_span_mutations_are_detectable(self):
        fixture = lab.synthetic_checked_ast_fixture(6)
        lab.assert_mutation_rejected(fixture, lambda value: value["nodes"][2].__setitem__("parentId", 1))
        lab.assert_mutation_rejected(fixture, lambda value: value["nodes"][2].__setitem__("startByte", 1000))
        lab.assert_mutation_rejected(fixture, lambda value: value.__setitem__("revision", "sha256:wrong"))

    def test_cursor_representations_preserve_authority_identity(self):
        rows = lab.cursor_size_rows("doc", "sha256:rev")
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["revisionPreserved"] and row["documentPreserved"] for row in rows))
        full = next(row for row in rows if row["representation"] == "full-existing-typed")
        minimal = next(row for row in rows if row["representation"] == "minimal-logical")
        self.assertLess(minimal["jsonBytes"], full["jsonBytes"])

    def test_future_fixtures_are_explicitly_labelled(self):
        self.assertEqual(lab.synthetic_checked_ast_fixture(1)["kind"], "synthetic-checked-ast")
        self.assertEqual(lab.synthetic_c23_emission_fixture(1)["kind"], "synthetic-c23-emission")

    def test_a12_measurement_is_explicitly_provisional(self):
        row = lab.provisional_a12_measurement(
            candidate_sha="69a47fe77187666bdd045b8dc8a9f633a7dd49d7",
            source_bytes=19425, nodes=2030, continuations=567,
            request_bytes=4183287, response_bytes=6100090,
            max_request_bytes=67408, max_response_bytes=69118,
        )
        self.assertEqual(row["authority"], "provisional-disposable-checkout")
        self.assertTrue(row["sourceCapUnchanged"])
        self.assertFalse(row["protocolChanged"])

    def test_self_test_has_negative_controls_and_json_output(self):
        result = lab.self_test()
        self.assertIn("parentId", result["negativeControls"])
        self.assertIn("sourceSpan", result["negativeControls"])
        json.dumps(result)

    def test_trial_and_source_caps_are_bounded(self):
        with self.assertRaises(ValueError):
            lab.run_a11_stage_profile(trials=lab.DEFAULT_MAX_TRIALS + 1)
        with self.assertRaises(ValueError):
            lab.synthetic_checked_ast_fixture(0)

    def test_fixed_estimated_and_feedback_strategies_preserve_budget(self):
        fixed = lab.simulate_batch_strategy(strategy="fixed", units=100, steps_per_unit=2000, bytes_per_unit=100)
        estimated = lab.simulate_batch_strategy(strategy="estimated", units=100, steps_per_unit=2000, bytes_per_unit=100)
        feedback = lab.simulate_batch_strategy(strategy="feedback", units=100, steps_per_unit=2000, bytes_per_unit=100)
        self.assertFalse(fixed["complete"])
        self.assertTrue(estimated["complete"])
        self.assertTrue(feedback["complete"])
        for result in (fixed, estimated, feedback):
            for batch in result["batches"]:
                if batch["outcome"] == "success":
                    self.assertLessEqual(batch["actualSteps"], lab.TOOL_STEP_BUDGET)
                    self.assertLessEqual(batch["actualBytes"], lab.TOOL_MESSAGE_BUDGET)

    def test_optimistic_estimator_records_bounded_failure_without_commit(self):
        result = lab.simulate_batch_strategy(
            strategy="estimated", units=500, steps_per_unit=5000, bytes_per_unit=100,
            optimistic=True,
        )
        self.assertFalse(result["complete"])
        self.assertLess(result["committedUnits"], 500)
        self.assertEqual(result["batches"][-1]["outcome"], "bounded-failure")

    def test_transport_scaling_contains_all_local_representations(self):
        rows = lab.transport_scaling((8, 32))
        self.assertEqual(len(rows), 6)
        self.assertEqual({row["nodes"] for row in rows}, {8, 32})

    def test_architecture_comparison_keeps_hybrid_design_only(self):
        rows = lab.architecture_comparison(
            a11_calls=10, a11_response_bytes=100, a12_calls=4,
            a12_response_bytes=80, compact_ratio=0.25,
        )
        self.assertEqual([row["model"] for row in rows], [
            "separated-tools", "composed-Pep-invocation", "hybrid-retained-state",
        ])
        self.assertEqual(rows[0]["roundTrips"], 14)
        self.assertEqual(rows[1]["roundTrips"], 4)
        self.assertEqual(rows[2]["responseBytes"], 20)
        self.assertTrue(rows[2]["status"].startswith("design-only"))

    def test_lifecycle_input_validation_is_bounded(self):
        with self.assertRaises(ValueError):
            lab.run_session_lifecycle(count=0)


if __name__ == "__main__":
    unittest.main()
