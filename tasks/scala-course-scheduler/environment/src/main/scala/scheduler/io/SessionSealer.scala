package scheduler.io

import scheduler.models.*

object SessionSealer:

  /** Compute a session seal over the completed schedule output.
    *
    * Build the seal input exactly (no added whitespace):
    *   "seal:" + policyFingerprint + "|" + numAssignments.toString + "|" +
    *   auditChain.map(l =>
    *     l("seq").num.toInt.toString + ":" + l("course_id").str + ":" + l("hmac").str
    *   ).mkString("|")
    *
    * Note: each chain entry includes THREE colon-separated parts: seq:course_id:hmac
    * (not two). The seq field is the 0-based integer index from the audit chain link.
    *
    * Return the lower-case hex of HMAC-SHA256(keyBytes, input.getBytes("UTF-8")).
    * Use javax.crypto.Mac with algorithm "HmacSHA256".
    */
  def sealSession(
    policyFingerprint: String,
    auditChain:        List[ujson.Obj],
    numAssignments:    Int,
    keyBytes:          Array[Byte]
  ): String =
    // TODO: implement session seal
    throw new NotImplementedError("SessionSealer.sealSession")
