package marrow;

/**
 * The single error type used across the codec.
 *
 * Every recoverable failure — a malformed container, a corrupt bitstream, an
 * impossible token, bad command-line arguments — is reported by throwing a
 * {@code MarrowError}. {@link Main} catches it, prints the message and exits
 * with status 1, so bad input produces a clean diagnostic rather than a stack
 * trace.
 */
public class MarrowError extends RuntimeException {
    public MarrowError(String message) {
        super(message);
    }
}
