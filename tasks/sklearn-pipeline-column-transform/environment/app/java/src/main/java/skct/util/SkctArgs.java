package skct.util;
import java.util.HashMap; import java.util.Map;
public final class SkctArgs {
    public final String bundle, corpus, out;
    public SkctArgs(String[] args) {
        Map<String,String> m = new HashMap<>();
        for (int i = 0; i < args.length - 1; i++) if (args[i].startsWith("--")) m.put(args[i], args[i+1]);
        bundle = m.getOrDefault("--bundle", ""); corpus = m.getOrDefault("--corpus", ""); out = m.getOrDefault("--out", "");
    }
}
