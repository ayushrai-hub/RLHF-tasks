package marrow;

/**
 * Process entry point.
 *
 * All real work lives in {@link Cli} and the stage classes. This wrapper only
 * forwards the arguments and maps a {@link MarrowError} to a clean message on
 * standard error and exit code 1, so malformed input or corrupt data never
 * surfaces as a Java stack trace.
 */
public final class Main {
    public static void main(String[] args) {
        try {
            Cli.run(args);
        } catch (MarrowError e) {
            System.err.println("marrow: " + e.getMessage());
            System.exit(1);
        }
    }
}
