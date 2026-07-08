package marrow;

import java.util.List;

/**
 * Reconstructs the original bytes from an LZ77 token stream.
 *
 * Literals append a byte. A back-reference copies {@code length} bytes from
 * {@code distance} bytes earlier in the output produced so far, one byte at a
 * time so that an overlapping copy (a distance smaller than the length, as in a
 * run) extends naturally. A back-reference that points before the start of the
 * output is a corrupt stream and is rejected.
 */
public final class LzDecoder {
    private LzDecoder() {}

    /** Decodes {@code tokens} into the original byte array. */
    public static byte[] decode(List<Token> tokens) {
        ByteList out = new ByteList();
        for (Token t : tokens) {
            if (!t.isMatch) {
                out.add(t.literal);
            } else {
                if (t.distance < 1 || t.distance > out.size()) {
                    throw new MarrowError("back-reference distance " + t.distance
                            + " out of range at output offset " + out.size());
                }
                int start = out.size() - t.distance;
                for (int k = 0; k < t.length; k++) {
                    out.add(out.get(start + k));
                }
            }
        }
        return out.toArray();
    }
}
