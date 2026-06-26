package com.coastal.buoy.spectra.io;

import com.coastal.buoy.spectra.model.RunManifest;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class ManifestReader {
    private static String extractString(String json, String key) {
        Pattern p = Pattern.compile("\"" + key + "\"\\s*:\\s*\"([^\"]+)\"");
        Matcher m = p.matcher(json);
        if (!m.find()) throw new IllegalArgumentException("missing " + key);
        return m.group(1);
    }

    private static Double extractDouble(String json, String key) {
        Pattern p = Pattern.compile("\"" + key + "\"\\s*:\\s*([0-9.]+)");
        Matcher m = p.matcher(json);
        if (!m.find()) return null;
        return Double.parseDouble(m.group(1));
    }

    public RunManifest read(Path manifestPath) throws Exception {
        String json = Files.readString(manifestPath);
        RunManifest m = new RunManifest();
        m.runId = extractString(json, "run_id");
        m.seriesPath = extractString(json, "series_path");
        m.profile = extractString(json, "profile");
        m.tomlOverlay = extractString(json, "toml_overlay");
        m.sampleRateHz = extractDouble(json, "sample_rate_hz");
        return m;
    }
}
