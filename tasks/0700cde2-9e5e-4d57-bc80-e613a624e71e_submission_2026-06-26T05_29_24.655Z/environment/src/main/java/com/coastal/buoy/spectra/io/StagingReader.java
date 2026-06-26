package com.coastal.buoy.spectra.io;

import com.coastal.buoy.spectra.model.CommitBind;
import com.coastal.buoy.spectra.model.StagingSnapshot;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class StagingReader {
    private static final Pattern STRING_FIELD = Pattern.compile("\"([a-z_]+)\": \"([^\"]+)\"");
    private static final Pattern INT_FIELD = Pattern.compile("\"([a-z_]+)\": (\\d+)");

    public StagingSnapshot readSnapshot(Path path) throws Exception {
        String text = Files.readString(path);
        StagingSnapshot snapshot = new StagingSnapshot();
        for (Matcher m = STRING_FIELD.matcher(text); m.find(); ) {
            String key = m.group(1);
            String value = m.group(2);
            if ("run_id".equals(key)) snapshot.runId = value;
            if ("profile_fingerprint".equals(key)) snapshot.profileFingerprint = value;
        }
        for (Matcher m = INT_FIELD.matcher(text); m.find(); ) {
            if ("samples_used".equals(m.group(1))) snapshot.samplesUsed = Integer.parseInt(m.group(2));
        }
        int start = text.indexOf("\"filled_pressures\": [");
        if (start < 0) throw new IllegalStateException("missing filled_pressures");
        start = text.indexOf('[', start);
        int end = text.indexOf(']', start);
        String body = text.substring(start + 1, end).trim();
        List<Double> values = new ArrayList<>();
        if (!body.isEmpty()) {
            for (String part : body.split(",")) {
                values.add(Double.parseDouble(part.trim()));
            }
        }
        snapshot.filledPressures = new double[values.size()];
        for (int i = 0; i < values.size(); i++) snapshot.filledPressures[i] = values.get(i);
        return snapshot;
    }

    public CommitBind readCommit(Path path) throws Exception {
        String text = Files.readString(path);
        CommitBind bind = new CommitBind();
        for (Matcher m = STRING_FIELD.matcher(text); m.find(); ) {
            String key = m.group(1);
            String value = m.group(2);
            if ("run_id".equals(key)) bind.runId = value;
            if ("profile_fingerprint".equals(key)) bind.profileFingerprint = value;
            if ("spectral_bind".equals(key)) bind.spectralBind = value;
        }
        return bind;
    }
}
