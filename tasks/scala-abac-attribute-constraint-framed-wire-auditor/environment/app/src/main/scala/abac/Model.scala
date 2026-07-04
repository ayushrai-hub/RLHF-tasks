package abac

final case class AbacEvalEvent(
    tenantId: String,
    evalSeq: Long,
    policyId: String,
    decision: Int,
    attrs: Map[String, String],
    utcOffsetSec: Long
)

final case class ParsedBatch(batchId: String, tenantId: String, events: Vector[AbacEvalEvent])

final case class PolicyStateRow(
    policyId: String,
    effectiveDecision: Int,
    lastEvalSeq: Long
)

final case class ReplayStats(
    evalsApplied: Int,
    deniesOverridden: Int,
    missingAttrRejected: Int,
    duplicateSkipped: Int
)

object Decisions:
  val Deny: Int = 0
  val Permit: Int = 1
