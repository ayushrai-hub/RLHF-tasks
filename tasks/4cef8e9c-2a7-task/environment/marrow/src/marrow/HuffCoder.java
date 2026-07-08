package marrow;

/**
 * Canonical Huffman coding helpers for the Marrow block format.
 */
public final class HuffCoder {
    private HuffCoder() {}

    private static final int MAX_LEN = 63;

    /** Canonical code value (MSB first) for each symbol; 0 where length is 0. */
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
        for (int k = 0; k < len; k++) {
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

    /** Decodes a stream produced by {@link #encode}, stopping at end-of-block. */
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
