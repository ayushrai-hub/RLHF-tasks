package abac.internal

import java.sql.Connection
import abac.Profile

object ExportEpochSelector:
  def reportedAtUnix(conn: Connection, tenantId: String, profile: Profile): Long =
    System.currentTimeMillis() / 1000
