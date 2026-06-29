package scheduler.io

import scheduler.models.*

object OverlayApplier:

  /** Apply the CSV at overlay.course_overrides_csv to the loaded inputs.
    *
    * CSV format (header row + comma-separated rows):
    *   course_id,field,value
    *
    * Supported `field` values:
    *   demand    -> integer; replaces demand[course_id]
    *
    * If overlayCsvPath is empty or the file does not exist, return the inputs unchanged.
    * Unknown course_ids in the CSV are silently ignored.
    * Unknown field names raise RuntimeException with the offending row text.
    */
  def applyDemandOverrides(
    demand:         Map[String, Int],
    overlayCsvPath: String
  ): Map[String, Int] =
    // TODO: implement CSV demand overlay
    throw new NotImplementedError("OverlayApplier.applyDemandOverrides")

  /** Expand instructor preferred-slot abbreviations into canonical 6-char slot IDs.
    *
    * The data files store the canonical form (e.g. "MON-09") already, but any
    * instructor entry whose preferred_slots contains a 3-char short code such as
    * "M09", "W14", "M16" must be expanded:
    *   M->MON, W->WED, then a literal '-' joining the digit pair.
    *
    * Any 6-char slot ID (already canonical) passes through unchanged.
    * Any other shape raises RuntimeException with the offending value.
    */
  def expandPreferredSlots(instructors: List[Instructor]): List[Instructor] =
    // TODO: implement abbreviation expansion
    throw new NotImplementedError("OverlayApplier.expandPreferredSlots")
