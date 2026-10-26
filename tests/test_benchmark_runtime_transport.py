import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests import benchmark_runtime_transport as harness


class _FakeFunction:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        self.calls += 1
        return self.result(*args) if callable(self.result) else self.result


class _FakeKernel:
    def __init__(self, handle=1):
        self.OpenProcess = _FakeFunction(handle)
        self.CloseHandle = _FakeFunction(True)


class _FakePsapi:
    def __init__(self, result):
        self.GetProcessMemoryInfo = _FakeFunction(result)


class _FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None and timeout is not None:
            raise harness.subprocess.TimeoutExpired("fake", timeout)
        return self.returncode


class _FakeStream:
    def __init__(self, data=b""):
        self.data = data

    def read(self):
        return self.data

    def readline(self):
        return self.data

    def write(self, data):
        return len(data)

    def flush(self):
        return None

    def close(self):
        return None


class BenchmarkHarnessTests(unittest.TestCase):
    def test_blocked_operation_times_out_and_terminates_child(self):
        process = _FakeProcess()
        client = object.__new__(harness.SessionClient)
        client.timeout_s = 0.01
        client.cleanup_timeout_s = 0.01
        client.process = process
        client._stderr_thread = threading.current_thread()
        client._join_stderr = lambda: None
        client._terminate_for_timeout = lambda phase: harness.terminate_process(process, client.cleanup_timeout_s)

        with self.assertRaises(harness.SessionTimeout) as raised:
            client._bounded_call("read", lambda: time.sleep(0.1))

        self.assertEqual(raised.exception.phase, "read")
        self.assertTrue(process.terminated)

    def test_startup_timeout_is_bounded(self):
        def stalled_popen(*args, **kwargs):
            time.sleep(0.1)

        started = time.perf_counter()
        with self.assertRaises(harness.SessionTimeout) as raised:
            harness.SessionClient(
                "direct", startup_timeout_s=0.01, cleanup_timeout_s=0.01,
                popen_factory=stalled_popen,
            )

        self.assertEqual(raised.exception.phase, "startup")
        self.assertLess(time.perf_counter() - started, 0.08)

    def test_jsonl_validation_distinguishes_missing_malformed_and_nonobject(self):
        with self.assertRaisesRegex(harness.SessionProtocolError, "missing"):
            harness.decode_response_line(b"")
        with self.assertRaisesRegex(harness.SessionProtocolError, "malformed"):
            harness.decode_response_line(b"not-json\n")
        with self.assertRaisesRegex(harness.SessionProtocolError, "not an object"):
            harness.decode_response_line(b"[]\n")

    def test_memory_unavailable_is_none_and_handle_is_closed(self):
        kernel = _FakeKernel(handle=1)
        psapi = _FakePsapi(False)
        self.assertIsNone(harness.process_memory(42, api=(kernel, psapi)))
        self.assertEqual(kernel.CloseHandle.calls, 1)

    def test_memory_zero_is_an_available_zero_sample(self):
        kernel = _FakeKernel(handle=1)

        def fill_zero(handle, pointer, size):
            pointer._obj.WorkingSetSize = 0
            pointer._obj.PrivateUsage = 0
            return True

        psapi = _FakePsapi(fill_zero)
        self.assertEqual(
            harness.process_memory(42, api=(kernel, psapi)),
            {"workingSetBytes": 0, "privateBytes": 0},
        )

    def test_profile_metadata_changes_with_source_and_configuration(self):
        first = harness.profile_build_metadata(b"source-a", b"profile-a", None, "switch", "5.5.2")
        changed_source = harness.profile_build_metadata(b"source-b", b"profile-a", None, "switch", "5.5.2")
        changed_switch = harness.profile_build_metadata(b"source-a", b"profile-a", None, "other", "5.5.2")
        self.assertNotEqual(first["sourceSha256"], changed_source["sourceSha256"])
        self.assertNotEqual(first["opamSwitch"], changed_switch["opamSwitch"])

    def test_profile_environment_is_truly_opt_in(self):
        captured = []

        def fake_popen(command, **kwargs):
            captured.append(kwargs["env"])
            process = _FakeProcess()
            process.returncode = 0
            process.stdin = _FakeStream()
            process.stdout = _FakeStream()
            process.stderr = _FakeStream()
            process.pid = 1
            return process

        disabled = harness.SessionClient("direct", profile=False, popen_factory=fake_popen)
        enabled = harness.SessionClient("direct", profile=True, popen_factory=fake_popen)
        disabled.abort()
        enabled.abort()
        self.assertNotIn("PEP_PROFILE", captured[0])
        self.assertEqual(captured[1]["PEP_PROFILE"], "1")

    def test_bounded_batch_candidate_respects_steps_output_and_hard_cap(self):
        self.assertEqual(harness.bounded_batch_width(512, 1000, 10, 20, 500), 25)
        self.assertEqual(harness.bounded_batch_width(512, 1, 10, 20, 500), 1)
        self.assertEqual(harness.bounded_batch_width(512, 100000, 1, 1, 100000), 256)

    def test_build_preflight_timeout_is_classified_and_bounded(self):
        seen = {}

        def timed_out_runner(*args, **kwargs):
            seen.update(kwargs)
            raise harness.subprocess.TimeoutExpired("pwsh", kwargs["timeout"])

        with self.assertRaises(harness.BuildPreflightTimeout) as raised:
            harness.ensure_build(timeout_s=0.01, runner=timed_out_runner)

        self.assertEqual(raised.exception.kind, "build_timeout")
        self.assertEqual(seen["timeout"], 0.01)

    def test_build_preflight_failure_and_unavailable_are_distinct(self):
        def failed_runner(*args, **kwargs):
            return SimpleNamespace(returncode=7, stderr="compile failed", stdout="")

        with self.assertRaises(harness.BuildPreflightFailed) as failed:
            harness.ensure_build(runner=failed_runner)

        self.assertEqual(failed.exception.kind, "build_failed")
        self.assertIn("compile failed", str(failed.exception))

        def unavailable_runner(*args, **kwargs):
            raise FileNotFoundError("pwsh")

        with self.assertRaises(harness.BuildPreflightUnavailable) as unavailable:
            harness.ensure_build(runner=unavailable_runner)

        self.assertEqual(unavailable.exception.kind, "build_unavailable")

    def test_main_fails_with_structured_build_timeout(self):
        with patch.object(
            harness, "ensure_build",
            side_effect=harness.BuildPreflightTimeout("preflight stalled"),
        ), patch.object(harness, "emit") as emit, patch.object(
            harness.sys, "argv", ["benchmark_runtime_transport.py"]
        ):
            self.assertEqual(harness.main(), 2)

        emit.assert_called_once_with({
            "kind": "benchmark-error",
            "stage": "build-preflight",
            "outcome": "build_timeout",
            "error": "preflight stalled",
        })

    def test_deliberate_variant_mismatch_is_rejected(self):
        expected = {
            "tokens": [{"kind": "identifier", "value": "x"}],
            "error": None,
        }
        actual = {
            "tokens": [{"kind": "identifier", "value": "y"}],
            "error": None,
        }

        diagnostic = harness.variant_mismatch_diagnostic(expected, actual)
        self.assertIsNotNone(diagnostic)
        self.assertEqual(diagnostic["firstDifferenceIndex"], 0)

        with self.assertRaisesRegex(
            harness.BenchmarkCorrectnessError, "width 128"
        ):
            harness.require_variant_match(128, "negative-control", expected, actual)


if __name__ == "__main__":
    unittest.main()
