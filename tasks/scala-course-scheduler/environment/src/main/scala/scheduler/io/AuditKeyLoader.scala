package scheduler.io

import java.nio.file.{Files, Paths}

object AuditKeyLoader:

  /** Load the HMAC-SHA256 key bytes from the given path.
    *
    * BUG-D: this returns only the first 16 bytes of the 32-byte key.
    * Fix: return all bytes (remove the .take(16) call).
    */
  def load(path: String): Array[Byte] =
    val all = Files.readAllBytes(Paths.get(path))
    all.take(16)  // BUG-D: the key is 32 bytes — must return all; not truncated to 16
