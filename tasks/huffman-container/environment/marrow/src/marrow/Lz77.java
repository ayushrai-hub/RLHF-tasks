package marrow;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * The LZ77 match finder.
 *
 * The input is scanned left to right. At each position a hash of the next three
 * bytes indexes a chain of earlier positions that began with the same three
 * bytes; the chain is walked (newest first, bounded by the window and a maximum
 * effort) to find the longest match. The policy is deterministic: the longest
 * match wins, and because the chain yields nearer positions first and a tie does
 * not replace the incumbent, the nearest match wins on ties. A match of at least
 * {@link Symbols#MIN_MATCH} bytes is emitted as a back-reference; otherwise a
 * single literal is emitted.
 */
public final class Lz77 {
    private static final int HASH_BITS = 15;
    private static final int HASH_SIZE = 1 << HASH_BITS;
    private static final int HASH_MASK = HASH_SIZE - 1;
    private static final int MAX_CHAIN = 256;

    private static int hash3(byte[] d, int i) {
        return ((Io.u8(d[i]) << 10) ^ (Io.u8(d[i + 1]) << 5) ^ Io.u8(d[i + 2])) & HASH_MASK;
    }

    private static int matchLen(byte[] d, int a, int b, int n) {
        int k = 0;
        int max = Math.min(Symbols.MAX_MATCH, n - b);
        while (k < max && d[a + k] == d[b + k]) {
            k++;
        }
        return k;
    }

    /** Compresses {@code data} into a list of literal and match tokens. */
    public static List<Token> encode(byte[] data) {
        int n = data.length;
        List<Token> tokens = new ArrayList<>();
        int[] head = new int[HASH_SIZE];
        Arrays.fill(head, -1);
        int[] prev = new int[Math.max(1, n)];
        Arrays.fill(prev, -1);

        int i = 0;
        while (i < n) {
            int bestLen = 0;
            int bestDist = 0;
            if (i + Symbols.MIN_MATCH <= n) {
                int h = hash3(data, i);
                int cand = head[h];
                int chain = 0;
                while (cand >= 0 && (i - cand) <= Symbols.WINDOW && chain < MAX_CHAIN) {
                    int len = matchLen(data, cand, i, n);
                    if (len > bestLen) {
                        bestLen = len;
                        bestDist = i - cand;
                        if (len >= Symbols.MAX_MATCH) {
                            break;
                        }
                    }
                    cand = prev[cand];
                    chain++;
                }
            }

            if (bestLen >= Symbols.MIN_MATCH) {
                tokens.add(Token.match(bestLen, bestDist));
                int end = i + bestLen;
                while (i < end) {
                    insert(data, i, n, head, prev);
                    i++;
                }
            } else {
                tokens.add(Token.literal(data[i]));
                insert(data, i, n, head, prev);
                i++;
            }
        }
        return tokens;
    }

    private static void insert(byte[] data, int i, int n, int[] head, int[] prev) {
        if (i + Symbols.MIN_MATCH > n) {
            return;
        }
        int h = hash3(data, i);
        prev[i] = head[h];
        head[h] = i;
    }
}
