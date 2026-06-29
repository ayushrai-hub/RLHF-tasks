package skct.export;
import skct.policy.SkctPolicySnapshot; import java.util.*;
public final class SkctPipelineSerializer {
    public static Map<String,Object> serialize(SkctPolicySnapshot policy, Map<String,Object> fit) {
        return Map.of("bundle_id", policy.bundleId);
    }
}
