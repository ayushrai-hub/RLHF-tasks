package scheduler.io

import scheduler.models.Assignment

object FnvAuditTag:

  /**
   * Compute an FNV-1a-64 audit tag over the full assignment list.
   *
   * Step 1 -- Build the input string (UTF-8 bytes):
   *   assignments.map(a =>
   *     s"${a.courseId}|${a.roomId}|${a.timeSlotId}|${a.instructorId}"
   *   ).mkString("\n")
   *
   * Step 2 -- FNV-1a-64 hash:
   *   val FNV_PRIME  = 1099511628211L
   *   val FNV_OFFSET = 0xcbf29ce484222325L   // = -3750763034362895579L as signed Long
   *   var hash = FNV_OFFSET
   *   for (byte <- input.getBytes("UTF-8")) {
   *     hash ^= (byte & 0xffL)
   *     hash *= FNV_PRIME
   *   }
   *
   * Step 3 -- Convert to UNSIGNED 16-char lowercase hex:
   *   java.lang.Long.toUnsignedString(hash, 16).reverse.padTo(16, '0').reverse
   *   (zero-pad on the LEFT to exactly 16 chars)
   *
   * HARD RULE: Do NOT use java.lang.Long.toHexString (it omits leading zeros and
   * mishandles negative longs).  Use Long.toUnsignedString(hash, 16) then pad.
   */
  def compute(assignments: List[Assignment]): String =
    // TODO: implement FNV-1a-64 audit tag
    throw new NotImplementedError("FnvAuditTag.compute")
