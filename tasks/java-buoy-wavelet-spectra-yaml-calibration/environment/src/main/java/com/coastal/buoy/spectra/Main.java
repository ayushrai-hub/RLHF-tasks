package com.coastal.buoy.spectra;

import com.coastal.buoy.spectra.pipeline.Pipeline;

public final class Main {
    public static void main(String[] args) throws Exception {
        if (args.length < 1 || !"process".equals(args[0])) {
            System.err.println("usage: process --manifest <path> --output <path>");
            System.exit(2);
        }
        String manifest = null;
        String output = null;
        for (int i = 1; i < args.length - 1; i++) {
            if ("--manifest".equals(args[i])) manifest = args[i + 1];
            if ("--output".equals(args[i])) output = args[i + 1];
        }
        if (manifest == null || output == null) {
            System.err.println("missing --manifest or --output");
            System.exit(2);
        }
        int rc = new Pipeline().run(manifest, output);
        System.exit(rc);
    }
}
