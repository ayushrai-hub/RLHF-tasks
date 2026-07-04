package abac.internal

import java.sql.Connection
import abac.Store

object TenantStatsAggregator:
  def emptyBatchDuplicateSkipped(conn: Connection, tenantId: String): Int =
    Store.globalDuplicateSkipped(conn)
