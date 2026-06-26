package com.coastal.buoy.spectra;

import com.coastal.buoy.spectra.pipeline.Pipeline;

public final class Main {
    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            usage();
            System.exit(2);
        }
        String command = args[0];
        String manifest = null;
        String output = null;
        for (int i = 1; i < args.length - 1; i++) {
            if ("--manifest".equals(args[i])) manifest = args[i + 1];
            if ("--output".equals(args[i])) output = args[i + 1];
        }
        Pipeline pipeline = new Pipeline();
        switch (command) {
            case "ingest" -> {
                if (manifest == null) {
                    usage();
                    System.exit(2);
                }
                System.exit(pipeline.ingest(manifest));
            }
            case "export" -> {
                if (manifest == null || output == null) {
                    usage();
                    System.exit(2);
                }
                System.exit(pipeline.export(manifest, output));
            }
            case "process" -> {
                if (manifest == null || output == null) {
                    usage();
                    System.exit(2);
                }
                System.exit(pipeline.run(manifest, output));
            }
            default -> {
                usage();
                System.exit(2);
            }
        }
    }

    private static void usage() {
        System.err.println("usage: ingest --manifest <path>");
        System.err.println("       export --manifest <path> --output <path>");
        System.err.println("       process --manifest <path> --output <path>");
    }
}
