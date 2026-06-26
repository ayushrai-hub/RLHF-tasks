package com.coastal.buoy.spectra.pipeline;

import com.coastal.buoy.spectra.config.ProfileHasher;
import com.coastal.buoy.spectra.config.ProfileLoader;
import com.coastal.buoy.spectra.io.ManifestReader;
import com.coastal.buoy.spectra.io.SeriesReader;
import com.coastal.buoy.spectra.io.StagingWriter;
import com.coastal.buoy.spectra.model.CommitBind;
import com.coastal.buoy.spectra.model.PressureSample;
import com.coastal.buoy.spectra.model.ProcessingProfile;
import com.coastal.buoy.spectra.model.RunManifest;
import com.coastal.buoy.spectra.model.StagingSnapshot;
import com.coastal.buoy.spectra.process.DriftCorrector;
import com.coastal.buoy.spectra.process.GapInterpolator;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public final class IngestStage {
    public static final Path STAGING = Path.of("/app/state/spectra-ingest-snapshot.json");
    public static final Path COMMIT = Path.of("/app/state/spectra-commit-bind.json");

    public int run(String manifestPath) throws Exception {
        Files.createDirectories(STAGING.getParent());
        Path manifestFile = Path.of(manifestPath);
        Path fixturesRoot = manifestFile.getParent().getParent();
        RunManifest manifest = new ManifestReader().read(manifestFile);
        ProcessingProfile profile = new ProfileLoader().load(
                resolve(fixturesRoot, manifest.profile),
                resolve(fixturesRoot, manifest.tomlOverlay));
        List<PressureSample> samples = new SeriesReader().read(resolve(fixturesRoot, manifest.seriesPath), manifest);

        double[] corrected = new DriftCorrector().correct(samples, profile);
        double[] filled = new GapInterpolator().fill(samples, corrected);

        StagingSnapshot snapshot = new StagingSnapshot();
        snapshot.runId = manifest.runId;
        snapshot.profileFingerprint = ProfileHasher.fingerprint(profile);
        snapshot.samplesUsed = samples.size();
        snapshot.filledPressures = filled;

        StagingWriter writer = new StagingWriter();
        writer.writeSnapshot(STAGING, snapshot);

        double mean = 0;
        for (double v : filled) mean += v;
        mean = filled.length > 0 ? mean / filled.length : 0;

        CommitBind bind = new CommitBind();
        bind.runId = manifest.runId;
        bind.profileFingerprint = snapshot.profileFingerprint;
        bind.spectralBind = ProfileHasher.spectralBind(snapshot.profileFingerprint, snapshot.samplesUsed, mean);
        writer.writeCommit(COMMIT, bind);
        return 0;
    }

    private Path resolve(Path root, String rel) {
        Path p = Path.of(rel);
        if (p.isAbsolute()) return p;
        if (rel.startsWith("profiles/")) return Path.of("/app", rel);
        return root.resolve(rel);
    }
}
