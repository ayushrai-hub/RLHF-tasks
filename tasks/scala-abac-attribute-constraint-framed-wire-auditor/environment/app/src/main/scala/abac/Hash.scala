package abac

import java.nio.charset.StandardCharsets
import java.security.MessageDigest

object Hash:
  def sha256Hex(data: String): String =
    val md = MessageDigest.getInstance("SHA-256")
    val bytes = md.digest(data.getBytes(StandardCharsets.UTF_8))
    bytes.map(b => f"$b%02x").mkString

  def sha256HexBytes(bytes: Array[Byte]): String =
    val md = MessageDigest.getInstance("SHA-256")
    val dig = md.digest(bytes)
    dig.map(b => f"$b%02x").mkString

  def fileDigest(bytes: Array[Byte]): String = sha256HexBytes(bytes)
