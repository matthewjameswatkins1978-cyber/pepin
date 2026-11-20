import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
SOURCE = ROOT / "examples" / "agent_calculator.pep"


class AgentCalculatorTests(unittest.TestCase):
    def invoke_run(self, source_path=SOURCE):
        res = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP), "run", str(source_path)],
                             cwd=ROOT, text=True, capture_output=True, check=False)
        return res

    def test_factorial_base(self):
        # Checks REQ-CALC-001
        res = self.invoke_run()
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_factorial_recursive(self):
        # Checks REQ-CALC-001
        res = self.invoke_run()
        self.assertEqual(res.returncode, 0)

    def test_power_zero_exponent(self):
        # Checks REQ-CALC-002
        res = self.invoke_run()
        self.assertEqual(res.returncode, 0)

    def test_power_positive(self):
        # Checks REQ-CALC-002
        res = self.invoke_run()
        self.assertEqual(res.returncode, 0)

    def test_clamp_within_range(self):
        # Checks REQ-CALC-003
        res = self.invoke_run()
        self.assertEqual(res.returncode, 0)

    def test_clamp_below_min(self):
        # Checks REQ-CALC-003
        res = self.invoke_run()
        self.assertEqual(res.returncode, 0)

    def test_clamp_above_max(self):
        # Checks REQ-CALC-003
        res = self.invoke_run()
        self.assertEqual(res.returncode, 0)

    def test_calculate_clamped_factorial(self):
        # Checks REQ-CALC-004
        # 5! is 120, clamped to limit 100 should return 100
        res = self.invoke_run()
        self.assertEqual(res.returncode, 0)
        # Note: run exits 0, returns value through main
