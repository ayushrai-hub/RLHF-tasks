package com.coastal.buoy.spectra.io;

import com.coastal.buoy.spectra.model.CommitBind;
import com.coastal.buoy.spectra.model.StagingSnapshot;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

public final class StagingWriter {
    public void writeSnapshot(Path path, StagingSnapshot snapshot) throws Exception {
        StringBuilder pressures = new StringBuilder();
        pressures.append("[");
        for (int i = 0; i < snapshot.filledPressures.length; i++) {
            if (i > 0) pressures.append(", ");
            pressures.append(String.format(Locale.US, "%.6f", snapshot.filledPressures[i]));
        }
        pressures.append("]");
        String json = String.format(
                Locale.US,
                "{\n  \"run_id\": \"%s\",\n  \"profile_fingerprint\": \"%s\",\n"
                        + "  \"samples_used\": %d,\n  \"filled_pressures\": %s\n}\n",
                snapshot.runId,
                snapshot.profileFingerprint,
                snapshot.samplesUsed,
                pressures);
        Files.writeString(path, json);
    }

    public void writeCommit(Path path, CommitBind bind) throws Exception {
        String json = String.format(
                Locale.US,
                "{\n  \"run_id\": \"%s\",\n  \"profile_fingerprint\": \"%s\",\n"
                        + "  \"spectral_bind\": \"%s\"\n}\n",
                bind.runId,
                bind.profileFingerprint,
                bind.spectralBind);
        Files.writeString(path, json);
    }
}
