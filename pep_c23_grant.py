"""Experimental trusted-host adapter for entry-bound native SourceBytes.

The host must obtain retained bytes and document identity from its session,
not from an untrusted tool or a second filesystem read. This adapter checks
the grant before code generation; it is not a session or tool-protocol API.
"""
from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class NativeSourceGrant:
    document: str
    revision: str
    source: bytes

    def __post_init__(self):
        if not isinstance(self.document, str) or not self.document:
            raise ValueError("Native source grant requires a retained document identity")
        if type(self.source) is not bytes or len(self.source) > 65536:
            raise ValueError("Native source grant requires immutable bytes within the 65536-byte cap")
        digest = "sha256:" + hashlib.sha256(self.source).hexdigest()
        if self.revision != digest:
            raise ValueError("Native source grant does not match the retained revision")

    @classmethod
    def bind(cls, target, retained_document, retained_bytes):
        """Bind an explicit target to the host's already retained bytes.

        Both target and retained_document are trusted host facts. Knowing a
        digest alone does not establish that a document is open in a session.
        """
        if not isinstance(target, dict) or target.get("sourceGrant") != {"mode": "entry-parameter"}:
            raise ValueError("Native source grant requires explicit entry-parameter authority")
        if target.get("document") != retained_document:
            raise ValueError("Native source grant does not match the retained document")
        return cls(retained_document, target.get("revision"), retained_bytes)

    def emit_entry_view(self):
        # Deliberately a disposable, deterministic proof artifact. It embeds
        # the selected bytes and is not a reusable session invocation carrier.
        if not self.source:
            return [], "(pep_source_bytes){nullptr, 0}"
        rows = [", ".join(f"0x{byte:02x}" for byte in self.source[i:i + 16])
                for i in range(0, len(self.source), 16)]
        return ["  static const unsigned char pep_granted_source[] = {",
                *(f"    {row}," for row in rows), "  };"], \
            "(pep_source_bytes){pep_granted_source, sizeof pep_granted_source}"
