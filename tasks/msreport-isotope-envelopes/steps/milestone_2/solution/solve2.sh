#!/bin/bash
set -euo pipefail

cd /app
cat > /app/src/MassSpec.java <<'JAVA'
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MassSpec {
    private static final double PROTON = 1.007276466812;
    private static final double NEUTRON = 1.003355;

    record Calibration(double mzOffset, double intensityScale) {}
    record Peak(double mz, int intensity) {}
    record Scan(int scan, List<Peak> peaks) {}
    record RunData(String run, Map<Integer, List<Peak>> scans) {}
    record Policy(String family, String run, int scan, int charge, int minPeaks, double mzStart, double mzEnd) {}
    record Envelope(String family, String run, int scan, int charge, int peakCount, double monoMz, double neutralMass, int intensitySum, List<Double> peakMz) {}

    public static void main(String[] args) throws Exception {
        Locale.setDefault(Locale.ROOT);
        if (args.length == 0) {
            die("missing command");
        }
        Map<String, String> opts = parseOptions(args);
        switch (args[0]) {
            case "centroid" -> centroid(opts);
            case "envelopes" -> envelopes(opts);
            case "review" -> review(opts);
            default -> die("unknown command: " + args[0]);
        }
    }

    private static Map<String, String> parseOptions(String[] args) {
        Map<String, String> opts = new HashMap<>();
        for (int i = 1; i < args.length; i += 2) {
            if (i + 1 >= args.length || !args[i].startsWith("--")) {
                die("invalid arguments");
            }
            opts.put(args[i].substring(2), args[i + 1]);
        }
        return opts;
    }

    private static void centroid(Map<String, String> opts) throws IOException {
        Path spectra = required(opts, "spectra");
        Map<String, Calibration> calibration = readCalibration(required(opts, "calibration"));
        Map<String, RunData> runs = new LinkedHashMap<>();
        List<Path> files;
        try (var stream = Files.list(spectra)) {
            files = stream.filter(p -> p.getFileName().toString().endsWith(".tsv"))
                    .sorted(Comparator.comparing(p -> p.getFileName().toString()))
                    .toList();
        }
        for (Path file : files) {
            List<String> lines = Files.readAllLines(file);
            for (int i = 1; i < lines.size(); i++) {
                String[] parts = lines.get(i).split("\\t", -1);
                if (parts.length < 5 || !"OK".equals(parts[4])) {
                    continue;
                }
                String run = parts[0];
                int scan = Integer.parseInt(parts[1]);
                Calibration c = calibration.getOrDefault(run, new Calibration(0.0, 1.0));
                double mz = round(Double.parseDouble(parts[2]) + c.mzOffset(), 4);
                int intensity = (int) Math.round(Double.parseDouble(parts[3]) * c.intensityScale());
                runs.computeIfAbsent(run, r -> new RunData(r, new LinkedHashMap<>()))
                        .scans().computeIfAbsent(scan, s -> new ArrayList<>())
                        .add(new Peak(mz, intensity));
            }
        }
        List<RunData> ordered = new ArrayList<>(runs.values());
        ordered.sort(Comparator.comparing(RunData::run));
        for (RunData run : ordered) {
            for (List<Peak> peaks : run.scans().values()) {
                peaks.sort(Comparator.comparingDouble(Peak::mz));
            }
        }
        write(required(opts, "output"), centroidsJson(ordered));
    }

    private static void envelopes(Map<String, String> opts) throws IOException {
        Map<String, RunData> runs = readCentroids(required(opts, "centroids"));
        List<Policy> policies = readPolicies(required(opts, "policy"));
        List<Envelope> envelopes = new ArrayList<>();
        for (Policy policy : policies) {
            RunData run = runs.get(policy.run());
            if (run == null || !run.scans().containsKey(policy.scan())) {
                continue;
            }
            List<Peak> window = run.scans().get(policy.scan()).stream()
                    .filter(p -> p.mz() >= policy.mzStart() && p.mz() <= policy.mzEnd())
                    .sorted(Comparator.comparingDouble(Peak::mz))
                    .toList();
            List<Peak> chain = bestChain(window, policy.charge());
            if (chain.size() < policy.minPeaks()) {
                continue;
            }
            int intensity = chain.stream().mapToInt(Peak::intensity).sum();
            double mono = chain.get(0).mz();
            double neutral = round((mono - PROTON) * policy.charge(), 5);
            List<Double> mz = chain.stream().map(p -> round(p.mz(), 4)).toList();
            envelopes.add(new Envelope(policy.family(), policy.run(), policy.scan(), policy.charge(),
                    chain.size(), round(mono, 4), neutral, intensity, mz));
        }
        envelopes.sort(Comparator.comparing(Envelope::family).thenComparing(Envelope::run));
        write(required(opts, "output"), envelopesJson(envelopes));
    }

    private static void review(Map<String, String> opts) throws IOException {
        List<Envelope> envelopes = readEnvelopes(required(opts, "envelopes"));
        Map<String, List<String>> groups = readReplicates(required(opts, "replicates"));
        Set<String> families = new LinkedHashSet<>();
        for (Envelope e : envelopes) {
            families.add(e.family());
        }
        List<String> groupIds = new ArrayList<>(groups.keySet());
        groupIds.sort(String::compareTo);
        List<String> familyIds = new ArrayList<>(families);
        familyIds.sort(String::compareTo);
        List<String> reviews = new ArrayList<>();
        Map<String, Integer> statusCounts = new HashMap<>();
        int reviewCount = 0;
        for (String group : groupIds) {
            List<String> expectedRuns = new ArrayList<>(groups.get(group));
            expectedRuns.sort(String::compareTo);
            for (String family : familyIds) {
                List<Envelope> observed = envelopes.stream()
                        .filter(e -> e.family().equals(family) && expectedRuns.contains(e.run()))
                        .sorted(Comparator.comparing(Envelope::run))
                        .toList();
                Set<String> observedRuns = new LinkedHashSet<>();
                for (Envelope e : observed) {
                    observedRuns.add(e.run());
                }
                List<String> missing = expectedRuns.stream().filter(r -> !observedRuns.contains(r)).toList();
                double meanMass = observed.stream().mapToDouble(Envelope::neutralMass).average().orElse(Double.NaN);
                double ppm = 0.0;
                if (!observed.isEmpty() && meanMass != 0.0) {
                    double min = observed.stream().mapToDouble(Envelope::neutralMass).min().orElse(meanMass);
                    double max = observed.stream().mapToDouble(Envelope::neutralMass).max().orElse(meanMass);
                    ppm = round(((max - min) / meanMass) * 1_000_000.0, 2);
                }
                Double cv = null;
                if (!observed.isEmpty()) {
                    double mean = observed.stream().mapToDouble(Envelope::intensitySum).average().orElse(0.0);
                    double variance = 0.0;
                    for (Envelope e : observed) {
                        double diff = e.intensitySum() - mean;
                        variance += diff * diff;
                    }
                    variance /= observed.size();
                    cv = mean == 0.0 ? 0.0 : round(Math.sqrt(variance) / mean, 4);
                }
                String status;
                if (!missing.isEmpty()) {
                    status = "missing";
                } else if (ppm > 12.0) {
                    status = "drift";
                } else if (cv != null && cv > 0.35) {
                    status = "unstable_intensity";
                } else {
                    status = "stable";
                }
                statusCounts.put(status, statusCounts.getOrDefault(status, 0) + 1);
                reviewCount++;
                reviews.add(reviewJson(group, family, expectedRuns, new ArrayList<>(observedRuns), missing,
                        meanMass, ppm, cv, status));
            }
        }
        write(required(opts, "output"), reviewRootJson(reviews, groupIds.size(), reviewCount, statusCounts));
    }

    private static List<Peak> bestChain(List<Peak> peaks, int charge) {
        double spacing = NEUTRON / charge;
        List<Peak> best = List.of();
        for (int i = 0; i < peaks.size(); i++) {
            List<Peak> chain = new ArrayList<>();
            chain.add(peaks.get(i));
            Peak last = peaks.get(i);
            for (int j = i + 1; j < peaks.size(); j++) {
                double delta = peaks.get(j).mz() - last.mz();
                if (Math.abs(delta - spacing) <= 0.015) {
                    chain.add(peaks.get(j));
                    last = peaks.get(j);
                }
            }
            int chainIntensity = chain.stream().mapToInt(Peak::intensity).sum();
            int bestIntensity = best.stream().mapToInt(Peak::intensity).sum();
            if (chain.size() > best.size() || (chain.size() == best.size() && chainIntensity > bestIntensity)) {
                best = chain;
            }
        }
        return best;
    }

    private static Map<String, Calibration> readCalibration(Path path) throws IOException {
        Map<String, Calibration> out = new HashMap<>();
        List<String> lines = Files.readAllLines(path);
        for (int i = 1; i < lines.size(); i++) {
            String[] p = lines.get(i).split("\\t", -1);
            if (p.length >= 3) {
                out.put(p[0], new Calibration(Double.parseDouble(p[1]), Double.parseDouble(p[2])));
            }
        }
        return out;
    }

    private static List<Policy> readPolicies(Path path) throws IOException {
        List<Policy> out = new ArrayList<>();
        List<String> lines = Files.readAllLines(path);
        for (int i = 1; i < lines.size(); i++) {
            String[] p = lines.get(i).split(",", -1);
            if (p.length >= 7) {
                out.add(new Policy(p[0], p[1], Integer.parseInt(p[2]), Integer.parseInt(p[3]),
                        Integer.parseInt(p[4]), Double.parseDouble(p[5]), Double.parseDouble(p[6])));
            }
        }
        return out;
    }

    private static Map<String, List<String>> readReplicates(Path path) throws IOException {
        Map<String, List<String>> out = new LinkedHashMap<>();
        List<String> lines = Files.readAllLines(path);
        for (int i = 1; i < lines.size(); i++) {
            String[] p = lines.get(i).split("\\t", -1);
            if (p.length >= 2) {
                out.computeIfAbsent(p[0], k -> new ArrayList<>()).add(p[1]);
            }
        }
        return out;
    }

    private static Map<String, RunData> readCentroids(Path path) throws IOException {
        String text = Files.readString(path);
        Map<String, RunData> out = new LinkedHashMap<>();
        String marker = "{\"run\":\"";
        String[] chunks = text.split(Pattern.quote(marker));
        for (int chunkIndex = 1; chunkIndex < chunks.length; chunkIndex++) {
            String chunk = chunks[chunkIndex];
            int endRun = chunk.indexOf('"');
            if (endRun < 0) {
                continue;
            }
            String run = chunk.substring(0, endRun);
            Map<Integer, List<Peak>> scans = new LinkedHashMap<>();
            Pattern scanPattern = Pattern.compile("\\{\\\"scan\\\":(\\d+),\\\"peaks\\\":\\[(.*?)\\]\\}", Pattern.DOTALL);
            Matcher scanMatcher = scanPattern.matcher(chunk);
            while (scanMatcher.find()) {
                int scan = Integer.parseInt(scanMatcher.group(1));
                String peakBody = scanMatcher.group(2);
                List<Peak> peaks = new ArrayList<>();
                Pattern peakPattern = Pattern.compile("\\{\\\"mz\\\":([0-9.\\-]+),\\\"intensity\\\":(\\d+)\\}");
                Matcher peakMatcher = peakPattern.matcher(peakBody);
                while (peakMatcher.find()) {
                    peaks.add(new Peak(Double.parseDouble(peakMatcher.group(1)), Integer.parseInt(peakMatcher.group(2))));
                }
                scans.put(scan, peaks);
            }
            out.put(run, new RunData(run, scans));
        }
        return out;
    }

    private static List<Envelope> readEnvelopes(Path path) throws IOException {
        String text = Files.readString(path);
        List<Envelope> out = new ArrayList<>();
        Pattern envPattern = Pattern.compile("\\{\\\"family\\\":\\\"([^\\\"]+)\\\",\\\"run\\\":\\\"([^\\\"]+)\\\",\\\"scan\\\":(\\d+),\\\"charge\\\":(\\d+),\\\"peak_count\\\":(\\d+),\\\"monoisotopic_mz\\\":([0-9.\\-]+),\\\"neutral_mass\\\":([0-9.\\-]+),\\\"intensity_sum\\\":(\\d+),\\\"peak_mz\\\":\\[(.*?)\\]\\}");
        Matcher matcher = envPattern.matcher(text);
        while (matcher.find()) {
            List<Double> mz = new ArrayList<>();
            String body = matcher.group(9).trim();
            if (!body.isEmpty()) {
                for (String part : body.split(",")) {
                    mz.add(Double.parseDouble(part));
                }
            }
            out.add(new Envelope(matcher.group(1), matcher.group(2), Integer.parseInt(matcher.group(3)),
                    Integer.parseInt(matcher.group(4)), Integer.parseInt(matcher.group(5)),
                    Double.parseDouble(matcher.group(6)), Double.parseDouble(matcher.group(7)),
                    Integer.parseInt(matcher.group(8)), mz));
        }
        return out;
    }

    private static String centroidsJson(List<RunData> runs) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"runs\":[");
        for (int i = 0; i < runs.size(); i++) {
            RunData run = runs.get(i);
            if (i > 0) sb.append(',');
            int tic = run.scans().values().stream().flatMap(List::stream).mapToInt(Peak::intensity).sum();
            List<Integer> scans = new ArrayList<>(run.scans().keySet());
            scans.sort(Integer::compareTo);
            sb.append("{\"run\":\"").append(escape(run.run())).append("\",\"scan_count\":").append(scans.size())
                    .append(",\"total_ion_current\":").append(tic).append(",\"scans\":[");
            for (int j = 0; j < scans.size(); j++) {
                if (j > 0) sb.append(',');
                int scan = scans.get(j);
                List<Peak> peaks = run.scans().get(scan);
                sb.append("{\"scan\":").append(scan).append(",\"peaks\":[");
                for (int k = 0; k < peaks.size(); k++) {
                    if (k > 0) sb.append(',');
                    Peak p = peaks.get(k);
                    sb.append("{\"mz\":").append(fmt(p.mz(), 4)).append(",\"intensity\":").append(p.intensity()).append('}');
                }
                sb.append("]}");
            }
            sb.append("]}");
        }
        return sb.append("]}\n").toString();
    }

    private static String envelopesJson(List<Envelope> envelopes) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"envelopes\":[");
        for (int i = 0; i < envelopes.size(); i++) {
            if (i > 0) sb.append(',');
            Envelope e = envelopes.get(i);
            sb.append("{\"family\":\"").append(escape(e.family())).append("\",\"run\":\"").append(escape(e.run()))
                    .append("\",\"scan\":").append(e.scan()).append(",\"charge\":").append(e.charge())
                    .append(",\"peak_count\":").append(e.peakCount()).append(",\"monoisotopic_mz\":")
                    .append(fmt(e.monoMz(), 4)).append(",\"neutral_mass\":").append(fmt(e.neutralMass(), 5))
                    .append(",\"intensity_sum\":").append(e.intensitySum()).append(",\"peak_mz\":[");
            for (int j = 0; j < e.peakMz().size(); j++) {
                if (j > 0) sb.append(',');
                sb.append(fmt(e.peakMz().get(j), 4));
            }
            sb.append("]}");
        }
        return sb.append("]}\n").toString();
    }

    private static String reviewJson(String group, String family, List<String> runs, List<String> observed,
                                     List<String> missing, double meanMass, double ppm, Double cv, String status) {
        return "{\"group\":\"" + escape(group) + "\",\"family\":\"" + escape(family)
                + "\",\"runs\":" + stringArray(runs) + ",\"observed_runs\":" + stringArray(observed)
                + ",\"missing_runs\":" + stringArray(missing) + ",\"mean_neutral_mass\":"
                + (Double.isNaN(meanMass) ? "null" : fmt(round(meanMass, 5), 5)) + ",\"ppm_span\":"
                + fmt(ppm, 2) + ",\"intensity_cv\":" + (cv == null ? "null" : fmt(cv, 4))
                + ",\"status\":\"" + status + "\"}";
    }

    private static String reviewRootJson(List<String> reviews, int groupCount, int reviewCount, Map<String, Integer> counts) {
        StringBuilder sb = new StringBuilder("{\"groups\":[");
        for (int i = 0; i < reviews.size(); i++) {
            if (i > 0) sb.append(',');
            sb.append(reviews.get(i));
        }
        sb.append("],\"summary\":{\"group_count\":").append(groupCount)
                .append(",\"family_review_count\":").append(reviewCount)
                .append(",\"stable_count\":").append(counts.getOrDefault("stable", 0))
                .append(",\"drift_count\":").append(counts.getOrDefault("drift", 0))
                .append(",\"unstable_intensity_count\":").append(counts.getOrDefault("unstable_intensity", 0))
                .append(",\"missing_count\":").append(counts.getOrDefault("missing", 0))
                .append("}}\n");
        return sb.toString();
    }

    private static String stringArray(List<String> values) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) sb.append(',');
            sb.append('"').append(escape(values.get(i))).append('"');
        }
        return sb.append(']').toString();
    }

    private static Path required(Map<String, String> opts, String key) {
        String value = opts.get(key);
        if (value == null || value.isBlank()) {
            die("missing --" + key);
        }
        return Path.of(value);
    }

    private static void write(Path path, String content) throws IOException {
        if (path.getParent() != null) {
            Files.createDirectories(path.getParent());
        }
        Files.writeString(path, content);
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static String fmt(double value, int places) {
        return String.format(Locale.ROOT, "%." + places + "f", value);
    }

    private static double round(double value, int places) {
        double scale = Math.pow(10.0, places);
        return Math.round(value * scale) / scale;
    }

    private static void die(String message) {
        System.err.println(message);
        System.exit(2);
    }
}
JAVA
perl -0pi -e 's/case "review" -> review\(opts\);/case "review" -> die("review not implemented in milestone 2");/' /app/src/MassSpec.java
echo 2 > /app/.msreport_milestone
make clean all
