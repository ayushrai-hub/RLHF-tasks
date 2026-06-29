package skct.export;
import skct.policy.SkctPolicySnapshot; import java.util.*;
public final class SkctPipelineSerializer {
    @SuppressWarnings("unchecked")
    public static Map<String,Object> serialize(SkctPolicySnapshot policy, Map<String,Object> fit) {
        Map<String,Object> out = new LinkedHashMap<>();
        out.put("bundle_id", policy.bundleId);
        out.put("export_order", policy.exportOrder);
        out.put("numeric_stats", fit.get("numeric_stats"));
        out.put("category_maps", fit.get("category_maps"));
        out.put("numeric_columns", policy.numericColumns);
        out.put("categorical_columns", policy.categoricalColumns);
        out.put("drop_columns", policy.dropColumns);
        out.put("passthrough_columns", policy.passthroughColumns);
        return out;
    }
}
