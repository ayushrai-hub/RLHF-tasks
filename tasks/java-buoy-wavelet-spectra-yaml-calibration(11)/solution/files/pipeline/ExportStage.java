package com.coastal.buoy.spectra.pipeline;

import com.coastal.buoy.spectra.config.ProfileHasher;
import com.coastal.buoy.spectra.config.ProfileLoader;
import com.coastal.buoy.spectra.io.ManifestReader;
import com.coastal.buoy.spectra.io.RunReportWriter;
import com.coastal.buoy.spectra.io.SeriesReader;
import com.coastal.buoy.spectra.io.StagingReader;
import com.coastal.buoy.spectra.model.CommitBind;
import com.coastal.buoy.spectra.model.PressureSample;
import com.coastal.buoy.spectra.model.ProcessingProfile;
import com.coastal.buoy.spectra.model.RunManifest;
import com.coastal.buoy.spectra.model.RunReport;
import com.coastal.buoy.spectra.model.StagingSnapshot;
import com.coastal.buoy.spectra.process.DriftCorrector;
import com.coastal.buoy.spectra.process.WaveletEngine;

import java.nio.file.Path;
import java.util.List;

public final class ExportStage {
    public int run(String manifestPath, String outputPath) throws Exception {
        Path manifestFile = Path.of(manifestPath);
        Path fixturesRoot = manifestFile.getParent().getParent();
        RunManifest manifest = new ManifestReader().read(manifestFile);
        ProcessingProfile profile = new ProfileLoader().load(
                resolve(fixturesRoot, manifest.profile),
                resolve(fixturesRoot, manifest.tomlOverlay));

        StagingReader reader = new StagingReader();
        StagingSnapshot staging = reader.readSnapshot(IngestStage.STAGING);
        CommitBind commit = reader.readCommit(IngestStage.COMMIT);

        if (!staging.runId.equals(manifest.runId) || !commit.runId.equals(manifest.runId)) {
            System.err.println("spectral staging witness drift");
            return 1;
        }
        if (!staging.profileFingerprint.equals(commit.profileFingerprint)
                || !staging.profileFingerprint.equals(ProfileHasher.fingerprint(profile))) {
            System.err.println("spectral staging witness drift");
            return 1;
        }

        double mean = 0;
        for (double v : staging.filledPressures) mean += v;
        mean = staging.filledPressures.length > 0 ? mean / staging.filledPressures.length : 0;
        String expectedBind = ProfileHasher.spectralBind(staging.profileFingerprint, staging.samplesUsed, mean);
        if (!expectedBind.equals(commit.spectralBind)) {
            System.err.println("spectral staging witness drift");
            return 1;
        }

        WaveletEngine.Result spectral = new WaveletEngine().analyze(staging.filledPressures, profile);
        List<PressureSample> samples = new SeriesReader().read(resolve(fixturesRoot, manifest.seriesPath), manifest);

        RunReport report = new RunReport();
        report.runId = manifest.runId;
        report.significantWaveHeightM = spectral.significantWaveHeightM;
        report.peakPeriodS = spectral.peakPeriodS;
        report.coiMaskedRatio = spectral.coiMaskedRatio;
        report.samplesUsed = staging.samplesUsed;
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
