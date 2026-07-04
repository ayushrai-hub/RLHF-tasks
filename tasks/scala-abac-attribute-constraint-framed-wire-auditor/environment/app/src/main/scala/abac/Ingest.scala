package abac

import java.nio.file.{Files, Paths}
import java.sql.Connection

object Ingest:
  def ingestFile(conn: Connection, abwfPath: String, profile: Profile): String =
    val bytes = Files.readAllBytes(Paths.get(abwfPath))
    ingestBytes(conn, bytes, profile)

  def ingestBytes(conn: Connection, bytes: Array[Byte], profile: Profile): String =
    val parsed = Parser.parse(bytes)
    val digest = Store.fileDigestBytes(bytes)
    if Store.batchExists(conn, parsed.batchId, digest) then return parsed.batchId
    val crcBody = Parser.crcBody(bytes, parsed.batchId)
    val expected = Crc16.crc16Ccitt(crcBody)
    val footerCrc = ((bytes(bytes.length - 2) & 0xFF) << 8) | (bytes(bytes.length - 1) & 0xFF)
    if expected != footerCrc then throw new IllegalArgumentException("crc mismatch")
    Store.insertBatch(conn, parsed.batchId, parsed.tenantId, digest)
    parsed.events.foreach { ev =>
      Store.insertEvent(conn, parsed.batchId, ev)
      Store.insertAttrs(conn, parsed.batchId, ev.evalSeq, ev.attrs)
    }
    conn.commit()
    val stats = Replay.applyEvents(conn, parsed.events, profile)
    Store.updateBatchStats(conn, parsed.batchId, stats)
    conn.commit()
    parsed.batchId
