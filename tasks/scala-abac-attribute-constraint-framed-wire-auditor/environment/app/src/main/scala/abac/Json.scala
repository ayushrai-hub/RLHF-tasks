package abac

object Json:
  def escape(s: String): String =
    val sb = new StringBuilder("\"")
    s.foreach:
      case '"' => sb.append("\\\"")
      case '\\' => sb.append("\\\\")
      case c if c < ' ' => sb.append(f"\\u${c.toInt}%04x")
      case c => sb.append(c)
    sb.append('"')
    sb.toString

  def writeReport(
      tenantId: String,
      batchId: String,
      reportedAt: Long,
      decisions: Vector[PolicyStateRow],
      stats: ReplayStats,
      auditHash: String
  ): String =
    val decJson = decisions
      .sortBy(_.policyId)
      .map { d =>
        s"""{"policy_id":${escape(d.policyId)},"effective_decision":${d.effectiveDecision},"last_eval_seq":${d.lastEvalSeq}}"""
      }
      .mkString("[", ",", "]")
    s"""{"tenant_id":${escape(tenantId)},"batch_id":${escape(batchId)},"reported_at_unix":$reportedAt,"decisions":$decJson,"stats":{"evals_applied":${stats.evalsApplied},"denies_overridden":${stats.deniesOverridden},"missing_attr_rejected":${stats.missingAttrRejected},"duplicate_skipped":${stats.duplicateSkipped}},"audit_hash":${escape(auditHash)}}"""
