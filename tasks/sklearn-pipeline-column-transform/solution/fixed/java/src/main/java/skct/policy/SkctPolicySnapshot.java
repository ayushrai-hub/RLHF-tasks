package skct.policy;
import java.util.ArrayList; import java.util.List;
public final class SkctPolicySnapshot {
    public final String bundleId; public final double trainRatio; public final List<String> exportOrder;
    public final List<String> numericColumns, categoricalColumns, dropColumns, passthroughColumns;
    public SkctPolicySnapshot(String bundleId, double trainRatio, List<String> exportOrder,
            List<String> numericColumns, List<String> categoricalColumns, List<String> dropColumns, List<String> passthroughColumns) {
        this.bundleId = bundleId; this.trainRatio = trainRatio; this.exportOrder = exportOrder;
        this.numericColumns = numericColumns; this.categoricalColumns = categoricalColumns;
        this.dropColumns = dropColumns; this.passthroughColumns = passthroughColumns;
    }
    public static SkctPolicySnapshot parse(String bundleId, String corpus, List<String> defaultOrder, double defaultRatio,
            List<String> num, List<String> cat, List<String> drop, List<String> pass, List<String> sidecar) {
        double ratio = defaultRatio;
        List<String> exportOrder = new ArrayList<>(defaultOrder);
        for (String line : corpus.split("\n")) {
            if (!line.contains(bundleId)) continue;
            if (line.contains("train_ratio=**")) ratio = Double.parseDouble(line.split("train_ratio=\\*\\*",2)[1].split("\\*\\*",2)[0].trim());
            if (line.contains("export_order=**")) {
                exportOrder = new ArrayList<>();
                for (String item : line.split("export_order=\\*\\*",2)[1].split("\\*\\*",2)[0].split("\\|"))
                    if (!item.trim().isEmpty()) exportOrder.add(item.trim());
            }
        }
        return new SkctPolicySnapshot(bundleId, ratio, exportOrder, num, cat, drop, pass);
    }
}
