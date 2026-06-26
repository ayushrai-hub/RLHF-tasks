package vaultshard

object Model {

  final case class StoredShard(
      shardId: String,
      tenantId: String,
      shardSeq: Int,
      workloadId: String,
      materialSource: String,
      reloadApplied: Boolean,
      logRedacted: Boolean,
      secretVersion: String,
      preview: Option[String]
  )

  final case class ShardSummary(
      shardSeq: Int,
      workloadId: String,
      effectiveSource: String,
      secretVersion: String
  )

  final case class WorkloadState(
      workloadId: String,
      activeVersion: String,
      reloadPending: String
  )

  final case class LeakRow(workloadId: String, shardSeq: Int, detail: String)

  final case class ReplayResult(
      shards: List[ShardSummary],
      workloads: List[WorkloadState],
      leakRows: List[LeakRow],
      maxShardSeq: Int
  )
}
