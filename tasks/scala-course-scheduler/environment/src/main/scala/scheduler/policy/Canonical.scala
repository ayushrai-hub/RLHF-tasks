package scheduler.policy

import scheduler.models.*

object Canonical:

  /** Compute the policy fingerprint hex string.
    *
    * Build the canonical input string by concatenating, exactly in this order, with NO
    * whitespace except the literal field separators shown:
    *
    *   "threshold=" + passScore-formatted-to-4-decimals +
    *   ";weights=ru:" + roomUtil-4dp + ",fs:" + facultySat-4dp +
    *   ",ca:" + conflictAvoid-4dp + ",lb:" + loadBalance-4dp +
    *   ";slots=" + enabledSlots.mkString(",")
    *
    * Format doubles with "%.4f" (Locale.ROOT).
    *
    * Then return the lower-case hex of SHA-256 of the UTF-8 bytes of the canonical string.
    *
    * Example for default-final policy:
    *   "threshold=0.8000;weights=ru:0.2000,fs:0.3400,ca:0.3100,lb:0.1500;slots=MON-09,MON-11,..."
    */
  def fingerprint(policy: EffectivePolicy): String =
    // TODO: implement canonical fingerprint
    throw new NotImplementedError("Canonical.fingerprint")
