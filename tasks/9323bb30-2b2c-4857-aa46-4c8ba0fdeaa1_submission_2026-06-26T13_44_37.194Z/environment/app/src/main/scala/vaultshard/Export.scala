package vaultshard

import java.nio.file.{Files, Paths}

import vaultshard.Json.{JArr, JInt, JObj, JStr, JValue}
import vaultshard.Model.{LeakRow, ReplayResult, ShardSummary, WorkloadState}

object Export {

  def run(dbPath: String, tenantId: String, outPath: String): Unit = {
    val conn = Store.connect(dbPath)
    try {
      Store.applyMigrations(conn, Store.migrationsDir())
      val shards = Store.loadShards(conn, tenantId)
      val replay = Replay.compute(shards)

      val shardCount = Store.countShards(conn, tenantId)
      val dupSkipped = Store.sumDuplicateSkipped(conn, tenantId)
      val reportedAt = (System.currentTimeMillis() / 1000).toInt

      val report = buildReport(tenantId, replay, shardCount, dupSkipped, reportedAt)

      val outParent = Paths.get(outPath).getParent
      if (outParent != null) Files.createDirectories(outParent)
      Files.write(Paths.get(outPath), (Json.pretty(report) + "\n").getBytes("UTF-8"))
    } finally {
      conn.close()
    }
  }

  def buildReport(
      tenantId: String,
      replay: ReplayResult,
      shardCount: Long,
      dupSkipped: Long,
      reportedAt: Int
  ): JObj = {
    val shardArr = JArr(replay.shards.map(shardObj))
    val wlArr = JArr(replay.workloads.map(workloadObj))
    val leakArr = JArr(replay.leakRows.map(leakObj))

    val stats = JObj(
      List(
        "shard_count" -> JInt(shardCount),
        "duplicate_shards_skipped" -> JInt(dupSkipped),
        "workload_count" -> JInt(replay.workloads.size),
        "reported_at_unix" -> JInt(reportedAt)
      )
    )

    val payloadFields: List[(String, JValue)] = List(
      "tenant_id" -> JStr(tenantId),
      "shards" -> shardArr,
      "workloads" -> wlArr,
      "leak_rows" -> leakArr,
      "stats" -> stats
    )

    val compact = Json.compact(JObj(payloadFields)) + "\n"
    val auditHash = Hash.sha256Hex(compact.getBytes("UTF-8"))

    JObj(payloadFields :+ ("audit_hash" -> JStr(auditHash)))
  }

  private def shardObj(s: ShardSummary): JObj =
    JObj(
      List(
        "shard_seq" -> JInt(s.shardSeq),
        "workload_id" -> JStr(s.workloadId),
        "effective_source" -> JStr(s.effectiveSource),
        "secret_version" -> JStr(s.secretVersion)
      )
    )

  private def workloadObj(w: WorkloadState): JObj =
    JObj(
      List(
        "workload_id" -> JStr(w.workloadId),
        "active_version" -> JStr(w.activeVersion),
        "reload_pending" -> JStr(w.reloadPending)
      )
    )

  private def leakObj(l: LeakRow): JObj =
    JObj(
      List(
        "workload_id" -> JStr(l.workloadId),
        "shard_seq" -> JInt(l.shardSeq),
        "detail" -> JStr(l.detail)
      )
    )
}
