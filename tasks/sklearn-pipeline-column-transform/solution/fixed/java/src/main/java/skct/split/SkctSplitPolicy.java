package skct.split;
import java.nio.charset.StandardCharsets; import java.security.MessageDigest;
import java.util.*;
public final class SkctSplitPolicy {
    public static Map<String,Object> assign(List<Map<String,Object>> rows, int seed, double ratio) throws Exception {
        List<Map<String,Object>> train = new ArrayList<>(), test = new ArrayList<>();
        for (Map<String,Object> row : rows) {
            String rid = String.valueOf(row.get("row_id"));
            byte[] d = MessageDigest.getInstance("SHA-256").digest((rid + ":" + seed).getBytes(StandardCharsets.UTF_8));
            long h = ((d[0] & 0xffL) << 24) | ((d[1] & 0xffL) << 16) | ((d[2] & 0xffL) << 8) | (d[3] & 0xffL);
            h = h % 10000L;
            if (h / 10000.0 < ratio) train.add(row); else test.add(row);
        }
        return Map.of("train", train, "test", test);
    }
}
