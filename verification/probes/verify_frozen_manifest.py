"""Pre-registration check for Candidate7 acceptance: verify the FROZEN MANIFEST is intact.

The frozen acceptance runner (`verification/tools/run_acceptance_gates.ps1`, blob b464e00e...)
pins 13 instrument files by git blob SHA and reports "frozen-manifest (13 entries)" as its first
gate. Before gating any candidate, the instrument itself must be provably unmodified, otherwise a
red/green verdict is meaningless.

This script extracts the pinned path->blob table from the runner source and compares it against
`git rev-parse HEAD:<path>` in the working tree that holds verification/**. It does NOT run the
gates (they need peer worktrees); it answers exactly one question: is the instrument intact?

Usage: python verify_frozen_manifest.py <repo-or-worktree-root>
Exit 0 = all 13 pins match; 1 = drift.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
RUNNER = ROOT / "verification" / "tools" / "run_acceptance_gates.ps1"
EXPECTED_BASELINE = "v2"

if not RUNNER.exists():
    raise SystemExit(f"runner not found: {RUNNER}")

source = RUNNER.read_text(encoding="utf-8", errors="replace")
pins = re.findall(r"'(verification/[^']+)'\s*=\s*'([0-9a-f]{40})'", source)
baseline = re.search(r"\$BaselineVersion\s*=\s*'([^']+)'", source)
runner_blob = subprocess.run(["git", "-C", str(ROOT), "rev-parse", f"HEAD:verification/tools/run_acceptance_gates.ps1"],
                             capture_output=True, text=True, check=False)

print(f"ROOT {ROOT}")
print(f"BASELINE declared in runner: {baseline.group(1) if baseline else 'UNKNOWN'} "
      f"(expected {EXPECTED_BASELINE})")
print(f"RUNNER blob at HEAD: {runner_blob.stdout.strip() or runner_blob.stderr.strip()[:80]}")
print(f"PINS found: {len(pins)}")

failures = 0
for path, pinned in pins:
    actual = subprocess.run(["git", "-C", str(ROOT), "rev-parse", f"HEAD:{path}"],
                            capture_output=True, text=True, check=False).stdout.strip()
    ok = actual == pinned
    if not ok:
        failures += 1
    print(f"{'OK  ' if ok else 'DRIFT'} {path}  pinned={pinned[:12]} actual={actual[:12] or 'ABSENT'}")
    # Also check the working tree copy is byte-identical to the commit (no local edits).
    local = ROOT / path
    if local.exists():
        blob_now = subprocess.run(["git", "-C", str(ROOT), "hash-object", str(local)],
                                  capture_output=True, text=True, check=False).stdout.strip()
        if blob_now != pinned:
            failures += 1
            print(f"     WORKTREE-DRIFT {path}  on-disk={blob_now[:12]}")

print(f"SUMMARY pins={len(pins)} drift={failures} baseline_ok={bool(baseline) and baseline.group(1) == EXPECTED_BASELINE}")
sys.exit(0 if failures == 0 and baseline and baseline.group(1) == EXPECTED_BASELINE else 1)
