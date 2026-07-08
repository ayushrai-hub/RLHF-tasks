package marrow;

/**
 * Top-level MRW1 container framing and integrity helpers.
 */
public final class Container {
    private Container() {}

    /** Compresses {@code original} into a Marrow container. */
    public static byte[] compress(byte[] original) {
        throw new UnsupportedOperationException("container compression is not implemented");
    }

    /** Decompresses a Marrow container back into the original bytes. */
    public static byte[] decompress(byte[] container) {
        throw new UnsupportedOperationException("container decompression is not implemented");
    }

    /** Header fields, parsed for the `inspect` report (no full decode). */
    public static int flag(byte[] container) {
        throw new UnsupportedOperationException("container parsing is not implemented");
    }

    public static long originalSize(byte[] container) {
        throw new UnsupportedOperationException("container parsing is not implemented");
    }

    public static long crc(byte[] container) {
        throw new UnsupportedOperationException("container parsing is not implemented");
    }
}
