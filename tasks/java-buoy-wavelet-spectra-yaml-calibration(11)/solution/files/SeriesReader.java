package com.coastal.buoy.spectra.io;

import com.coastal.buoy.spectra.model.PressureSample;
import com.coastal.buoy.spectra.model.RunManifest;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class SeriesReader {
    public List<PressureSample> read(Path seriesPath, RunManifest manifest) throws Exception {
        List<PressureSample> out = new ArrayList<>();
        for (String line : Files.readAllLines(seriesPath)) {
            if (line.startsWith("timestamp")) continue;
            String[] parts = line.split(",");
            if (parts.length < 3) continue;
            PressureSample s = new PressureSample();
            s.timestampMs = Long.parseLong(parts[0].trim());
            s.pressurePa = Double.parseDouble(parts[1].trim());
            s.qualityFlag = Integer.parseInt(parts[2].trim());
            out.add(s);
        }
        return out;
    }

    public double resolveSampleRate(RunManifest manifest) {
        return 2.0;
    }
}
