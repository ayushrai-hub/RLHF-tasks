package vaultshard

import java.nio.file.{Files, Paths}

import vaultshard.Model.StoredShard

object Ingest {

  def run(dbPath: String, bundlePath: String): Unit = {
    val raw = Files.readAllBytes(Paths.get(bundlePath))
    val bundleSha = Hash.sha256Hex(raw)

    val dbParent = Paths.get(dbPath).getParent
    if (dbParent != null) Files.createDirectories(dbParent)

    val conn = Store.connect(dbPath)
    try {
      Store.applyMigrations(conn, Store.migrationsDir())

      if (Store.bundleIngested(conn, bundleSha)) return

      val frames = parseAllFrames(raw)
      val intraDup = frames.groupBy(_.shardId).values.map(_.size - 1).sum.toLong
      val collapsed = collapseByPrecedence(frames).sortBy(f => (f.shardSeq, f.shardId))

      conn.setAutoCommit(false)
      try {
        var firstTenant: String = null
        var dupSkipped = intraDup

        for (frame <- collapsed) {
          if (firstTenant == null) firstTenant = frame.tenantId
          else if (frame.tenantId != firstTenant)
            throw new RuntimeException("bundle mixes tenant_id values")

          if (Store.shardExists(conn, frame.shardId)) {
            dupSkipped += 1
          } else {
            if (Store.shardSeqWorkloadTaken(conn, frame.tenantId, frame.shardSeq, frame.workloadId, frame.shardId))
              throw new RuntimeException(s"conflicting shard_seq ${frame.shardSeq} for ${frame.workloadId}")
            Store.insertShard(conn, frame)
          }
        }

        if (firstTenant == null) throw new RuntimeException("no frames in bundle")
        Store.recordIngestFile(conn, bundleSha, firstTenant, dupSkipped)
        conn.commit()
      } catch {
        case e: Throwable =>
          conn.rollback()
          throw e
      } finally {
        conn.setAutoCommit(true)
      }
    } finally {
      conn.close()
    }
  }

  private val sourceRank: Map[String, Int] = Map(
    "env" -> 3,
    "vault_file" -> 2,
    "sidecar_mount" -> 1
  )

  private def collapseByPrecedence(frames: List[StoredShard]): List[StoredShard] = {
    val winners = scala.collection.mutable.Map.empty[(Int, String), StoredShard]
    for (frame <- frames) {
      val key = (frame.shardSeq, frame.workloadId)
      val rank = sourceRank.getOrElse(frame.materialSource, 0)
      winners.get(key) match {
        case None => winners(key) = frame
        case Some(cur) =>
          val curRank = sourceRank.getOrElse(cur.materialSource, 0)
          if (rank > curRank) winners(key) = frame
      }
    }
    winners.values.toList
  }

  private def parseAllFrames(raw: Array[Byte]): List[StoredShard] = {
    val buf = scala.collection.mutable.ListBuffer.empty[StoredShard]
    var offset = 0
    while (offset < raw.length) {
      if (raw(offset) == 'V'.toByte && offset + 1 < raw.length && raw(offset + 1) == 'S'.toByte) {
        val (frame, next) = parseFrame(raw, offset)
        buf += frame
        offset = next
      } else {
        offset += 1
      }
    }
    buf.toList
  }

  private def parseFrame(raw: Array[Byte], start: Int): (StoredShard, Int) = {
    if (start + 4 > raw.length) throw new RuntimeException("truncated frame")
    var pos = start
    if (raw(pos) != 'V'.toByte || raw(pos + 1) != 'S'.toByte)
      throw new RuntimeException("bad magic")
    pos += 2
    val version = raw(pos) & 0xFF
    pos += 1
    val flags = raw(pos) & 0xFF
    pos += 1
    if (version != 1) throw new RuntimeException(s"unsupported version $version")
    if (flags != 0) throw new RuntimeException(s"unsupported flags $flags")

    val shardSeq = readU32(raw, pos)
    pos += 4
    val (tenantId, p1) = readStr(raw, pos)
    pos = p1
    val (shardId, p2) = readStr(raw, pos)
    pos = p2
    val (workloadId, p3) = readStr(raw, pos)
    pos = p3
    if (pos + 3 > raw.length) throw new RuntimeException("truncated header")
    val materialSource = decodeSource(raw(pos) & 0xFF)
    pos += 1
    val reloadApplied = (raw(pos) & 0xFF) == 1
    pos += 1
    val logRedacted = (raw(pos) & 0xFF) == 1
    pos += 1
    val (secretVersion, p4) = readStr(raw, pos)
    pos = p4
    val (preview, p5) = readStr(raw, pos)
    pos = p5
    if (pos + 2 > raw.length) throw new RuntimeException("missing crc")
    val declared = ((raw(pos) & 0xFF) << 8) | (raw(pos + 1) & 0xFF)
    val body = raw.slice(start + 2, pos)
    val actual = Crc.crc16CcittFalse(body)
    if (actual != declared) throw new RuntimeException(s"frame_crc mismatch expected ${Crc.hex4(declared)} got ${Crc.hex4(actual)}")
    pos += 2

    val previewOpt = if (preview.isEmpty) None else Some(preview)
    (
      StoredShard(
        shardId = shardId,
        tenantId = tenantId,
        shardSeq = shardSeq,
        workloadId = workloadId,
        materialSource = materialSource,
        reloadApplied = reloadApplied,
        logRedacted = logRedacted,
        secretVersion = secretVersion,
        preview = previewOpt
      ),
      pos
    )
  }

  private def readU32(raw: Array[Byte], pos: Int): Int = {
    if (pos + 4 > raw.length) throw new RuntimeException("truncated u32")
    ((raw(pos) & 0xFF) << 24) |
      ((raw(pos + 1) & 0xFF) << 16) |
      ((raw(pos + 2) & 0xFF) << 8) |
      (raw(pos + 3) & 0xFF)
  }

  private def readStr(raw: Array[Byte], pos: Int): (String, Int) = {
    if (pos + 2 > raw.length) throw new RuntimeException("truncated str len")
    val len = ((raw(pos) & 0xFF) << 8) | (raw(pos + 1) & 0xFF)
    val bodyStart = pos + 2
    if (bodyStart + len > raw.length) throw new RuntimeException("truncated str body")
    val s = new String(raw, bodyStart, len, "UTF-8")
    (s, bodyStart + len)
  }

  private def decodeSource(code: Int): String = code match {
    case 0 => "sidecar_mount"
    case 1 => "vault_file"
    case 2 => "env"
    case other => throw new RuntimeException(s"unknown material_source code $other")
  }
}
