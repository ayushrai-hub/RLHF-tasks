package skct.export;
import skct.policy.SkctPolicySnapshot; import java.nio.charset.StandardCharsets; import java.security.MessageDigest; import java.util.*;
import com.google.gson.Gson;
public final class SkctExportDigest {
    public static String compute(SkctPolicySnapshot policy, List<Map<String,Object>> blocks) throws Exception {
        List<String> order = new ArrayList<>(policy.exportOrder); Collections.sort(order);
        String snap = new Gson().toJson(Map.of("bundle_id", policy.bundleId, "export_order", order));
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        return bytesToHex(md.digest(new Gson().toJson(blocks).getBytes(StandardCharsets.UTF_8)));
    }
    private static String bytesToHex(byte[] b) { StringBuilder sb = new StringBuilder(); for (byte v : b) sb.append(String.format("%02x", v)); return sb.toString(); }
}
