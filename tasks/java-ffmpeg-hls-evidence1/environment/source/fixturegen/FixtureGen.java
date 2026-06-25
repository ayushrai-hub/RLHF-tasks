package fixturegen;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Build the deterministic fixture set the task depends on.
 *
 * Args:
 *   0 - master key hex path (64-char file)
 *   1 - data dir (writable)            : wrapped_keys.json, recovery_config.json,
 *                                        segment_index.json, hls_export/
 *   2 - fixtures dir (writable)        : expected_validators.json,
 *                                        validator_cases.json,
 *                                        expected_decrypt.json,
 *                                        expected_recovery_config.json
 *   3 - plain segments dir             : seven valid MPEG-TS plaintext
 *                                        files staged by the Dockerfile
 *                                        (0000.ts .. 0006.ts).
 *   4 - seed (long)                    : base unix-second seed (used for
 *                                        IV randomness).
 */
public class FixtureGen {

  public static void main(String[] args) throws Exception {
    if (args.length < 5) {
      throw new IllegalArgumentException(
          "Usage: FixtureGen <master_key_hex_path> <data_dir> <fixtures_dir>"
              + " <plain_segments_dir> <seed>");
    }
    Path masterKeyHexPath = Paths.get(args[0]);
    Path dataDir = Paths.get(args[1]);
    Path fixturesDir = Paths.get(args[2]);
    Path plainSegmentsDir = Paths.get(args[3]);
    long seed = Long.parseLong(args[4]);

    byte[] masterKey = unhex(new String(Files.readAllBytes(masterKeyHexPath),
        StandardCharsets.UTF_8).trim());
    if (masterKey.length != 32) {
      throw new IllegalStateException("master key must be 32 bytes hex");
    }

    Files.createDirectories(dataDir);
    Files.createDirectories(dataDir.resolve("hls_export").resolve("manifests"));
    Files.createDirectories(dataDir.resolve("hls_export").resolve("segments"));
    Files.createDirectories(fixturesDir);

    Random rng = new Random(seed);
    List<Playlist> playlists = new ArrayList<>();
    // Three "real" playlists used end-to-end by recover / decrypt / remux /
    // validate. Each one gets its own wrapped content key, its own IV, and
    // its own segment count. We keep segment counts small (2-3) so the
    // remux step runs in seconds. Plain TS bytes come from the staging dir.
    int[] segIdxAlloc = {0};
    playlists.add(build(rng, "cam001", 1, 3, masterKey, plainSegmentsDir, segIdxAlloc));
    playlists.add(build(rng, "cam002", 1, 2, masterKey, plainSegmentsDir, segIdxAlloc));
    playlists.add(build(rng, "cam003", 1, 2, masterKey, plainSegmentsDir, segIdxAlloc));

    // wrapped_keys.json - input to `init` seeding.
    List<Map<String, Object>> rows = new ArrayList<>();
    for (Playlist p : playlists) {
      Map<String, Object> r = new LinkedHashMap<>();
      r.put("codec_private_sha256", sha256Hex(p.codecPrivate));
      r.put("iv_hex", hex(p.iv));
      r.put("key_version", p.keyVersion);
      r.put("manifest_path", "manifests/" + p.id + ".m3u8");
      r.put("playlist_id", p.id);
      r.put("segment_count", p.segments.size());
      r.put("sig_hex", p.sigHex);
      r.put("wrapped_key_hex", p.wrappedHex);
      rows.add(r);
    }
    writeText(dataDir.resolve("wrapped_keys.json"), prettyJson(rows));

    // recovery_config.json - broken values the agent must repair.
    Map<String, Object> broken = new LinkedHashMap<>();
    broken.put("master_key_path", "/etc/keys/master.bin");
    broken.put("key_wrap_algorithm", "AES-GCM-256");
    broken.put("segment_cipher", "AES-256-CTR");
    broken.put("segment_padding", "none");
    broken.put("audit_log_table", "audit");
    writeText(dataDir.resolve("recovery_config.json"), prettyJson(broken));

    // expected_recovery_config.json - what the agent should produce.
    Map<String, Object> good = new TreeMap<>();
    good.put("audit_log_table", "audit_log");
    good.put("key_wrap_algorithm", "AES-KW-256");
    good.put("master_key_path", "/opt/evidence_keys/master.key.hex");
    good.put("segment_cipher", "AES-128-CBC");
    good.put("segment_padding", "PKCS#7");
    writeText(fixturesDir.resolve("expected_recovery_config.json"), prettyJson(good));

    // segment_index.json - maps (segment_index -> playlist_id, key_version,
    // segment_filename, original_plaintext_sha256). globalIdx is assigned
    // here so we can fill in manifest segment filenames once they are
    // known.
    List<Map<String, Object>> segIdx = new ArrayList<>();
    int globalIdx = 0;
    for (Playlist p : playlists) {
      for (int s = 0; s < p.segments.size(); s++) {
        Segment seg = p.segments.get(s);
        Map<String, Object> e = new LinkedHashMap<>();
        e.put("playlist_id", p.id);
        e.put("plaintext_sha256", sha256Hex(seg.plaintext));
        e.put("segment_filename", String.format("%04d.ts", globalIdx));
        e.put("segment_index", globalIdx);
        seg.globalIndex = globalIdx;
        segIdx.add(e);
        // Write the encrypted segment to disk.
        Path encPath = dataDir.resolve("hls_export").resolve("segments")
            .resolve(String.format("%04d.ts.enc", globalIdx));
        Files.write(encPath, seg.ciphertext);
        globalIdx++;
      }
    }
    writeText(dataDir.resolve("segment_index.json"), prettyJson(segIdx));

    // Manifest .m3u8 files - rebuild now that segment filenames are known.
    for (Playlist p : playlists) {
      StringBuilder sb = new StringBuilder();
      sb.append("#EXTM3U\n");
      sb.append("#EXT-X-VERSION:3\n");
      sb.append("#EXT-X-TARGETDURATION:10\n");
      sb.append("#EXT-X-MEDIA-SEQUENCE:0\n");
      sb.append("#EXT-X-KEY:METHOD=AES-128,URI=\"key://").append(p.id).append("/")
          .append(p.keyVersion).append("\",IV=0x").append(hex(p.iv)).append("\n");
      for (Segment seg : p.segments) {
        sb.append("#EXTINF:6.000,\n");
        sb.append(String.format("%04d.ts\n", seg.globalIndex));
      }
      sb.append("#EXT-X-ENDLIST\n");
      p.manifestText = sb.toString();
      Path m = dataDir.resolve("hls_export").resolve("manifests")
          .resolve(p.id + ".m3u8");
      Files.write(m, p.manifestText.getBytes(StandardCharsets.UTF_8));
    }

    // expected_decrypt.json - per-segment plaintext sha + byte length so the
    // verifier can sanity-check `decrypt`.
    List<Map<String, Object>> expDecrypt = new ArrayList<>();
    for (Playlist p : playlists) {
      for (Segment seg : p.segments) {
        Map<String, Object> e = new LinkedHashMap<>();
        e.put("bytes", seg.plaintext.length);
        e.put("playlist_id", p.id);
        e.put("plaintext_sha256", sha256Hex(seg.plaintext));
        e.put("segment_index", seg.globalIndex);
        expDecrypt.add(e);
      }
    }
    writeText(fixturesDir.resolve("expected_decrypt.json"), prettyJson(expDecrypt));

    // validator_cases.json - 24 (2 valid + 2 invalid) per rule across 6 rules.
    // Each case is described by (rule, fixture_playlist_id, expected_valid).
    // The verifier writes the manifest variant into /tmp before invocation.
    String[] rules = {
        "byte_range_parse", "key_uri_format", "iv_pinning",
        "ext_x_key_scope", "segment_encryption_rotation",
        "codec_private_integrity"
    };
    List<Map<String, Object>> vCases = new ArrayList<>();
    for (String rule : rules) {
      for (int k = 0; k < 4; k++) {
        Map<String, Object> e = new LinkedHashMap<>();
        e.put("case_id", rule + "_" + (k < 2 ? "good" : "bad") + (k % 2));
        e.put("expected_valid", k < 2);
        e.put("rule", rule);
        vCases.add(e);
      }
    }
    writeText(fixturesDir.resolve("validator_cases.json"), prettyJson(vCases));

    // expected_validators.json - what playlists.audit_validator_sha256
    // should be after a documented sequence of validate() calls. The
    // sequence the verifier exercises is each rule once against cam001
    // with the natural fixture (all good); each call returns true and the
    // chain folds in '1'.
    String chain = "";
    List<Map<String, Object>> expChain = new ArrayList<>();
    for (String rule : rules) {
      String msg = chain + "|" + rule + "|1";
      chain = sha256Hex(msg.getBytes(StandardCharsets.UTF_8));
      Map<String, Object> step = new LinkedHashMap<>();
      step.put("after_validator_sha256", chain);
      step.put("rule", rule);
      step.put("valid", true);
      expChain.add(step);
    }
    Map<String, Object> chainOut = new LinkedHashMap<>();
    chainOut.put("final_validator_sha256", chain);
    chainOut.put("playlist_id", "cam001");
    chainOut.put("rules_in_order", Arrays.asList(rules));
    chainOut.put("steps", expChain);
    writeText(fixturesDir.resolve("expected_validators.json"), prettyJson(chainOut));

    // Pointer file the verifier reads to learn which playlists exist and
    // their per-playlist expected MP4 sha is intentionally absent - ffmpeg
    // muxing is not byte-deterministic across ffmpeg versions, so we
    // verify the MP4 only by ffprobe-able-and-nonzero-bytes + audit row.
    Map<String, Object> manifestInv = new LinkedHashMap<>();
    List<Map<String, Object>> plArr = new ArrayList<>();
    for (Playlist p : playlists) {
      Map<String, Object> e = new LinkedHashMap<>();
      e.put("playlist_id", p.id);
      e.put("segment_count", p.segments.size());
      e.put("iv_hex", hex(p.iv));
      e.put("key_version", p.keyVersion);
      plArr.add(e);
    }
    manifestInv.put("playlists", plArr);
    writeText(fixturesDir.resolve("playlist_inventory.json"), prettyJson(manifestInv));
  }

  // --------------------------------------------------------------------
  // helpers
  // --------------------------------------------------------------------

  static Playlist build(Random rng, String id, int keyVersion, int segCount,
      byte[] masterKey, Path plainSegmentsDir, int[] segIdxAlloc) throws Exception {
    Playlist p = new Playlist();
    p.id = id;
    p.keyVersion = keyVersion;
    p.contentKey = new byte[16];
    rng.nextBytes(p.contentKey);
    p.iv = new byte[16];
    rng.nextBytes(p.iv);

    // Wrap the content key with AES-KW (RFC 3394).
    p.wrappedHex = hex(aesKwWrap(masterKey, p.contentKey));

    // Build segments by consuming the next real TS files from the
    // staging dir. codec_private bytes are simply the first 16 bytes of
    // the first segment's plaintext (validator rule 6 hashes the same
    // window at runtime).
    for (int i = 0; i < segCount; i++) {
      int idxAlloc = segIdxAlloc[0]++;
      Path src = plainSegmentsDir.resolve(String.format("%04d.ts", idxAlloc));
      byte[] plaintext = Files.readAllBytes(src);
      if (plaintext.length < 16) {
        throw new IllegalStateException("staged segment " + src + " < 16 bytes");
      }
      if (i == 0) {
        p.codecPrivate = Arrays.copyOfRange(plaintext, 0, 16);
      }
      Segment seg = new Segment();
      seg.plaintext = plaintext;
      seg.ciphertext = aesCbcEncrypt(p.contentKey, p.iv, plaintext);
      p.segments.add(seg);
    }

    // Signature: HMAC-SHA256 of "playlist_id|key_version|wrapped|iv" keyed
    // by master.
    String canon = p.id + "|" + p.keyVersion + "|" + p.wrappedHex + "|" + hex(p.iv);
    p.sigHex = hex(hmacSha256(masterKey, canon.getBytes(StandardCharsets.UTF_8)));

    // Manifest text.
    StringBuilder sb = new StringBuilder();
    sb.append("#EXTM3U\n");
    sb.append("#EXT-X-VERSION:3\n");
    sb.append("#EXT-X-TARGETDURATION:10\n");
    sb.append("#EXT-X-MEDIA-SEQUENCE:0\n");
    sb.append("#EXT-X-KEY:METHOD=AES-128,URI=\"key://").append(p.id).append("/")
        .append(p.keyVersion).append("\",IV=0x").append(hex(p.iv)).append("\n");
    for (Segment seg : p.segments) {
      sb.append("#EXTINF:6.000,\n");
      sb.append(String.format("%04d.ts\n", seg.globalIndex));
    }
    sb.append("#EXT-X-ENDLIST\n");
    p.manifestText = sb.toString();
    return p;
  }

  static byte[] aesKwWrap(byte[] kek, byte[] plaintext) throws Exception {
    Cipher c = Cipher.getInstance("AESWrap");
    c.init(Cipher.WRAP_MODE, new SecretKeySpec(kek, "AES"));
    return c.wrap(new SecretKeySpec(plaintext, "AES"));
  }

  static byte[] aesCbcEncrypt(byte[] key, byte[] iv, byte[] pt) throws Exception {
    Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");
    c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new IvParameterSpec(iv));
    return c.doFinal(pt);
  }

  static byte[] hmacSha256(byte[] key, byte[] msg) throws Exception {
    Mac m = Mac.getInstance("HmacSHA256");
    m.init(new SecretKeySpec(key, "HmacSHA256"));
    return m.doFinal(msg);
  }

  static String sha256Hex(byte[] bytes) throws Exception {
    MessageDigest md = MessageDigest.getInstance("SHA-256");
    return hex(md.digest(bytes));
  }

  static String hex(byte[] bytes) {
    StringBuilder sb = new StringBuilder(bytes.length * 2);
    for (byte b : bytes) sb.append(String.format("%02x", b & 0xff));
    return sb.toString();
  }

  static byte[] unhex(String s) {
    s = s.trim();
    if (s.length() % 2 != 0) throw new IllegalArgumentException("odd hex");
    byte[] out = new byte[s.length() / 2];
    for (int i = 0; i < out.length; i++) {
      out[i] = (byte) Integer.parseInt(s.substring(i * 2, i * 2 + 2), 16);
    }
    return out;
  }

  static void writeText(Path p, String s) throws IOException {
    try (OutputStream o = Files.newOutputStream(p)) {
      o.write(s.getBytes(StandardCharsets.UTF_8));
    }
  }

  static String prettyJson(Object node) {
    StringBuilder sb = new StringBuilder();
    writePretty(sb, node, 0);
    sb.append('\n');
    return sb.toString();
  }

  static void writePretty(StringBuilder sb, Object node, int depth) {
    if (node == null) {
      sb.append("null");
    } else if (node instanceof Boolean) {
      sb.append(((Boolean) node) ? "true" : "false");
    } else if (node instanceof Number) {
      sb.append(node.toString());
    } else if (node instanceof String) {
      escape(sb, (String) node);
    } else if (node instanceof Map) {
      Map<?, ?> raw = (Map<?, ?>) node;
      TreeMap<String, Object> sorted = new TreeMap<>();
      for (Map.Entry<?, ?> e : raw.entrySet()) {
        sorted.put(String.valueOf(e.getKey()), e.getValue());
      }
      if (sorted.isEmpty()) { sb.append("{}"); return; }
      sb.append("{\n");
      boolean first = true;
      for (Map.Entry<String, Object> e : sorted.entrySet()) {
        if (!first) sb.append(",\n");
        first = false;
        indent(sb, depth + 1);
        escape(sb, e.getKey());
        sb.append(": ");
        writePretty(sb, e.getValue(), depth + 1);
      }
      sb.append("\n");
      indent(sb, depth);
      sb.append("}");
    } else if (node instanceof Iterable) {
      Iterable<?> items = (Iterable<?>) node;
      Iterator<?> it = items.iterator();
      if (!it.hasNext()) { sb.append("[]"); return; }
      sb.append("[\n");
      boolean first = true;
      while (it.hasNext()) {
        if (!first) sb.append(",\n");
        first = false;
        indent(sb, depth + 1);
        writePretty(sb, it.next(), depth + 1);
      }
      sb.append("\n");
      indent(sb, depth);
      sb.append("]");
    } else {
      escape(sb, node.toString());
    }
  }

  static void indent(StringBuilder sb, int depth) {
    for (int i = 0; i < depth; i++) sb.append("  ");
  }

  static void escape(StringBuilder sb, String s) {
    sb.append('"');
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      switch (c) {
        case '"': sb.append("\\\""); break;
        case '\\': sb.append("\\\\"); break;
        case '\n': sb.append("\\n"); break;
        case '\r': sb.append("\\r"); break;
        case '\t': sb.append("\\t"); break;
        default:
          if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
          else sb.append(c);
      }
    }
    sb.append('"');
  }

  static class Playlist {
    String id;
    int keyVersion;
    byte[] contentKey;
    byte[] iv;
    byte[] codecPrivate;
    String wrappedHex;
    String sigHex;
    String manifestText;
    final List<Segment> segments = new ArrayList<>();
  }

  static class Segment {
    byte[] plaintext;
    byte[] ciphertext;
    int globalIndex;
  }
}
