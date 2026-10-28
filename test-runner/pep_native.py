"""Native differential adapter for `pep test` — interpreter vs Clang vs GCC (C23).

Purpose
-------
Run the *same* Pep program through Pep's real backends and compare what they
actually do:

    interpreter   .\\pep.ps1 run FILE        (top-level statements execute)
    clang         .\\pep.ps1 run-c23 FILE --compiler clang
    gcc           .\\pep.ps1 run-c23 FILE --compiler gcc

Nothing here re-implements Pep, the checker, the emitter or C. The adapter
only drives the real CLI, separates build chatter from program output, and
classifies the outcome so a differential result can never be faked.

Measured facts this adapter is built on (probed against the real CLI,
clang 23.1.4 and gcc 16.2.0, 2026-10-28)
-------------------------------------------------------------
* `run` executes top-level statements only; it never calls `fn main`.
* `run-c23` requires a top-level `fn main() -> Int`; it prints the returned
  Int to stdout and exits 0. A `Unit`/`Bool` main, a record/variant program,
  a `for`-in list or a `var`/`while` body are rejected as *unsupported*.
* `run-c23` writes exactly two build lines to stderr before the program runs:

      C23: <generated .c path>
      Executable: <exe path>

  so a program's own stderr starts on line 3.
* Unsupported subset  -> stderr `Pep C23 unsupported: <reason>`, exit 2.
* Adapter/toolchain   -> stderr `Pep C23 error: <reason>`, exit 2.
* Runtime guards      -> exit 1, diagnostic code on stderr
                          (interpreter prints `line:col: CODE: message`).
* A compiler rejecting the emitted C exits nonzero with no Pep prefix.

Consequence for honesty: for a `fn main` program the interpreter's *runtime*
observable is empty, so a genuine three-way runtime differential needs the
hybrid shape — the same value computed both in `main` (native) and at top
level (interpreter). Fixtures in this suite use that shape, and the shared
expectation is what all three backends must reproduce.
"""
import re
import shutil
import subprocess

INTERPRETER = "interpreter"
CLANG = "clang"
GCC = "gcc"
NATIVE_BACKENDS = (CLANG, GCC)
ALL_BACKENDS = (INTERPRETER,) + NATIVE_BACKENDS

UNSUPPORTED_PREFIX = "Pep C23 unsupported:"
ERROR_PREFIX = "Pep C23 error:"
BUILD_METADATA_PREFIXES = ("C23: ", "Executable: ")
DIAGNOSTIC_CODE = re.compile(r"\bPEP_[A-Z][A-Z0-9_]*\b")
# Observed interpreter runtime diagnostic shape: `line:col: CODE: message`.
INTERPRETER_DIAGNOSTIC = re.compile(r"(?m)^\d+:\d+:\s*(PEP_[A-Z][A-Z0-9_]*)\b")

#: Native outcome classes, deliberately distinct from test outcomes.
RAN = "ran"
UNSUPPORTED = "unsupported"
BUILD_ERROR = "build_error"
TOOL_ERROR = "tool_error"


class Unavailable(Exception):
    """A selected backend's toolchain is not installed."""


class ConfigError(Exception):
    """The fixture or the invocation asks for something incoherent."""


def parse_backends(text):
    """Parse `--backend a,b` into a validated, de-duplicated tuple."""
    if text is None:
        return (INTERPRETER,)
    names = []
    # PowerShell hands `a,b,c` through to a native command as "a b c",
    # so accept commas, semicolons and whitespace as separators.
    for raw in re.split(r"[,;\s]+", str(text)):
        name = raw.strip().lower()
        if not name:
            continue
        if name in ("interp", "interpreter", "run"):
            name = INTERPRETER
        elif name in ("cc", "clang-c23", "clang23"):
            name = CLANG
        elif name in ("gcc-c23", "gcc23", "gnu"):
            name = GCC
        if name not in ALL_BACKENDS:
            raise ConfigError(
                "unknown backend %r (want interpreter|clang|gcc)" % raw.strip())
        if name not in names:
            names.append(name)
    if not names:
        raise ConfigError("--backend selected no backends")
    return tuple(names)


def wants_native(backends):
    return any(b in NATIVE_BACKENDS for b in backends)


def resolve_compiler(backend, explicit=None):
    """Resolve a native compiler path or raise Unavailable."""
    if backend not in NATIVE_BACKENDS:
        raise ConfigError("%r is not a native backend" % backend)
    if explicit:
        found = shutil.which(explicit)
        if found:
            return found
        raise Unavailable("%s compiler not found: %s" % (backend, explicit))
    found = shutil.which(backend) or shutil.which(backend + ".exe")
    if found:
        return found
    raise Unavailable("%s compiler not found on PATH" % backend)


def split_build_metadata(stderr):
    """Split the two leading `run-c23` build lines from program stderr.

    Only lines at the very start of stderr are treated as metadata, and at
    most two of them, so a program that itself prints `C23: ...` later is
    preserved verbatim instead of being silently stripped.
    """
    if not stderr:
        return [], ""
    lines = stderr.splitlines(keepends=True)
    metadata = []
    for line in lines[:2]:
        if line.startswith(BUILD_METADATA_PREFIXES):
            metadata.append(line.rstrip("\r\n"))
        else:
            break
    return metadata, "".join(lines[len(metadata):])


def classify_native(exit_code, stdout, program_stderr):
    """Classify a `run-c23` result into one native outcome class."""
    combined = (stdout or "") + (program_stderr or "")
    if UNSUPPORTED_PREFIX in combined:
        tail = combined.split(UNSUPPORTED_PREFIX, 1)[1].strip()
        reason = (tail.splitlines() or ["unspecified"])[0]
        if exit_code != 2:
            # An unsupported marker carrying another status is a malformed
            # response: not a clean refusal, and certainly not a run.
            return BUILD_ERROR, ("malformed unsupported response (exit %s): %s"
                                 % (exit_code, reason))
        return UNSUPPORTED, reason
    if ERROR_PREFIX in combined:
        tail = combined.split(ERROR_PREFIX, 1)[1].strip()
        return TOOL_ERROR, (tail.splitlines() or ["unspecified"])[0]
    if exit_code == 2:
        # Emitted C refused by the compiler, or the CLI failed to start.
        detail = (combined.strip().splitlines() or ["exit 2"])[0]
        return BUILD_ERROR, detail
    return RAN, None


def diagnostic_code(text):
    """First Pep diagnostic code in interpreter or native output."""
    match = INTERPRETER_DIAGNOSTIC.search(text or "")
    if match:
        return match.group(1), match.group(0)
    match = DIAGNOSTIC_CODE.search(text or "")
    if match:
        return match.group(0), match.group(0)
    return None, None


def observe(cli, backend, pep_file, timeout, invoke, compiler=None):
    """Run one backend through the real CLI and normalise its observation."""
    if backend == INTERPRETER:
        rc, out, err, elapsed, timed_out = invoke(
            cli, ["run", str(pep_file)], timeout)
        return {"backend": backend, "command": "pep run", "exit": rc,
                "stdout": out, "stderr": err, "elapsed_s": round(elapsed, 3),
                "timed_out": timed_out, "metadata": []}
    args = ["run-c23", str(pep_file)]
    if compiler:
        args += ["--compiler", str(compiler)]
    rc, out, err, elapsed, timed_out = invoke(cli, args, timeout)
    metadata, program_err = split_build_metadata(err or "")
    return {"backend": backend, "command": "pep run-c23", "exit": rc,
            "stdout": out, "stderr": program_err, "elapsed_s": round(elapsed, 3),
            "timed_out": timed_out, "metadata": metadata,
            "compiler": str(compiler) if compiler else None}


def compiler_identity(path, timeout=15):
    """Record which compiler produced a differential result.

    A receipt that says "clang agreed with gcc" is only reproducible if it
    names the compilers. A compiler that cannot report itself is recorded as
    unknown rather than guessed, and never aborts the run.
    """
    try:
        proc = subprocess.run([str(path), "--version"], text=True,
                              capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"path": str(path), "version": "unknown: %s" % exc}
    lines = ((proc.stdout or "") or (proc.stderr or "")).strip().splitlines()
    version = (lines or ["unknown: no version output"])[0][:200]
    return {"path": str(path), "version": version}


def toolchain_identities(compilers):
    """Identity for every resolved native compiler, keyed by backend name."""
    return {name: compiler_identity(path) for name, path in sorted(compilers.items())}


def check_toolchains(backends, compilers):
    """Resolve every selected native backend once, before running anything.

    Failing fast here keeps "compiler missing" an infrastructure result rather
    than a pile of per-fixture failures, and makes it impossible to read a
    missing toolchain as a passing differential.
    """
    resolved = {}
    for backend in backends:
        if backend in NATIVE_BACKENDS:
            resolved[backend] = resolve_compiler(backend, compilers.get(backend))
    return resolved


def _format(observations):
    parts = []
    for item in observations:
        parts.append("%s(exit=%s, out=%r)" % (
            item["backend"], item.get("exit"), (item.get("stdout") or "")[:80]))
    return " ".join(parts)


def validate_expect(expect):
    """Reject incoherent native expectations before anything runs."""
    if not isinstance(expect, dict):
        return "expect must be an object"
    mode = expect.get("match", "exact")
    if mode not in ("exact", "diagnostic", "reject"):
        return ("unknown match mode %r for a native fixture "
                "(want exact|diagnostic|reject)" % mode)
    if mode in ("diagnostic", "reject") and not expect.get("diagnosticCode"):
        return "match=%s requires expect.diagnosticCode" % mode
    if "nativeUnsupported" in expect and mode == "reject":
        return ("expect declares both nativeUnsupported and match=reject; "
                "a fixture must declare one outcome")
    if "nativeUnsupported" in expect and not isinstance(expect["nativeUnsupported"], str):
        return "expect.nativeUnsupported must be a string substring"
    if "stdout" in expect and not isinstance(expect["stdout"], str):
        return "expect.stdout must be a string"
    if "exit" in expect and (isinstance(expect["exit"], bool)
                             or not isinstance(expect["exit"], int)):
        return "expect.exit must be an integer"
    return None


def _native_divergence(native_items, mode):
    """Return a detail when the native compilers disagree with each other."""
    if len(native_items) < 2:
        return None
    first, *rest = native_items
    for other in rest:
        if (other.get("stdout") or "") != (first.get("stdout") or ""):
            return "%s and %s disagree on stdout: %r vs %r" % (
                first["backend"], other["backend"],
                first.get("stdout"), other.get("stdout"))
        if other.get("exit") != first.get("exit"):
            return "%s and %s disagree on exit: %s vs %s" % (
                first["backend"], other["backend"],
                first.get("exit"), other.get("exit"))
        if mode == "diagnostic":
            a = diagnostic_code((first.get("stdout") or "") + (first.get("stderr") or ""))[0]
            b = diagnostic_code((other.get("stdout") or "") + (other.get("stderr") or ""))[0]
            if a != b:
                return "%s and %s disagree on diagnostic code: %r vs %r" % (
                    first["backend"], other["backend"], a, b)
    return None


def _check_interpreter(expect, observations):
    """Verify the interpreter's own declared observable, if one is declared."""
    for item in observations:
        if item["backend"] != INTERPRETER:
            continue
        want_exit = expect.get("exit", 0)
        if item.get("exit") != want_exit:
            return "interpreter exit %s, expected %s" % (item.get("exit"), want_exit)
        if "stdout" in expect and (item.get("stdout") or "") != expect["stdout"]:
            return "interpreter stdout %r, expected %r" % (
                item.get("stdout"), expect["stdout"])
    return None


def _reject_parity(expect, observations, classes, unsupported):
    """An invalid program must be rejected by every backend, never executed."""
    want_code = expect.get("diagnosticCode")
    if not want_code:
        return "infra_error", "match=reject requires expect.diagnosticCode"
    for item in observations:
        if item["backend"] == INTERPRETER:
            if item.get("exit") == 0:
                return "fail", "interpreter accepted an invalid program (exit 0)"
            code, _ = diagnostic_code(
                (item.get("stdout") or "") + (item.get("stderr") or ""))
            if code != want_code:
                return "fail", "interpreter reported %r, expected %s" % (
                    code, want_code)
            continue
        cls = classes.get(item["backend"], (None, None))[0]
        if cls != UNSUPPORTED:
            return "fail", (
                "%s did not reject the invalid program (class=%s, exit=%s); "
                "an invalid program must never run" % (
                    item["backend"], cls, item.get("exit")))
    return "pass", "all backends rejected the program (interpreter %s)" % want_code


def verdict(expect, observations, backends):
    """Decide one native fixture. Returns (status, detail).

    status values: pass | fail | divergence | unsupported | compile_error |
    timeout | infra_error. A native backend that reports unsupported without a
    declaration is a failure, and a declaration that no longer holds is also a
    failure — the differential can move but never silently.
    """
    for item in observations:
        if item.get("timed_out"):
            return "timeout", "%s exceeded the per-phase timeout" % item["backend"]
        if item.get("exit") is None:
            return "infra_error", "%s transport failure: %s" % (
                item["backend"], (item.get("stderr") or "")[:200])

    classes = {}
    for item in observations:
        if item["backend"] == INTERPRETER:
            continue
        combined_err = item.get("stderr") or ""
        classes[item["backend"]] = classify_native(
            item.get("exit"), item.get("stdout"), combined_err)

    for backend, (cls, detail) in classes.items():
        if cls == TOOL_ERROR:
            return "infra_error", "%s toolchain error: %s" % (backend, detail)
        if cls == BUILD_ERROR:
            return "compile_error", "%s rejected the emitted C23: %s" % (
                backend, detail)

    native_items = [o for o in observations if o["backend"] != INTERPRETER]
    declared = expect.get("nativeUnsupported")
    mode = expect.get("match", "exact")
    unsupported = {b: d for b, (c, d) in classes.items() if c == UNSUPPORTED}

    if mode == "reject":
        return _reject_parity(expect, observations, classes, unsupported)

    if declared is not None:
        problem = _check_interpreter(expect, observations)
        if problem:
            return "fail", problem
        ran = [b for b in classes if b not in unsupported]
        if ran:
            return "fail", (
                "fixture declares the native subset unsupported (%r) but %s "
                "now ran it; update the manifest declaration" % (declared, ", ".join(ran)))
        for backend, reason in unsupported.items():
            if str(declared) not in reason:
                return "fail", ("%s unsupported reason changed: %r no longer "
                                "contains %r" % (backend, reason, declared))
        return "unsupported", "declared unsupported on %s: %s" % (
            "+".join(sorted(unsupported)), unsupported[sorted(unsupported)[0]])
    if unsupported:
        return "fail", ("native backend reported the fixture unsupported "
                        "without a declaration: %s" % _format(native_items))

    # Native-vs-native disagreement is decided before any oracle comparison.
    # Otherwise the single expected answer that one compiler matches would
    # classify the split as an ordinary failure and hide the divergence.
    drift = _native_divergence(native_items, mode)
    if drift:
        return "divergence", drift

    # Supported: every selected backend must reproduce the shared expectation.
    want_exit = expect.get("exit", 0)
    if mode == "exact":
        want_stdout = expect.get("stdout", "")
        for item in observations:
            if item.get("exit") != want_exit:
                return "fail", "%s exit %s, expected %s" % (
                    item["backend"], item.get("exit"), want_exit)
            if (item.get("stdout") or "") != want_stdout:
                return "fail", "%s stdout %r, expected %r" % (
                    item["backend"], item.get("stdout"), want_stdout)
    elif mode == "diagnostic":
        want_code = expect.get("diagnosticCode")
        if not want_code:
            return "infra_error", "match=diagnostic requires expect.diagnosticCode"
        for item in observations:
            if item.get("exit") != want_exit:
                return "fail", "%s exit %s, expected %s" % (
                    item["backend"], item.get("exit"), want_exit)
            code, _ = diagnostic_code((item.get("stdout") or "") + (item.get("stderr") or ""))
            if code != want_code:
                return "fail", "%s reported %r, expected %s" % (
                    item["backend"], code, want_code)
    else:
        return "infra_error", "unknown match mode %r for native fixture (want exact|diagnostic)" % mode

    return "pass", "agreed across %s: %s" % (
        "+".join(o["backend"] for o in observations), _format(observations))
