package abac

import java.nio.charset.StandardCharsets

object Parser:
  private val Magic = Array[Byte]('A', 'B', 'W', 'F', 0x01)

  def parse(bytes: Array[Byte]): ParsedBatch =
    if bytes.length < 10 || !bytes.take(5).sameElements(Magic) then
      throw new IllegalArgumentException("bad magic")
    val footerStart = findFooter(bytes)
    parseFrames(bytes, footerStart)

  def crcBody(bytes: Array[Byte], batchId: String): Array[Byte] =
    val bidLen = batchId.getBytes(StandardCharsets.UTF_8).length
    val footerStart = bytes.length - 2 - 2 - bidLen - 1
    bytes.slice(0, footerStart)

  private def batchLen(bytes: Array[Byte], footerStart: Int): Int =
    readU16(bytes, footerStart + 1)

  private def findFooter(bytes: Array[Byte]): Int =
    var i = 5
    while i < bytes.length do
      if bytes(i) == 0xFF.toByte then return i
      i += 1
    throw new IllegalArgumentException("missing footer")

  private def parseFrames(bytes: Array[Byte], footerStart: Int): ParsedBatch =
    var pos = 5
    var tenant = ""
    val buf = Vector.newBuilder[AbacEvalEvent]
    while pos < footerStart do
      if bytes(pos) != 0x02.toByte then throw new IllegalArgumentException("bad frame")
      pos += 1
      val t = new String(bytes.slice(pos, pos + 3), StandardCharsets.US_ASCII)
      pos += 3
      if tenant.isEmpty then tenant = t
      else if tenant != t then throw new IllegalArgumentException("mixed tenant")
      val evalSeq = readU32(bytes, pos); pos += 4
      val pidLen = readU16(bytes, pos); pos += 2
      val policyId = new String(bytes.slice(pos, pos + pidLen), StandardCharsets.UTF_8)
      pos += pidLen
      val decision = bytes(pos) & 0xFF; pos += 1
      val attrCount = bytes(pos) & 0xFF; pos += 1
      val attrs = scala.collection.mutable.Map.empty[String, String]
      var ac = 0
      while ac < attrCount do
        val klen = readU16(bytes, pos); pos += 2
        val key = new String(bytes.slice(pos, pos + klen), StandardCharsets.UTF_8)
        pos += klen
        val vlen = readU16(bytes, pos); pos += 2
        val value = new String(bytes.slice(pos, pos + vlen), StandardCharsets.UTF_8)
        pos += vlen
        attrs(key) = value
        ac += 1
      val utc = readU32(bytes, pos).toLong; pos += 4
      buf += AbacEvalEvent(tenant, evalSeq, policyId, decision, attrs.toMap, utc)
    pos = footerStart + 1
    val blen = readU16(bytes, pos); pos += 2
    val batchId = new String(bytes.slice(pos, pos + blen), StandardCharsets.UTF_8)
    ParsedBatch(batchId, tenant, buf.result())

  private def readU16(b: Array[Byte], p: Int): Int =
    ((b(p) & 0xFF) << 8) | (b(p + 1) & 0xFF)

  private def readU32(b: Array[Byte], p: Int): Long =
    ((b(p) & 0xFF).toLong << 24) | ((b(p + 1) & 0xFF).toLong << 16) |
      ((b(p + 2) & 0xFF).toLong << 8) | (b(p + 3) & 0xFF).toLong
