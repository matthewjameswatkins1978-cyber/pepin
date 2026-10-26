import importlib.util
from pathlib import Path


_path = Path(__file__).resolve().parents[1] / "experiments" / "c23_feasibility" / "test_feasibility.py"
_spec = importlib.util.spec_from_file_location("pep_c23_feasibility_tests", _path)
_module = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_module)

CorpusPolicyTests = _module.CorpusPolicyTests
InterpreterOracleTests = _module.InterpreterOracleTests
NativeProofTests = _module.NativeProofTests
