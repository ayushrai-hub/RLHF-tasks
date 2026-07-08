package marrow;

/**
 * The standard CRC-32 (the one used by zlib, gzip and PNG).
 *
 * It is the reflected algorithm with polynomial {@code 0xEDB88320}, an initial
 * value of all ones, and a final ones-complement. A 256-entry lookup table,
 * built once, processes the input one byte at a time. The container stores the
 * CRC of the original data so the decoder can detect corruption end to end.
 */
public final class Crc32 {
    private static final int[] TABLE = buildTable();

    private static int[] buildTable() {
        int[] table = new int[256];
        for (int n = 0; n < 256; n++) {
            int c = n;
            for (int k = 0; k < 8; k++) {
                if ((c & 1) != 0) {
                    c = 0xEDB88320 ^ (c >>> 1);
                } else {
                    c = c >>> 1;
                }
            }
            table[n] = c;
        }
        return table;
    }

    /** Returns the CRC-32 of {@code data} as an unsigned value in a long. */
    public static long compute(byte[] data) {
        int crc = 0xFFFFFFFF;
        for (byte b : data) {
            int index = (crc ^ b) & 0xFF;
            crc = TABLE[index] ^ (crc >>> 8);
        }
        crc = crc ^ 0xFFFFFFFF;
        return crc & 0xFFFFFFFFL;
    }
}
