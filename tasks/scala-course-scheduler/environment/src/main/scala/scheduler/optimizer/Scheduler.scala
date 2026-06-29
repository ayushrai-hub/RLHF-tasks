package scheduler.optimizer

import scheduler.models.*

object Scheduler:

  /** Produce a valid, score-maximising schedule.  EVERY course in `courses` must appear
    * exactly once in the returned list, satisfying all six hard constraints.
    *
    * The optimiser receives the already-effective inputs (demand has the CSV overlay
    * applied; instructor preferred_slots have been expanded).  It may consult `weights`
    * via SoftScorer.score(...) during local search but the SAME weights must be used
    * consistently — do NOT bake the base-tier weights into the optimiser.
    *
    * `enabledSlots` filters the slot universe to those slots whitelisted by the
    * effective policy; assignments must use only those slot IDs.
    *
    * Throw RuntimeException if no feasible assignment exists for some course
    * (the message must name the unplaceable course id).
    */
  def optimize(
    courses:      List[Course],
    rooms:        List[Room],
    slots:        List[TimeSlot],
    instructors:  List[Instructor],
    demand:       Map[String, Int],
    conflicts:    List[List[String]],
    weights:      Weights,
    enabledSlots: List[String]
  ): List[Assignment] =
    // TODO: implement course scheduling optimizer
    throw new NotImplementedError("Scheduler.optimize")
