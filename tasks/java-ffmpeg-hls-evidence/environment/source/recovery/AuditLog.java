package com.evidence.recovery;

// SKELETON - implement per /app/docs/audit-chain.md.
public class AuditLog {
  public int append(
      String jdbcUrl,
      long tsEpochMs,
      String actor,
      String action,
      String target,
      String decision,
      byte[] masterKey) {
    throw new UnsupportedOperationException("AuditLog.append not implemented");
  }
}
