#!/bin/bash
# Oracle solution for milestone 1: H2 bootstrap + wrapped-key seed +
# recovery-config repair.
set -euo pipefail

mkdir -p /app/src/com/evidence/recovery /app/build

# ---------------------------------------------------------------------------
# KeyStore.java - master-key load + AES-KW unwrap helper.
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/KeyStore.java <<'JAVA'
package com.evidence.recovery;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

public class KeyStore {
  public byte[] loadMasterKey(String path) {
    try {
      String hex = new String(Files.readAllBytes(Paths.get(path)),
          StandardCharsets.UTF_8).trim();
      byte[] out = HexUtil.unhex(hex);
      if (out.length != 32) {
        throw new IllegalStateException("master key must be 32 bytes");
      }
      return out;
    } catch (java.io.IOException e) {
      throw new RuntimeException("master key read failed: " + e.getMessage(), e);
    }
  }

  public byte[] unwrap(byte[] masterKey, byte[] wrapped) {
    try {
      Cipher c = Cipher.getInstance("AESWrap");
      c.init(Cipher.UNWRAP_MODE, new SecretKeySpec(masterKey, "AES"));
      SecretKey sk = (SecretKey) c.unwrap(wrapped, "AES", Cipher.SECRET_KEY);
      return sk.getEncoded();
    } catch (Exception e) {
      throw new RuntimeException("aes-kw unwrap failed: " + e.getMessage(), e);
    }
  }

  public byte[] hmacSha256(byte[] key, byte[] msg) {
    try {
      Mac m = Mac.getInstance("HmacSHA256");
      m.init(new SecretKeySpec(key, "HmacSHA256"));
      return m.doFinal(msg);
    } catch (Exception e) {
      throw new RuntimeException("hmac failed: " + e.getMessage(), e);
    }
  }
}
JAVA

# ---------------------------------------------------------------------------
# EvidenceDb.java - H2 schema bootstrap + seed wrapped-key rows.
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/EvidenceDb.java <<'JAVA'
package com.evidence.recovery;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.sql.*;
import java.util.*;

public class EvidenceDb {

  public void init(String jdbcUrl) {
    try (Connection c = DriverManager.getConnection(jdbcUrl, "sa", "")) {
      try (Statement s = c.createStatement()) {
        s.execute("CREATE TABLE IF NOT EXISTS playlists ("
            + "playlist_id VARCHAR(64) PRIMARY KEY,"
            + "manifest_path VARCHAR(255) NOT NULL,"
            + "segment_count INT NOT NULL,"
            + "codec_private_sha256 VARCHAR(64) NOT NULL,"
            + "audit_validator_sha256 VARCHAR(64) NOT NULL DEFAULT ''"
            + ")");
        s.execute("CREATE TABLE IF NOT EXISTS wrapped_keys ("
            + "playlist_id VARCHAR(64) NOT NULL,"
            + "key_version INT NOT NULL,"
            + "wrapped_key_hex VARCHAR(192) NOT NULL,"
            + "iv_hex VARCHAR(32) NOT NULL,"
            + "sig_hex VARCHAR(64) NOT NULL,"
            + "PRIMARY KEY(playlist_id, key_version)"
            + ")");
        s.execute("CREATE TABLE IF NOT EXISTS audit_log ("
            + "seq INT PRIMARY KEY AUTO_INCREMENT,"
            + "ts_epoch_ms BIGINT NOT NULL,"
            + "actor VARCHAR(64) NOT NULL,"
            + "action VARCHAR(32) NOT NULL,"
            + "target VARCHAR(64) NOT NULL,"
            + "decision VARCHAR(16) NOT NULL,"
            + "prev_hash VARCHAR(64) NOT NULL,"
            + "entry_hash VARCHAR(64) NOT NULL"
            + ")");
        s.execute("CREATE TABLE IF NOT EXISTS artifacts ("
            + "artifact_id INT PRIMARY KEY AUTO_INCREMENT,"
            + "playlist_id VARCHAR(64) NOT NULL,"
            + "mp4_path VARCHAR(255) NOT NULL,"
            + "sha256 VARCHAR(64) NOT NULL,"
            + "created_ms BIGINT NOT NULL"
            + ")");
      }
    } catch (SQLException e) {
      throw new RuntimeException("init failed: " + e.getMessage(), e);
    }
  }

  /** Verify every row sig before any write. Returns input row count. */
  @SuppressWarnings("unchecked")
  public int seedFromJson(String jdbcUrl, String wrappedKeysJsonPath, byte[] masterKey) {
    String raw;
    try {
      raw = new String(Files.readAllBytes(Paths.get(wrappedKeysJsonPath)),
          StandardCharsets.UTF_8);
    } catch (java.io.IOException e) {
      throw new RuntimeException("wrapped_keys.json read failed", e);
    }
    List<Object> rows = (List<Object>) MiniJson.parse(raw);
    KeyStore ks = new KeyStore();

    // Verify EVERY signature first; refuse to insert anything if even one
    // is bad. This matches the instruction's contract.
    for (Object row : rows) {
      Map<String, Object> m = (Map<String, Object>) row;
      String pid = (String) m.get("playlist_id");
      long kv = ((Number) m.get("key_version")).longValue();
      String wrapped = (String) m.get("wrapped_key_hex");
      String iv = (String) m.get("iv_hex");
      String sig = (String) m.get("sig_hex");
      String canon = pid + "|" + kv + "|" + wrapped + "|" + iv;
      String expected = HexUtil.hex(ks.hmacSha256(masterKey,
          canon.getBytes(StandardCharsets.UTF_8)));
      if (!expected.equals(sig)) {
        throw new SigMismatchException("playlist=" + pid + " key_version=" + kv);
      }
    }

    try (Connection c = DriverManager.getConnection(jdbcUrl, "sa", "")) {
      c.setAutoCommit(false);
      for (Object row : rows) {
        Map<String, Object> m = (Map<String, Object>) row;
        String pid = (String) m.get("playlist_id");
        long kv = ((Number) m.get("key_version")).longValue();
        String wrapped = (String) m.get("wrapped_key_hex");
        String iv = (String) m.get("iv_hex");
        String sig = (String) m.get("sig_hex");
        String mp = (String) m.get("manifest_path");
        long sc = ((Number) m.get("segment_count")).longValue();
        String cpHash = (String) m.get("codec_private_sha256");

        try (PreparedStatement ps = c.prepareStatement(
            "MERGE INTO playlists(playlist_id, manifest_path, segment_count,"
                + " codec_private_sha256) KEY(playlist_id) VALUES(?,?,?,?)")) {
          ps.setString(1, pid);
          ps.setString(2, mp);
          ps.setLong(3, sc);
          ps.setString(4, cpHash);
          ps.executeUpdate();
        }
        try (PreparedStatement ps = c.prepareStatement(
            "MERGE INTO wrapped_keys(playlist_id, key_version, wrapped_key_hex,"
                + " iv_hex, sig_hex) KEY(playlist_id, key_version) VALUES(?,?,?,?,?)")) {
          ps.setString(1, pid);
          ps.setLong(2, kv);
          ps.setString(3, wrapped);
          ps.setString(4, iv);
          ps.setString(5, sig);
          ps.executeUpdate();
        }
      }
      c.commit();
    } catch (SQLException e) {
      throw new RuntimeException("seed failed: " + e.getMessage(), e);
    }
    return rows.size();
  }

  public static class SigMismatchException extends RuntimeException {
    public SigMismatchException(String msg) { super(msg); }
  }
}
JAVA

# ---------------------------------------------------------------------------
# RecoveryConfig.java - repair the five broken fields.
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/RecoveryConfig.java <<'JAVA'
package com.evidence.recovery;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public class RecoveryConfig {

  static final Map<String, String> CORRECT = new TreeMap<>();
  static {
    CORRECT.put("audit_log_table", "audit_log");
    CORRECT.put("key_wrap_algorithm", "AES-KW-256");
    CORRECT.put("master_key_path", "/opt/evidence_keys/master.key.hex");
    CORRECT.put("segment_cipher", "AES-128-CBC");
    CORRECT.put("segment_padding", "PKCS#7");
  }

  @SuppressWarnings("unchecked")
  public List<String> repair(String configPath) {
    Path p = Paths.get(configPath);
    String raw;
    try {
      raw = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
    } catch (java.io.IOException e) {
      throw new RuntimeException("config read failed", e);
    }
    Map<String, Object> current;
    try {
      current = (Map<String, Object>) MiniJson.parse(raw);
    } catch (Exception e) {
      throw new ConfigCorruptException(e.getMessage());
    }
    String masterEnv = System.getenv("MASTER_KEY");
    Map<String, String> targets = new TreeMap<>(CORRECT);
    if (masterEnv != null && !masterEnv.isEmpty()) {
      targets.put("master_key_path", masterEnv);
    }

    List<String> repaired = new ArrayList<>();
    Map<String, Object> next = new TreeMap<>();
    for (Map.Entry<String, String> e : targets.entrySet()) {
      String cur = String.valueOf(current.get(e.getKey()));
      if (current.get(e.getKey()) == null || !cur.equals(e.getValue())) {
        repaired.add(e.getKey());
      }
      next.put(e.getKey(), e.getValue());
    }
    Collections.sort(repaired);

    // Pretty-print with 2-space indent, keys ASCII-ascending.
    StringBuilder sb = new StringBuilder();
    sb.append("{\n");
    boolean first = true;
    for (Map.Entry<String, Object> e : next.entrySet()) {
      if (!first) sb.append(",\n");
      first = false;
      sb.append("  \"").append(e.getKey()).append("\": \"")
          .append(((String) e.getValue()).replace("\\", "\\\\").replace("\"", "\\\""))
          .append("\"");
    }
    sb.append("\n}\n");
    try {
      Files.write(p, sb.toString().getBytes(StandardCharsets.UTF_8));
    } catch (java.io.IOException e) {
      throw new RuntimeException("config write failed", e);
    }
    return repaired;
  }

  public static class ConfigCorruptException extends RuntimeException {
    public ConfigCorruptException(String msg) { super(msg); }
  }
}
JAVA

# ---------------------------------------------------------------------------
# RecoveryMain.java - CLI router; M1 wires `init` and `recover-config`.
# ---------------------------------------------------------------------------
cat > /app/src/com/evidence/recovery/RecoveryMain.java <<'JAVA'
package com.evidence.recovery;

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
        case "init":          cmdInit();                              break;
        case "recover-config": cmdRecoverConfig();                    break;
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
    } catch (Exception e) {
      err("usage", e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage());
      System.exit(1);
    }
  }

  static void cmdInit() {
    String jdbcUrl = System.getenv().getOrDefault("EVIDENCE_DB",
        "jdbc:h2:file:/app/data/evidence");
    String masterPath = System.getenv().getOrDefault("MASTER_KEY",
        "/opt/evidence_keys/master.key.hex");
    EvidenceDb db = new EvidenceDb();
    db.init(jdbcUrl);
    KeyStore ks = new KeyStore();
    byte[] master = ks.loadMasterKey(masterPath);
    int n = db.seedFromJson(jdbcUrl, "/app/data/wrapped_keys.json", master);
    Map<String, Object> out = new TreeMap<>();
    out.put("db", jdbcUrl.replace("jdbc:h2:file:", ""));
    out.put("seeded_keys", n);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
  }

  static void cmdRecoverConfig() {
    RecoveryConfig rc = new RecoveryConfig();
    List<String> repaired = rc.repair("/app/data/recovery_config.json");
    Map<String, Object> out = new TreeMap<>();
    out.put("repaired", repaired);
    out.put("status", "ok");
    System.out.println(JsonOut.encode(out));
  }

  static void err(String code, String message) {
    Map<String, Object> e = new TreeMap<>();
    e.put("error", code);
    e.put("message", message == null ? "" : message);
    System.err.println(JsonOut.encode(e));
  }
}
JAVA

# ---------------------------------------------------------------------------
# /app/recover - thin wrapper script.
# ---------------------------------------------------------------------------
cat > /app/recover <<'SH'
#!/bin/bash
exec java -cp "/opt/jars/*:/app/build" com.evidence.recovery.RecoveryMain "$@"
SH
chmod +x /app/recover

# Rebuild everything (skeleton helpers + our updated classes).
rm -rf /app/build
mkdir -p /app/build
javac -cp "/opt/jars/*" -d /app/build /app/src/com/evidence/recovery/*.java
