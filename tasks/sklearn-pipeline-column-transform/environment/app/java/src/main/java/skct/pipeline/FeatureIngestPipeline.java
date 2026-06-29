package skct.pipeline;
import skct.corpus.SkctCorpusGate; import skct.ingest.*; import skct.policy.SkctPolicySnapshot; import skct.split.SkctSplitPolicy;
import com.google.gson.Gson; import com.google.gson.GsonBuilder;
import java.nio.file.*; import java.util.*;
public final class FeatureIngestPipeline {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    @SuppressWarnings("unchecked")
    public void run(String[] args) throws Exception {
        skct.util.SkctArgs a = new skct.util.SkctArgs(args);
        SkctCorpusGate.require(Path.of(a.corpus));
        Map<String,Object> bundle = SkctBundleLoader.load(Path.of(a.bundle));
        String corpus = Files.readString(Path.of(a.corpus));
        Map<String,Object> defs = SkctBundleLoader.defaults(bundle);
        List<String> defOrder = (List<String>) defs.get("export_order");
        List<String> num = (List<String>) defs.get("numeric_columns");
        List<String> cat = (List<String>) defs.get("categorical_columns");
        List<String> drop = (List<String>) defs.get("drop_columns");
        List<String> pass = (List<String>) defs.get("passthrough_columns");
        SkctPolicySnapshot policy = SkctPolicySnapshot.parse(
            String.valueOf(bundle.get("bundle_id")), corpus, defOrder,
            ((Number)defs.get("train_ratio")).doubleValue(), num, cat, drop, pass, defOrder);
        List<Map<String,Object>> rows = SkctBundleLoader.rows(bundle);
        Map<String,Object> split = SkctSplitPolicy.assign(rows, ((Number)defs.get("split_seed")).intValue(), policy.trainRatio);
        List<Map<String,Object>> train = (List<Map<String,Object>>) split.get("train");
        List<Map<String,Object>> test = (List<Map<String,Object>>) split.get("test");
        Map<String,Object> manifest = new LinkedHashMap<>();
        manifest.put("bundle_id", bundle.get("bundle_id"));
        manifest.put("train_count", train.size());
        manifest.put("test_count", test.size());
        manifest.put("column_codec", SkctColumnCodec.digest(SkctBundleLoader.columns(bundle)));
        manifest.put("sample_persistence_id", SkctPersistenceId.forBundle(
            String.valueOf(bundle.get("bundle_id")), String.valueOf(bundle.get("feature_lane")),
            ((Number)bundle.get("row_count")).intValue()));
        manifest.put("policy", Map.of("train_ratio", policy.trainRatio, "export_order", policy.exportOrder));
        Files.createDirectories(Path.of(a.out));
        Files.writeString(Path.of(a.out, "feature_manifest.json"), GSON.toJson(manifest));
        System.out.println("FEATURE_INGEST_OK");
    }
}
