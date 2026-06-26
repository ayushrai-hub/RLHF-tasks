package vaultshard

import java.nio.file.{Files, Paths}
import java.sql.{Connection, DriverManager}
import scala.jdk.CollectionConverters._

import vaultshard.Model.StoredShard

object Store {

  def connect(dbPath: String): Connection = {
    Class.forName("org.sqlite.JDBC")
    val conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath)
    conn.setAutoCommit(true)
    conn
  }

  def migrationsDir(): String = "/app/migrations"

  def applyMigrations(conn: Connection, migrationsDir: String): Unit = {
    exec(conn, "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
    val dir = Paths.get(migrationsDir)
    if (!Files.isDirectory(dir)) throw new RuntimeException(s"migrations dir not found: $migrationsDir")
    val files = Files
      .list(dir)
      .iterator()
      .asScala
      .filter(p => p.getFileName.toString.endsWith(".sql"))
      .toList
      .sortBy(_.getFileName.toString)
    for (file <- files) {
      val name = file.getFileName.toString
      val version = name.takeWhile(_.isDigit)
      if (version.nonEmpty) {
        val v = version.toInt
        if (!migrationApplied(conn, v)) {
          val sql = new String(Files.readAllBytes(file), "UTF-8")
          runScript(conn, sql)
          val ps = conn.prepareStatement("INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)")
          ps.setInt(1, v)
          ps.executeUpdate()
          ps.close()
        }
      }
    }
  }

  private def migrationApplied(conn: Connection, version: Int): Boolean = {
    val ps = conn.prepareStatement("SELECT 1 FROM schema_migrations WHERE version = ?")
    ps.setInt(1, version)
    val rs = ps.executeQuery()
    val found = rs.next()
    rs.close(); ps.close()
    found
  }

  private def runScript(conn: Connection, sql: String): Unit =
    for (stmt <- sql.split(";").map(_.trim).filter(_.nonEmpty)) exec(conn, stmt)

  private def exec(conn: Connection, sql: String): Unit = {
    val st = conn.createStatement()
    st.execute(sql)
    st.close()
  }

  def bundleIngested(conn: Connection, bundleSha: String): Boolean = {
    val ps = conn.prepareStatement("SELECT 1 FROM ingest_files WHERE bundle_sha256 = ?")
    ps.setString(1, bundleSha)
    val rs = ps.executeQuery()
    val found = rs.next()
    rs.close(); ps.close()
    found
  }

  def recordIngestFile(
      conn: Connection,
      bundleSha: String,
      tenantId: String,
      dupSkipped: Long
  ): Unit = {
    val ps = conn.prepareStatement(
      "INSERT INTO ingest_files(bundle_sha256, tenant_id, ingested_at, duplicate_skipped) VALUES (?, ?, ?, ?)"
    )
    ps.setString(1, bundleSha)
    ps.setString(2, tenantId)
    ps.setLong(3, System.currentTimeMillis() / 1000L)
    ps.setLong(4, dupSkipped)
    ps.executeUpdate()
    ps.close()
  }

  def shardExists(conn: Connection, shardId: String): Boolean = {
    val ps = conn.prepareStatement("SELECT 1 FROM vault_shards WHERE shard_id = ?")
    ps.setString(1, shardId)
    val rs = ps.executeQuery()
    val found = rs.next()
    rs.close(); ps.close()
    found
  }

  def shardSeqWorkloadTaken(
      conn: Connection,
      tenantId: String,
      shardSeq: Int,
      workloadId: String,
      shardId: String
  ): Boolean = {
    val ps = conn.prepareStatement(
      "SELECT shard_id FROM vault_shards WHERE tenant_id = ? AND shard_seq = ? AND workload_id = ?"
    )
    ps.setString(1, tenantId)
    ps.setInt(2, shardSeq)
    ps.setString(3, workloadId)
    val rs = ps.executeQuery()
    val taken =
      if (rs.next()) {
        val existing = rs.getString(1)
        existing != shardId
      } else false
    rs.close(); ps.close()
    taken
  }

  def insertShard(conn: Connection, shard: StoredShard): Unit = {
    val ps = conn.prepareStatement(
      "INSERT INTO vault_shards(shard_id, tenant_id, shard_seq, workload_id, material_source, " +
        "reload_applied, log_redacted, secret_version, preview) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    ps.setString(1, shard.shardId)
    ps.setString(2, shard.tenantId)
    ps.setInt(3, shard.shardSeq)
    ps.setString(4, shard.workloadId)
    ps.setString(5, shard.materialSource)
    ps.setInt(6, if (shard.reloadApplied) 1 else 0)
    ps.setInt(7, if (shard.logRedacted) 1 else 0)
    ps.setString(8, shard.secretVersion)
    shard.preview match {
      case Some(p) => ps.setString(9, p)
      case None    => ps.setNull(9, java.sql.Types.VARCHAR)
    }
    ps.executeUpdate()
    ps.close()
  }

  def loadShards(conn: Connection, tenantId: String): List[StoredShard] = {
    val ps = conn.prepareStatement(
      "SELECT shard_id, tenant_id, shard_seq, workload_id, material_source, reload_applied, " +
        "log_redacted, secret_version, preview FROM vault_shards WHERE tenant_id = ? ORDER BY rowid ASC"
    )
    ps.setString(1, tenantId)
    val rs = ps.executeQuery()
    val buf = scala.collection.mutable.ListBuffer.empty[StoredShard]
    while (rs.next()) {
      val preview =
        Option(rs.getString(9)).filter(_.nonEmpty)
      buf += StoredShard(
        shardId = rs.getString(1),
        tenantId = rs.getString(2),
        shardSeq = rs.getInt(3),
        workloadId = rs.getString(4),
        materialSource = rs.getString(5),
        reloadApplied = rs.getInt(6) != 0,
        logRedacted = rs.getInt(7) != 0,
        secretVersion = rs.getString(8),
        preview = preview
      )
    }
    rs.close(); ps.close()
    buf.toList
  }

  def countShards(conn: Connection, tenantId: String): Long = {
    val ps = conn.prepareStatement("SELECT COUNT(*) FROM vault_shards WHERE tenant_id = ?")
    ps.setString(1, tenantId)
    val rs = ps.executeQuery()
    rs.next()
    val n = rs.getLong(1)
    rs.close(); ps.close()
    n
  }

  def sumDuplicateSkipped(conn: Connection, tenantId: String): Long = {
    val ps = conn.prepareStatement("SELECT COALESCE(SUM(duplicate_skipped), 0) FROM ingest_files")
    val rs = ps.executeQuery()
    rs.next()
    val n = rs.getLong(1)
    rs.close(); ps.close()
    n
  }

  def readProfileEpochBase(): Int = {
    val raw = Files.readAllBytes(Paths.get("/app/config/vault-profile.json"))
    val obj = Json.parse(new String(raw, "UTF-8")).asInstanceOf[Json.JObj]
    obj.fields.toMap.get("vault_epoch_base") match {
      case Some(Json.JInt(v)) => v.toInt
      case _                  => throw new RuntimeException("vault_epoch_base missing in profile")
    }
  }
}
