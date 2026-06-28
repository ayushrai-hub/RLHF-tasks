package scheduler.io

import scheduler.models.Assignment

object ManifestSeal:
  /** Compute a PBKDF2WithHmacSHA256 manifest hash over sorted assignments.
   *
   * Input string: assignments sorted by courseId, each as
   *   "courseId:roomId:timeSlotId:instructorId"
   * joined with "\n".
   * Salt: first 16 bytes of keyBytes.
   * Iterations: 4096. Key length: 32 bytes.
   * Returns: lowercase hex string of 32 bytes (64 chars).
   */
  def compute(assignments: List[Assignment], keyBytes: Array[Byte]): String =
    throw new NotImplementedError("ManifestSeal.compute not yet implemented")
