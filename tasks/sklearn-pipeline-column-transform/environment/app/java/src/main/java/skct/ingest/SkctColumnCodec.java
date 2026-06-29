package skct.ingest;
import java.nio.charset.StandardCharsets; import java.security.MessageDigest; import java.util.*;
public final class SkctColumnCodec {
    public static String digest(List<String> columns) throws Exception {
        List<String> ordered = new ArrayList<>(columns); Collections.sort(ordered);
        String body = new com.google.gson.Gson().toJson(ordered);
        byte[] d = MessageDigest.getInstance("SHA-256").digest(body.getBytes(StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder(); for (int i = 0; i < 8; i++) sb.append(String.format("%02x", d[i]));
        return sb.toString();
    }
}
