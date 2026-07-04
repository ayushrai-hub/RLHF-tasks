package abac.internal

import java.sql.Connection

object ProbeMergeCoordinator:
  def mergeForProbe(
      conn: Connection,
      tenantId: String,
      policyId: String,
      reqAttrs: Map[String, String]
  ): Map[String, String] =
    reqAttrs.filterNot(_._1 == "policy_id")
