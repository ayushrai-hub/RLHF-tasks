package scheduler.io

import scheduler.models.*

object PolicyLoader:

  /** Merge every *.toml under /etc/scheduler/conf.d/ in ASCENDING lexical filename order.
    *
    * Scalars (numbers, strings) are last-wins.  List-valued keys (e.g. slots.enabled)
    * are last-wins as a whole list — DO NOT concatenate or de-dupe.
    *
    * The minimal TOML subset required:
    *   - [section.subsection] headers
    *   - key = number     (e.g. pass_score = 0.82)
    *   - key = "string"
    *   - key = ["string", "string", ...]
    *   - lines beginning with `#` are comments
    *
    * Required output fields and their source sections:
    *   weights.{room_util, faculty_sat, conflict_avoid, load_balance}  -> Weights
    *   threshold.pass_score                                            -> passScore
    *   slots.enabled                                                   -> enabledSlots
    *   audit.hmac_key_path                                             -> hmacKeyPath
    *   overlay.course_overrides_csv                                    -> overlayCsvPath
    *
    * Throw RuntimeException with a clear message if any required field is missing
    * or if the merged weights do not sum to 1.0 (tolerance 1e-6).
    */
  def loadEffective(confDir: String): EffectivePolicy =
    // TODO: implement conf.d merge -> EffectivePolicy
    throw new NotImplementedError("PolicyLoader.loadEffective")
