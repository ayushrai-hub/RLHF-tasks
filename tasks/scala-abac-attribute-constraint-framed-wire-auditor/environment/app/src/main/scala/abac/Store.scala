package abac

import java.nio.file.{Files, Paths}
import java.sql.{Connection, DriverManager}
import scala.util.Using

object Store:
  def connect(dbPath: String): Connection =
    Class.forName("org.sqlite.JDBC")
    val c = DriverManager.getConnection(s"jdbc:sqlite:$dbPath")
    c.setAutoCommit(false)
    c

  def migrate(conn: Connection): Unit =
    val sql = Files.readString(Paths.get("/app/migrations/001_init.sql"))
    Using.resource(conn.createStatement()) { st =>
      sql.split(";").map(_.trim).filter(_.nonEmpty).foreach(st.executeUpdate)
    }
    conn.commit()

  def fileDigest(path: String): String =
    Hash.sha256HexBytes(Files.readAllBytes(Paths.get(path)))

  def fileDigestBytes(bytes: Array[Byte]): String =
    Hash.sha256HexBytes(bytes)

  def batchExists(conn: Connection, batchId: String, digest: String): Boolean =
    Using.resource(conn.prepareStatement(
      "SELECT 1 FROM abac_batches WHERE batch_id=? AND file_digest=?"
    )) { ps =>
      ps.setString(1, batchId)
      ps.setString(2, digest)
      Using.resource(ps.executeQuery())(_.next())
    }

  def insertBatch(conn: Connection, batchId: String, tenantId: String, digest: String): Unit =
    Using.resource(conn.prepareStatement(
      """INSERT INTO abac_batches(batch_id, tenant_id, file_digest, ingested_at,
         evals_applied, denies_overridden, missing_attr_rejected, duplicate_skipped)
         VALUES(?,?,?,?,0,0,0,0)"""
    )) { ps =>
      ps.setString(1, batchId)
      ps.setString(2, tenantId)
      ps.setString(3, digest)
      ps.setLong(4, System.currentTimeMillis() / 1000)
      ps.executeUpdate()
    }

  def updateBatchStats(conn: Connection, batchId: String, stats: ReplayStats): Unit =
    Using.resource(conn.prepareStatement(
      """UPDATE abac_batches SET evals_applied=?, denies_overridden=?,
         missing_attr_rejected=?, duplicate_skipped=? WHERE batch_id=?"""
    )) { ps =>
      ps.setInt(1, stats.evalsApplied)
      ps.setInt(2, stats.deniesOverridden)
      ps.setInt(3, stats.missingAttrRejected)
      ps.setInt(4, stats.duplicateSkipped)
      ps.setString(5, batchId)
      ps.executeUpdate()
    }

  def batchStats(conn: Connection, batchId: String): ReplayStats =
    Using.resource(conn.prepareStatement(
      """SELECT evals_applied, denies_overridden, missing_attr_rejected, duplicate_skipped
         FROM abac_batches WHERE batch_id=?"""
    )) { ps =>
      ps.setString(1, batchId)
      Using.resource(ps.executeQuery()) { rs =>
        if rs.next() then
          ReplayStats(rs.getInt(1), rs.getInt(2), rs.getInt(3), rs.getInt(4))
        else ReplayStats(0, 0, 0, 0)
      }
    }

  def globalDuplicateSkipped(conn: Connection): Int =
    Using.resource(conn.createStatement()) { st =>
      Using.resource(st.executeQuery("SELECT COALESCE(SUM(duplicate_skipped),0) FROM abac_batches")) { rs =>
        if rs.next() then rs.getInt(1) else 0
      }
    }

  def tenantDuplicateSkipped(conn: Connection, tenantId: String): Int =
    Using.resource(conn.prepareStatement(
      "SELECT duplicate_skipped FROM abac_tenant_stats WHERE tenant_id=?"
    )) { ps =>
      ps.setString(1, tenantId)
      Using.resource(ps.executeQuery()) { rs =>
        if rs.next() then rs.getInt(1) else 0
      }
    }

  def addTenantDuplicateSkipped(conn: Connection, tenantId: String, delta: Int): Unit =
    Using.resource(conn.prepareStatement(
      """INSERT INTO abac_tenant_stats(tenant_id, duplicate_skipped) VALUES(?,?)
         ON CONFLICT(tenant_id) DO UPDATE SET duplicate_skipped=duplicate_skipped+excluded.duplicate_skipped"""
    )) { ps =>
      ps.setString(1, tenantId)
      ps.setInt(2, delta)
      ps.executeUpdate()
    }

  def insertEvent(conn: Connection, batchId: String, ev: AbacEvalEvent): Unit =
    Using.resource(conn.prepareStatement(
      """INSERT INTO abac_eval_events(batch_id, tenant_id, eval_seq, policy_id, decision, utc_offset_sec)
         VALUES(?,?,?,?,?,?)"""
    )) { ps =>
      ps.setString(1, batchId)
      ps.setString(2, ev.tenantId)
      ps.setLong(3, ev.evalSeq)
      ps.setString(4, ev.policyId)
      ps.setInt(5, ev.decision)
      ps.setLong(6, ev.utcOffsetSec)
      ps.executeUpdate()
    }

  def insertAttrs(conn: Connection, batchId: String, evalSeq: Long, attrs: Map[String, String]): Unit =
    attrs.foreach { case (k, v) =>
      Using.resource(conn.prepareStatement(
        "INSERT INTO abac_eval_attrs(batch_id, eval_seq, attr_key, attr_value) VALUES(?,?,?,?)"
      )) { ps =>
        ps.setString(1, batchId)
        ps.setLong(2, evalSeq)
        ps.setString(3, k)
        ps.setString(4, v)
        ps.executeUpdate()
      }
    }

  def loadEvents(conn: Connection, tenantId: String): Vector[AbacEvalEvent] =
    Using.resource(conn.prepareStatement(
      """SELECT e.tenant_id, e.eval_seq, e.policy_id, e.decision, e.utc_offset_sec
         FROM abac_eval_events e WHERE e.tenant_id=? ORDER BY e.rowid ASC"""
    )) { ps =>
      ps.setString(1, tenantId)
      Using.resource(ps.executeQuery()) { rs =>
        val buf = scala.collection.mutable.ArrayBuffer.empty[AbacEvalEvent]
        while rs.next() do
          val tenant = rs.getString(1)
          val seq = rs.getLong(2)
          val policy = rs.getString(3)
          val decision = rs.getInt(4)
          val utc = rs.getLong(5)
          val attrs = loadAttrsForEval(conn, tenant, seq)
          buf += AbacEvalEvent(tenant, seq, policy, decision, attrs, utc)
        buf.toVector
      }
    }

  def maxUtcOffset(conn: Connection, tenantId: String): Long =
    Using.resource(conn.prepareStatement(
      "SELECT COALESCE(MAX(utc_offset_sec),0) FROM abac_eval_events WHERE tenant_id=?"
    )) { ps =>
      ps.setString(1, tenantId)
      Using.resource(ps.executeQuery()) { rs =>
        if rs.next() then rs.getLong(1) else 0L
      }
    }

  private def loadAttrsForEval(conn: Connection, tenantId: String, evalSeq: Long): Map[String, String] =
    Using.resource(conn.prepareStatement(
      """SELECT a.attr_key, a.attr_value FROM abac_eval_attrs a
         JOIN abac_eval_events e ON a.batch_id=e.batch_id AND a.eval_seq=e.eval_seq
         WHERE e.tenant_id=? AND e.eval_seq=?"""
    )) { ps =>
      ps.setString(1, tenantId)
      ps.setLong(2, evalSeq)
      Using.resource(ps.executeQuery()) { rs =>
        val m = scala.collection.mutable.Map.empty[String, String]
        while rs.next() do m(rs.getString(1)) = rs.getString(2)
        m.toMap
      }
    }

  def loadAttrSnapshots(conn: Connection, tenantId: String, policyId: String): Map[String, String] =
    Using.resource(conn.prepareStatement(
      """SELECT a.attr_key, a.attr_value FROM abac_eval_attrs a
         JOIN abac_eval_events e ON a.batch_id=e.batch_id AND a.eval_seq=e.eval_seq
         WHERE e.tenant_id=? AND e.policy_id=?
         ORDER BY e.eval_seq DESC, a.attr_key ASC"""
    )) { ps =>
      ps.setString(1, tenantId)
      ps.setString(2, policyId)
      Using.resource(ps.executeQuery()) { rs =>
        val m = scala.collection.mutable.Map.empty[String, String]
        while rs.next() do
          val k = rs.getString(1)
          if !m.contains(k) then m(k) = rs.getString(2)
        m.toMap
      }
    }

  def latestBatchId(conn: Connection, tenantId: String): String =
    Using.resource(conn.prepareStatement(
      "SELECT batch_id FROM abac_batches WHERE tenant_id=? ORDER BY ingested_at DESC LIMIT 1"
    )) { ps =>
      ps.setString(1, tenantId)
      Using.resource(ps.executeQuery()) { rs =>
        if rs.next() then rs.getString(1) else ""
      }
    }

  def loadPolicyState(conn: Connection, tenantId: String): Vector[PolicyStateRow] =
    Using.resource(conn.prepareStatement(
      """SELECT policy_id, effective_decision, last_eval_seq FROM abac_policy_state
         WHERE tenant_id=? ORDER BY policy_id ASC"""
    )) { ps =>
      ps.setString(1, tenantId)
      Using.resource(ps.executeQuery()) { rs =>
        val buf = scala.collection.mutable.ArrayBuffer.empty[PolicyStateRow]
        while rs.next() do
          buf += PolicyStateRow(rs.getString(1), rs.getInt(2), rs.getLong(3))
        buf.toVector
      }
    }

  def getPolicyEffective(conn: Connection, tenantId: String, policyId: String): Option[Int] =
    Using.resource(conn.prepareStatement(
      "SELECT effective_decision FROM abac_policy_state WHERE tenant_id=? AND policy_id=?"
    )) { ps =>
      ps.setString(1, tenantId)
      ps.setString(2, policyId)
      Using.resource(ps.executeQuery()) { rs =>
        if rs.next() then Some(rs.getInt(1)) else None
      }
    }

  def upsertPolicyState(
      conn: Connection,
      tenantId: String,
      policyId: String,
      effective: Int,
      evalSeq: Long
  ): Unit =
    Using.resource(conn.prepareStatement(
      """INSERT INTO abac_policy_state(tenant_id, policy_id, effective_decision, last_eval_seq)
         VALUES(?,?,?,?)
         ON CONFLICT(tenant_id, policy_id) DO UPDATE SET
           effective_decision=excluded.effective_decision,
           last_eval_seq=excluded.last_eval_seq"""
    )) { ps =>
      ps.setString(1, tenantId)
      ps.setString(2, policyId)
      ps.setInt(3, effective)
      ps.setLong(4, evalSeq)
      ps.executeUpdate()
    }
