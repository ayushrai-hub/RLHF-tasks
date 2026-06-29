package skct.audit;
import skct.jni.SkctNative; import com.google.gson.Gson;
import java.util.*;
public final class SkctParityAudit {
    public static List<Map<String,Object>> compare(List<Map<String,Object>> trainRows, String pipelinePath, Map<String,List<Double>> javaVectors) {
        Gson gson = new Gson();
        List<Map<String,Object>> flags = new ArrayList<>();
        for (Map<String,Object> row : trainRows) {
            String rid = String.valueOf(row.get("row_id"));
            List<Double> jvec = javaVectors.get(rid);
            double[] nativeArr = SkctNative.scoreRow(pipelinePath, gson.toJson(row));
            List<Double> nvec = new ArrayList<>();
            for (double v : nativeArr) nvec.add(v);
            double delta = 0.0;
            if (jvec.size() == nvec.size()) {
                for (int i = 0; i < jvec.size(); i++) delta = Math.max(delta, Math.abs(jvec.get(i) - nvec.get(i)));
            } else delta = 1.0;
            if (delta > 1e-9) flags.add(Map.of("row_id", rid, "max_delta", delta));
        }
        return flags;
    }
}
