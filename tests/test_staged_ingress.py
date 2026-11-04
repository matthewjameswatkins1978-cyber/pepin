"""Staged source ingress: open a 64 KiB prefix, append the rest with metadata.

The source byte cap an individual open may carry is unchanged (65536). What
this covers is ingress of a real module larger than that cap: the prefix is
opened with open_bytes, then successive apply_edit appends carry the
remainder. metadataOnly keeps each edit response free of the AST, which is
what previously pushed the response over the 1 MiB JSONL budget.
"""
import hashlib
import pathlib
import unittest

import pep_c23
from pep_c23 import Session, require

ROOT = pathlib.Path(__file__).resolve().parents[1]
WINDOW = 65536


def open_bundle(session):
    bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
    opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                           "name": "pep-c23", "metadataOnly": True})
    require(opened, "outcome", "ok", "open compiler bundle")
    return opened


def ingest(session, raw, metadata_only=True):
    cut = min(WINDOW, len(raw))
    while cut < len(raw) and (raw[cut] & 0xC0) == 0x80:
        cut -= 1
    prefix = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": "staged", "bytes": list(raw[:cut]),
                           "metadataOnly": True})
    require(prefix, "outcome", "ok", "open prefix")
    document, revision = prefix["document"], prefix["revision"]
    offset, appends = cut, 0
    while offset < len(raw):
        end = min(offset + WINDOW, len(raw))
        while end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        request = {"schemaVersion": 3, "op": "apply_edit",
                   "document": document,
                   "expected_revision": revision,
                   "start_byte": offset, "end_byte": offset,
                   "replacement": raw[offset:end].decode("utf-8")}
        if metadata_only:
            request["metadataOnly"] = True
        response = session.send(request)
        require(response, "outcome", "ok", f"append at {offset}")
        document, revision = response["document"], response["revision"]
        offset, appends = end, appends + 1
    return document, revision, appends


class StagedIngressTests(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        open_bundle(self.session)

    def tearDown(self):
        self.session.process.stdin.close()
        self.session.process.terminate()

    def test_single_open_still_refuses_more_than_65536_bytes(self):
        raw = b"//" + b"x" * 65536
        response = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                      "name": "too-big", "bytes": list(raw)})
        self.assertEqual(response.get("outcome"), "error", response)
        self.assertEqual((response.get("error") or {}).get("code"),
                         "PEP_SOURCE_BYTE_LIMIT")

    def test_chunked_ingress_reproduces_a_real_module_revision(self):
        # examples/pep_parser.pep is 96149 bytes, 1.47x the per-open cap.
        raw = (ROOT / "examples" / "pep_parser.pep").read_bytes()
        self.assertGreater(len(raw), WINDOW)
        document, revision, appends = ingest(self.session, raw)
        self.assertGreater(appends, 0)
        self.assertEqual(revision,
                         "sha256:" + hashlib.sha256(raw).hexdigest())

    def test_metadata_only_ingress_keeps_responses_small(self):
        # The same ingress without metadataOnly returns the AST on every
        # edit, which is what exceeded the response budget for large modules.
        raw = (ROOT / "examples" / "lexer_fragment.pep").read_bytes()
        document, revision, appends = ingest(self.session, raw,
                                             metadata_only=False)
        self.assertEqual(revision,
                         "sha256:" + hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
