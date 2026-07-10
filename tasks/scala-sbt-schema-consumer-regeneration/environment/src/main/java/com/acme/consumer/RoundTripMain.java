package com.acme.consumer;

import com.acme.rift.SchemaIndexProvider;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.ServiceLoader;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class RoundTripMain {
    private static final Pattern STRING_FIELD = Pattern.compile("\\\"([A-Za-z0-9_]+)\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"");

    private static String field(String text, String key) {
        Matcher matcher = STRING_FIELD.matcher(text);
        while (matcher.find()) {
            if (matcher.group(1).equals(key)) {
                return matcher.group(2);
            }
        }
        return "";
    }

    private static String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] bytes = Files.readAllBytes(path);
        byte[] hashed = digest.digest(bytes);
        StringBuilder out = new StringBuilder();
        for (byte b : hashed) {
            out.append(String.format("%02x", b));
        }
        return out.toString();
    }

    private static String jsonEscape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.err.println("usage: RoundTripMain <report> <schema-index-jar-rel> <fixture>...");
            System.exit(2);
        }
        Path report = Path.of(args[0]);
        String schemaJarRel = args[1];
        Path schemaJar = Path.of(schemaJarRel);
        if (!Files.exists(schemaJar)) {
            schemaJar = Path.of(".").resolve(schemaJarRel).normalize();
        }
        ServiceLoader<SchemaIndexProvider> loader = ServiceLoader.load(SchemaIndexProvider.class);
        Iterator<SchemaIndexProvider> iterator = loader.iterator();
        List<SchemaIndexProvider> providers = new ArrayList<>();
        while (iterator.hasNext()) {
            providers.add(iterator.next());
        }
        if (providers.size() != 1) {
            System.err.println("expected exactly one SchemaIndexProvider, found " + providers.size());
            System.exit(40);
        }
        SchemaIndexProvider provider = providers.get(0);
        Set<String> descriptors = provider.canonicalDescriptors();
        List<String> rows = new ArrayList<>();
        boolean allOk = true;
        for (int i = 2; i < args.length; i++) {
            Path fixture = Path.of(args[i]);
            String text = Files.readString(fixture, StandardCharsets.UTF_8);
            String fixtureId = field(text, "fixture_id");
            String descriptor = field(text, "descriptor");
            String expected = field(text, "expected_descriptor");
            String canonical = provider.canonicalize(descriptor);
            boolean ok = expected.equals(canonical) && provider.supports(canonical);
            allOk = allOk && ok;
            rows.add("{\"fixture\":\"" + jsonEscape(fixture.toString()) + "\","
                + "\"fixture_id\":\"" + jsonEscape(fixtureId) + "\","
                + "\"input_descriptor\":\"" + jsonEscape(descriptor) + "\","
                + "\"expected_descriptor\":\"" + jsonEscape(expected) + "\","
                + "\"canonical_descriptor\":\"" + jsonEscape(canonical) + "\","
                + "\"ok\":" + ok + "}");
        }
        StringBuilder out = new StringBuilder();
        out.append("{\n");
        out.append("  \"schema_index_jar\": \"").append(jsonEscape(schemaJarRel)).append("\",\n");
        out.append("  \"schema_index_jar_sha256\": \"").append(sha256(schemaJar)).append("\",\n");
        out.append("  \"provider_count\": ").append(providers.size()).append(",\n");
        out.append("  \"canonical_descriptor_count\": ").append(descriptors.size()).append(",\n");
        out.append("  \"all_ok\": ").append(allOk).append(",\n");
        out.append("  \"roundtrips\": [\n    ").append(String.join(",\n    ", rows)).append("\n  ]\n");
        out.append("}\n");
        Files.createDirectories(report.getParent());
        Files.writeString(report, out.toString(), StandardCharsets.UTF_8);
        if (!allOk) {
            System.err.println("one or more fixture round-trips did not match the canonical schema index");
            System.exit(41);
        }
    }
}
