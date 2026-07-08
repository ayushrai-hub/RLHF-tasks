package marrow;

import java.util.List;

/**
 * Stable, line-oriented text rendering for the inspection subcommands. Keeping
 * the formats here (rather than scattered through {@link Cli}) keeps command
 * output stable and easy to test.
 */
public final class Report {
    private Report() {}

    /** One token per line (see {@link Token#toString()}). */
    public static String tokens(List<Token> tokens) {
        StringBuilder sb = new StringBuilder();
        for (Token t : tokens) {
            sb.append(t).append('\n');
        }
        return sb.toString();
    }

    /** The non-zero canonical code lengths, one per used symbol, then a count. */
    public static String huffLengths(int[] lengths) {
        StringBuilder sb = new StringBuilder();
        int count = 0;
        for (int s = 0; s < lengths.length; s++) {
            if (lengths[s] > 0) {
                sb.append("code ").append(s).append(' ').append(lengths[s]).append('\n');
                count++;
            }
        }
        sb.append("count ").append(count).append('\n');
        return sb.toString();
    }

    /** The container header fields, without decoding the payload. */
    public static String inspect(byte[] container) {
        if (container.length < Format.HEADER_SIZE) {
            throw new MarrowError("container too short to hold a header");
        }
        for (int i = 0; i < Format.MAGIC.length; i++) {
            if (container[i] != Format.MAGIC[i]) {
                throw new MarrowError("bad magic: not a Marrow container");
            }
        }
        int flag = Container.flag(container);
        String flagName = flag == Format.FLAG_COMPRESSED ? "compressed"
                : flag == Format.FLAG_STORED ? "stored" : ("unknown(" + flag + ")");
        StringBuilder sb = new StringBuilder();
        sb.append("magic MRW1\n");
        sb.append("flag ").append(flagName).append('\n');
        sb.append("original_size ").append(Container.originalSize(container)).append('\n');
        sb.append("crc32 ").append(Io.hex32(Container.crc(container))).append('\n');
        sb.append("container_size ").append(container.length).append('\n');
        sb.append("payload_size ").append(container.length - Format.HEADER_SIZE).append('\n');
        return sb.toString();
    }
}
