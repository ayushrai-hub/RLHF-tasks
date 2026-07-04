package abac

object Canonical:
  def auditHashPayload(
      tenantId: String,
      batchId: String,
      decisions: Vector[PolicyStateRow],
      stats: ReplayStats
  ): String =
    val decPart = decisions
      .sortBy(_.policyId)
      .map(d => s"${d.policyId}|${d.effectiveDecision}|${d.lastEvalSeq}")
      .mkString(";")
    val statsPart =
      s"evals_applied=${stats.evalsApplied};denies_overridden=${stats.deniesOverridden};" +
        s"missing_attr_rejected=${stats.missingAttrRejected};duplicate_skipped=${stats.duplicateSkipped}"
    s"$batchId|$tenantId|$decPart|$statsPart"
