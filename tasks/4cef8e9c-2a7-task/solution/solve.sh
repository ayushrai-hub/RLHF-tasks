#!/bin/bash
set -euo pipefail

APP_DIR="${MARROW_APP:-/app/marrow}"
mkdir -p "$APP_DIR/src/marrow"

cat > "$APP_DIR/src/marrow/Huffman.java" <<'MARROW_SOLVE_EOF'
package marrow;

import java.util.PriorityQueue;

/**
 * Builds canonical Huffman code lengths from symbol frequencies.
 *
 * A Huffman tree is grown with a priority queue: the two lowest-weight nodes are
 * merged until one root remains, and each used symbol's code length is its depth
 * in that tree. Ties are broken deterministically with the node weight and a
 * stable tag, so the same frequencies always yield the same lengths.
 */
public final class Huffman {
    private Huffman() {}

    /** Returns the code length of every symbol, using 0 for unused symbols. */
    public static int[] lengths(int[] freq) {
        int alphabet = freq.length;
        int[] lengths = new int[alphabet];

        int used = 0;
        int last = -1;
        for (int s = 0; s < alphabet; s++) {
            if (freq[s] > 0) {
                used++;
                last = s;
            }
        }
        if (used == 0) {
            return lengths;
        }
        if (used == 1) {
            lengths[last] = 1;
            return lengths;
        }

        int maxNodes = 2 * alphabet;
        long[] weight = new long[maxNodes];
        int[] tie = new int[maxNodes];
        int[] left = new int[maxNodes];
        int[] right = new int[maxNodes];
        int[] sym = new int[maxNodes];
        int count = 0;

        PriorityQueue<Integer> pq = new PriorityQueue<>((x, y) -> {
            if (weight[x] != weight[y]) {
                return Long.compare(weight[x], weight[y]);
            }
            return Integer.compare(tie[x], tie[y]);
        });

        for (int s = 0; s < alphabet; s++) {
            if (freq[s] > 0) {
                int idx = count++;
                weight[idx] = freq[s];
                tie[idx] = s;
                left[idx] = -1;
                right[idx] = -1;
                sym[idx] = s;
                pq.add(idx);
            }
        }

        int internalTie = alphabet;
        while (pq.size() > 1) {
            int a = pq.poll();
            int b = pq.poll();
            int idx = count++;
            weight[idx] = weight[a] + weight[b];
            tie[idx] = internalTie++;
            left[idx] = a;
            right[idx] = b;
            sym[idx] = -1;
            pq.add(idx);
        }

        int root = pq.poll();
        assignDepths(root, 0, left, right, sym, lengths);
        return lengths;
    }

    private static void assignDepths(int node, int depth, int[] left, int[] right, int[] sym, int[] lengths) {
        if (sym[node] >= 0) {
            lengths[sym[node]] = depth;
            return;
        }
        assignDepths(left[node], depth + 1, left, right, sym, lengths);
        assignDepths(right[node], depth + 1, left, right, sym, lengths);
    }
}
MARROW_SOLVE_EOF

cat > "$APP_DIR/src/marrow/HuffCoder.java" <<'MARROW_SOLVE_EOF'
package marrow;

/**
 * Turns Huffman code lengths into canonical bit patterns and uses them to read
 * and write symbols.
 */
public final class HuffCoder {
    private HuffCoder() {}

    private static final int MAX_LEN = 63;

    private static void validateLengthCounts(long[] count, boolean rejectEmpty) {
        long available = 1;
        long used = 0;
        for (int bits = 1; bits < count.length; bits++) {
            if (available < 1_000_000_000L) {
                available <<= 1;
            } else {
                available = 1_000_000_000L;
            }
            if (count[bits] > available) {
                throw new MarrowError("oversubscribed huffman length table");
            }
            available -= count[bits];
            used += count[bits];
        }
        if (rejectEmpty && used == 0) {
            throw new MarrowError("empty huffman length table");
        }
    }

    /** Canonical code value for each symbol; 0 where length is 0. */
    public static long[] canonicalCodes(int[] lengths) {
        int maxLen = 0;
        for (int len : lengths) {
            if (len > MAX_LEN) {
                throw new MarrowError("code length " + len + " exceeds the supported maximum");
            }
            if (len > maxLen) {
                maxLen = len;
            }
        }
        long[] blCount = new long[maxLen + 1];
        for (int len : lengths) {
            if (len > 0) {
                blCount[len]++;
            }
        }
        validateLengthCounts(blCount, false);
        long[] nextCode = new long[maxLen + 1];
        long code = 0;
        for (int bits = 1; bits <= maxLen; bits++) {
            code = (code + blCount[bits - 1]) << 1;
            nextCode[bits] = code;
        }
        long[] codes = new long[lengths.length];
        for (int s = 0; s < lengths.length; s++) {
            if (lengths[s] > 0) {
                codes[s] = nextCode[lengths[s]]++;
            }
        }
        return codes;
    }

    /** Writes one symbol's canonical code, most significant bit first. */
    public static void writeSymbol(BitIo.Writer w, long[] codes, int[] lengths, int sym) {
        int len = lengths[sym];
        if (len == 0) {
            throw new MarrowError("symbol " + sym + " has no code");
        }
        long code = codes[sym];
        for (int k = len - 1; k >= 0; k--) {
            w.write((int) ((code >>> k) & 1), 1);
        }
    }

    /** A canonical-code decoder built once from a length table. */
    public static final class Decoder {
        private final int maxLen;
        private final long[] firstCode;
        private final int[] firstIndex;
        private final int[] count;
        private final int[] symbols;

        public Decoder(int[] lengths) {
            int m = 0;
            for (int len : lengths) {
                if (len > MAX_LEN) {
                    throw new MarrowError("code length " + len + " exceeds the supported maximum");
                }
                if (len > m) {
                    m = len;
                }
            }
            this.maxLen = m;
            this.count = new int[m + 1];
            for (int len : lengths) {
                if (len > 0) {
                    count[len]++;
                }
            }
            long[] longCount = new long[m + 1];
            for (int bits = 0; bits <= m; bits++) {
                longCount[bits] = count[bits];
            }
            validateLengthCounts(longCount, true);
            this.firstCode = new long[m + 1];
            this.firstIndex = new int[m + 1];
            long code = 0;
            int index = 0;
            for (int bits = 1; bits <= m; bits++) {
                code = (code + (bits >= 2 ? count[bits - 1] : 0)) << 1;
                firstCode[bits] = code;
                firstIndex[bits] = index;
                index += count[bits];
            }
            this.symbols = new int[index];
            int[] cursor = firstIndex.clone();
            for (int s = 0; s < lengths.length; s++) {
                int len = lengths[s];
                if (len > 0) {
                    symbols[cursor[len]++] = s;
                }
            }
        }

        /** Reads and returns one symbol. */
        public int read(BitIo.Reader r) {
            long code = 0;
            for (int len = 1; len <= maxLen; len++) {
                code = (code << 1) | r.readBit();
                if (count[len] > 0) {
                    long offset = code - firstCode[len];
                    if (offset >= 0 && offset < count[len]) {
                        return symbols[firstIndex[len] + (int) offset];
                    }
                }
            }
            throw new MarrowError("invalid huffman code in bitstream");
        }
    }

    /** Encodes a symbol array followed by end-of-block, returning packed bytes. */
    public static byte[] encode(int[] symbols, int[] lengths) {
        long[] codes = canonicalCodes(lengths);
        BitIo.Writer w = new BitIo.Writer();
        for (int s : symbols) {
            writeSymbol(w, codes, lengths, s);
        }
        writeSymbol(w, codes, lengths, Symbols.EOB);
        return w.finish();
    }

    /** Decodes a stream produced by encode, stopping at end-of-block. */
    public static int[] decodeUntilEob(byte[] data, int offset, int[] lengths) {
        Decoder dec = new Decoder(lengths);
        BitIo.Reader r = new BitIo.Reader(data, offset);
        java.util.ArrayList<Integer> out = new java.util.ArrayList<>();
        while (true) {
            int sym = dec.read(r);
            if (sym == Symbols.EOB) {
                break;
            }
            out.add(sym);
        }
        int[] result = new int[out.size()];
        for (int i = 0; i < result.length; i++) {
            result[i] = out.get(i);
        }
        return result;
    }
}
MARROW_SOLVE_EOF

cat > "$APP_DIR/src/marrow/BlockCodec.java" <<'MARROW_SOLVE_EOF'
package marrow;

import java.util.ArrayList;
import java.util.List;

/**
 * Encodes and decodes one compressed block between LZ77 tokens and the packed
 * Huffman bitstream.
 */
public final class BlockCodec {
    private BlockCodec() {}

    /** Encodes a token stream into a self-describing compressed block. */
    public static byte[] encodeBlock(List<Token> tokens) {
        int[] freq = new int[Symbols.ALPHABET];
        for (Token t : tokens) {
            if (t.isMatch) {
                freq[Symbols.MATCH]++;
            } else {
                freq[t.literal]++;
            }
        }
        freq[Symbols.EOB]++;

        int[] lengths = Huffman.lengths(freq);
        long[] codes = HuffCoder.canonicalCodes(lengths);

        BitIo.Writer w = new BitIo.Writer();
        for (Token t : tokens) {
            if (t.isMatch) {
                HuffCoder.writeSymbol(w, codes, lengths, Symbols.MATCH);
                w.write(t.length - Symbols.MIN_MATCH, Symbols.LEN_BITS);
                w.write(t.distance - 1, Symbols.DIST_BITS);
            } else {
                HuffCoder.writeSymbol(w, codes, lengths, t.literal);
            }
        }
        HuffCoder.writeSymbol(w, codes, lengths, Symbols.EOB);
        byte[] bits = w.finish();

        byte[] block = new byte[Symbols.ALPHABET + bits.length];
        for (int s = 0; s < Symbols.ALPHABET; s++) {
            block[s] = (byte) lengths[s];
        }
        System.arraycopy(bits, 0, block, Symbols.ALPHABET, bits.length);
        return block;
    }

    /** Decodes a compressed block starting at offset into bytes. */
    public static byte[] decodeBlock(byte[] data, int offset) {
        if (offset + Symbols.ALPHABET > data.length) {
            throw new MarrowError("truncated block header");
        }
        int[] lengths = new int[Symbols.ALPHABET];
        for (int s = 0; s < Symbols.ALPHABET; s++) {
            lengths[s] = data[offset + s] & 0xFF;
        }
        HuffCoder.Decoder dec = new HuffCoder.Decoder(lengths);
        BitIo.Reader r = new BitIo.Reader(data, offset + Symbols.ALPHABET);

        List<Token> tokens = new ArrayList<>();
        while (true) {
            int sym = dec.read(r);
            if (sym == Symbols.EOB) {
                break;
            }
            if (sym == Symbols.MATCH) {
                int length = r.read(Symbols.LEN_BITS) + Symbols.MIN_MATCH;
                int distance = r.read(Symbols.DIST_BITS) + 1;
                tokens.add(Token.match(length, distance));
            } else {
                tokens.add(Token.literal(sym));
            }
        }
        byte[] expectedBits = encodeBits(tokens, lengths);
        int bitOffset = offset + Symbols.ALPHABET;
        int actualBits = data.length - bitOffset;
        if (actualBits != expectedBits.length) {
            throw new MarrowError("trailing data after end of block");
        }
        for (int i = 0; i < actualBits; i++) {
            if (data[bitOffset + i] != expectedBits[i]) {
                throw new MarrowError("trailing data after end of block");
            }
        }
        return LzDecoder.decode(tokens);
    }

    private static byte[] encodeBits(List<Token> tokens, int[] lengths) {
        long[] codes = HuffCoder.canonicalCodes(lengths);
        BitIo.Writer w = new BitIo.Writer();
        for (Token t : tokens) {
            if (t.isMatch) {
                HuffCoder.writeSymbol(w, codes, lengths, Symbols.MATCH);
                w.write(t.length - Symbols.MIN_MATCH, Symbols.LEN_BITS);
                w.write(t.distance - 1, Symbols.DIST_BITS);
            } else {
                HuffCoder.writeSymbol(w, codes, lengths, t.literal);
            }
        }
        HuffCoder.writeSymbol(w, codes, lengths, Symbols.EOB);
        return w.finish();
    }
}
MARROW_SOLVE_EOF

cat > "$APP_DIR/src/marrow/Container.java" <<'MARROW_SOLVE_EOF'
package marrow;

import java.util.Arrays;
import java.util.List;

/**
 * The top-level codec: framing, integrity, and the stored/compressed decision.
 */
public final class Container {
    private Container() {}

    /** Compresses original bytes into a Marrow container. */
    public static byte[] compress(byte[] original) {
        List<Token> tokens = Lz77.encode(original);
        byte[] block = BlockCodec.encodeBlock(tokens);
        long crc = Crc32.compute(original);

        boolean useCompressed = block.length < original.length;
        int flag = useCompressed ? Format.FLAG_COMPRESSED : Format.FLAG_STORED;
        byte[] payload = useCompressed ? block : original;

        byte[] out = new byte[Format.HEADER_SIZE + payload.length];
        System.arraycopy(Format.MAGIC, 0, out, 0, 4);
        out[4] = (byte) flag;
        putU32BE(out, 5, original.length);
        putU32BE(out, 9, crc);
        System.arraycopy(payload, 0, out, Format.HEADER_SIZE, payload.length);
        return out;
    }

    /** Decompresses a Marrow container back into the original bytes. */
    public static byte[] decompress(byte[] container) {
        if (container.length < Format.HEADER_SIZE) {
            throw new MarrowError("container too short to hold a header");
        }
        for (int i = 0; i < Format.MAGIC.length; i++) {
            if (container[i] != Format.MAGIC[i]) {
                throw new MarrowError("bad magic: not a Marrow container");
            }
        }
        int flag = container[4] & 0xFF;
        long originalSize = getU32BE(container, 5);
        long crc = getU32BE(container, 9);

        byte[] original;
        if (flag == Format.FLAG_STORED) {
            original = Arrays.copyOfRange(container, Format.HEADER_SIZE, container.length);
        } else if (flag == Format.FLAG_COMPRESSED) {
            original = BlockCodec.decodeBlock(container, Format.HEADER_SIZE);
        } else {
            throw new MarrowError("unknown container flag " + flag);
        }

        if (original.length != originalSize) {
            throw new MarrowError("size mismatch: header says " + originalSize
                    + " but decoded " + original.length);
        }
        if (Crc32.compute(original) != crc) {
            throw new MarrowError("checksum mismatch: data is corrupt");
        }
        return original;
    }

    /** Header fields, parsed for the inspect report without full decoding. */
    public static int flag(byte[] container) {
        int flag = container[4] & 0xFF;
        if (flag != Format.FLAG_STORED && flag != Format.FLAG_COMPRESSED) {
            throw new MarrowError("unknown container flag " + flag);
        }
        return flag;
    }

    public static long originalSize(byte[] container) {
        return getU32BE(container, 5);
    }

    public static long crc(byte[] container) {
        return getU32BE(container, 9);
    }

    private static void putU32BE(byte[] out, int off, long value) {
        out[off] = (byte) ((value >>> 24) & 0xFF);
        out[off + 1] = (byte) ((value >>> 16) & 0xFF);
        out[off + 2] = (byte) ((value >>> 8) & 0xFF);
        out[off + 3] = (byte) (value & 0xFF);
    }

    private static long getU32BE(byte[] in, int off) {
        return ((long) (in[off] & 0xFF) << 24)
                | ((long) (in[off + 1] & 0xFF) << 16)
                | ((long) (in[off + 2] & 0xFF) << 8)
                | ((long) (in[off + 3] & 0xFF));
    }
}
MARROW_SOLVE_EOF
