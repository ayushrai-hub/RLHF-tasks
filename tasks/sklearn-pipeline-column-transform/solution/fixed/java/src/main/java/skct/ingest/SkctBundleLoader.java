package skct.ingest;
import com.google.gson.Gson; import com.google.gson.reflect.TypeToken;
import java.nio.file.*; import java.util.*;
public final class SkctBundleLoader {
    private static final Gson GSON = new Gson();
    public static Map<String,Object> load(Path path) throws Exception {
        return GSON.fromJson(Files.readString(path), new TypeToken<Map<String,Object>>(){}.getType());
    }
    @SuppressWarnings("unchecked")
    public static List<Map<String,Object>> rows(Map<String,Object> bundle) { return (List<Map<String,Object>>) bundle.get("rows"); }
    @SuppressWarnings("unchecked")
    public static List<String> columns(Map<String,Object> bundle) { return (List<String>) bundle.get("columns"); }
    @SuppressWarnings("unchecked")
    public static Map<String,Object> defaults(Map<String,Object> bundle) { return (Map<String,Object>) bundle.get("policy_defaults"); }
}
