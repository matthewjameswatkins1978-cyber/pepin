"""Independent native UTF-8 validity, scalar and seed diagnostic-offset gate.

Python's strict UTF-8 codec is the validity oracle. The seed's documented
offset policy differs from Python's exception offset: complete malformed
sequences report the first non-continuation byte, otherwise the lead byte.
The source of this policy is pep_ocaml.ml:invalid_utf8_offset and the
same rule in examples/pep_lexer.pep:utf8_check. No Pep compiler is mocked.
"""

import itertools
import os
import pathlib
import random
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "runtime" / "pep_text"


def seed_expected(raw):
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        lead = error.start
        byte = raw[lead]
        width = (2 if 0xC0 <= byte <= 0xDF else
                 3 if 0xE0 <= byte <= 0xEF else
                 4 if 0xF0 <= byte <= 0xF7 else 0)
        if width and len(raw) - lead >= width:
            for at in range(lead + 1, lead + width):
                if raw[at] & 0xC0 != 0x80:
                    return 1, at
        return 1, lead
    return 0, 999


def first_scalar_expected(raw):
    for width in range(1, min(len(raw), 4) + 1):
        try:
            decoded = raw[:width].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            continue
        if len(decoded) == 1:
            return width, ord(decoded)
    return 0, 0xFFFFFFFF


class NativeUtf8ParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compilers = [path for name in ("gcc", "clang")
                         if (path := shutil.which(name))]
        if not cls.compilers:
            raise unittest.SkipTest("No C23 compiler (GCC/Clang) available")
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.probes = []
        extra_flags = (["-fsanitize=undefined", "-fno-sanitize-recover=undefined"]
                       if os.environ.get("PEPIN_UTF8_UBSAN") == "1" else [])
        for i, compiler in enumerate(cls.compilers):
            exe = pathlib.Path(cls.temp.name) / f"probe_{i}.exe"
            proc = subprocess.run([
                compiler, "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                "-Werror", "-O2", *extra_flags, "-I", str(NATIVE),
                str(ROOT / "verification" / "lucy_utf8_probe.c"),
                str(NATIVE / "pep_utf8.c"), "-o", str(exe),
            ], capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                raise AssertionError(f"{compiler}: {proc.stderr}")
            cls.probes.append((compiler, exe))

    def check_vectors(self, vectors):
        mismatches = 0
        examples = []
        vectors = iter(vectors)
        while batch := list(itertools.islice(vectors, 8192)):
            expected = [seed_expected(raw) + first_scalar_expected(raw)
                        for raw in batch]
            payload = "".join(raw.hex() + "\n" for raw in batch)
            for compiler, exe in self.probes:
                proc = subprocess.run([str(exe)], input=payload, text=True,
                                      capture_output=True, timeout=30)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                lines = proc.stdout.splitlines()
                self.assertEqual(len(lines), len(batch))
                for raw, want, line in zip(batch, expected, lines):
                    actual = tuple(map(int, line.split()))
                    if actual != want:
                        mismatches += 1
                        if len(examples) < 8:
                            examples.append((compiler, raw.hex(), want, actual))
        self.assertEqual(mismatches, 0, f"first mismatches: {examples}")

    def test_seed_error_offset_and_precedence(self):
        # Complete invalid scalars point to the lead; a malformed continuation
        # in a complete sequence takes precedence, even after an invalid range.
        raw = [b"", b"a\x00z", b"\xe0\x9f\x80", b"\xed\xa0\x80",
               b"\xf4\x90\x80\x80", b"\xc0(", b"\xf5\x80(\x80",
               b"\xe0\x9f(", b"\xe0(\x80", b"\xf4\x90\x80(",
               b"\xf4\x90(", b"\xe2\x82", b"\xff", b"\xe2(\xa1"]
        expected = [(0, 999), (0, 999), (1, 0), (1, 0), (1, 0),
                    (1, 1), (1, 2), (1, 2), (1, 1), (1, 3),
                    (1, 0), (1, 0), (1, 0), (1, 1)]
        self.assertEqual([seed_expected(v) for v in raw], expected)
        self.check_vectors(raw + [b"\xc3\xa9\r\n" + v for v in raw])

    def test_all_one_and_two_byte_inputs(self):
        self.check_vectors(bytes(v) for width in (1, 2)
                           for v in itertools.product(range(256), repeat=width))

    def test_three_and_four_byte_range_and_continuation_boundaries(self):
        edge = (0, 0x7F, 0x80, 0x8F, 0x90, 0x9F, 0xA0, 0xBF, 0xC0, 0xFF)
        def vectors():
            for lead in range(0xE0, 0xF8):
                for second in range(256):
                    for third in edge:
                        yield bytes((lead, second, third))
                        if lead >= 0xF0:
                            for fourth in edge:
                                yield bytes((lead, second, third, fourth))
        self.check_vectors(vectors())

    def test_all_unicode_scalar_values(self):
        self.check_vectors(chr(cp).encode("utf-8") for cp in range(0x110000)
                           if not 0xD800 <= cp <= 0xDFFF)

    def test_mixed_sequences_and_offsets(self):
        rng = random.Random(20261121)
        fragments = (b"a", b"\x00", b"\r\n", "é".encode(), "😀".encode(),
                     b"\xff", b"\xe0\x80\x80", b"\xf4\x90\x80(", b"\xc0", b"\x80")
        def vectors():
            for _ in range(5000):
                yield b"".join(rng.choices(fragments, k=rng.randrange(9)))
        self.check_vectors(vectors())


if __name__ == "__main__":
    unittest.main()
