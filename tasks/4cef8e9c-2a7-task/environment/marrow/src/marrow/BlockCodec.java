package marrow;

import java.util.ArrayList;
import java.util.List;

/**
 * Encodes and decodes one compressed Marrow block.
 */
public final class BlockCodec {
    private BlockCodec() {}

    /** Encodes a token stream into a self-describing compressed block. */
    public static byte[] encodeBlock(List<Token> tokens) {
        int[] freq = new int[Symbols.ALPHABET];
        for (Token t : tokens) {
            if (t.isMatch) {
                freq[Symbols.MATCH]++;
            } else {
                freq[t.literal]++;
            }
        }
        freq[Symbols.EOB]++;

        int[] lengths = Huffman.lengths(freq);
        long[] codes = HuffCoder.canonicalCodes(lengths);

        BitIo.Writer w = new BitIo.Writer();
        for (Token t : tokens) {
            if (t.isMatch) {
                HuffCoder.writeSymbol(w, codes, lengths, Symbols.MATCH);
                w.write(t.length - Symbols.MIN_MATCH, Symbols.LEN_BITS);
            } else {
                HuffCoder.writeSymbol(w, codes, lengths, t.literal);
            }
        }
        HuffCoder.writeSymbol(w, codes, lengths, Symbols.EOB);
        byte[] bits = w.finish();

        byte[] block = new byte[Symbols.ALPHABET + bits.length];
        for (int s = 0; s < Symbols.ALPHABET; s++) {
            block[s] = (byte) lengths[s];
        }
        System.arraycopy(bits, 0, block, Symbols.ALPHABET, bits.length);
        return block;
    }

    /** Decodes a compressed block (starting at {@code offset}) into bytes. */
    public static byte[] decodeBlock(byte[] data, int offset) {
        if (offset + Symbols.ALPHABET > data.length) {
            throw new MarrowError("truncated block header");
        }
        int[] lengths = new int[Symbols.ALPHABET];
        for (int s = 0; s < Symbols.ALPHABET; s++) {
            lengths[s] = data[offset + s] & 0xFF;
        }
        HuffCoder.Decoder dec = new HuffCoder.Decoder(lengths);
        BitIo.Reader r = new BitIo.Reader(data, offset + Symbols.ALPHABET);

        List<Token> tokens = new ArrayList<>();
        while (true) {
            int sym = dec.read(r);
            if (sym == Symbols.EOB) {
                break;
            }
            if (sym == Symbols.MATCH) {
                int length = r.read(Symbols.LEN_BITS) + Symbols.MIN_MATCH;
                int distance = r.read(Symbols.DIST_BITS) + 1;
                tokens.add(Token.match(length, distance));
            } else {
                tokens.add(Token.literal(sym));
            }
        }
        return LzDecoder.decode(tokens);
    }
}
