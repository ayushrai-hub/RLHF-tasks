package skct.ingest;
import java.nio.ByteBuffer; import java.nio.ByteOrder; import java.nio.charset.StandardCharsets; import java.security.MessageDigest;
public final class SkctPersistenceId {
    public static String forBundle(String bundleId, String lane, int rowCount) throws Exception {
        String payload = String.format("{\"bundle_id\":\"%s\",\"lane\":\"%s\",\"row_count\":%d}", bundleId, lane, rowCount);
        byte[] d = MessageDigest.getInstance("SHA-256").digest(payload.getBytes(StandardCharsets.UTF_8));
        int prefix = ByteBuffer.wrap(d,0,4).order(ByteOrder.LITTLE_ENDIAN).getInt() & 0xFFFFFFFF;
        return String.format("%08x:%s:%d", prefix, lane.replace("/","-"), rowCount);
    }
}
