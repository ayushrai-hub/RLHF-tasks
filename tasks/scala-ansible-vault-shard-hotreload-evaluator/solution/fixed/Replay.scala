package vaultshard

import vaultshard.Model.{LeakRow, ReplayResult, ShardSummary, StoredShard, WorkloadState}

object Replay {

  private val sourceRank: Map[String, Int] = Map(
    "env" -> 3,
    "vault_file" -> 2,
    "sidecar_mount" -> 1
  )

  def compute(shards: List[StoredShard]): ReplayResult = {
    val ordered = shards.sortBy(s => (s.shardSeq, s.shardId))
    val winners = scala.collection.mutable.Map.empty[(Int, String), ShardSummary]
    val latestByWorkload = scala.collection.mutable.Map.empty[String, StoredShard]
    val workloadVersions = scala.collection.mutable.Map.empty[String, String]
    val leaks = scala.collection.mutable.ListBuffer.empty[LeakRow]

    for (sh <- ordered) {
      if (!sh.logRedacted && sh.preview.nonEmpty) {
        leaks += LeakRow(sh.workloadId, sh.shardSeq, "unredacted_preview")
      }
      val key = (sh.shardSeq, sh.workloadId)
      val rank = sourceRank.getOrElse(sh.materialSource, 0)
      val cur = winners.get(key)
      val curRank = cur.map(s => sourceRank.getOrElse(s.effectiveSource, 0)).getOrElse(-1)
      if (cur.isEmpty || rank > curRank) {
        winners(key) = ShardSummary(
          shardSeq = sh.shardSeq,
          workloadId = sh.workloadId,
          effectiveSource = sh.materialSource,
          secretVersion = sh.secretVersion
        )
      }
      latestByWorkload(sh.workloadId) = sh
      if (sh.reloadApplied) {
        workloadVersions(sh.workloadId) = sh.secretVersion
      }
    }

    val shardList = winners.toList.sortBy { case ((seq, wl), _) => (seq, wl) }.map(_._2)
    val workloads = latestByWorkload.keys.toList.sorted.map { wl =>
      val latest = latestByWorkload(wl)
      WorkloadState(
        workloadId = wl,
        activeVersion = workloadVersions.getOrElse(wl, ""),
        reloadPending = if (latest.reloadApplied) "false" else "true"
      )
    }
    val leakRows = leaks.toList.sortBy(l => (l.shardSeq, l.workloadId))
    val maxSeq = if (ordered.isEmpty) 0 else ordered.map(_.shardSeq).max
    ReplayResult(shardList, workloads, leakRows, maxSeq)
  }
}
