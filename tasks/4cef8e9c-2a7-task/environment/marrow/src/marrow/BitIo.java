package marrow;

import java.io.ByteArrayOutputStream;

/**
 * Least-significant-bit-first bit packing.
 *
 * The {@link Writer} accumulates bits into bytes low bit first: the first bit
 * written becomes bit 0 of the first output byte. {@link #finish()} pads the
 * final partial byte with zero bits. The {@link Reader} consumes the same stream
 * in the same order, so {@code reader.read(n)} returns exactly what
 * {@code writer.write(value, n)} put in. This ordering is what ties the Huffman
 * codes and the raw match bits together into one coherent stream.
 */
public final class BitIo {
    private BitIo() {}

    /** Packs values into a growing byte array, LSB first. */
    public static final class Writer {
        private final ByteArrayOutputStream out = new ByteArrayOutputStream();
        private long acc = 0;
        private int nbits = 0;

        /** Writes the low {@code count} bits of {@code value}, low bit first. */
        public void write(int value, int count) {
            if (count == 0) {
                return;
            }
            long masked = value & ((1L << count) - 1);
            acc |= masked << nbits;
            nbits += count;
            while (nbits >= 8) {
                out.write((int) (acc & 0xFF));
                acc >>>= 8;
                nbits -= 8;
            }
        }

        /** Number of bits written so far. */
        public long bitLength() {
            return (long) out.size() * 8 + nbits;
        }

        /** Flushes any partial final byte (zero padded) and returns the bytes. */
        public byte[] finish() {
            if (nbits > 0) {
                out.write((int) (acc & 0xFF));
                acc = 0;
                nbits = 0;
            }
            return out.toByteArray();
        }
    }

    /** Reads values from a byte array, LSB first. */
    public static final class Reader {
        private final byte[] data;
        private int pos;
        private long acc = 0;
        private int nbits = 0;

        public Reader(byte[] data, int offset) {
            this.data = data;
            this.pos = offset;
        }

        /** Reads {@code count} bits and returns them, low bit first. */
        public int read(int count) {
            if (count == 0) {
                return 0;
            }
            while (nbits < count) {
                if (pos >= data.length) {
                    throw new MarrowError("bitstream underrun");
                }
                acc |= (long) (data[pos++] & 0xFF) << nbits;
                nbits += 8;
            }
            int value = (int) (acc & ((1L << count) - 1));
            acc >>>= count;
            nbits -= count;
            return value;
        }

        /** Reads a single bit (0 or 1). */
        public int readBit() {
            return read(1);
        }
    }
}
