package scheduler.io

import scheduler.models.Assignment

object ScheduleWriter:

  /** Serialise the schedule to `outputPath` as pretty-printed JSON.
    *
    * Top-level keys MUST appear in exactly this order:
    * {
    *   "assignments":        [ { "course_id":..., "room_id":..., "time_slot_id":..., "instructor_id":... }, ... ],
    *   "audit_chain":        [ { "seq": <int>, "course_id":..., "hmac":... }, ... ],
    *   "policy_fingerprint": "hex",
    *   "session_seal":       "hex",
    *   "audit_tag":          "16-char lowercase hex (FNV-1a-64 over assignments)",
    *   "manifest_hash":      "64-char lowercase hex (PBKDF2WithHmacSHA256 manifest seal)",
    *   "metadata": { "total_courses": <int>, "generated_at": "<ISO-8601 UTC>" }
    * }
    *
    * Each audit_chain link must have THREE fields in order: "seq" (0-based int), "course_id", "hmac".
    * session_seal = SessionSealer.sealSession(policyFingerprint, auditChain, assignments.size, keyBytes)
    * audit_tag = FnvAuditTag.compute(assignments)  -- already computed by Main, passed as auditTag param
    *
    * The `audit_chain` MUST be in the same order as `assignments`.
    * Use ujson pretty-print with indent = 2 and an ISO-8601 UTC timestamp (Instant.now().toString).
    */
  def write(
    assignments:        List[Assignment],
    auditChain:         List[ujson.Obj],
    policyFingerprint:  String,
    keyBytes:           Array[Byte],
    auditTag:           String,
    manifestHash:       String,
    outputPath:         String
  ): Unit =
    // TODO: implement schedule writer with audit chain + fingerprint + session seal + audit_tag + manifest_hash
    throw new NotImplementedError("ScheduleWriter.write")
