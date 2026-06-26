package com.coastal.buoy.spectra.pipeline;

import java.nio.file.Path;

public final class Pipeline {

    public int ingest(String manifestPath) throws Exception {
        return new IngestStage().run(manifestPath);
    }

    public int export(String manifestPath, String outputPath) throws Exception {
        return new ExportStage().run(manifestPath, outputPath);
    }

    public int run(String manifestPath, String outputPath) throws Exception {
        int rc = ingest(manifestPath);
        if (rc != 0) return rc;
        return export(manifestPath, outputPath);
    }
}
