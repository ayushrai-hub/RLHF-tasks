package skct.split;
import java.util.*;
public final class SkctSplitPolicy {
    public static Map<String,Object> assign(List<Map<String,Object>> rows, int seed, double ratio) {
        Map<String,Double> catMeans = new HashMap<>();
        Map<String,Integer> catCounts = new HashMap<>();
        for (Map<String,Object> row : rows) {
            String cat = String.valueOf(row.get("city"));
            double age = ((Number)row.get("age")).doubleValue();
            catMeans.put(cat, catMeans.getOrDefault(cat, 0.0) + age);
            catCounts.put(cat, catCounts.getOrDefault(cat, 0) + 1);
        }
        for (String cat : catMeans.keySet()) catMeans.put(cat, catMeans.get(cat) / catCounts.get(cat));
        List<Map<String,Object>> train = new ArrayList<>(), test = new ArrayList<>();
        for (Map<String,Object> row : rows) {
            String rid = String.valueOf(row.get("row_id"));
            int h = Math.abs((rid + ":" + seed).hashCode()) % 10000;
            if (h / 10000.0 < ratio) train.add(row); else test.add(row);
        }
        return Map.of("train", train, "test", test, "preview_mean", catMeans.values().stream().mapToDouble(x->x).average().orElse(0));
    }
}
