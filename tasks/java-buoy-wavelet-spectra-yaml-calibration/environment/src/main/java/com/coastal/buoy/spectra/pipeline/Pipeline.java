package com.coastal.buoy.spectra.pipeline;

import com.coastal.buoy.spectra.config.ProfileLoader;
import com.coastal.buoy.spectra.io.ManifestReader;
import com.coastal.buoy.spectra.io.RunReportWriter;
import com.coastal.buoy.spectra.io.SeriesReader;
import com.coastal.buoy.spectra.model.PressureSample;
import com.coastal.buoy.spectra.model.ProcessingProfile;
import com.coastal.buoy.spectra.model.RunManifest;
import com.coastal.buoy.spectra.model.RunReport;
import com.coastal.buoy.spectra.process.DriftCorrector;
import com.coastal.buoy.spectra.process.GapInterpolator;
import com.coastal.buoy.spectra.process.WaveletEngine;

import java.nio.file.Path;
import java.util.List;

public final class Pipeline {

    public int run(String manifestPath, String outputPath) throws Exception {
        Path manifestFile = Path.of(manifestPath);
        Path fixturesRoot = manifestFile.getParent().getParent();
        RunManifest manifest = new ManifestReader().read(manifestFile);
        ProcessingProfile profile = new ProfileLoader().load(
                resolve(fixturesRoot, manifest.profile),
                resolve(fixturesRoot, manifest.tomlOverlay));
        List<PressureSample> samples = new SeriesReader().read(resolve(fixturesRoot, manifest.seriesPath), manifest);
        profile.sampleRateHz = new SeriesReader().resolveSampleRate(manifest);

        double[] corrected = new DriftCorrector().correct(samples, profile);
        double[] filled = new GapInterpolator().fill(samples, corrected);
        WaveletEngine.Result spectral = new WaveletEngine().analyze(filled, profile);

        RunReport report = new RunReport();
        report.runId = manifest.runId;
        report.significantWaveHeightM = spectral.significantWaveHeightM;
        report.peakPeriodS = spectral.peakPeriodS;
        report.coiMaskedRatio = spectral.coiMaskedRatio;
        report.samplesUsed = samples.size();
        report.driftCorrectionPa = new DriftCorrector().meanCorrection(samples, profile);

        new RunReportWriter().write(Path.of(outputPath), report);
        return 0;
    }

    private Path resolve(Path root, String rel) {
        Path p = Path.of(rel);
        if (p.isAbsolute()) return p;
        if (rel.startsWith("profiles/")) return Path.of("/app", rel);
        return root.resolve(rel);
    }
}
