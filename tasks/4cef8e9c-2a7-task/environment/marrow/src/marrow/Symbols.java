package marrow;

/**
 * The symbol alphabet and the fixed parameters of the Marrow format.
 *
 * The LZ77 stage produces literals and back-references; the Huffman stage codes
 * a single alphabet of 258 symbols:
 * <ul>
 *   <li>{@code 0..255} — a literal byte;</li>
 *   <li>{@code 256} ({@link #EOB}) — end of block;</li>
 *   <li>{@code 257} ({@link #MATCH}) — a back-reference follows, whose length and
 *       distance are written as raw bits right after the symbol's Huffman code.</li>
 * </ul>
 */
public final class Symbols {
    private Symbols() {}

    /** Number of distinct symbols in the Huffman alphabet. */
    public static final int ALPHABET = 258;
    /** End-of-block symbol. */
    public static final int EOB = 256;
    /** Back-reference marker symbol. */
    public static final int MATCH = 257;

    /** Smallest and largest back-reference length. */
    public static final int MIN_MATCH = 3;
    public static final int MAX_MATCH = 258;

    /** The sliding-window size; the largest representable distance. */
    public static final int WINDOW = 32768;

    /** Raw bit widths written after a {@link #MATCH} symbol. */
    public static final int LEN_BITS = 8;   // stores (length - MIN_MATCH), 0..255
    public static final int DIST_BITS = 15; // stores (distance - 1), 0..32767
}
