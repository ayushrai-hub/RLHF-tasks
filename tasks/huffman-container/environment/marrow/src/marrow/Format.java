package marrow;

/**
 * The on-disk container format.
 *
 * <pre>
 *   offset 0  : magic "MRW1"            (4 bytes)
 *   offset 4  : flags                   (1 byte: 0 = stored, 1 = compressed)
 *   offset 5  : original size           (4 bytes, big-endian unsigned)
 *   offset 9  : CRC-32 of the original  (4 bytes, big-endian)
 *   offset 13 : payload
 * </pre>
 *
 * For a <b>stored</b> container the payload is the original bytes verbatim (used
 * when compression would not help). For a <b>compressed</b> container the payload
 * is one Huffman-coded block: {@link Symbols#ALPHABET} code-length bytes followed
 * by the LSB-first bitstream, which the decoder reads until the end-of-block
 * symbol.
 */
public final class Format {
    private Format() {}

    public static final byte[] MAGIC = {'M', 'R', 'W', '1'};
    public static final int HEADER_SIZE = 13;

    public static final int FLAG_STORED = 0;
    public static final int FLAG_COMPRESSED = 1;
}
