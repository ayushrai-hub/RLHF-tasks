package skct.export;
import skct.policy.SkctPolicySnapshot; import java.nio.charset.StandardCharsets; import java.security.MessageDigest; import java.util.*;
import com.google.gson.Gson; import com.google.gson.GsonBuilder;
public final class SkctExportDigest {
    private static final Gson GSON = new GsonBuilder().disableHtmlEscaping().create();
    public static String compute(SkctPolicySnapshot policy, List<Map<String,Object>> blocks) throws Exception {
        Map<String,Object> snapMap = new LinkedHashMap<>();
        snapMap.put("bundle_id", policy.bundleId);
        snapMap.put("export_order", policy.exportOrder);
        Map<String,Object> tp = new LinkedHashMap<>();
        tp.put("numeric_columns", policy.numericColumns);
        tp.put("categorical_columns", policy.categoricalColumns);
        tp.put("drop_columns", policy.dropColumns);
        tp.put("passthrough_columns", policy.passthroughColumns);
        snapMap.put("transform_policy", tp);
        String snap = GSON.toJson(snapMap);
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] h1 = md.digest(snap.getBytes(StandardCharsets.UTF_8));
        byte[] body = GSON.toJson(blocks).getBytes(StandardCharsets.UTF_8);
        byte[] combined = new byte[body.length + h1.length];
        System.arraycopy(body, 0, combined, 0, body.length); System.arraycopy(h1, 0, combined, body.length, h1.length);
        return bytesToHex(md.digest(combined));
    }
    private static String bytesToHex(byte[] b) { StringBuilder sb = new StringBuilder(); for (byte v : b) sb.append(String.format("%02x", v)); return sb.toString(); }
}
