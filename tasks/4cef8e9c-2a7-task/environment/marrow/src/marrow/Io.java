package marrow;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Small filesystem and byte helpers shared across the codec.
 *
 * Java's {@code byte} is signed; everywhere a byte is treated as a value in
 * {@code 0..255} the codec goes through {@link #u8(byte)} so the sign bit never
 * leaks into a computation.
 */
public final class Io {
    private Io() {}

    /** Reads a whole file into a byte array. */
    public static byte[] readFile(String path) {
        try {
            return Files.readAllBytes(Path.of(path));
        } catch (IOException e) {
            throw new MarrowError("cannot read '" + path + "': " + e.getMessage());
        }
    }

    /** Writes a byte array to a file, truncating any existing contents. */
    public static void writeFile(String path, byte[] data) {
        try {
            Files.write(Path.of(path), data);
        } catch (IOException e) {
            throw new MarrowError("cannot write '" + path + "': " + e.getMessage());
        }
    }

    /** The unsigned value (0..255) of a byte. */
    public static int u8(byte b) {
        return b & 0xFF;
    }

    /** Lowercase hex of an unsigned 32-bit value, zero padded to 8 digits. */
    public static String hex32(long v) {
        return String.format("%08x", v & 0xFFFFFFFFL);
    }
}
