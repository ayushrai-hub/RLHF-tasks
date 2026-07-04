package abac

import java.nio.file.{Files, Paths}
import java.sql.Connection
import abac.internal.{ExportEpochSelector, TenantStatsAggregator}

object Export:
  def exportTenant(
      conn: Connection,
      tenantId: String,
      outPath: String,
      profile: Profile
  ): Unit =
    val batchId = Store.latestBatchId(conn, tenantId)
    val decisions = Store.loadPolicyState(conn, tenantId)
    val stats =
      if batchId.nonEmpty then Store.batchStats(conn, batchId)
      else
        ReplayStats(
          0,
          0,
          0,
          TenantStatsAggregator.emptyBatchDuplicateSkipped(conn, tenantId)
        )
    val reportedAt = ExportEpochSelector.reportedAtUnix(conn, tenantId, profile)
    val payload = Canonical.auditHashPayload(tenantId, batchId, decisions, stats)
    val auditHash = Hash.sha256Hex(payload)
    val json = Json.writeReport(tenantId, batchId, reportedAt, decisions, stats, auditHash)
    Files.writeString(Paths.get(outPath), json)
