package marrow;

import java.util.ArrayList;
import java.util.List;

/**
 * Command-line dispatch.
 *
 * Each subcommand exercises one stage of the codec so the layers can be
 * inspected and tested independently:
 *
 * <pre>
 *   bitprobe                 round-trips a fixed bit pattern (bit I/O)
 *   crc &lt;file&gt;                CRC-32 of a file
 *   lz &lt;file&gt;                 the LZ77 token stream
 *   unlz &lt;tokens&gt; &lt;out&gt;       reconstruct bytes from a token listing
 *   huff &lt;file&gt;               canonical Huffman code lengths for a file
 *   huffround &lt;file&gt;          Huffman encode + decode round-trip
 *   compress &lt;in&gt; &lt;out&gt;       write a Marrow container
 *   decompress &lt;in&gt; &lt;out&gt;     recover the original from a container
 *   inspect &lt;file&gt;            a container's header
 * </pre>
 */
public final class Cli {
    private Cli() {}

    /** A fixed (value, width) program used by `bitprobe` to exercise bit I/O. */
    private static final int[][] PROBE = {
        {1, 1}, {2, 2}, {5, 3}, {255, 8}, {0, 5}, {12345, 15}, {170, 8},
    };

    public static void run(String[] args) {
        if (args.length == 0) {
            System.out.print(usage());
            return;
        }
        String cmd = args[0];
        switch (cmd) {
            case "bitprobe": bitprobe(); break;
            case "crc": crc(arg(args, 1, "file")); break;
            case "lz": lz(arg(args, 1, "file")); break;
            case "unlz": unlz(arg(args, 1, "tokens file"), arg(args, 2, "output file")); break;
            case "huff": huff(arg(args, 1, "file")); break;
            case "huffround": huffround(arg(args, 1, "file")); break;
            case "compress": compress(arg(args, 1, "input"), arg(args, 2, "output")); break;
            case "decompress": decompress(arg(args, 1, "input"), arg(args, 2, "output")); break;
            case "inspect": inspect(arg(args, 1, "file")); break;
            default: throw new MarrowError("unknown command '" + cmd + "'\n\n" + usage());
        }
    }

    private static void bitprobe() {
        BitIo.Writer w = new BitIo.Writer();
        for (int[] p : PROBE) {
            w.write(p[0], p[1]);
        }
        byte[] packed = w.finish();
        StringBuilder hex = new StringBuilder();
        for (byte b : packed) {
            hex.append(String.format("%02x", b & 0xFF));
        }
        BitIo.Reader r = new BitIo.Reader(packed, 0);
        StringBuilder read = new StringBuilder("read");
        for (int[] p : PROBE) {
            read.append(' ').append(r.read(p[1]));
        }
        System.out.println("packed " + hex);
        System.out.println(read);
    }

    private static void crc(String file) {
        System.out.println("crc32 " + Io.hex32(Crc32.compute(Io.readFile(file))));
    }

    private static void lz(String file) {
        System.out.print(Report.tokens(Lz77.encode(Io.readFile(file))));
    }

    private static void unlz(String tokensFile, String outFile) {
        List<Token> tokens = parseTokens(new String(Io.readFile(tokensFile)));
        Io.writeFile(outFile, LzDecoder.decode(tokens));
    }

    private static void huff(String file) {
        System.out.print(Report.huffLengths(Huffman.lengths(byteFreq(Io.readFile(file)))));
    }

    private static void huffround(String file) {
        byte[] data = Io.readFile(file);
        int[] lengths = Huffman.lengths(byteFreq(data));
        int[] symbols = new int[data.length];
        for (int i = 0; i < data.length; i++) {
            symbols[i] = Io.u8(data[i]);
        }
        byte[] encoded = HuffCoder.encode(symbols, lengths);
        int[] decoded = HuffCoder.decodeUntilEob(encoded, 0, lengths);
        if (decoded.length != symbols.length) {
            throw new MarrowError("round-trip length mismatch");
        }
        for (int i = 0; i < symbols.length; i++) {
            if (decoded[i] != symbols[i]) {
                throw new MarrowError("round-trip mismatch at symbol " + i);
            }
        }
        System.out.println("ok symbols=" + symbols.length + " bytes=" + encoded.length);
    }

    private static void compress(String in, String out) {
        byte[] original = Io.readFile(in);
        byte[] container = Container.compress(original);
        Io.writeFile(out, container);
        System.out.println("compressed " + original.length + " -> " + container.length);
    }

    private static void decompress(String in, String out) {
        byte[] container = Io.readFile(in);
        byte[] original = Container.decompress(container);
        Io.writeFile(out, original);
        System.out.println("decompressed " + container.length + " -> " + original.length);
    }

    private static void inspect(String file) {
        System.out.print(Report.inspect(Io.readFile(file)));
    }

    // ---- helpers ----------------------------------------------------------

    private static int[] byteFreq(byte[] data) {
        int[] freq = new int[Symbols.ALPHABET];
        for (byte b : data) {
            freq[Io.u8(b)]++;
        }
        freq[Symbols.EOB]++;
        return freq;
    }

    private static List<Token> parseTokens(String text) {
        List<Token> tokens = new ArrayList<>();
        for (String raw : text.split("\n")) {
            String line = raw.trim();
            if (line.isEmpty()) {
                continue;
            }
            String[] parts = line.split("\\s+");
            try {
                if (parts[0].equals("LIT")) {
                    tokens.add(Token.literal(Integer.parseInt(parts[1])));
                } else if (parts[0].equals("MATCH")) {
                    tokens.add(Token.match(Integer.parseInt(parts[1]), Integer.parseInt(parts[2])));
                } else {
                    throw new MarrowError("unknown token '" + parts[0] + "'");
                }
            } catch (ArrayIndexOutOfBoundsException | NumberFormatException e) {
                throw new MarrowError("malformed token line: " + line);
            }
        }
        return tokens;
    }

    private static String arg(String[] args, int i, String what) {
        if (i >= args.length) {
            throw new MarrowError("missing " + what);
        }
        return args[i];
    }

    private static String usage() {
        return "marrow — a lossless LZ77 + Huffman compression codec\n\n"
                + "usage:\n"
                + "  marrow bitprobe\n"
                + "  marrow crc <file>\n"
                + "  marrow lz <file>\n"
                + "  marrow unlz <tokens> <out>\n"
                + "  marrow huff <file>\n"
                + "  marrow huffround <file>\n"
                + "  marrow compress <in> <out>\n"
                + "  marrow decompress <in> <out>\n"
                + "  marrow inspect <file>\n";
    }
}
