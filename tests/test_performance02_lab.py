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

    def test_independent_ast_validator_checks_identity_topology_and_spans(self):
        fixture = lab.synthetic_checked_ast_fixture(8)
        checked = lab.validate_checked_ast_fixture(
            fixture, expected_document=fixture["document"],
            expected_revision=fixture["revision"], source_bytes=fixture["sourceBytes"],
        )
        self.assertEqual(checked["checkedNodes"], 8)
        bad = json.loads(json.dumps(fixture))
        bad["nodes"][1]["parentId"] = 999
        with self.assertRaises(lab.AstValidationError) as error:
            lab.validate_checked_ast_fixture(bad)
        self.assertEqual(error.exception.code, "structural-invalidity")
        bad = json.loads(json.dumps(fixture))
        bad["revision"] = "sha256:wrong"
        with self.assertRaises(lab.AstValidationError) as error:
            lab.validate_checked_ast_fixture(
                bad, expected_document=fixture["document"], expected_revision=fixture["revision"],
                source_bytes=fixture["sourceBytes"],
            )
        self.assertEqual(error.exception.code, "revision-mismatch")

    def test_serialized_corruption_corpus_rejects_every_representation(self):
        fixture = lab.synthetic_checked_ast_fixture(8)
        rows = lab.representation_mutation_corpus(fixture)
        self.assertEqual(len(rows), 3 * len(lab.AST_MUTATIONS))
        self.assertEqual({row["oracle"] for row in rows}, {
            "decode-error", "structural-invalidity", "revision-mismatch",
            "reference-equivalence-mismatch",
        })
        self.assertIn({
            "representation": "compact-interned-array",
            "mutation": "changed-value",
            "oracle": "reference-equivalence-mismatch",
        }, [dict((key, row[key]) for key in ("representation", "mutation", "oracle")) for row in rows])

    def test_roundtrippable_corruption_fails_independent_reference_oracle(self):
        fixture = lab.synthetic_checked_ast_fixture(8)
        payload, decoder = lab.representation_variants(fixture)["flat-node-array"]()
        corrupted = lab._mutate_encoded_payload("flat-node-array", payload, "changed-value")
        decoded = decoder(corrupted)
        self.assertEqual(lab.validate_checked_ast_fixture(decoded)["valid"], True)
        with self.assertRaises(lab.AstValidationError) as error:
            lab.validate_serialized_payload("flat-node-array", corrupted, fixture, decoder)
        self.assertEqual(error.exception.code, "reference-equivalence-mismatch")

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
        with self.assertRaises(ValueError):
            lab.run_session_lifecycle(count=lab.MAX_LIFECYCLE_COUNT + 1)
        with self.assertRaises(ValueError):
            lab.run_session_lifecycle(repeated_invokes=lab.MAX_LIFECYCLE_INVOKES + 1)
        with self.assertRaises(ValueError):
            lab.run_session_lifecycle(cold_trials=lab.MAX_LIFECYCLE_COLD_TRIALS + 1)

    def test_lifecycle_verifier_rejects_fail_open_negative_controls(self):
        source = "fn f() -> Int { return 1 }\n"
        edited_source = " " + source
        recovery_source = edited_source + " "
        initial = lab.base.revision(source.encode())
        edited = lab.base.revision(edited_source.encode())
        recovery = lab.base.revision(recovery_source.encode())
        document = "doc-1"

        def query(revision, status="valid", marker=1):
            return {
                "outcome": "ok", "operation": "query", "document": document,
                "revision": revision, "status": status, "ast": {"marker": marker},
                "typedTree": {"marker": marker}, "holes": [], "diagnostics": [],
            }

        valid = {
            "opened": {**query(initial), "operation": "open"},
            "edited": {"outcome": "ok", "operation": "apply_edit", "document": document, "revision": edited},
            "before_stale": query(edited),
            "stale": {"outcome": "error", "operation": "apply_edit", "document": document,
                      "currentRevision": edited, "error": {"code": "PEP_STALE_REVISION"}},
            "recovered": query(edited),
            "recovery_edit": {"outcome": "ok", "operation": "apply_edit", "document": document, "revision": recovery},
            "final": query(recovery),
        }

        def assert_rejected(**changes):
            case = {key: value.copy() for key, value in valid.items()}
            for key, value in changes.items():
                case[key] = value
            with self.assertRaises(lab.LifecycleInvariantError):
                lab.verify_revision_lifecycle(
                    **case, source=source, edited_source=edited_source, recovery_source=recovery_source,
                )

        assert_rejected(edited={**valid["edited"], "outcome": "error"})
        assert_rejected(edited={**valid["edited"], "revision": initial})
        assert_rejected(stale={**valid["stale"], "outcome": "ok"})
        assert_rejected(stale={**valid["stale"], "error": {"code": "WRONG_CODE"}})
        assert_rejected(recovered=query(edited, marker=2))
        assert_rejected(recovery_edit={**valid["recovery_edit"], "outcome": "error"})
        assert_rejected(final={**valid["final"], "outcome": "error"})

    def test_lifecycle_verifier_accepts_exact_recovery_contract(self):
        source = "fn f() -> Int { return 1 }\n"
        edited_source = " " + source
        recovery_source = edited_source + " "
        initial = lab.base.revision(source.encode())
        edited = lab.base.revision(edited_source.encode())
        recovery = lab.base.revision(recovery_source.encode())
        document = "doc-1"
        state = {"status": "valid", "ast": {"n": 1}, "typedTree": {"n": 1}, "holes": [], "diagnostics": []}
        query = lambda revision: {"outcome": "ok", "operation": "query", "document": document, "revision": revision, **state}
        result = lab.verify_revision_lifecycle(
            opened={"outcome": "ok", "operation": "open", "document": document, "revision": initial},
            edited={"outcome": "ok", "operation": "apply_edit", "document": document, "revision": edited},
            before_stale=query(edited),
            stale={"outcome": "error", "operation": "apply_edit", "document": document,
                   "currentRevision": edited, "error": {"code": "PEP_STALE_REVISION"}},
            recovered=query(edited),
            recovery_edit={"outcome": "ok", "operation": "apply_edit", "document": document, "revision": recovery},
            final=query(recovery), source=source, edited_source=edited_source, recovery_source=recovery_source,
        )
        self.assertTrue(result["verified"])
        self.assertTrue(result["stateUnchangedAfterStale"])
        self.assertEqual(result["recoveryRevision"], recovery)


if __name__ == "__main__":
    unittest.main()
