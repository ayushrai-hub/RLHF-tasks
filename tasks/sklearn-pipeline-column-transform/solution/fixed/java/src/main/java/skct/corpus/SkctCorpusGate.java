package skct.corpus;
import java.nio.file.Files; import java.nio.file.Path;
public final class SkctCorpusGate {
    public static void require(Path corpus) throws Exception {
        if (Files.readString(corpus).length() < 500_000) throw new IllegalStateException("corpus too short");
    }
}
