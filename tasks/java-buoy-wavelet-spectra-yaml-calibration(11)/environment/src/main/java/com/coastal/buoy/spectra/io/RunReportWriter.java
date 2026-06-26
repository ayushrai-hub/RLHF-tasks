package com.coastal.buoy.spectra.io;

import com.coastal.buoy.spectra.model.RunReport;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

public final class RunReportWriter {
    public void write(Path output, RunReport report) throws Exception {
        String json = String.format(
                Locale.US,
                "{\n  \"run_id\": \"%s\",\n  \"significant_wave_height_m\": %.6f,\n"
                        + "  \"peak_period_s\": %.6f,\n  \"coi_masked_ratio\": %.6f,\n"
                        + "  \"samples_used\": %d,\n  \"drift_correction_pa\": %.6f\n}\n",
                report.runId,
                report.significantWaveHeightM,
                report.peakPeriodS,
                report.coiMaskedRatio,
                report.samplesUsed,
                report.driftCorrectionPa);
        Files.writeString(output, json);
    }
}
