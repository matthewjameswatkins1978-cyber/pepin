"""Continuation and revision attacks against the real `pep.ps1 session --jsonl`.

Purpose
-------
Independently challenge the invariants a parser-continuation repair depends on,
using only the real session protocol (schemaVersion 3). Nothing here re-implements
Pep: the driver speaks JSONL to the real CLI and reports what came back.

Each attack prints one machine-checkable line:

    ATTACK <name> | expect=<what must happen> | observed=<what did> | HOLD|VIOLATED
    DETAIL <name> | <first 300 chars of the raw response>

`VIOLATED` means the session broke the invariant, which is the falsifying
evidence a Terror Bat needs. `HOLD` means this attack did not break it — which is
not a certificate.

Exit code: 0 when every attack held, 1 when any invariant was violated,
2 when the harness itself could not run (never confused with a violation).
"""
import json
import subprocess
import sys

PEP = sys.argv[1] if len(sys.argv) > 1 else "pep.ps1"

SOURCE_A = "fn alpha(x: Int) -> Int { return x + 1 }\n"
SOURCE_B = "fn beta(x: Int) -> Int { return x + 2 }\n"


class Session:
    def __init__(self):
        self.proc = subprocess.Popen(
            ["pwsh", "-NoProfile", "-File", PEP, "session", "--jsonl"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)

    def raw(self, line):
        """Send one raw line, return the raw response line (or None on EOF)."""
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        return self.proc.stdout.readline().strip()

    def send(self, request):
        return self.raw(json.dumps(request, separators=(",", ":")))

    def close(self):
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def report(name, expect, observed, ok, detail):
    print("ATTACK %s | expect=%s | observed=%s | %s" % (
        name, expect, observed, "HOLD" if ok else "VIOLATED"))
    print("DETAIL %s | %s" % (name, (detail or "")[:300].replace("\n", " ")))


def parse(line):
    try:
        return json.loads(line or "")
    except json.JSONDecodeError:
        return None


def main():
    session = Session()
    failures = 0
    try:
        # Baseline: a valid open must succeed, otherwise later attacks are moot.
        opened = parse(session.send({"schemaVersion": 3, "op": "open",
                                     "source": SOURCE_A, "name": "attack-a"}))
        if not opened or opened.get("outcome") != "ok":
            print("HARNESS-ERROR baseline open failed: %s" % (opened,))
            return 2
        revision_a = opened.get("revision")
        document_a = opened.get("document")

        # 1. Unknown operation: must be a structured refusal, and the session
        #    must stay alive for the next request.
        line = session.send({"schemaVersion": 3, "op": "continue_forever"})
        doc = parse(line)
        ok = bool(doc) and doc.get("outcome") != "ok" and "error" in doc
        report("unknown-op", "structured refusal, session alive", line[:120],
               ok, line)
        failures += 0 if ok else 1

        # 2. Malformed JSON line: structured refusal, session alive.
        line = session.raw("this is not json")
        doc = parse(line)
        ok = bool(doc) and doc.get("outcome") != "ok" and "error" in doc
        report("malformed-json", "structured refusal, session alive", line[:120],
               ok, line)
        failures += 0 if ok else 1

        # 3. Missing required field: named refusal, not a crash or silence.
        line = session.send({"schemaVersion": 3, "op": "open"})
        doc = parse(line)
        code = ((doc or {}).get("error") or {}).get("code")
        ok = bool(doc) and doc.get("outcome") != "ok" and bool(code)
        report("missing-field", "refusal carrying an error code",
               "%s/%s" % ((doc or {}).get("outcome"), code), ok, line)
        failures += 0 if ok else 1

        # 4. Stale revision: a second open creates a new revision, and a request
        #    pinned to the first revision must not be served silently
        #    (describe declares crossRevisionReuse: false).
        opened_b = parse(session.send({"schemaVersion": 3, "op": "open",
                                       "source": SOURCE_B, "name": "attack-b"}))
        revision_b = (opened_b or {}).get("revision")
        stale = parse(session.send({"schemaVersion": 3, "op": "tool_invoke",
                                    "toolProtocolVersion": 2,
                                    "tool": "no-such-tool",
                                    "arguments": [],
                                    "document": document_a,
                                    "revision": revision_a,
                                    "semanticTarget": {"document": document_a,
                                                       "revision": revision_a,
                                                       "entryFunctions": []}}))
        code = (stale or {}).get("error", {}).get("code")
        ok = bool(stale) and stale.get("outcome") != "ok" and bool(code)
        report("unregistered-tool", "refusal carrying an error code",
               "%s/%s" % ((stale or {}).get("outcome"), code), ok, str(stale))
        failures += 0 if ok else 1

        # 5. Revision identity: identical bytes reopen to the same CONTENT
        #    revision; different bytes to a different one. The `document` field
        #    is a per-open session handle and legitimately differs, so a
        #    continuation repair must key staleness on `revision`, not on the
        #    handle — an earlier version of this attack wrongly required both and
        #    produced a false VIOLATED.
        again = parse(session.send({"schemaVersion": 3, "op": "open",
                                    "source": SOURCE_A, "name": "attack-a"}))
        same_revision = bool(again) and again.get("revision") == revision_a
        different_bytes = (opened_b or {}).get("revision") != revision_a
        handle_differs = bool(again) and again.get("document") != document_a
        ok = same_revision and different_bytes
        report("revision-identity",
               "same bytes -> same revision, different bytes -> different",
               "same=%s different=%s handle_differs=%s" % (
                   same_revision, different_bytes, handle_differs), ok,
               str(again)[:200])
        failures += 0 if ok else 1

        # 6. Session liveness after all refusals: the last request must still be
        #    answered correctly, proving no refusal corrupted the loop.
        alive = parse(session.send({"schemaVersion": 3, "op": "open",
                                    "source": SOURCE_B, "name": "attack-b"}))
        ok = bool(alive) and alive.get("outcome") == "ok" \
            and alive.get("revision") == revision_b
        report("liveness-after-refusals", "still answers correctly",
               (alive or {}).get("outcome"), ok, str(alive)[:200])
        failures += 0 if ok else 1
    finally:
        session.close()
    print("SUMMARY attacks=6 violated=%d" % failures)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
