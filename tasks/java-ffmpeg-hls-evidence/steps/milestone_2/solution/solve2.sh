#!/bin/bash
# Oracle solution for milestone 2: AES-128 CBC segment decryption +
# tamper-evident audit chain.
set -euo pipefail

# ---------------------------------------------------------------------------
# AuditLog.java - chained HMAC-SHA256 inserts.
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/AuditLog.java <<'JAVA'
package com.evidence.recovery;

import java.nio.charset.StandardCharsets;
import java.sql.*;

public class AuditLog {

  public int append(
      String jdbcUrl,
      long tsEpochMs,
      String actor,
      String action,
      String target,
      String decision,
      byte[] masterKey) {
    try (Connection c = DriverManager.getConnection(jdbcUrl, "sa", "")) {
      String prevHash = "0000000000000000000000000000000000000000000000000000000000000000";
      int nextSeq = 1;
      try (Statement s = c.createStatement();
           ResultSet rs = s.executeQuery(
               "SELECT seq, entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1")) {
        if (rs.next()) {
          nextSeq = rs.getInt(1) + 1;
          prevHash = rs.getString(2);
        }
      }
      String canon = nextSeq + "|" + tsEpochMs + "|" + actor + "|" + action
          + "|" + target + "|" + decision + "|" + prevHash;
      KeyStore ks = new KeyStore();
      String entryHash = HexUtil.hex(ks.hmacSha256(masterKey,
          canon.getBytes(StandardCharsets.UTF_8)));
      try (PreparedStatement ps = c.prepareStatement(
          "INSERT INTO audit_log(seq, ts_epoch_ms, actor, action, target,"
              + " decision, prev_hash, entry_hash) VALUES(?,?,?,?,?,?,?,?)")) {
        ps.setInt(1, nextSeq);
        ps.setLong(2, tsEpochMs);
        ps.setString(3, actor);
        ps.setString(4, action);
        ps.setString(5, target);
        ps.setString(6, decision);
        ps.setString(7, prevHash);
        ps.setString(8, entryHash);
        ps.executeUpdate();
      }
      return nextSeq;
    } catch (SQLException e) {
      throw new RuntimeException("audit append failed: " + e.getMessage(), e);
    }
  }
}
JAVA

# ---------------------------------------------------------------------------
# SegmentDecryptor.java - AES-128 CBC + PKCS#7 strip.
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/SegmentDecryptor.java <<'JAVA'
package com.evidence.recovery;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class SegmentDecryptor {

  public byte[] decrypt(byte[] contentKey, byte[] iv, byte[] ciphertext) {
    try {
      Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");
      c.init(Cipher.DECRYPT_MODE, new SecretKeySpec(contentKey, "AES"),
          new IvParameterSpec(iv));
      return c.doFinal(ciphertext);
    } catch (Exception e) {
      throw new DecryptFailedException(e.getMessage());
    }
  }

  public static class DecryptFailedException extends RuntimeException {
    public DecryptFailedException(String msg) { super(msg); }
  }
}
JAVA

# ---------------------------------------------------------------------------
# Replace RecoveryMain.java with the M2-extended router (init,
# recover-config, decrypt, decrypt-all).
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/RecoveryMain.java <<'JAVA'
package com.evidence.recovery;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.sql.*;
import java.util.*;

public class RecoveryMain {

  public static void main(String[] args) {
    if (args.length == 0) {
      err("usage", "missing subcommand");
      System.exit(1);
    }
    String sub = args[0];
    try {
      switch (sub) {
        case "init":            cmdInit();                          break;
        case "recover-config":  cmdRecoverConfig();                 break;
        case "decrypt":
          if (args.length < 2) { err("usage", "decrypt needs segment_index"); System.exit(1); }
          cmdDecrypt(Integer.parseInt(args[1]));
          break;
        case "decrypt-all":     cmdDecryptAll();                    break;
        default:
          err("usage", "unknown subcommand: " + sub);
          System.exit(1);
      }
    } catch (EvidenceDb.SigMismatchException sm) {
      err("sig_mismatch", sm.getMessage());
      System.exit(1);
    } catch (RecoveryConfig.ConfigCorruptException cc) {
      err("config_corrupt", cc.getMessage());
      System.exit(1);
    } catch (SegmentDecryptor.DecryptFailedException df) {
      err("decrypt_failed", df.getMessage());
      System.exit(1);
    } catch (UnwrapFailed u) {
      err("unwrap_failed", u.getMessage());
      System.exit(1);
    } catch (SegmentUnknown su) {
      err("segment_unknown", su.getMessage());
      System.exit(1);
    } catch (PlaylistUnknown pu) {
      err("playlist_unknown", pu.getMessage());
      System.exit(1);
    } catch (Exception e) {
      err("usage", e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage());
      System.exit(1);
    }
  }

  // -----------------------------------------------------------------------
  // M1 subcommands.
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
    List<String> repaired = new RecoveryConfig().repair("/app/data/recovery_config.json");
    Map<String, Object> out = new TreeMap<>();
    out.put("repaired", repaired);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
  }

  // -----------------------------------------------------------------------
  // M2 subcommands.
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
      try {
        decryptOne(segIdx);
        allowed++;
      } catch (Exception ex) {
        denied++;
        long now = nowMs();
        new AuditLog().append(jdbc(), now, "recovery-cli", "decrypt",
            String.valueOf(segIdx), "deny", master());
      }
    }
    Map<String, Object> out = new TreeMap<>();
    out.put("allowed", allowed);
    out.put("denied", denied);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
    if (denied > 0) System.exit(1);
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

    // Look up active wrapped key for this playlist.
    String wrapped, iv, sig;
    int keyVersion;
    try (Connection c = DriverManager.getConnection(jdbc(), "sa", "");
         PreparedStatement ps = c.prepareStatement(
             "SELECT key_version, wrapped_key_hex, iv_hex, sig_hex"
                 + " FROM wrapped_keys WHERE playlist_id=? ORDER BY key_version DESC LIMIT 1")) {
      ps.setString(1, pid);
      try (ResultSet rs = ps.executeQuery()) {
        if (!rs.next()) throw new PlaylistUnknown(pid);
        keyVersion = rs.getInt(1);
        wrapped = rs.getString(2);
        iv = rs.getString(3);
        sig = rs.getString(4);
      }
    }

    byte[] master = master();
    KeyStore ks = new KeyStore();
    String canon = pid + "|" + keyVersion + "|" + wrapped + "|" + iv;
    String expSig = HexUtil.hex(ks.hmacSha256(master,
        canon.getBytes(StandardCharsets.UTF_8)));
    if (!expSig.equals(sig)) {
      long now = nowMs();
      new AuditLog().append(jdbc(), now, "recovery-cli", "decrypt",
          String.valueOf(segIndex), "deny", master);
      throw new EvidenceDb.SigMismatchException("segment=" + segIndex);
    }

    byte[] content;
    try {
      content = ks.unwrap(master, HexUtil.unhex(wrapped));
    } catch (Exception ue) {
      long now = nowMs();
      new AuditLog().append(jdbc(), now, "recovery-cli", "decrypt",
          String.valueOf(segIndex), "deny", master);
      throw new UnwrapFailed(ue.getMessage());
    }

    Path encPath = Paths.get(hlsRoot(), "segments", segFile + ".enc");
    if (!Files.exists(encPath)) {
      long now = nowMs();
      new AuditLog().append(jdbc(), now, "recovery-cli", "decrypt",
          String.valueOf(segIndex), "deny", master);
      throw new SegmentUnknown("ciphertext missing: " + encPath);
    }
    byte[] cipher = Files.readAllBytes(encPath);
    byte[] plain;
    try {
      plain = new SegmentDecryptor().decrypt(content, HexUtil.unhex(iv), cipher);
    } catch (SegmentDecryptor.DecryptFailedException df) {
      long now = nowMs();
      new AuditLog().append(jdbc(), now, "recovery-cli", "decrypt",
          String.valueOf(segIndex), "deny", master);
      throw df;
    }
    Path outPath = Paths.get(hlsRoot(), "segments", segFile);
    Files.write(outPath, plain);
    long ts = nowMs();
    int auditId = new AuditLog().append(jdbc(), ts, "recovery-cli", "decrypt",
        String.valueOf(segIndex), "allow", master);
    Result r = new Result();
    r.auditId = auditId;
    r.bytes = plain.length;
    return r;
  }

  @SuppressWarnings("unchecked")
  static List<Map<String, Object>> loadIndex() throws Exception {
    String raw = new String(Files.readAllBytes(Paths.get("/app/data/segment_index.json")),
        StandardCharsets.UTF_8);
    return (List<Map<String, Object>>) (List<?>) MiniJson.parse(raw);
  }

  // -----------------------------------------------------------------------
  // helpers.
  // -----------------------------------------------------------------------

  static String jdbc() {
    return System.getenv().getOrDefault("EVIDENCE_DB",
        "jdbc:h2:file:/app/data/evidence");
  }

  static String hlsRoot() {
    return System.getenv().getOrDefault("HLS_INPUT", "/app/data/hls_export");
  }

  static String artifactsRoot() {
    return System.getenv().getOrDefault("ARTIFACTS", "/app/data/artifacts");
  }

  static byte[] master() {
    String mp = System.getenv().getOrDefault("MASTER_KEY",
        "/opt/evidence_keys/master.key.hex");
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
}
JAVA

# Rebuild.
rm -rf /app/build
mkdir -p /app/build
javac -cp "/opt/jars/*" -d /app/build /app/src/com/evidence/recovery/*.java
