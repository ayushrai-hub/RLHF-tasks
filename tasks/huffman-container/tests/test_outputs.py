"""Verifier for Marrow Huffman, block, and container layers."""

import binascii
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

APP = Path(os.environ.get("MARROW_APP", "/app/marrow"))
SPEC = Path(os.environ.get("MARROW_SPEC", str(APP / "docs" / "spec.md")))
PROGRAMS = APP / "programs"
REFERENCE_CONTAINERS = Path(__file__).with_name("reference_containers")
CORPORA = ["poem.txt", "repeat.txt", "struct.txt", "mixed.bin", "empty.txt"]


@pytest.fixture(scope="module", autouse=True)
def build():
    """Compile the Marrow Java sources once before running verifier checks."""
    assert SPEC.exists(), f"Marrow spec not found at {SPEC}"
    srcs = sorted(str(p) for p in (APP / "src" / "marrow").glob("*.java"))
    r = subprocess.run(["javac", "-d", "out", *srcs], cwd=APP, text=True, capture_output=True)
    assert r.returncode == 0, "javac failed:\n" + r.stdout + r.stderr


def run(*args):
    """Run the Marrow CLI with captured stdout and stderr."""
    return subprocess.run(
        ["java", "-cp", "out", "marrow.Main", *args], cwd=APP, text=True, capture_output=True
    )


def tmp():
    """Create a temporary file path that the caller is responsible for removing."""
    f = tempfile.NamedTemporaryFile(delete=False)
    f.close()
    return f.name


def write_tmp(data):
    """Write bytes to a temporary file and return its path."""
    f = tempfile.NamedTemporaryFile(delete=False, mode="wb")
    f.write(data)
    f.close()
    return f.name


def huff_of(data):
    """Return the CLI Huffman report for an in-memory byte sequence."""
    path = write_tmp(data)
    try:
        r = run("huff", path)
        assert r.returncode == 0, r.stdout + r.stderr
        assert r.stderr == ""
        lines = r.stdout.splitlines()
        assert lines
        code_symbols = []
        for line in lines[:-1]:
            parts = line.split()
            assert len(parts) == 3
            assert parts[0] == "code"
            symbol = int(parts[1])
            length = int(parts[2])
            assert 0 <= symbol < 258
            assert length > 0
            code_symbols.append(symbol)
        count_parts = lines[-1].split()
        assert len(count_parts) == 2
        assert count_parts[0] == "count"
        assert int(count_parts[1]) == len(code_symbols)
        assert code_symbols == sorted(code_symbols)
        assert len(code_symbols) == len(set(code_symbols))
        return lines
    finally:
        os.unlink(path)


def inspect_fields(container_path):
    """Parse the CLI inspection report into a dictionary of header fields."""
    r = run("inspect", container_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stderr == ""
    fields = {}
    for line in r.stdout.splitlines():
        key, _, value = line.partition(" ")
        assert key and value
        assert key not in fields
        fields[key] = value
    assert list(fields) == [
        "magic",
        "flag",
        "original_size",
        "crc32",
        "container_size",
        "payload_size",
    ]
    return fields


def java_classpath(*entries):
    """Join classpath entries using the separator expected by the container."""
    return ":".join(str(e) for e in entries)


def assert_clean_marrow_failure(result):
    """Require a user-facing Marrow error without a Java exception trace."""
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("marrow: ")
    assert "Exception" not in result.stderr
    assert "Traceback" not in result.stderr
    assert "\tat " not in result.stderr


def parse_huff_report(lines):
    """Parse non-zero Huffman length lines into a symbol-to-length mapping."""
    lengths = {}
    count_line = None
    for line in lines:
        parts = line.split()
        if parts[0] == "code":
            lengths[int(parts[1])] = int(parts[2])
        elif parts[0] == "count":
            count_line = int(parts[1])
    assert count_line == len(lengths)
    return lengths


def reference_huffman_lengths(freq):
    """Compute Marrow Huffman lengths with the documented stable tie tags."""
    import heapq

    lengths = [0] * len(freq)
    heap = []
    nodes = []
    for symbol, weight in enumerate(freq):
        if weight > 0:
            index = len(nodes)
            nodes.append((symbol, -1, -1))
            heapq.heappush(heap, (weight, symbol, index))

    if not heap:
        return lengths
    if len(heap) == 1:
        lengths[nodes[heap[0][2]][0]] = 1
        return lengths

    next_internal_tag = len(freq)
    while len(heap) > 1:
        weight_a, _, index_a = heapq.heappop(heap)
        weight_b, _, index_b = heapq.heappop(heap)
        index = len(nodes)
        nodes.append((-1, index_a, index_b))
        heapq.heappush(heap, (weight_a + weight_b, next_internal_tag, index))
        next_internal_tag += 1

    def assign(index, depth):
        """Assign code lengths by walking the reference Huffman tree."""
        symbol, left, right = nodes[index]
        if symbol >= 0:
            lengths[symbol] = depth
        else:
            assign(left, depth + 1)
            assign(right, depth + 1)

    assign(heap[0][2], 0)
    return lengths


def reference_lz_tokens(data):
    """Build deterministic LZ77 tokens with the documented Marrow policy."""
    tokens = []
    i = 0
    while i < len(data):
        best_len = 0
        best_dist = 0
        max_len = min(258, len(data) - i)
        for dist in range(1, min(32768, i) + 1):
            start = i - dist
            length = 0
            while length < max_len and data[start + length] == data[i + length]:
                length += 1
            if length > best_len:
                best_len = length
                best_dist = dist
                if best_len == 258:
                    break
        if best_len >= 3:
            tokens.append(("MATCH", best_len, best_dist))
            i += best_len
        else:
            tokens.append(("LIT", data[i]))
            i += 1
    return tokens


def reference_canonical_codes(lengths):
    """Return canonical code values for a Marrow code-length table."""
    max_len = max(lengths, default=0)
    bl_count = [0] * (max_len + 1)
    for length in lengths:
        if length:
            bl_count[length] += 1

    next_code = [0] * (max_len + 1)
    code = 0
    for length in range(1, max_len + 1):
        code = (code + bl_count[length - 1]) << 1
        next_code[length] = code

    codes = [0] * len(lengths)
    for symbol, length in enumerate(lengths):
        if length:
            codes[symbol] = next_code[length]
            next_code[length] += 1
    return codes


class ReferenceBitWriter:
    """Write LSB-first fields and MSB-first Huffman codes for reference data."""

    def __init__(self):
        """Initialize an empty reference bit accumulator."""
        self.out = bytearray()
        self.acc = 0
        self.nbits = 0

    def write_lsb(self, value, count):
        """Append the low count bits of value in LSB-first order."""
        for bit in range(count):
            self.acc |= ((value >> bit) & 1) << self.nbits
            self.nbits += 1
            if self.nbits == 8:
                self.out.append(self.acc)
                self.acc = 0
                self.nbits = 0

    def write_code(self, code, length):
        """Append one canonical Huffman code in MSB-first order."""
        for shift in range(length - 1, -1, -1):
            self.write_lsb((code >> shift) & 1, 1)

    def finish(self):
        """Return the byte stream with a zero-padded final byte."""
        if self.nbits:
            self.out.append(self.acc)
        return bytes(self.out)


class ReferenceBitReader:
    """Read LSB-first fields from a reference bitstream."""

    def __init__(self, data, offset):
        """Initialize a reader at the byte offset inside data."""
        self.data = data
        self.pos = offset
        self.acc = 0
        self.nbits = 0

    def read(self, count):
        """Read count bits as an LSB-first integer."""
        while self.nbits < count:
            if self.pos >= len(self.data):
                raise ValueError("bitstream underrun")
            self.acc |= self.data[self.pos] << self.nbits
            self.pos += 1
            self.nbits += 8
        value = self.acc & ((1 << count) - 1)
        self.acc >>= count
        self.nbits -= count
        return value

    def read_bit(self):
        """Read a single bit."""
        return self.read(1)


def reference_lz_decode(tokens):
    """Decode reference LZ tokens into bytes."""
    out = bytearray()
    for token in tokens:
        if token[0] == "LIT":
            out.append(token[1])
            continue
        _, length, distance = token
        if length < 3 or length > 258 or distance < 1 or distance > 32768 or distance > len(out):
            raise ValueError("invalid match")
        start = len(out) - distance
        for index in range(length):
            out.append(out[start + index])
    return bytes(out)


def reference_encode_block(tokens):
    """Encode a token stream as a Marrow compressed block."""
    freq = [0] * 258
    for token in tokens:
        if token[0] == "LIT":
            freq[token[1]] += 1
        else:
            freq[257] += 1
    freq[256] += 1

    lengths = reference_huffman_lengths(freq)
    codes = reference_canonical_codes(lengths)
    writer = ReferenceBitWriter()
    for token in tokens:
        if token[0] == "LIT":
            symbol = token[1]
            writer.write_code(codes[symbol], lengths[symbol])
        else:
            _, length, distance = token
            writer.write_code(codes[257], lengths[257])
            writer.write_lsb(length - 3, 8)
            writer.write_lsb(distance - 1, 15)
    writer.write_code(codes[256], lengths[256])
    return bytes(lengths) + writer.finish()


def reference_decode_symbol(reader, table):
    """Read one symbol from canonical code table."""
    code = 0
    for length in range(1, table["max_len"] + 1):
        code = (code << 1) | reader.read_bit()
        symbol = table["by_code"].get((length, code))
        if symbol is not None:
            return symbol
    raise ValueError("invalid huffman code")


def reference_decoder_table(lengths):
    """Build a compact canonical decode table."""
    codes = reference_canonical_codes(lengths)
    return {
        "max_len": max(lengths, default=0),
        "by_code": {(length, codes[symbol]): symbol for symbol, length in enumerate(lengths) if length},
    }


def reference_decode_block(block):
    """Decode a Marrow compressed block with the verifier reference codec."""
    if len(block) < 258:
        raise ValueError("truncated block")
    lengths = list(block[:258])
    table = reference_decoder_table(lengths)
    reader = ReferenceBitReader(block, 258)
    tokens = []
    while True:
        symbol = reference_decode_symbol(reader, table)
        if symbol == 256:
            return reference_lz_decode(tokens)
        if symbol == 257:
            tokens.append(("MATCH", reader.read(8) + 3, reader.read(15) + 1))
        else:
            tokens.append(("LIT", symbol))


def reference_container(data):
    """Build a deterministic MRW1 container with the verifier reference codec."""
    block = reference_encode_block(reference_lz_tokens(data))
    if len(block) < len(data):
        flag = 1
        payload = block
    else:
        flag = 0
        payload = data
    header = b"MRW1" + bytes([flag]) + len(data).to_bytes(4, "big")
    header += (binascii.crc32(data) & 0xFFFFFFFF).to_bytes(4, "big")
    return header + payload


def reference_huffround_encoded_size(data):
    """Return the verifier reference byte count for huffround output."""
    freq = [0] * 258
    for value in data:
        freq[value] += 1
    freq[256] += 1
    lengths = reference_huffman_lengths(freq)
    codes = reference_canonical_codes(lengths)
    writer = ReferenceBitWriter()
    for value in data:
        writer.write_code(codes[value], lengths[value])
    writer.write_code(codes[256], lengths[256])
    return len(writer.finish())


def reference_decompress_container(blob):
    """Decode an MRW1 container with the verifier reference codec."""
    if len(blob) < 13:
        raise ValueError("short container")
    if blob[:4] != b"MRW1":
        raise ValueError("bad magic")
    flag = blob[4]
    size = int.from_bytes(blob[5:9], "big")
    crc = int.from_bytes(blob[9:13], "big")
    payload = blob[13:]
    if flag == 0:
        data = payload
    elif flag == 1:
        data = reference_decode_block(payload)
    else:
        raise ValueError("bad flag")
    if len(data) != size:
        raise ValueError("size mismatch")
    if binascii.crc32(data) & 0xFFFFFFFF != crc:
        raise ValueError("crc mismatch")
    return data


def container_blob(flag, original_size, crc, payload):
    """Construct a raw MRW1 blob for malformed-container checks."""
    return b"MRW1" + bytes([flag]) + original_size.to_bytes(4, "big") + crc.to_bytes(4, "big") + payload


def decompress_blob_result(blob):
    """Run decompression against a temporary container blob."""
    mar, out = tmp(), tmp()
    try:
        Path(mar).write_bytes(blob)
        return run("decompress", mar, out)
    finally:
        os.unlink(mar)
        os.unlink(out)


def decompress_blob_output(blob):
    """Run decompression against a temporary blob and return its output bytes."""
    mar, out = tmp(), tmp()
    try:
        Path(mar).write_bytes(blob)
        result = run("decompress", mar, out)
        if result.returncode == 0:
            assert result.stderr == ""
        data = Path(out).read_bytes() if result.returncode == 0 else b""
        return result, data
    finally:
        os.unlink(mar)
        os.unlink(out)


def inspect_blob_result(blob):
    """Run inspect against a temporary container blob."""
    mar = tmp()
    try:
        Path(mar).write_bytes(blob)
        return run("inspect", mar)
    finally:
        os.unlink(mar)


def test_huff_lengths_unique_tree():
    """Check deterministic Huffman lengths for a multi-symbol frequency tree."""
    assert huff_of(b"aaaabbcd") == [
        "code 97 1",
        "code 98 3",
        "code 99 3",
        "code 100 3",
        "code 256 3",
        "count 5",
    ]


def test_huff_two_symbols_each_one_bit_and_count():
    """Verify a two-symbol alphabet and the reported used-symbol count."""
    assert huff_of(b"aaaa") == ["code 97 1", "code 256 1", "count 2"]
    assert huff_of(b"") == ["code 256 1", "count 1"]
    out = huff_of(b"the quick brown fox")
    assert next(line for line in out if line.startswith("count ")) == "count 17"


def test_huffman_direct_empty_alphabet_and_single_symbol():
    """Exercise Huffman boundary alphabets without going through the CLI."""
    source = """
        import marrow.Huffman;
        import marrow.Symbols;

        public final class HuffmanHarness {
            private static int nonZeroCount(int[] values) {
                int count = 0;
                for (int v : values) {
                    if (v != 0) {
                        count++;
                    }
                }
                return count;
            }

            public static void main(String[] args) {
                int[] empty = Huffman.lengths(new int[Symbols.ALPHABET]);
                System.out.println("empty_count " + nonZeroCount(empty));

                int[] singleFreq = new int[Symbols.ALPHABET];
                singleFreq[42] = 9;
                int[] single = Huffman.lengths(singleFreq);
                System.out.println("single_len " + single[42]);
                System.out.println("single_count " + nonZeroCount(single));
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffmanHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffmanHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == ["empty_count 0", "single_len 1", "single_count 1"]


def test_huffman_internal_tie_tags_are_stable():
    """Pin equal-weight ordering when internal nodes compete with leaves."""
    source = """
        import marrow.Huffman;
        import marrow.Symbols;

        public final class HuffmanTieHarness {
            public static void main(String[] args) {
                int[] freq = new int[Symbols.ALPHABET];
                freq[10] = 1;
                freq[20] = 1;
                freq[30] = 2;
                freq[40] = 4;
                int[] lengths = Huffman.lengths(freq);
                System.out.println("lengths " + lengths[10] + " " + lengths[20]
                        + " " + lengths[30] + " " + lengths[40]);
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffmanTieHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffmanTieHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "lengths 3 3 2 1"


def test_huffman_full_alphabet_and_match_symbol_tie_ladders():
    """Compare difficult Huffman frequency sets with an independent reference."""
    full_freq = [0] * 258
    for symbol in range(256):
        full_freq[symbol] = 1
    full_freq[256] = 1
    full_expected = {
        symbol: length for symbol, length in enumerate(reference_huffman_lengths(full_freq)) if length
    }
    assert parse_huff_report(huff_of(bytes(range(256)))) == full_expected

    source = """
        import marrow.Huffman;
        import marrow.Symbols;

        public final class HuffmanStressHarness {
            private static void emit(String name, int[] freq) {
                int[] lengths = Huffman.lengths(freq);
                StringBuilder sb = new StringBuilder(name);
                for (int i = 0; i < lengths.length; i++) {
                    if (lengths[i] != 0) {
                        sb.append(' ').append(i).append(':').append(lengths[i]);
                    }
                }
                System.out.println(sb);
            }

            public static void main(String[] args) {
                int[] ties = new int[Symbols.ALPHABET];
                int[] tieSymbols = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 128, 129, 130, 255,
                        Symbols.EOB, Symbols.MATCH};
                for (int s : tieSymbols) {
                    ties[s] = 1;
                }
                int[][] weighted = {
                    {10, 2}, {11, 2}, {12, 3}, {13, 3}, {14, 5},
                    {15, 8}, {16, 13}, {17, 21}, {18, 34}, {19, 55}, {20, 89},
                };
                for (int[] pair : weighted) {
                    ties[pair[0]] = pair[1];
                }
                emit("ties", ties);

                int[] sparse = new int[Symbols.ALPHABET];
                int[][] sparsePairs = {
                    {3, 17}, {7, 17}, {11, 17}, {19, 17}, {23, 17},
                    {29, 34}, {31, 34}, {37, 68}, {41, 68}, {43, 136},
                    {Symbols.EOB, 17}, {Symbols.MATCH, 17},
                };
                for (int[] pair : sparsePairs) {
                    sparse[pair[0]] = pair[1];
                }
                emit("sparse", sparse);

                int[] internal = new int[Symbols.ALPHABET];
                int[][] internalPairs = {
                    {0, 1}, {1, 1}, {2, 1}, {3, 1}, {4, 2}, {5, 2},
                    {6, 4}, {7, 4}, {128, 8}, {255, 8},
                    {Symbols.EOB, 1}, {Symbols.MATCH, 1},
                };
                for (int[] pair : internalPairs) {
                    internal[pair[0]] = pair[1];
                }
                emit("internal", internal);
            }
        }
    """
    cases = {
        "ties": {
            **{symbol: 1 for symbol in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 128, 129, 130, 255, 256, 257]},
            **{10: 2, 11: 2, 12: 3, 13: 3, 14: 5, 15: 8, 16: 13, 17: 21, 18: 34, 19: 55, 20: 89},
        },
        "sparse": {
            3: 17,
            7: 17,
            11: 17,
            19: 17,
            23: 17,
            29: 34,
            31: 34,
            37: 68,
            41: 68,
            43: 136,
            256: 17,
            257: 17,
        },
        "internal": {
            0: 1,
            1: 1,
            2: 1,
            3: 1,
            4: 2,
            5: 2,
            6: 4,
            7: 4,
            128: 8,
            255: 8,
            256: 1,
            257: 1,
        },
    }
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffmanStressHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffmanStressHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    for line in r.stdout.splitlines():
        name, *entries = line.split()
        observed = {int(entry.split(":")[0]): int(entry.split(":")[1]) for entry in entries}
        freq = [0] * 258
        for symbol, weight in cases[name].items():
            freq[symbol] = weight
        expected = {
            symbol: length for symbol, length in enumerate(reference_huffman_lengths(freq)) if length
        }
        assert observed == expected


def test_huffman_large_frequency_weights_are_stable():
    """Compare very large Huffman weights with the independent reference."""
    weights = {
        0: 2_147_483_647,
        1: 2_147_483_646,
        2: 8192,
        3: 8192,
        128: 17,
        255: 17,
        256: 1,
        257: 1,
    }
    source = """
        import marrow.Huffman;
        import marrow.Symbols;

        public final class HuffmanLargeWeightHarness {
            public static void main(String[] args) {
                int[] freq = new int[Symbols.ALPHABET];
                freq[0] = Integer.MAX_VALUE;
                freq[1] = Integer.MAX_VALUE - 1;
                freq[2] = 8192;
                freq[3] = 8192;
                freq[128] = 17;
                freq[255] = 17;
                freq[Symbols.EOB] = 1;
                freq[Symbols.MATCH] = 1;
                int[] lengths = Huffman.lengths(freq);
                StringBuilder sb = new StringBuilder("large");
                for (int i = 0; i < lengths.length; i++) {
                    if (lengths[i] != 0) {
                        sb.append(' ').append(i).append(':').append(lengths[i]);
                    }
                }
                System.out.println(sb);
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffmanLargeWeightHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffmanLargeWeightHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    name, *entries = r.stdout.strip().split()
    assert name == "large"
    observed = {int(entry.split(":")[0]): int(entry.split(":")[1]) for entry in entries}
    freq = [0] * 258
    for symbol, weight in weights.items():
        freq[symbol] = weight
    expected = {
        symbol: length for symbol, length in enumerate(reference_huffman_lengths(freq)) if length
    }
    assert observed == expected


def test_huffcoder_canonical_codes_and_msb_first_writes():
    """Validate canonical code values, MSB-first emission, and decoding."""
    source = """
        import marrow.HuffCoder;
        import marrow.Symbols;

        public final class HuffCoderHarness {
            private static String hex(byte[] data) {
                StringBuilder sb = new StringBuilder();
                for (byte b : data) {
                    sb.append(String.format("%02x", b & 0xFF));
                }
                return sb.toString();
            }

            public static void main(String[] args) {
                int[] lengths = new int[Symbols.ALPHABET];
                lengths[5] = 1;
                lengths[7] = 3;
                lengths[9] = 3;
                lengths[Symbols.EOB] = 2;

                long[] codes = HuffCoder.canonicalCodes(lengths);
                System.out.println("codes " + codes[5] + " " + codes[7] + " "
                        + codes[9] + " " + codes[Symbols.EOB]);

                int[] symbols = {7, 9, 5};
                byte[] encoded = HuffCoder.encode(symbols, lengths);
                System.out.println("hex " + hex(encoded));

                int[] decoded = HuffCoder.decodeUntilEob(encoded, 0, lengths);
                System.out.println("decoded " + decoded.length + " " + decoded[0]
                        + " " + decoded[1] + " " + decoded[2]);
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffCoderHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffCoderHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == ["codes 0 6 7 2", "hex bb00", "decoded 3 7 9 5"]


def test_huffcoder_sparse_lengths_unused_symbols_and_missing_eob_failure():
    """Stress sparse canonical tables and clean failure for unusable symbols."""
    source = """
        import marrow.HuffCoder;
        import marrow.MarrowError;
        import marrow.Symbols;

        public final class HuffCoderSparseHarness {
            private static String hex(byte[] data) {
                StringBuilder sb = new StringBuilder();
                for (byte b : data) {
                    sb.append(String.format("%02x", b & 0xFF));
                }
                return sb.toString();
            }

            public static void main(String[] args) {
                int[] lengths = new int[Symbols.ALPHABET];
                lengths[2] = 2;
                lengths[4] = 4;
                lengths[99] = 4;
                lengths[200] = 3;
                lengths[Symbols.EOB] = 2;
                long[] codes = HuffCoder.canonicalCodes(lengths);
                System.out.println("codes " + codes[2] + " " + codes[4] + " "
                        + codes[99] + " " + codes[200] + " " + codes[Symbols.EOB]);

                int[] symbols = {200, 4, 99, 2, 200};
                byte[] encoded = HuffCoder.encode(symbols, lengths);
                System.out.println("encoded " + hex(encoded));
                int[] decoded = HuffCoder.decodeUntilEob(encoded, 0, lengths);
                System.out.println("decoded " + decoded.length + " " + decoded[0] + " "
                        + decoded[1] + " " + decoded[2] + " " + decoded[3] + " " + decoded[4]);

                try {
                    HuffCoder.writeSymbol(new marrow.BitIo.Writer(), codes, lengths, 5);
                    System.out.println("unused not rejected");
                } catch (MarrowError e) {
                    System.out.println("unused rejected");
                }

                int[] missingEob = new int[Symbols.ALPHABET];
                missingEob[65] = 1;
                try {
                    HuffCoder.decodeUntilEob(new byte[] {0}, 0, missingEob);
                    System.out.println("missing_eob not rejected");
                } catch (MarrowError e) {
                    System.out.println("missing_eob rejected");
                }
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffCoderSparseHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffCoderSparseHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == [
        "codes 0 10 11 4 1",
        "encoded a92602",
        "decoded 5 200 4 99 2 200",
        "unused rejected",
        "missing_eob rejected",
    ]


def test_huffcoder_empty_stream_and_zero_table_failure():
    """Check empty EOB streams and reject an all-zero decode table."""
    source = """
        import marrow.HuffCoder;
        import marrow.MarrowError;
        import marrow.Symbols;

        public final class HuffCoderEmptyHarness {
            private static String hex(byte[] data) {
                StringBuilder sb = new StringBuilder();
                for (byte b : data) {
                    sb.append(String.format("%02x", b & 0xFF));
                }
                return sb.toString();
            }

            public static void main(String[] args) {
                int[] onlyEob = new int[Symbols.ALPHABET];
                onlyEob[Symbols.EOB] = 1;
                byte[] encoded = HuffCoder.encode(new int[0], onlyEob);
                int[] decoded = HuffCoder.decodeUntilEob(encoded, 0, onlyEob);
                System.out.println("empty " + hex(encoded) + " " + decoded.length);

                try {
                    HuffCoder.decodeUntilEob(new byte[] {0}, 0, new int[Symbols.ALPHABET]);
                    System.out.println("zero_table not rejected");
                } catch (MarrowError e) {
                    System.out.println("zero_table rejected");
                }
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffCoderEmptyHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffCoderEmptyHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == ["empty 00 0", "zero_table rejected"]


def test_huffcoder_rejects_invalid_codeword_bits():
    """Reject bit patterns that do not map to any canonical code."""
    source = """
        import marrow.HuffCoder;
        import marrow.MarrowError;
        import marrow.Symbols;

        public final class HuffCoderInvalidCodeHarness {
            public static void main(String[] args) {
                int[] lengths = new int[Symbols.ALPHABET];
                lengths[65] = 2;
                lengths[Symbols.EOB] = 2;
                try {
                    HuffCoder.decodeUntilEob(new byte[] {3}, 0, lengths);
                    System.out.println("invalid not rejected");
                } catch (MarrowError e) {
                    System.out.println("invalid rejected");
                }
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffCoderInvalidCodeHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffCoderInvalidCodeHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "invalid rejected"


def test_huffcoder_rejects_unusable_canonical_length_tables():
    """Reject canonical length tables that cannot form a usable prefix code."""
    source = """
        import marrow.HuffCoder;
        import marrow.MarrowError;
        import marrow.Symbols;

        public final class HuffCoderBadTableHarness {
            public static void main(String[] args) {
                int[] oversubscribed = new int[Symbols.ALPHABET];
                oversubscribed[65] = 1;
                oversubscribed[66] = 1;
                oversubscribed[Symbols.EOB] = 1;

                try {
                    HuffCoder.canonicalCodes(oversubscribed);
                    System.out.println("codes not rejected");
                } catch (MarrowError e) {
                    System.out.println("codes rejected");
                }

                try {
                    HuffCoder.decodeUntilEob(new byte[] {0}, 0, oversubscribed);
                    System.out.println("decode not rejected");
                } catch (MarrowError e) {
                    System.out.println("decode rejected");
                }
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffCoderBadTableHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffCoderBadTableHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == ["codes rejected", "decode rejected"]


def test_huffcoder_long_canonical_codes_and_offset_decode():
    """Decode valid long canonical codes from a nonzero byte offset."""
    source = """
        import marrow.HuffCoder;
        import marrow.Symbols;

        public final class HuffCoderLongCodeHarness {
            private static String hex(byte[] data) {
                StringBuilder sb = new StringBuilder();
                for (byte b : data) {
                    sb.append(String.format("%02x", b & 0xFF));
                }
                return sb.toString();
            }

            public static void main(String[] args) {
                int[] lengths = new int[Symbols.ALPHABET];
                lengths[65] = 1;
                lengths[66] = 63;
                lengths[Symbols.EOB] = 63;
                long[] codes = HuffCoder.canonicalCodes(lengths);
                byte[] encoded = HuffCoder.encode(new int[] {65, 66}, lengths);
                byte[] framed = new byte[encoded.length + 5];
                for (int i = 0; i < 5; i++) {
                    framed[i] = (byte) (0xC0 + i);
                }
                System.arraycopy(encoded, 0, framed, 5, encoded.length);
                int[] decoded = HuffCoder.decodeUntilEob(framed, 5, lengths);
                System.out.println("codes " + codes[65] + " " + codes[66]
                        + " " + codes[Symbols.EOB]);
                System.out.println("encoded_len " + encoded.length + " hex " + hex(encoded));
                System.out.println("decoded " + decoded.length + " " + decoded[0]
                        + " " + decoded[1]);
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffCoderLongCodeHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffCoderLongCodeHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == [
        "codes 0 4611686018427387904 4611686018427387905",
        "encoded_len 16 hex 02000000000000000100000000000040",
        "decoded 2 65 66",
    ]


def test_huffcoder_dense_high_symbol_ordering_and_payload_bits():
    """Validate canonical order and bit emission for high-numbered symbols."""
    lengths = [0] * 258
    active = [0, 1, 2, 127, 128, 254, 255, 256, 257]
    for symbol in active:
        lengths[symbol] = 4
    symbols = [257, 255, 128, 0, 254, 1]
    codes = reference_canonical_codes(lengths)
    writer = ReferenceBitWriter()
    for symbol in symbols:
        writer.write_code(codes[symbol], lengths[symbol])
    writer.write_code(codes[256], lengths[256])
    expected_hex = writer.finish().hex()

    source = """
        import marrow.HuffCoder;
        import marrow.Symbols;

        public final class HuffCoderDenseHarness {
            private static String hex(byte[] data) {
                StringBuilder sb = new StringBuilder();
                for (byte b : data) {
                    sb.append(String.format("%02x", b & 0xFF));
                }
                return sb.toString();
            }

            public static void main(String[] args) {
                int[] lengths = new int[Symbols.ALPHABET];
                int[] active = {0, 1, 2, 127, 128, 254, 255, Symbols.EOB, Symbols.MATCH};
                for (int symbol : active) {
                    lengths[symbol] = 4;
                }
                long[] codes = HuffCoder.canonicalCodes(lengths);
                System.out.println("codes " + codes[0] + " " + codes[128] + " "
                        + codes[255] + " " + codes[Symbols.EOB] + " " + codes[Symbols.MATCH]);

                int[] symbols = {Symbols.MATCH, 255, 128, 0, 254, 1};
                byte[] encoded = HuffCoder.encode(symbols, lengths);
                System.out.println("hex " + hex(encoded));

                int[] decoded = HuffCoder.decodeUntilEob(encoded, 0, lengths);
                StringBuilder out = new StringBuilder("decoded " + decoded.length);
                for (int value : decoded) {
                    out.append(' ').append(value);
                }
                System.out.println(out);
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "HuffCoderDenseHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "HuffCoderDenseHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == [
        f"codes {codes[0]} {codes[128]} {codes[255]} {codes[256]} {codes[257]}",
        f"hex {expected_hex}",
        "decoded 6 257 255 128 0 254 1",
    ]


def test_blockcodec_length_table_eob_and_match_payloads():
    """Inspect block headers, EOB handling, match payload bits, and decode."""
    source = """
        import java.util.ArrayList;
        import java.util.List;
        import marrow.BitIo;
        import marrow.BlockCodec;
        import marrow.HuffCoder;
        import marrow.Symbols;
        import marrow.Token;

        public final class BlockCodecHarness {
            private static String hex(byte[] data) {
                StringBuilder sb = new StringBuilder();
                for (byte b : data) {
                    sb.append(String.format("%02x", b & 0xFF));
                }
                return sb.toString();
            }

            public static void main(String[] args) {
                byte[] emptyBlock = BlockCodec.encodeBlock(new ArrayList<Token>());
                System.out.println("empty_len " + emptyBlock.length);
                System.out.println("empty_eob_len " + (emptyBlock[Symbols.EOB] & 0xFF));
                System.out.println("empty_decoded_len " + BlockCodec.decodeBlock(emptyBlock, 0).length);

                List<Token> tokens = new ArrayList<>();
                tokens.add(Token.literal(65));
                tokens.add(Token.match(5, 1));
                byte[] block = BlockCodec.encodeBlock(tokens);
                byte[] decoded = BlockCodec.decodeBlock(block, 0);
                System.out.println("match_len " + block.length);
                System.out.println("match_lengths " + (block[65] & 0xFF) + " "
                        + (block[Symbols.MATCH] & 0xFF) + " " + (block[Symbols.EOB] & 0xFF));
                System.out.println("match_decoded " + decoded.length + " " + hex(decoded));

                List<Token> edgeTokens = new ArrayList<>();
                edgeTokens.add(Token.literal(66));
                edgeTokens.add(Token.match(Symbols.MAX_MATCH, Symbols.WINDOW));
                byte[] edgeBlock = BlockCodec.encodeBlock(edgeTokens);
                int[] edgeLengths = new int[Symbols.ALPHABET];
                for (int i = 0; i < Symbols.ALPHABET; i++) {
                    edgeLengths[i] = edgeBlock[i] & 0xFF;
                }
                HuffCoder.Decoder edgeDecoder = new HuffCoder.Decoder(edgeLengths);
                BitIo.Reader edgeReader = new BitIo.Reader(edgeBlock, Symbols.ALPHABET);
                int edgeLiteral = edgeDecoder.read(edgeReader);
                int edgeMatch = edgeDecoder.read(edgeReader);
                int rawLength = edgeReader.read(Symbols.LEN_BITS);
                int rawDistance = edgeReader.read(Symbols.DIST_BITS);
                int edgeEob = edgeDecoder.read(edgeReader);
                System.out.println("edge_symbols " + edgeLiteral + " " + edgeMatch + " " + edgeEob);
                System.out.println("edge_raw " + rawLength + " " + rawDistance);

                byte[] manualBlock = new byte[Symbols.ALPHABET + 1];
                manualBlock[66] = 1;
                manualBlock[Symbols.EOB] = 1;
                manualBlock[Symbols.ALPHABET] = 0x02;
                byte[] manualDecoded = BlockCodec.decodeBlock(manualBlock, 0);
                System.out.println("manual_decoded " + manualDecoded.length + " " + hex(manualDecoded));
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "BlockCodecHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "BlockCodecHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == [
        "empty_len 259",
        "empty_eob_len 1",
        "empty_decoded_len 0",
        "match_len 262",
        "match_lengths 2 1 2",
        "match_decoded 6 414141414141",
        "edge_symbols 66 257 256",
        "edge_raw 255 32767",
        "manual_decoded 1 42",
    ]


def test_blockcodec_encoded_block_matches_reference_bytes():
    """Compare Java block bytes with the independent reference block encoder."""
    tokens = [
        ("LIT", 65),
        ("LIT", 66),
        ("MATCH", 6, 2),
        ("LIT", 255),
        ("LIT", 0),
        ("MATCH", 3, 5),
    ]
    expected_block = reference_encode_block(tokens)
    expected_decoded = reference_lz_decode(tokens)
    source = """
        import java.util.ArrayList;
        import java.util.List;
        import marrow.BlockCodec;
        import marrow.Token;

        public final class BlockExactHarness {
            private static String hex(byte[] data) {
                StringBuilder sb = new StringBuilder();
                for (byte b : data) {
                    sb.append(String.format("%02x", b & 0xFF));
                }
                return sb.toString();
            }

            public static void main(String[] args) {
                List<Token> tokens = new ArrayList<>();
                tokens.add(Token.literal(65));
                tokens.add(Token.literal(66));
                tokens.add(Token.match(6, 2));
                tokens.add(Token.literal(255));
                tokens.add(Token.literal(0));
                tokens.add(Token.match(3, 5));

                byte[] block = BlockCodec.encodeBlock(tokens);
                byte[] decoded = BlockCodec.decodeBlock(block, 0);
                System.out.println("block " + hex(block));
                System.out.println("decoded " + hex(decoded));
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "BlockExactHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "BlockExactHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == [
        f"block {expected_block.hex()}",
        f"decoded {expected_decoded.hex()}",
    ]


def test_blockcodec_decodes_offset_manual_multi_match_blocks():
    """Decode a hand-built block from a non-zero offset with multiple matches."""
    source = """
        import marrow.BitIo;
        import marrow.BlockCodec;
        import marrow.HuffCoder;
        import marrow.Symbols;

        public final class BlockOffsetHarness {
            private static String hex(byte[] data) {
                StringBuilder sb = new StringBuilder();
                for (byte b : data) {
                    sb.append(String.format("%02x", b & 0xFF));
                }
                return sb.toString();
            }

            private static void writeSymbol(BitIo.Writer writer, long[] codes, int[] lengths, int symbol) {
                HuffCoder.writeSymbol(writer, codes, lengths, symbol);
            }

            public static void main(String[] args) {
                int[] lengths = new int[Symbols.ALPHABET];
                lengths[65] = 2;
                lengths[66] = 2;
                lengths[67] = 3;
                lengths[Symbols.EOB] = 3;
                lengths[Symbols.MATCH] = 2;
                long[] codes = HuffCoder.canonicalCodes(lengths);
                BitIo.Writer writer = new BitIo.Writer();
                writeSymbol(writer, codes, lengths, 65);
                writeSymbol(writer, codes, lengths, 66);
                writeSymbol(writer, codes, lengths, Symbols.MATCH);
                writer.write(4 - Symbols.MIN_MATCH, Symbols.LEN_BITS);
                writer.write(2 - 1, Symbols.DIST_BITS);
                writeSymbol(writer, codes, lengths, 67);
                writeSymbol(writer, codes, lengths, Symbols.MATCH);
                writer.write(5 - Symbols.MIN_MATCH, Symbols.LEN_BITS);
                writer.write(3 - 1, Symbols.DIST_BITS);
                writeSymbol(writer, codes, lengths, Symbols.EOB);

                byte[] bits = writer.finish();
                byte[] block = new byte[Symbols.ALPHABET + bits.length];
                for (int i = 0; i < Symbols.ALPHABET; i++) {
                    block[i] = (byte) lengths[i];
                }
                System.arraycopy(bits, 0, block, Symbols.ALPHABET, bits.length);

                byte[] framed = new byte[block.length + 7];
                for (int i = 0; i < 7; i++) {
                    framed[i] = (byte) (0xA0 + i);
                }
                System.arraycopy(block, 0, framed, 7, block.length);

                byte[] decoded = BlockCodec.decodeBlock(framed, 7);
                System.out.println("bits " + hex(bits));
                System.out.println("decoded " + decoded.length + " " + hex(decoded));
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "BlockOffsetHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "BlockOffsetHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == [
        "bits 584000600908000e",
        "decoded 12 414241424142434142434142",
    ]


def test_blockcodec_roundtrips_maximum_distance_match():
    """Round-trip a block containing a match at the largest legal distance."""
    source = """
        import java.util.ArrayList;
        import java.util.List;
        import marrow.BlockCodec;
        import marrow.Symbols;
        import marrow.Token;

        public final class BlockMaxDistanceHarness {
            public static void main(String[] args) {
                List<Token> tokens = new ArrayList<>();
                for (int i = 0; i < Symbols.WINDOW; i++) {
                    tokens.add(Token.literal((i & 1) == 0 ? 65 : 66));
                }
                tokens.add(Token.match(Symbols.MAX_MATCH, Symbols.WINDOW));

                byte[] block = BlockCodec.encodeBlock(tokens);
                byte[] decoded = BlockCodec.decodeBlock(block, 0);
                System.out.println("lengths " + (block[65] & 0xFF) + " "
                        + (block[66] & 0xFF) + " " + (block[Symbols.MATCH] & 0xFF)
                        + " " + (block[Symbols.EOB] & 0xFF));
                System.out.println("decoded " + decoded.length + " " + (decoded[0] & 0xFF)
                        + " " + (decoded[1] & 0xFF) + " "
                        + (decoded[Symbols.WINDOW - 1] & 0xFF) + " "
                        + (decoded[Symbols.WINDOW] & 0xFF) + " "
                        + (decoded[decoded.length - 1] & 0xFF));
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "BlockMaxDistanceHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "BlockMaxDistanceHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == [
        "lengths 2 1 3 3",
        "decoded 33026 65 66 66 65 66",
    ]


def test_blockcodec_rejects_data_after_end_of_block():
    """Reject compressed blocks with nonzero padding or bytes after EOB."""
    good = reference_encode_block([("LIT", 65)])
    source = """
        import marrow.BlockCodec;
        import marrow.MarrowError;
        import java.util.Arrays;

        public final class BlockTrailingHarness {
            private static byte[] fromHex(String hex) {
                byte[] out = new byte[hex.length() / 2];
                for (int i = 0; i < out.length; i++) {
                    out[i] = (byte) Integer.parseInt(hex.substring(i * 2, i * 2 + 2), 16);
                }
                return out;
            }

            private static void check(String label, byte[] block) {
                try {
                    BlockCodec.decodeBlock(block, 0);
                    System.out.println(label + " not rejected");
                } catch (MarrowError e) {
                    System.out.println(label + " rejected");
                }
            }

            public static void main(String[] args) {
                byte[] good = fromHex(args[0]);
                byte[] badPadding = Arrays.copyOf(good, good.length);
                badPadding[badPadding.length - 1] |= (byte) 0x80;
                check("padding", badPadding);
                check("zero_byte", fromHex(args[0] + "00"));
                check("nonzero_byte", fromHex(args[0] + "ff"));
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "BlockTrailingHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "BlockTrailingHarness", good.hex()],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == [
        "padding rejected",
        "zero_byte rejected",
        "nonzero_byte rejected",
    ]


def test_blockcodec_rejects_trailing_data_at_nonzero_offset():
    """Reject bytes after EOB when the block starts at a nonzero offset."""
    good = reference_encode_block([("LIT", 65), ("MATCH", 8, 1)])
    source = """
        import marrow.BlockCodec;
        import marrow.MarrowError;

        public final class BlockOffsetTrailingHarness {
            private static byte[] fromHex(String hex) {
                byte[] out = new byte[hex.length() / 2];
                for (int i = 0; i < out.length; i++) {
                    out[i] = (byte) Integer.parseInt(hex.substring(i * 2, i * 2 + 2), 16);
                }
                return out;
            }

            private static byte[] frame(byte[] block, boolean extra) {
                byte[] framed = new byte[11 + block.length + (extra ? 1 : 0)];
                for (int i = 0; i < 11; i++) {
                    framed[i] = (byte) (0x50 + i);
                }
                System.arraycopy(block, 0, framed, 11, block.length);
                if (extra) {
                    framed[framed.length - 1] = 0;
                }
                return framed;
            }

            public static void main(String[] args) {
                byte[] good = fromHex(args[0]);
                byte[] decoded = BlockCodec.decodeBlock(frame(good, false), 11);
                System.out.println("decoded " + decoded.length + " " + (decoded[0] & 0xFF)
                        + " " + (decoded[decoded.length - 1] & 0xFF));
                try {
                    BlockCodec.decodeBlock(frame(good, true), 11);
                    System.out.println("trailing not rejected");
                } catch (MarrowError e) {
                    System.out.println("trailing rejected");
                }
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "BlockOffsetTrailingHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "BlockOffsetTrailingHarness", good.hex()],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == ["decoded 9 65 65", "trailing rejected"]


def test_blockcodec_rejects_truncated_header_at_nonzero_offset():
    """Reject a compressed block whose length table is truncated after an offset."""
    source = """
        import marrow.BlockCodec;
        import marrow.MarrowError;
        import marrow.Symbols;

        public final class BlockTruncatedOffsetHarness {
            public static void main(String[] args) {
                byte[] framed = new byte[Symbols.ALPHABET + 6];
                try {
                    BlockCodec.decodeBlock(framed, 7);
                    System.out.println("truncated not rejected");
                } catch (MarrowError e) {
                    System.out.println("truncated rejected");
                }
            }
        }
    """
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "BlockTruncatedOffsetHarness.java"
        harness.write_text(source)
        c = subprocess.run(
            ["javac", "-cp", "out", "-d", td, str(harness)],
            cwd=APP,
            text=True,
            capture_output=True,
        )
        assert c.returncode == 0, c.stdout + c.stderr
        r = subprocess.run(
            ["java", "-cp", java_classpath(APP / "out", td), "BlockTruncatedOffsetHarness"],
            cwd=APP,
            text=True,
            capture_output=True,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "truncated rejected"


@pytest.mark.parametrize(
    "name,size",
    [("poem.txt", 4680), ("repeat.txt", 1801), ("struct.txt", 4680), ("mixed.bin", 2048), ("empty.txt", 0)],
)
def test_huffround_roundtrips(name, size):
    """Round-trip raw Huffman streams for each corpus input."""
    r = run("huffround", str(PROGRAMS / name))
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stderr == ""
    data = (PROGRAMS / name).read_bytes()
    assert r.stdout.splitlines() == [
        f"ok symbols={size} bytes={reference_huffround_encoded_size(data)}"
    ]


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"A",
        bytes(range(256)),
        (b"canonical-huff" * 31) + bytes([0, 255, 128, 127]),
    ],
    ids=["empty", "single", "full-byte-range", "mixed-repeated-binary"],
)
def test_huffround_exact_symbol_and_byte_counts_are_quiet(data):
    """Require huffround to report exact symbol and encoded-byte counts."""
    src = write_tmp(data)
    try:
        result = run("huffround", src)
    finally:
        os.unlink(src)

    expected = f"ok symbols={len(data)} bytes={reference_huffround_encoded_size(data)}"
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.splitlines() == [expected]


def test_successful_public_commands_are_quiet_on_stderr():
    """Require successful public entropy and container commands to use stdout only."""
    src = PROGRAMS / "repeat.txt"
    mar, out = tmp(), tmp()
    try:
        huff = run("huff", str(src))
        assert huff.returncode == 0, huff.stdout + huff.stderr
        assert huff.stderr == ""
        assert huff.stdout.startswith("code ")

        huffround = run("huffround", str(src))
        assert huffround.returncode == 0, huffround.stdout + huffround.stderr
        assert huffround.stderr == ""
        assert huffround.stdout.startswith("ok symbols=")

        compress = run("compress", str(src), mar)
        assert compress.returncode == 0, compress.stdout + compress.stderr
        assert compress.stderr == ""
        assert compress.stdout.startswith("compressed ")

        inspect = run("inspect", mar)
        assert inspect.returncode == 0, inspect.stdout + inspect.stderr
        assert inspect.stderr == ""
        assert inspect.stdout.splitlines()[0] == "magic MRW1"

        decompress = run("decompress", mar, out)
        assert decompress.returncode == 0, decompress.stdout + decompress.stderr
        assert decompress.stderr == ""
        assert decompress.stdout.startswith("decompressed ")
        assert Path(out).read_bytes() == src.read_bytes()
    finally:
        os.unlink(mar)
        os.unlink(out)


@pytest.mark.parametrize("name", CORPORA)
def test_roundtrip_is_lossless(name):
    """Compress and decompress every corpus file without byte changes."""
    src = PROGRAMS / name
    mar, out = tmp(), tmp()
    try:
        c = run("compress", str(src), mar)
        assert c.returncode == 0, c.stdout + c.stderr
        assert c.stderr == ""
        assert c.stdout.splitlines() == [
            f"compressed {src.stat().st_size} -> {Path(mar).stat().st_size}"
        ]
        d = run("decompress", mar, out)
        assert d.returncode == 0, d.stdout + d.stderr
        assert d.stderr == ""
        assert d.stdout.splitlines() == [
            f"decompressed {Path(mar).stat().st_size} -> {src.stat().st_size}"
        ]
        assert Path(out).read_bytes() == src.read_bytes()
    finally:
        os.unlink(mar)
        os.unlink(out)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"A",
        b"A" * 520,
        (b"ABCDXYZ" * 80) + b"ABCDXYQ" + bytes(range(32)),
        bytes(range(256)) + bytes(range(128)) + b"tail",
        b"abcD" + (b"abcE" * 64) + b"ZabcD",
        (bytes([0, 255, 0, 255, 1, 254]) * 90) + bytes([0, 255, 0, 255, 2]),
        bytes((i * 37 + 19) & 0xFF for i in range(1024)),
        (b"1234567890abcdef" * 40) + b"1234567890abcdeg" + bytes(range(64)),
    ],
    ids=[
        "empty",
        "single-byte",
        "max-match-run",
        "branching-periodic-tail",
        "binary-prefix-repeat",
        "distant-longer-candidate",
        "high-byte-periodic-tail",
        "deterministic-incompressible-stride",
        "near-tie-long-suffix",
    ],
)
def test_generated_reference_codec_interoperability(data):
    """Cross-check Java containers against an independent reference codec."""
    src, java_mar, out = write_tmp(data), tmp(), tmp()
    ref_blob = reference_container(data)
    ref_mar = write_tmp(ref_blob)
    try:
        java_decompress_ref = run("decompress", ref_mar, out)
        assert java_decompress_ref.returncode == 0, java_decompress_ref.stdout + java_decompress_ref.stderr
        assert java_decompress_ref.stderr == ""
        assert java_decompress_ref.stdout.splitlines() == [
            f"decompressed {len(ref_blob)} -> {len(data)}"
        ]
        assert Path(out).read_bytes() == data

        java_compress = run("compress", src, java_mar)
        assert java_compress.returncode == 0, java_compress.stdout + java_compress.stderr
        assert java_compress.stderr == ""
        java_blob = Path(java_mar).read_bytes()
        assert java_compress.stdout.splitlines() == [
            f"compressed {len(data)} -> {len(java_blob)}"
        ]
        assert reference_decompress_container(java_blob) == data
        assert java_blob == ref_blob
    finally:
        os.unlink(src)
        os.unlink(java_mar)
        os.unlink(out)
        os.unlink(ref_mar)


def test_compressible_input_shrinks_and_incompressible_input_is_stored():
    """Check compressed savings and stored fallback header semantics."""
    repeat = PROGRAMS / "repeat.txt"
    mixed = PROGRAMS / "mixed.bin"
    repeat_mar, mixed_mar = tmp(), tmp()
    try:
        repeat_result = run("compress", str(repeat), repeat_mar)
        assert repeat_result.returncode == 0, repeat_result.stdout + repeat_result.stderr
        assert repeat_result.stderr == ""
        assert repeat_result.stdout.splitlines() == [
            f"compressed {repeat.stat().st_size} -> {Path(repeat_mar).stat().st_size}"
        ]
        repeat_fields = inspect_fields(repeat_mar)
        assert repeat_fields["flag"] == "compressed"
        assert repeat_fields["original_size"] == str(repeat.stat().st_size)
        assert repeat_fields["crc32"] == "b7abb5ee"
        assert int(repeat_fields["container_size"]) < repeat.stat().st_size
        assert int(repeat_fields["payload_size"]) == int(repeat_fields["container_size"]) - 13

        mixed_result = run("compress", str(mixed), mixed_mar)
        assert mixed_result.returncode == 0, mixed_result.stdout + mixed_result.stderr
        assert mixed_result.stderr == ""
        mixed_data = mixed.read_bytes()
        mixed_blob = Path(mixed_mar).read_bytes()
        assert mixed_result.stdout.splitlines() == [
            f"compressed {len(mixed_data)} -> {len(mixed_blob)}"
        ]
        mixed_fields = inspect_fields(mixed_mar)
        assert mixed_fields["flag"] == "stored"
        assert mixed_fields["original_size"] == "2048"
        assert mixed_fields["crc32"] == f"{binascii.crc32(mixed_data) & 0xFFFFFFFF:08x}"
        assert int(mixed_fields["container_size"]) == 2048 + 13
        assert mixed_fields["payload_size"] == "2048"
        assert mixed_blob[:4] == b"MRW1"
        assert mixed_blob[4] == 0
        assert int.from_bytes(mixed_blob[5:9], "big") == len(mixed_data)
        assert int.from_bytes(mixed_blob[9:13], "big") == binascii.crc32(mixed_data) & 0xFFFFFFFF
        assert mixed_blob[13:] == mixed_data
    finally:
        os.unlink(repeat_mar)
        os.unlink(mixed_mar)


def test_compressed_container_header_is_big_endian_and_reported_exactly():
    """Verify compressed MRW1 header bytes and public report counts."""
    src = PROGRAMS / "repeat.txt"
    mar = tmp()
    try:
        result = run("compress", str(src), mar)
        blob = Path(mar).read_bytes()
        data = src.read_bytes()

        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ""
        assert result.stdout.splitlines() == [f"compressed {len(data)} -> {len(blob)}"]
        assert blob[:4] == b"MRW1"
        assert blob[4] == 1
        assert int.from_bytes(blob[5:9], "big") == len(data)
        assert int.from_bytes(blob[9:13], "big") == binascii.crc32(data) & 0xFFFFFFFF

        inspect = run("inspect", mar)
        assert inspect.returncode == 0, inspect.stdout + inspect.stderr
        assert inspect.stderr == ""
        assert inspect.stdout.splitlines() == [
            "magic MRW1",
            "flag compressed",
            f"original_size {len(data)}",
            f"crc32 {binascii.crc32(data) & 0xFFFFFFFF:08x}",
            f"container_size {len(blob)}",
            f"payload_size {len(blob) - 13}",
        ]
    finally:
        os.unlink(mar)


def test_small_redundant_input_uses_stored_fallback_when_block_is_not_smaller():
    """Store redundant data when the compressed block is not smaller than input."""
    for size in [258, 265]:
        data = b"A" * size
        assert len(reference_encode_block(reference_lz_tokens(data))) >= len(data)
        src, mar = write_tmp(data), tmp()
        try:
            result = run("compress", src, mar)
            assert result.returncode == 0, result.stdout + result.stderr
            assert result.stderr == ""
            blob = Path(mar).read_bytes()
            assert result.stdout.splitlines() == [f"compressed {len(data)} -> {len(blob)}"]
            expected = container_blob(0, len(data), binascii.crc32(data) & 0xFFFFFFFF, data)
            assert blob == expected
            fields = inspect_fields(mar)
            assert fields["flag"] == "stored"
            assert fields["original_size"] == str(size)
            assert fields["payload_size"] == str(size)
        finally:
            os.unlink(src)
            os.unlink(mar)


def test_empty_input_uses_stored_container_header():
    """Verify the exact stored container metadata for an empty input."""
    src = PROGRAMS / "empty.txt"
    mar = tmp()
    try:
        result = run("compress", str(src), mar)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ""
        assert result.stdout.splitlines() == ["compressed 0 -> 13"]
        fields = inspect_fields(mar)
        assert fields["magic"] == "MRW1"
        assert fields["flag"] == "stored"
        assert fields["original_size"] == "0"
        assert fields["crc32"] == "00000000"
        assert fields["container_size"] == "13"
        assert fields["payload_size"] == "0"
    finally:
        os.unlink(mar)


def test_manual_stored_container_decompresses_exact_payload():
    """Read a handwritten stored container containing binary payload bytes."""
    payload = bytes([0, 255, 1, 254, 2, 253, 3, 252])
    blob = container_blob(0, len(payload), binascii.crc32(payload) & 0xFFFFFFFF, payload)
    result, data = decompress_blob_output(blob)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [f"decompressed {len(blob)} -> {len(payload)}"]
    assert data == payload


def test_manual_stored_container_decompress_report_is_exact_and_quiet():
    """Verify successful decompression report counts for stored containers."""
    payload = b"stored-report\x00\xff"
    blob = container_blob(0, len(payload), binascii.crc32(payload) & 0xFFFFFFFF, payload)
    mar, out = write_tmp(blob), tmp()
    try:
        result = run("decompress", mar, out)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ""
        assert result.stdout.splitlines() == [f"decompressed {len(blob)} -> {len(payload)}"]
        assert Path(out).read_bytes() == payload
    finally:
        os.unlink(mar)
        os.unlink(out)


def test_manual_compressed_literal_container_decompresses_exact_payload():
    """Read a forced compressed container containing only literal symbols."""
    expected = bytes([0, 17, 34, 51, 68, 85, 170, 255])
    payload = reference_encode_block([("LIT", value) for value in expected])
    blob = container_blob(1, len(expected), binascii.crc32(expected) & 0xFFFFFFFF, payload)
    result, data = decompress_blob_output(blob)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [f"decompressed {len(blob)} -> {len(expected)}"]
    assert data == expected


def test_manual_compressed_long_code_container_decompresses_exact_payload():
    """Read a container with 63-bit canonical codes above 32-bit range."""
    lengths = bytearray(258)
    lengths[65] = 1
    lengths[66] = 63
    lengths[256] = 63
    codes = reference_canonical_codes(lengths)
    writer = ReferenceBitWriter()
    writer.write_code(codes[65], lengths[65])
    writer.write_code(codes[66], lengths[66])
    writer.write_code(codes[256], lengths[256])
    payload = bytes(lengths) + writer.finish()
    blob = container_blob(1, 2, binascii.crc32(b"AB") & 0xFFFFFFFF, payload)
    result, data = decompress_blob_output(blob)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [f"decompressed {len(blob)} -> 2"]
    assert data == b"AB"


def test_manual_compressed_overlap_match_container_decompresses_exact_payload():
    """Read a forced compressed container containing an overlapping match."""
    expected = b"A" * 20
    payload = reference_encode_block([("LIT", 65), ("MATCH", 19, 1)])
    blob = container_blob(1, len(expected), binascii.crc32(expected) & 0xFFFFFFFF, payload)
    result, data = decompress_blob_output(blob)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [f"decompressed {len(blob)} -> {len(expected)}"]
    assert data == expected


def test_corruption_is_detected_cleanly():
    """Ensure payload corruption returns a clean Marrow failure."""
    src = PROGRAMS / "poem.txt"
    mar, out = tmp(), tmp()
    try:
        assert run("compress", str(src), mar).returncode == 0
        blob = bytearray(Path(mar).read_bytes())
        blob[-1] ^= 0xFF
        Path(mar).write_bytes(bytes(blob))
        d = run("decompress", mar, out)
        assert_clean_marrow_failure(d)
    finally:
        os.unlink(mar)
        os.unlink(out)


def test_decompress_failure_preserves_existing_output_file():
    """Keep an existing output file unchanged when decompression fails."""
    seed = b"existing-output-sentinel"
    payload = reference_encode_block([("LIT", 65)])
    bad_crc_blob = container_blob(1, 1, 0, payload)
    mar = write_tmp(bad_crc_blob)
    out = write_tmp(seed)
    try:
        result = run("decompress", mar, out)
        assert_clean_marrow_failure(result)
        assert Path(out).read_bytes() == seed
    finally:
        os.unlink(mar)
        os.unlink(out)


def test_decompress_failure_does_not_create_missing_output_file():
    """Keep a missing requested output path absent after decompression failure."""
    lengths = bytearray(258)
    lengths[65] = 1
    malformed = container_blob(1, 0, 0, bytes(lengths) + b"\x00")
    mar = write_tmp(malformed)
    out = tmp()
    os.unlink(out)
    try:
        result = run("decompress", mar, out)
        assert_clean_marrow_failure(result)
        assert not Path(out).exists()
    finally:
        os.unlink(mar)
        if Path(out).exists():
            os.unlink(out)


def test_container_header_rejections_are_clean():
    """Reject malformed stored-container headers and payloads cleanly."""
    src = PROGRAMS / "mixed.bin"
    mar = tmp()
    try:
        assert run("compress", str(src), mar).returncode == 0
        original = bytearray(Path(mar).read_bytes())

        for index in range(4):
            bad_magic = bytearray(original)
            bad_magic[index] ^= 0x7F
            assert_clean_marrow_failure(decompress_blob_result(bytes(bad_magic)))

        for flag in [2, 99, 255]:
            bad_flag = bytearray(original)
            bad_flag[4] = flag
            assert_clean_marrow_failure(decompress_blob_result(bytes(bad_flag)))

        bad_size = bytearray(original)
        bad_size[8] ^= 0x01
        assert_clean_marrow_failure(decompress_blob_result(bytes(bad_size)))

        bad_crc = bytearray(original)
        bad_crc[12] ^= 0x01
        assert_clean_marrow_failure(decompress_blob_result(bytes(bad_crc)))

        bad_payload = bytearray(original)
        bad_payload[-1] ^= 0x01
        assert_clean_marrow_failure(decompress_blob_result(bytes(bad_payload)))
    finally:
        os.unlink(mar)


def test_stored_container_boundary_mismatches_are_clean():
    """Reject handwritten stored containers with boundary size or CRC mismatches."""
    extra_payload = container_blob(0, 0, 0, b"extra")
    assert_clean_marrow_failure(decompress_blob_result(extra_payload))

    missing_payload = container_blob(0, 1, binascii.crc32(b"A") & 0xFFFFFFFF, b"")
    assert_clean_marrow_failure(decompress_blob_result(missing_payload))

    bad_crc = container_blob(0, 1, 0, b"A")
    assert_clean_marrow_failure(decompress_blob_result(bad_crc))


def test_container_short_headers_and_unsigned_size_boundaries_are_clean():
    """Handle short containers and unsigned header-size boundaries precisely."""
    for length in range(13):
        short_blob = (b"MRW1" + bytes(range(8)))[:length]
        assert_clean_marrow_failure(decompress_blob_result(short_blob))
        assert_clean_marrow_failure(inspect_blob_result(short_blob))

    huge_size = container_blob(0, 0xFFFFFFFF, 0, b"")
    inspect_result = inspect_blob_result(huge_size)
    assert inspect_result.returncode == 0, inspect_result.stdout + inspect_result.stderr
    assert inspect_result.stderr == ""
    assert inspect_result.stdout.splitlines() == [
        "magic MRW1",
        "flag stored",
        "original_size 4294967295",
        "crc32 00000000",
        "container_size 13",
        "payload_size 0",
    ]
    assert_clean_marrow_failure(decompress_blob_result(huge_size))


def test_compressed_container_size_crc_and_payload_rejections_are_clean():
    """Reject malformed compressed-container metadata and payloads cleanly."""
    src = PROGRAMS / "repeat.txt"
    mar = tmp()
    try:
        assert run("compress", str(src), mar).returncode == 0
        fields = inspect_fields(mar)
        assert fields["flag"] == "compressed"

        original = bytearray(Path(mar).read_bytes())

        bad_size = bytearray(original)
        bad_size[8] ^= 0x01
        assert_clean_marrow_failure(decompress_blob_result(bytes(bad_size)))

        bad_crc = bytearray(original)
        bad_crc[12] ^= 0x01
        assert_clean_marrow_failure(decompress_blob_result(bytes(bad_crc)))

        bad_payload = bytearray(original)
        bad_payload[13 + 258] ^= 0x01
        assert_clean_marrow_failure(decompress_blob_result(bytes(bad_payload)))
    finally:
        os.unlink(mar)


def test_compressed_container_truncated_and_missing_eob_rejections_are_clean():
    """Reject malformed compressed block payloads through Marrow errors."""
    empty_lengths = bytearray(258)
    empty_lengths[256] = 1
    empty_block = container_blob(1, 0, 0, bytes(empty_lengths) + b"\x00")
    empty_result, empty_data = decompress_blob_output(empty_block)
    assert empty_result.returncode == 0, empty_result.stdout + empty_result.stderr
    assert empty_data == b""

    short_payload = container_blob(1, 0, 0, b"")
    assert_clean_marrow_failure(decompress_blob_result(short_payload))

    no_lengths = container_blob(1, 0, 0, bytes(257))
    assert_clean_marrow_failure(decompress_blob_result(no_lengths))

    zero_table = container_blob(1, 0, 0, bytes(258) + b"\x00")
    assert_clean_marrow_failure(decompress_blob_result(zero_table))

    missing_bits_lengths = bytearray(258)
    missing_bits_lengths[256] = 1
    missing_bits = container_blob(1, 0, 0, bytes(missing_bits_lengths))
    assert_clean_marrow_failure(decompress_blob_result(missing_bits))

    too_long_lengths = bytearray(258)
    too_long_lengths[256] = 64
    too_long_code = container_blob(1, 0, 0, bytes(too_long_lengths) + b"\x00")
    assert_clean_marrow_failure(decompress_blob_result(too_long_code))

    oversubscribed_lengths = bytearray(258)
    oversubscribed_lengths[65] = 1
    oversubscribed_lengths[66] = 1
    oversubscribed_lengths[256] = 1
    oversubscribed_code = container_blob(1, 0, 0, bytes(oversubscribed_lengths) + b"\x00")
    assert_clean_marrow_failure(decompress_blob_result(oversubscribed_code))

    no_eob_lengths = bytearray(258)
    no_eob_lengths[65] = 1
    missing_eob = container_blob(1, 0, 0, bytes(no_eob_lengths) + b"\x00")
    assert_clean_marrow_failure(decompress_blob_result(missing_eob))

    invalid_match = container_blob(1, 0, 0, reference_encode_block([("MATCH", 3, 1)]))
    assert_clean_marrow_failure(decompress_blob_result(invalid_match))

    invalid_later_match = container_blob(
        1,
        0,
        0,
        reference_encode_block([("LIT", 65), ("MATCH", 3, 2)]),
    )
    assert_clean_marrow_failure(decompress_blob_result(invalid_later_match))

    truncated_match_lengths = bytearray(258)
    truncated_match_lengths[256] = 1
    truncated_match_lengths[257] = 1
    truncated_match = container_blob(1, 0, 0, bytes(truncated_match_lengths) + b"\x01")
    assert_clean_marrow_failure(decompress_blob_result(truncated_match))

    valid_payload = reference_encode_block([("LIT", 65)])
    valid_crc = binascii.crc32(b"A") & 0xFFFFFFFF
    bad_padding = bytearray(valid_payload)
    bad_padding[-1] |= 0x80
    padding_bits = container_blob(1, 1, valid_crc, bytes(bad_padding))
    assert_clean_marrow_failure(decompress_blob_result(padding_bits))
    trailing_zero = container_blob(1, 1, valid_crc, valid_payload + b"\x00")
    assert_clean_marrow_failure(decompress_blob_result(trailing_zero))
    trailing_nonzero = container_blob(1, 1, valid_crc, valid_payload + b"\x7f")
    assert_clean_marrow_failure(decompress_blob_result(trailing_nonzero))

    long_lengths = bytearray(258)
    long_lengths[65] = 1
    long_lengths[66] = 63
    long_lengths[256] = 63
    codes = reference_canonical_codes(long_lengths)
    writer = ReferenceBitWriter()
    writer.write_code(codes[65], long_lengths[65])
    writer.write_code(codes[66], long_lengths[66])
    writer.write_code(codes[256], long_lengths[256])
    long_payload = bytes(long_lengths) + writer.finish()
    long_truncated = container_blob(1, 2, binascii.crc32(b"AB") & 0xFFFFFFFF, long_payload[:-1])
    assert_clean_marrow_failure(decompress_blob_result(long_truncated))


def test_compressed_container_crc_mismatch_after_valid_decode_is_clean():
    """Reject a valid compressed block whose decoded bytes miss the header CRC."""
    payload = reference_encode_block([("LIT", 65)])
    crc_mismatch = container_blob(1, 1, 0, payload)
    assert_clean_marrow_failure(decompress_blob_result(crc_mismatch))


def test_compressed_container_size_mismatch_after_valid_decode_is_clean():
    """Reject a valid compressed block whose decoded size misses the header."""
    payload = reference_encode_block([("LIT", 65)])
    size_mismatch = container_blob(1, 2, binascii.crc32(b"A") & 0xFFFFFFFF, payload)
    assert_clean_marrow_failure(decompress_blob_result(size_mismatch))


def test_inspect_rejects_invalid_container_headers_cleanly():
    """Reject inspect input with too-short headers, bad magic, or bad flags."""
    assert_clean_marrow_failure(inspect_blob_result(b"MRW"))
    valid = bytearray(container_blob(0, 0, 0, b""))
    for index in range(4):
        bad_magic = bytearray(valid)
        bad_magic[index] ^= 0x7F
        assert_clean_marrow_failure(inspect_blob_result(bytes(bad_magic)))
    for flag in [2, 3, 127, 255]:
        assert_clean_marrow_failure(inspect_blob_result(container_blob(flag, 0, 0, b"")))


def test_inspect_reports_stored_header_without_payload_validation():
    """Report stored headers without requiring payload size or CRC validity."""
    blob = container_blob(0, 99, 0xDEADBEEF, b"abc")
    result = inspect_blob_result(blob)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "magic MRW1",
        "flag stored",
        "original_size 99",
        "crc32 deadbeef",
        "container_size 16",
        "payload_size 3",
    ]
    assert_clean_marrow_failure(decompress_blob_result(blob))


def test_inspect_reports_header_without_decoding_payload():
    """Report a valid compressed header without requiring a decodable payload."""
    payload = b"not-a-valid-block"
    blob = container_blob(1, 123, 0x12345678, payload)
    result = inspect_blob_result(blob)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "magic MRW1",
        "flag compressed",
        "original_size 123",
        "crc32 12345678",
        "container_size 30",
        "payload_size 17",
    ]

    empty_payload = container_blob(1, 0xFFFFFFFF, 0xFEEDFACE, b"")
    empty_result = inspect_blob_result(empty_payload)
    assert empty_result.returncode == 0, empty_result.stdout + empty_result.stderr
    assert empty_result.stderr == ""
    assert empty_result.stdout.splitlines() == [
        "magic MRW1",
        "flag compressed",
        "original_size 4294967295",
        "crc32 feedface",
        "container_size 13",
        "payload_size 0",
    ]
    assert_clean_marrow_failure(decompress_blob_result(empty_payload))


def test_reference_maximum_distance_container_decompresses_with_java():
    """Accept a reference-built compressed container with the largest distance."""
    prefix = bytes(65 + (i & 1) for i in range(32768))
    expected = prefix + prefix[:258]
    tokens = [("LIT", value) for value in prefix]
    tokens.append(("MATCH", 258, 32768))
    payload = reference_encode_block(tokens)
    blob = container_blob(1, len(expected), binascii.crc32(expected) & 0xFFFFFFFF, payload)
    result, data = decompress_blob_output(blob)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [f"decompressed {len(blob)} -> {len(expected)}"]
    assert data == expected


@pytest.mark.parametrize("name", CORPORA)
def test_java_compress_matches_reference_container(name):
    """Require Java compression to match the fixed reference containers."""
    src = PROGRAMS / name
    mar = tmp()
    try:
        result = run("compress", str(src), mar)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ""
        blob = Path(mar).read_bytes()
        assert result.stdout.splitlines() == [f"compressed {src.stat().st_size} -> {len(blob)}"]
        assert blob == (REFERENCE_CONTAINERS / f"{name}.mrw").read_bytes()
    finally:
        os.unlink(mar)


@pytest.mark.parametrize("name", CORPORA)
def test_reference_container_decompresses_with_java(name):
    """Require Java decompression to accept the fixed reference containers."""
    src = PROGRAMS / name
    out = tmp()
    try:
        mar = REFERENCE_CONTAINERS / f"{name}.mrw"
        d = run("decompress", mar, out)
        assert d.returncode == 0, d.stdout + d.stderr
        assert d.stderr == ""
        assert d.stdout.splitlines() == [
            f"decompressed {mar.stat().st_size} -> {src.stat().st_size}"
        ]
        assert Path(out).read_bytes() == src.read_bytes()
    finally:
        os.unlink(out)
