#!/bin/bash
# Oracle solution for milestone 3: ffmpeg remux + six-rule HLS validator
# chain + audit list.
set -euo pipefail

# ---------------------------------------------------------------------------
# FfmpegMux.java
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/FfmpegMux.java <<'JAVA'
package com.evidence.recovery;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

public class FfmpegMux {

  public String remux(List<Path> segments, Path outMp4) {
    try {
      Path list = Files.createTempFile("concat-", ".txt");
      try (BufferedWriter w = Files.newBufferedWriter(list)) {
        for (Path s : segments) {
          w.write("file '" + s.toAbsolutePath().toString() + "'\n");
        }
      }
      List<String> argv = Arrays.asList(
          "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
          "-fflags", "+bitexact",
          "-f", "concat", "-safe", "0",
          "-i", list.toAbsolutePath().toString(),
          "-flags", "+bitexact",
          "-map_metadata", "-1",
          "-c", "copy", outMp4.toAbsolutePath().toString());
      ProcessBuilder pb = new ProcessBuilder(argv).redirectErrorStream(true);
      Process p = pb.start();
      StringBuilder log = new StringBuilder();
      try (BufferedReader r = new BufferedReader(
          new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
        String line;
        while ((line = r.readLine()) != null) {
          log.append(line).append("\n");
        }
      }
      int rc = p.waitFor();
      if (rc != 0 || !Files.exists(outMp4) || Files.size(outMp4) == 0) {
        throw new FfmpegFailedException("ffmpeg rc=" + rc + " log=" + log);
      }
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      byte[] bytes = Files.readAllBytes(outMp4);
      return HexUtil.hex(md.digest(bytes));
    } catch (IOException | InterruptedException | java.security.NoSuchAlgorithmException e) {
      throw new FfmpegFailedException(e.getMessage());
    }
  }

  public static class FfmpegFailedException extends RuntimeException {
    public FfmpegFailedException(String msg) { super(msg); }
  }
}
JAVA

# ---------------------------------------------------------------------------
# HlsValidator.java - six rules. We accept an override manifest dir so the
# verifier can drop case-specific manifest mutations into /tmp and re-run.
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/HlsValidator.java <<'JAVA'
package com.evidence.recovery;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.sql.*;
import java.util.*;
import java.util.regex.*;

public class HlsValidator {

  static final Set<String> RULES = new LinkedHashSet<>(Arrays.asList(
      "byte_range_parse",
      "key_uri_format",
      "iv_pinning",
      "ext_x_key_scope",
      "segment_encryption_rotation",
      "codec_private_integrity"));

  public boolean validate(String rule, String playlistId, String manifestsDir,
      String segmentsDir, String jdbcUrl) {
    if (!RULES.contains(rule)) {
      throw new ValidatorUnknownException(rule);
    }
    Path m = Paths.get(manifestsDir, playlistId + ".m3u8");
    List<String> lines;
    try {
      lines = Files.readAllLines(m, StandardCharsets.UTF_8);
    } catch (java.io.IOException e) {
      return false;
    }
    switch (rule) {
      case "byte_range_parse":          return checkByteRange(lines);
      case "key_uri_format":            return checkKeyUri(lines);
      case "iv_pinning":                return checkIvPinning(lines, playlistId, jdbcUrl);
      case "ext_x_key_scope":           return checkKeyScope(lines);
      case "segment_encryption_rotation": return checkRotation(lines, playlistId, jdbcUrl);
      case "codec_private_integrity":   return checkCodecPrivate(lines, playlistId, segmentsDir, jdbcUrl);
      default:                          throw new ValidatorUnknownException(rule);
    }
  }

  static final Pattern BYTERANGE = Pattern.compile(
      "^#EXT-X-BYTERANGE:(\\d+)(?:@(\\d+))?$");

  boolean checkByteRange(List<String> lines) {
    boolean any = false;
    for (String l : lines) {
      if (!l.startsWith("#EXT-X-BYTERANGE:")) continue;
      any = true;
      Matcher mm = BYTERANGE.matcher(l);
      if (!mm.matches()) return false;
      long len = Long.parseLong(mm.group(1));
      if (len <= 0) return false;
      if (mm.group(2) != null) {
        long off = Long.parseLong(mm.group(2));
        if (off < 0) return false;
      }
    }
    // manifests with no byte-range directive pass trivially.
    return true;
  }

  static final Pattern KEYURI = Pattern.compile(
      "^key://([a-z0-9_-]{1,32})/([1-9][0-9]{0,3})$");

  boolean checkKeyUri(List<String> lines) {
    String firstPid = null;
    int prevKv = -1;
    int seen = 0;
    for (String l : lines) {
      if (!l.startsWith("#EXT-X-KEY:")) continue;
      Map<String, String> attr = parseAttrs(l.substring("#EXT-X-KEY:".length()));
      if (!"AES-128".equals(attr.get("METHOD")) && !"NONE".equals(attr.get("METHOD"))) {
        return false;
      }
      if ("NONE".equals(attr.get("METHOD"))) { seen++; continue; }
      String uri = attr.get("URI");
      if (uri == null) return false;
      uri = stripQuotes(uri);
      Matcher mm = KEYURI.matcher(uri);
      if (!mm.matches()) return false;
      String pid = mm.group(1);
      int kv = Integer.parseInt(mm.group(2));
      if (firstPid == null) { firstPid = pid; }
      else if (!firstPid.equals(pid)) { return false; }
      if (kv <= prevKv) return false;
      prevKv = kv;
      seen++;
    }
    return seen > 0;
  }

  boolean checkIvPinning(List<String> lines, String playlistId, String jdbcUrl) {
    Map<Integer, String> expected = loadIvByVersion(playlistId, jdbcUrl);
    int curKv = -1;
    int seen = 0;
    for (String l : lines) {
      if (!l.startsWith("#EXT-X-KEY:")) continue;
      Map<String, String> attr = parseAttrs(l.substring("#EXT-X-KEY:".length()));
      if (!"AES-128".equals(attr.get("METHOD"))) continue;
      String uri = stripQuotes(attr.get("URI"));
      Matcher mm = KEYURI.matcher(uri);
      if (!mm.matches()) return false;
      curKv = Integer.parseInt(mm.group(2));
      String iv = attr.get("IV");
      if (iv == null) return false;
      if (!iv.startsWith("0x")) return false;
      String hex = iv.substring(2);
      if (!hex.matches("[0-9a-f]{32}")) return false;
      String want = expected.get(curKv);
      if (want == null || !want.equals(hex)) return false;
      seen++;
    }
    return seen > 0;
  }

  boolean checkKeyScope(List<String> lines) {
    boolean keyInScope = false;
    boolean seenExtInf = false;
    for (String l : lines) {
      if (l.startsWith("#EXT-X-KEY:")) {
        Map<String, String> attr = parseAttrs(l.substring("#EXT-X-KEY:".length()));
        String method = attr.get("METHOD");
        if ("AES-128".equals(method)) keyInScope = true;
        else if ("NONE".equals(method)) keyInScope = false;
        else return false;
      } else if (l.startsWith("#EXTINF:")) {
        seenExtInf = true;
        if (!keyInScope) return false;
      }
    }
    return seenExtInf;
  }

  boolean checkRotation(List<String> lines, String playlistId, String jdbcUrl) {
    Set<Integer> versionsInDb = loadIvByVersion(playlistId, jdbcUrl).keySet();
    List<Integer> keyOrder = new ArrayList<>();
    Map<Integer, Integer> segmentsAfterKv = new HashMap<>();
    int curKv = -1;
    for (String l : lines) {
      if (l.startsWith("#EXT-X-KEY:")) {
        Map<String, String> attr = parseAttrs(l.substring("#EXT-X-KEY:".length()));
        if (!"AES-128".equals(attr.get("METHOD"))) continue;
        String uri = stripQuotes(attr.get("URI"));
        Matcher mm = KEYURI.matcher(uri);
        if (!mm.matches()) return false;
        int kv = Integer.parseInt(mm.group(2));
        if (!keyOrder.isEmpty() && kv <= keyOrder.get(keyOrder.size() - 1)) return false;
        keyOrder.add(kv);
        curKv = kv;
        segmentsAfterKv.put(kv, 0);
      } else if (l.startsWith("#EXTINF:") && curKv > 0) {
        segmentsAfterKv.merge(curKv, 1, Integer::sum);
      }
    }
    if (keyOrder.size() < 2) {
      // Rotation rule is only meaningful when at least two key versions are
      // declared. A single-key manifest is trivially valid.
      return keyOrder.size() == 1 && segmentsAfterKv.getOrDefault(keyOrder.get(0), 0) > 0;
    }
    for (int kv : keyOrder) {
      if (!versionsInDb.contains(kv)) return false;
      if (segmentsAfterKv.getOrDefault(kv, 0) < 1) return false;
    }
    return true;
  }

  boolean checkCodecPrivate(List<String> lines, String playlistId, String segmentsDir,
      String jdbcUrl) {
    String expected = loadCodecPrivateSha(playlistId, jdbcUrl);
    if (expected == null || expected.isEmpty()) return false;
    String firstSeg = null;
    for (String l : lines) {
      if (l.startsWith("#") || l.trim().isEmpty()) continue;
      firstSeg = l.trim();
      break;
    }
    if (firstSeg == null) return false;
    Path p = Paths.get(segmentsDir, firstSeg);
    if (!Files.exists(p)) return false;
    try {
      byte[] bytes = Files.readAllBytes(p);
      if (bytes.length < 16) return false;
      byte[] codecPriv = Arrays.copyOfRange(bytes, 0, 16);
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      String got = HexUtil.hex(md.digest(codecPriv));
      return expected.equals(got);
    } catch (Exception e) {
      return false;
    }
  }

  // ---------------------------------------------------------------------
  // helpers
  // ---------------------------------------------------------------------

  static Map<String, String> parseAttrs(String s) {
    Map<String, String> out = new LinkedHashMap<>();
    int i = 0;
    StringBuilder key = new StringBuilder();
    StringBuilder val = new StringBuilder();
    boolean inKey = true;
    boolean inQuote = false;
    while (i < s.length()) {
      char c = s.charAt(i++);
      if (inKey) {
        if (c == '=') { inKey = false; continue; }
        key.append(c);
      } else {
        if (c == '"') { inQuote = !inQuote; val.append(c); continue; }
        if (c == ',' && !inQuote) {
          out.put(key.toString().trim(), val.toString().trim());
          key.setLength(0); val.setLength(0); inKey = true;
          continue;
        }
        val.append(c);
      }
    }
    if (key.length() > 0 || val.length() > 0) {
      out.put(key.toString().trim(), val.toString().trim());
    }
    return out;
  }

  static String stripQuotes(String s) {
    if (s == null) return null;
    if (s.length() >= 2 && s.startsWith("\"") && s.endsWith("\"")) {
      return s.substring(1, s.length() - 1);
    }
    return s;
  }

  Map<Integer, String> loadIvByVersion(String playlistId, String jdbcUrl) {
    Map<Integer, String> out = new HashMap<>();
    try (Connection c = DriverManager.getConnection(jdbcUrl, "sa", "");
         PreparedStatement ps = c.prepareStatement(
             "SELECT key_version, iv_hex FROM wrapped_keys WHERE playlist_id=?")) {
      ps.setString(1, playlistId);
      try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
          out.put(rs.getInt(1), rs.getString(2));
        }
      }
    } catch (SQLException e) {
      throw new RuntimeException(e);
    }
    return out;
  }

  String loadCodecPrivateSha(String playlistId, String jdbcUrl) {
    try (Connection c = DriverManager.getConnection(jdbcUrl, "sa", "");
         PreparedStatement ps = c.prepareStatement(
             "SELECT codec_private_sha256 FROM playlists WHERE playlist_id=?")) {
      ps.setString(1, playlistId);
      try (ResultSet rs = ps.executeQuery()) {
        if (rs.next()) return rs.getString(1);
        return null;
      }
    } catch (SQLException e) {
      throw new RuntimeException(e);
    }
  }

  public static class ValidatorUnknownException extends RuntimeException {
    public ValidatorUnknownException(String rule) { super(rule); }
  }
}
JAVA

# ---------------------------------------------------------------------------
# RecoveryMain.java - full router with M1+M2+M3 subcommands. (Replaces M2
# version.)
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/RecoveryMain.java <<'JAVA'
package com.evidence.recovery;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.sql.*;
import java.util.*;

public class RecoveryMain {

  public static void main(String[] args) {
    if (args.length == 0) { err("usage", "missing subcommand"); System.exit(1); }
    String sub = args[0];
    try {
      switch (sub) {
        case "init":           cmdInit(); break;
        case "recover-config": cmdRecoverConfig(); break;
        case "decrypt":
          if (args.length < 2) { err("usage", "decrypt needs segment_index"); System.exit(1); }
          cmdDecrypt(Integer.parseInt(args[1])); break;
        case "decrypt-all":    cmdDecryptAll(); break;
        case "remux":
          if (args.length < 2) { err("usage", "remux needs playlist_id"); System.exit(1); }
          cmdRemux(args[1]); break;
        case "validate":
          if (args.length < 2) { err("usage", "validate needs rule"); System.exit(1); }
          cmdValidate(args[1], args.length > 2 ? args[2] : "cam001"); break;
        case "audit":
          if (args.length < 2 || !"list".equals(args[1])) { err("usage", "audit list"); System.exit(1); }
          cmdAuditList(); break;
        default:
          err("usage", "unknown subcommand: " + sub); System.exit(1);
      }
    } catch (EvidenceDb.SigMismatchException sm) {
      err("sig_mismatch", sm.getMessage()); System.exit(1);
    } catch (RecoveryConfig.ConfigCorruptException cc) {
      err("config_corrupt", cc.getMessage()); System.exit(1);
    } catch (SegmentDecryptor.DecryptFailedException df) {
      err("decrypt_failed", df.getMessage()); System.exit(1);
    } catch (HlsValidator.ValidatorUnknownException vu) {
      err("validator_unknown", vu.getMessage()); System.exit(1);
    } catch (FfmpegMux.FfmpegFailedException ff) {
      err("ffmpeg_failed", ff.getMessage()); System.exit(1);
    } catch (UnwrapFailed u) {
      err("unwrap_failed", u.getMessage()); System.exit(1);
    } catch (SegmentUnknown su) {
      err("segment_unknown", su.getMessage()); System.exit(1);
    } catch (PlaylistUnknown pu) {
      err("playlist_unknown", pu.getMessage()); System.exit(1);
    } catch (MissingSegments ms) {
      err("missing_segments", ms.getMessage()); System.exit(1);
    } catch (Exception e) {
      err("usage", e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage());
      System.exit(1);
    }
  }

  // -----------------------------------------------------------------------
  // M1
  // -----------------------------------------------------------------------

  static void cmdInit() {
    String jdbcUrl = jdbc();
    EvidenceDb db = new EvidenceDb();
    db.init(jdbcUrl);
    byte[] master = master();
    int n = db.seedFromJson(jdbcUrl, "/app/data/wrapped_keys.json", master);
    Map<String, Object> out = new TreeMap<>();
    out.put("db", jdbcUrl.replace("jdbc:h2:file:", ""));
    out.put("seeded_keys", n);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
  }

  static void cmdRecoverConfig() {
    List<String> r = new RecoveryConfig().repair("/app/data/recovery_config.json");
    Map<String, Object> out = new TreeMap<>();
    out.put("repaired", r);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
  }

  // -----------------------------------------------------------------------
  // M2
  // -----------------------------------------------------------------------

  static void cmdDecrypt(int segIndex) throws Exception {
    Result r = decryptOne(segIndex);
    Map<String, Object> out = new TreeMap<>();
    out.put("audit_id", r.auditId);
    out.put("bytes", r.bytes);
    out.put("segment", segIndex);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
  }

  static void cmdDecryptAll() throws Exception {
    List<Map<String, Object>> idx = loadIndex();
    int allowed = 0, denied = 0;
    for (Map<String, Object> e : idx) {
      int segIdx = ((Number) e.get("segment_index")).intValue();
      try { decryptOne(segIdx); allowed++; }
      catch (Exception ex) {
        denied++;
        new AuditLog().append(jdbc(), nowMs(), "recovery-cli", "decrypt",
            String.valueOf(segIdx), "deny", master());
      }
    }
    Map<String, Object> out = new TreeMap<>();
    out.put("allowed", allowed);
    out.put("denied", denied);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
  }

  static Result decryptOne(int segIndex) throws Exception {
    List<Map<String, Object>> idx = loadIndex();
    Map<String, Object> hit = null;
    for (Map<String, Object> e : idx) {
      if (((Number) e.get("segment_index")).intValue() == segIndex) { hit = e; break; }
    }
    if (hit == null) throw new SegmentUnknown("segment " + segIndex);
    String pid = (String) hit.get("playlist_id");
    String segFile = (String) hit.get("segment_filename");

    String wrapped, iv, sig; int keyVersion;
    try (Connection c = DriverManager.getConnection(jdbc(), "sa", "");
         PreparedStatement ps = c.prepareStatement(
             "SELECT key_version, wrapped_key_hex, iv_hex, sig_hex"
                 + " FROM wrapped_keys WHERE playlist_id=? ORDER BY key_version DESC LIMIT 1")) {
      ps.setString(1, pid);
      try (ResultSet rs = ps.executeQuery()) {
        if (!rs.next()) throw new PlaylistUnknown(pid);
        keyVersion = rs.getInt(1);
        wrapped = rs.getString(2); iv = rs.getString(3); sig = rs.getString(4);
      }
    }

    byte[] master = master();
    KeyStore ks = new KeyStore();
    String canon = pid + "|" + keyVersion + "|" + wrapped + "|" + iv;
    String expSig = HexUtil.hex(ks.hmacSha256(master, canon.getBytes(StandardCharsets.UTF_8)));
    if (!expSig.equals(sig)) {
      new AuditLog().append(jdbc(), nowMs(), "recovery-cli", "decrypt",
          String.valueOf(segIndex), "deny", master);
      throw new EvidenceDb.SigMismatchException("segment=" + segIndex);
    }
    byte[] content;
    try { content = ks.unwrap(master, HexUtil.unhex(wrapped)); }
    catch (Exception ue) {
      new AuditLog().append(jdbc(), nowMs(), "recovery-cli", "decrypt",
          String.valueOf(segIndex), "deny", master);
      throw new UnwrapFailed(ue.getMessage());
    }
    Path encPath = Paths.get(hlsRoot(), "segments", segFile + ".enc");
    if (!Files.exists(encPath)) {
      new AuditLog().append(jdbc(), nowMs(), "recovery-cli", "decrypt",
          String.valueOf(segIndex), "deny", master);
      throw new SegmentUnknown("ciphertext missing: " + encPath);
    }
    byte[] cipher = Files.readAllBytes(encPath);
    byte[] plain;
    try { plain = new SegmentDecryptor().decrypt(content, HexUtil.unhex(iv), cipher); }
    catch (SegmentDecryptor.DecryptFailedException df) {
      new AuditLog().append(jdbc(), nowMs(), "recovery-cli", "decrypt",
          String.valueOf(segIndex), "deny", master);
      throw df;
    }
    Files.write(Paths.get(hlsRoot(), "segments", segFile), plain);
    int auditId = new AuditLog().append(jdbc(), nowMs(), "recovery-cli", "decrypt",
        String.valueOf(segIndex), "allow", master);
    Result r = new Result(); r.auditId = auditId; r.bytes = plain.length; return r;
  }

  // -----------------------------------------------------------------------
  // M3
  // -----------------------------------------------------------------------

  static void cmdRemux(String playlistId) throws Exception {
    List<Map<String, Object>> idx = loadIndex();
    List<Path> segs = new ArrayList<>();
    for (Map<String, Object> e : idx) {
      if (playlistId.equals(e.get("playlist_id"))) {
        Path p = Paths.get(hlsRoot(), "segments", (String) e.get("segment_filename"));
        if (!Files.exists(p)) {
          new AuditLog().append(jdbc(), nowMs(), "recovery-cli", "remux",
              playlistId, "deny", master());
          throw new MissingSegments(p.toString());
        }
        segs.add(p);
      }
    }
    if (segs.isEmpty()) throw new PlaylistUnknown(playlistId);
    Files.createDirectories(Paths.get(artifactsRoot()));
    Path outMp4 = Paths.get(artifactsRoot(), playlistId + ".mp4");
    String sha = new FfmpegMux().remux(segs, outMp4);
    long created = nowMs();
    int artifactId;
    try (Connection c = DriverManager.getConnection(jdbc(), "sa", "");
         PreparedStatement ps = c.prepareStatement(
             "INSERT INTO artifacts(playlist_id, mp4_path, sha256, created_ms) VALUES(?,?,?,?)",
             Statement.RETURN_GENERATED_KEYS)) {
      ps.setString(1, playlistId);
      ps.setString(2, outMp4.toString());
      ps.setString(3, sha);
      ps.setLong(4, created);
      ps.executeUpdate();
      try (ResultSet rs = ps.getGeneratedKeys()) {
        rs.next();
        artifactId = rs.getInt(1);
      }
    }
    new AuditLog().append(jdbc(), created, "recovery-cli", "remux",
        playlistId, "allow", master());
    Map<String, Object> out = new TreeMap<>();
    out.put("artifact_id", artifactId);
    out.put("playlist_id", playlistId);
    out.put("sha256", sha);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
  }

  static void cmdValidate(String rule, String playlistId) throws Exception {
    String canonicalManifestsDir = hlsRoot() + "/manifests";
    String manifestsDir = System.getenv().getOrDefault("HLS_MANIFESTS_DIR",
        canonicalManifestsDir);
    String segmentsDir = System.getenv().getOrDefault("HLS_SEGMENTS_DIR",
        hlsRoot() + "/segments");
    boolean valid = new HlsValidator().validate(rule, playlistId, manifestsDir,
        segmentsDir, jdbc());
    // Per spec (steps/milestone_3/instruction.md): "Invalid cases MUST NOT
    // mutate the playlist's audit_validator_sha256 chain on cam001 because
    // the verifier injects them against scratch playlists in /tmp." We
    // implement this by only folding the result into the chain when the
    // manifest input is the canonical /app/data/hls_export/manifests dir.
    // Scratch overrides (any other HLS_MANIFESTS_DIR) are non-canonical and
    // do not mutate the persisted playlist chain.
    boolean canonicalInput = java.nio.file.Paths.get(manifestsDir).toAbsolutePath()
        .normalize().equals(
            java.nio.file.Paths.get(canonicalManifestsDir).toAbsolutePath().normalize());
    String newChain;
    try (Connection c = DriverManager.getConnection(jdbc(), "sa", "")) {
      String prev;
      try (PreparedStatement ps = c.prepareStatement(
          "SELECT audit_validator_sha256 FROM playlists WHERE playlist_id=?")) {
        ps.setString(1, playlistId);
        try (ResultSet rs = ps.executeQuery()) {
          if (!rs.next()) throw new PlaylistUnknown(playlistId);
          prev = rs.getString(1);
          if (prev == null) prev = "";
        }
      }
      String canon = prev + "|" + rule + "|" + (valid ? "1" : "0");
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      newChain = HexUtil.hex(md.digest(canon.getBytes(StandardCharsets.UTF_8)));
      if (canonicalInput) {
        try (PreparedStatement ps = c.prepareStatement(
            "UPDATE playlists SET audit_validator_sha256=? WHERE playlist_id=?")) {
          ps.setString(1, newChain);
          ps.setString(2, playlistId);
          ps.executeUpdate();
        }
      }
    }
    new AuditLog().append(jdbc(), nowMs(), "recovery-cli", "validate",
        rule + ":" + playlistId, valid ? "allow" : "deny", master());
    Map<String, Object> out = new TreeMap<>();
    out.put("rule", rule);
    out.put("valid", valid);
    out.put("validator_sha256", newChain);
    System.out.println(JsonOut.encode(out));
  }

  static void cmdAuditList() throws Exception {
    List<Map<String, Object>> rows = new ArrayList<>();
    try (Connection c = DriverManager.getConnection(jdbc(), "sa", "");
         Statement s = c.createStatement();
         ResultSet rs = s.executeQuery(
             "SELECT seq, ts_epoch_ms, actor, action, target, decision,"
                 + " prev_hash, entry_hash FROM audit_log ORDER BY seq")) {
      while (rs.next()) {
        Map<String, Object> r = new TreeMap<>();
        r.put("action", rs.getString("action"));
        r.put("actor", rs.getString("actor"));
        r.put("decision", rs.getString("decision"));
        r.put("entry_hash", rs.getString("entry_hash"));
        r.put("prev_hash", rs.getString("prev_hash"));
        r.put("seq", rs.getInt("seq"));
        r.put("target", rs.getString("target"));
        r.put("ts_epoch_ms", rs.getLong("ts_epoch_ms"));
        rows.add(r);
      }
    }
    Map<String, Object> out = new TreeMap<>();
    out.put("count", rows.size());
    out.put("entries", rows);
    System.out.println(JsonOut.encode(out));
  }

  // -----------------------------------------------------------------------
  // helpers
  // -----------------------------------------------------------------------

  @SuppressWarnings("unchecked")
  static List<Map<String, Object>> loadIndex() throws Exception {
    String raw = new String(Files.readAllBytes(Paths.get("/app/data/segment_index.json")),
        StandardCharsets.UTF_8);
    return (List<Map<String, Object>>) (List<?>) MiniJson.parse(raw);
  }

  static String jdbc() {
    return System.getenv().getOrDefault("EVIDENCE_DB",
        "jdbc:h2:file:/app/data/evidence");
  }
  static String hlsRoot() { return System.getenv().getOrDefault("HLS_INPUT", "/app/data/hls_export"); }
  static String artifactsRoot() { return System.getenv().getOrDefault("ARTIFACTS", "/app/data/artifacts"); }
  static byte[] master() {
    String mp = System.getenv().getOrDefault("MASTER_KEY", "/opt/evidence_keys/master.key.hex");
    return new KeyStore().loadMasterKey(mp);
  }
  static long nowMs() {
    String ov = System.getenv("RECOVERY_NOW_OVERRIDE");
    if (ov != null && !ov.isEmpty()) return Long.parseLong(ov);
    return System.currentTimeMillis();
  }
  static void err(String code, String message) {
    Map<String, Object> e = new TreeMap<>();
    e.put("error", code);
    e.put("message", message == null ? "" : message);
    System.err.println(JsonOut.encode(e));
  }
  static class Result { int auditId; int bytes; }
  static class UnwrapFailed extends RuntimeException { UnwrapFailed(String s) { super(s); } }
  static class SegmentUnknown extends RuntimeException { SegmentUnknown(String s) { super(s); } }
  static class PlaylistUnknown extends RuntimeException { PlaylistUnknown(String s) { super(s); } }
  static class MissingSegments extends RuntimeException { MissingSegments(String s) { super(s); } }
}
JAVA

rm -rf /app/build
mkdir -p /app/build
javac -cp "/opt/jars/*" -d /app/build /app/src/com/evidence/recovery/*.java
