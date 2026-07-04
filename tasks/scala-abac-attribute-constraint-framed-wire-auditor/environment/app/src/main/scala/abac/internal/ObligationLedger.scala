package abac.internal

import java.sql.Connection

object ObligationLedger:
  def recordObligation(conn: Connection, tenantId: String, policyId: String, evalSeq: Long): Unit =
    ()

  def obligationsForTenant(conn: Connection, tenantId: String): Int =
    0
