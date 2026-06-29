package scheduler.io

import scheduler.models.*

object AuditChain:

  /** Build a Merkle-style HMAC-SHA256 chain over the assignment list.
    *
    * For each assignment a_i (i starting at 0), compute:
    *   prev_i  = "GENESIS" if i == 0 else chain[i-1].hmac
    *   payload = s"$prev_i|${a_i.courseId}|${a_i.roomId}|${a_i.timeSlotId}|${a_i.instructorId}"
    *   hmac_i  = lower-case hex of HMAC_SHA256(keyBytes, payload.getBytes("UTF-8"))
    *
    * Return the chain as a List[ujson.Obj] with THREE fields per link (order matters):
    *   "seq"       -> i               (0-based integer index — MUST be present)
    *   "course_id" -> a_i.courseId
    *   "hmac"      -> hmac_i
    *
    * The order of the input list is preserved.
    */
  def build(assignments: List[Assignment], keyBytes: Array[Byte]): List[ujson.Obj] =
    // TODO: implement HMAC-SHA256 chain
    throw new NotImplementedError("AuditChain.build")
