package skct.ingest;
import java.nio.ByteBuffer; import java.nio.ByteOrder; import java.nio.charset.StandardCharsets; import java.security.MessageDigest;
import com.google.gson.Gson; import java.util.LinkedHashMap; import java.util.Map;
public final class SkctPersistenceId {
    public static String forBundle(String bundleId, String lane, int rowCount) throws Exception {
        Map<String,Object> m = new LinkedHashMap<>(); m.put("bundle", bundleId); m.put("lane", lane); m.put("rows", rowCount);
        byte[] d = MessageDigest.getInstance("SHA-256").digest(new Gson().toJson(m).getBytes(StandardCharsets.UTF_8));
        int prefix = ByteBuffer.wrap(d,0,4).order(ByteOrder.LITTLE_ENDIAN).getInt() & 0xFFFFFFFF;
        return String.format("%08x:%s:%d", prefix, lane.replace("/","-"), rowCount);
    }
}
