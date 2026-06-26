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

import java.nio.file.Path;
import java.util.List;

public final class IngestStage {
    public static final Path STAGING = Path.of("/app/state/spectra-ingest-snapshot.json");
    public static final Path COMMIT = Path.of("/app/state/spectra-commit-bind.json");

    public int run(String manifestPath) throws Exception {
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

        StagingSnapshot snapshot = new StagingSnapshot();
        snapshot.runId = manifest.runId;
        snapshot.profileFingerprint = ProfileHasher.fingerprint(profile);
        snapshot.samplesUsed = samples.size();
        snapshot.filledPressures = filled;

        StagingWriter writer = new StagingWriter();
        writer.writeSnapshot(STAGING, snapshot);

        CommitBind bind = new CommitBind();
        bind.runId = manifest.runId;
        bind.profileFingerprint = snapshot.profileFingerprint;
        bind.spectralBind = writer.brokenBind(manifest.runId);
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
