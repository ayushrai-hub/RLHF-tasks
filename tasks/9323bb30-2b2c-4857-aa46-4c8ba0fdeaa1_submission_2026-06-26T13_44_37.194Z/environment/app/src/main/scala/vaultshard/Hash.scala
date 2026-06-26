package vaultshard

import java.security.MessageDigest

object Hash {
  def sha256Hex(data: Array[Byte]): String = {
    val md = MessageDigest.getInstance("SHA-256")
    md.digest(data).map(b => "%02x".format(b & 0xFF)).mkString
  }
}
