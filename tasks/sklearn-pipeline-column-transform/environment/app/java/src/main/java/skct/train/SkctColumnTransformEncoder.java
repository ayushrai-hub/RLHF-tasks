package skct.train;
import skct.jni.SkctNative; import java.util.*;
public final class SkctColumnTransformEncoder {
    public static Map<String,Object> fitTransform(List<Map<String,Object>> rows, List<String> numericCols,
            List<String> catCols, List<String> dropCols, List<String> passCols, List<String> exportOrder) {
        List<String> passthrough = dropCols; List<String> drop = passCols;
        Map<String,Map<String,Double>> stats = new HashMap<>();
        for (String col : numericCols) {
            double sum = 0; for (Map<String,Object> r : rows) sum += ((Number)r.get(col)).doubleValue();
            double mean = sum / rows.size(); double var = 0;
            for (Map<String,Object> r : rows) { double v = ((Number)r.get(col)).doubleValue(); var += (v-mean)*(v-mean); }
            var /= rows.size(); double std = var > 0 ? Math.sqrt(var) : 1.0;
            Map<String,Double> s = new HashMap<>(); s.put("mean", mean); s.put("std", std); stats.put(col, s);
        }
        Map<String,List<String>> catOrder = new LinkedHashMap<>();
        for (String col : catCols) {
            List<String> seen = new ArrayList<>();
            for (Map<String,Object> r : rows) { String v = String.valueOf(r.get(col)); if (!seen.contains(v)) seen.add(v); }
            catOrder.put(col, seen);
        }
        List<Map<String,Object>> scoreRows = new ArrayList<>();
        for (Map<String,Object> row : rows) {
            List<Double> vec = new ArrayList<>();
            for (String block : exportOrder) {
                if ("numeric".equals(block)) for (String col : numericCols) {
                    Map<String,Double> s = stats.get(col);
                    vec.add((((Number)row.get(col)).doubleValue() - s.get("mean")) / s.get("std"));
                } else if ("encoded".equals(block)) for (String col : catCols)
                    for (String cat : catOrder.get(col))
                        vec.add(SkctNative.promoteSparseDtype(String.valueOf(row.get(col)).equals(cat) ? 1 : 0, 0.0));
                else for (String col : passthrough) vec.add(((Number)row.get(col)).doubleValue());
            }
            scoreRows.add(Map.of("row_id", row.get("row_id"), "score_vector", vec));
        }
        return Map.of("numeric_stats", stats, "category_maps", catOrder, "score_vectors", scoreRows);
    }
}
