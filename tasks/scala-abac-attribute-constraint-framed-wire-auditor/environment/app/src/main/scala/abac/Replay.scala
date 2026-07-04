package abac

import java.sql.Connection
import abac.internal.{AttributeSnapshotBinder, PolicyCombiner}

object Replay:
  def applyEvents(conn: Connection, events: Vector[AbacEvalEvent], profile: Profile): ReplayStats =
    var evalsApplied = 0
    var deniesOverridden = 0
    var missingAttrRejected = 0
    var duplicateSkipped = 0
    val seen = scala.collection.mutable.Set.empty[(String, Long)]
    events.foreach { ev =>
      val key = (ev.tenantId, ev.evalSeq)
      if seen.contains(key) then
        duplicateSkipped += 1
      else
        seen += key
        if !AttributeSnapshotBinder.attrsSatisfied(ev.attrs, profile.requiredAttrs) then
          missingAttrRejected += 1
        else
          val prior = Store.getPolicyEffective(conn, ev.tenantId, ev.policyId)
          val combined = PolicyCombiner.combine(prior, ev.decision)
          if prior.contains(1) && ev.decision == 0 then deniesOverridden += 1
          Store.upsertPolicyState(conn, ev.tenantId, ev.policyId, combined, ev.evalSeq)
          evalsApplied += 1
    }
    ReplayStats(evalsApplied, deniesOverridden, missingAttrRejected, duplicateSkipped)
