package skct.cli;
import skct.pipeline.*;
import java.util.Arrays;
public final class SkctMain {
    public static void main(String[] args) throws Exception {
        if (args.length == 0) System.exit(2);
        String cmd = args[0];
        String[] rest = Arrays.copyOfRange(args, 1, args.length);
        switch (cmd) {
            case "feature-ingest" -> new FeatureIngestPipeline().run(rest);
            case "column-transform-train" -> new ColumnTransformTrainPipeline().run(rest);
            case "pipeline-export" -> new PipelineExportPipeline().run(rest);
            case "parity-audit" -> new ParityAuditPipeline().run(rest);
            default -> System.exit(2);
        }
    }
}
