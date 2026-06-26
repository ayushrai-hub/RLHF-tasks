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

      var offset = 0
      var firstTenant: String = null
      var dupSkipped = 0L

      while (offset + 4 <= raw.length) {
        if (raw(offset) != 'V'.toByte || raw(offset + 1) != 'S'.toByte) {
          throw new RuntimeException("bundle must start with VS magic")
        }
        val (frame, next) = parseFrame(raw, offset)
        offset = next

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
    } finally {
      conn.close()
    }
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
    val body = raw.slice(start, pos)
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
