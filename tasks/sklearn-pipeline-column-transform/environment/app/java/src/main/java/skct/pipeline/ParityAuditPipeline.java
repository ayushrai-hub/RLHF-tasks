package skct.pipeline;
import skct.audit.SkctParityAudit; import skct.corpus.SkctCorpusGate; import skct.export.*; import skct.ingest.*; import skct.policy.SkctPolicySnapshot; import skct.split.SkctSplitPolicy; import skct.train.SkctColumnTransformEncoder;
import com.google.gson.Gson; import com.google.gson.GsonBuilder;
import java.nio.file.*; import java.util.*;
public final class ParityAuditPipeline {
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
        Map<String,Object> fit = SkctColumnTransformEncoder.fitTransform(rows, policy.numericColumns,
            policy.categoricalColumns, policy.dropColumns, policy.passthroughColumns, policy.exportOrder);
        Map<String,List<Double>> javaVectors = new HashMap<>();
        for (Map<String,Object> sv : (List<Map<String,Object>>) fit.get("score_vectors")) {
            javaVectors.put(String.valueOf(sv.get("row_id")), (List<Double>) sv.get("score_vector"));
        }
        Path portablePath = Path.of(a.out, "portable_pipeline.json");
        if (!Files.exists(portablePath)) {
            Files.createDirectories(Path.of(a.out));
            Files.writeString(portablePath, GSON.toJson(SkctPipelineSerializer.serialize(policy, fit)));
        }
        List<Map<String,Object>> flags = SkctParityAudit.compare(train, portablePath.toString(), javaVectors);
        List<Map<String,Object>> blocks = new ArrayList<>();
        for (String lane : policy.exportOrder) {
            Map<String,Object> block = new LinkedHashMap<>();
            block.put("block", lane);
            block.put("flag_count", flags.size());
            blocks.add(block);
        }
        Map<String,Object> report = new LinkedHashMap<>();
        report.put("bundle_id", bundle.get("bundle_id"));
        report.put("parity_flags", flags);
        report.put("audit_digest", SkctExportDigest.compute(policy, blocks));
        Files.createDirectories(Path.of(a.out));
        Files.writeString(Path.of(a.out, "parity_audit.json"), GSON.toJson(report));
        System.out.println("PARITY_AUDIT_OK");
    }
}
