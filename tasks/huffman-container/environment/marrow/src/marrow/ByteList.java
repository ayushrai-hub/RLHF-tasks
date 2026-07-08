package marrow;

import java.util.Arrays;

/**
 * A minimal growable byte buffer with indexed reads.
 *
 * Decoding needs to append output bytes and, for a back-reference, read bytes it
 * has already written (possibly overlapping the region being produced). A plain
 * stream cannot do indexed reads, so the codec uses this buffer wherever output
 * is being built up.
 */
public final class ByteList {
    private byte[] buf;
    private int size;

    public ByteList() {
        this(64);
    }

    public ByteList(int capacity) {
        buf = new byte[Math.max(1, capacity)];
        size = 0;
    }

    public void add(int b) {
        if (size == buf.length) {
            buf = Arrays.copyOf(buf, buf.length * 2);
        }
        buf[size++] = (byte) b;
    }

    /** Unsigned value of the byte at {@code index}. */
    public int get(int index) {
        return buf[index] & 0xFF;
    }

    public int size() {
        return size;
    }

    public byte[] toArray() {
        return Arrays.copyOf(buf, size);
    }
}
