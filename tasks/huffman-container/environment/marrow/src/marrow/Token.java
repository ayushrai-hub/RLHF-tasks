package marrow;

/**
 * One LZ77 token: either a literal byte or a back-reference (match).
 *
 * A literal carries a byte value in {@code 0..255}. A match carries a length in
 * {@code MIN_MATCH..MAX_MATCH} and a distance in {@code 1..WINDOW}, meaning
 * "copy {@code length} bytes from {@code distance} bytes earlier in the already
 * decoded output".
 */
public final class Token {
    public final boolean isMatch;
    public final int literal;   // valid when !isMatch
    public final int length;    // valid when isMatch
    public final int distance;  // valid when isMatch

    private Token(boolean isMatch, int literal, int length, int distance) {
        this.isMatch = isMatch;
        this.literal = literal;
        this.length = length;
        this.distance = distance;
    }

    public static Token literal(int b) {
        return new Token(false, b & 0xFF, 0, 0);
    }

    public static Token match(int length, int distance) {
        return new Token(true, 0, length, distance);
    }

    @Override
    public String toString() {
        return isMatch ? ("MATCH " + length + " " + distance) : ("LIT " + literal);
    }
}
