package scheduler.optimizer

import scheduler.models.*

object SoftScorer:

  /** Compute the four-component soft score exactly mirroring /opt/scheduler/model.py.
    *
    * Components:
    *   roomUtil      = mean( min(1.0, demand[c] / room.capacity) ) across assignments
    *   facultySat    = mean( 1.0 if slot in instr.preferredSlots else 0.5 )
    *   conflictScore = 1.0 - (#conflict-groups with >=2 members in same slot) / max(1, #groups)
    *   loadBalance   = if #unique-slot-counts <= 1 then 0.5
    *                   else max(0, 1.0 - stdDev / mean)
    *                   where stdDev = sqrt(mean((c - meanLoad)^2)),
    *                         meanLoad = sum(slotCounts) / size(slotCounts),
    *                         mean     = n / 8        (n = assignments.size, 8 = total slot universe)
    *
    * Final = w.roomUtil*roomUtil + w.facultySat*facultySat
    *       + w.conflictAvoid*conflictScore + w.loadBalance*loadBalance
    *
    * Return 0.0 if assignments is empty.
    */
  def score(
    assignments: List[Assignment],
    instrMap:    Map[String, Instructor],
    demand:      Map[String, Int],
    roomMap:     Map[String, Room],
    conflicts:   List[List[String]],
    weights:     Weights
  ): Double =
    // TODO: implement soft scoring
    throw new NotImplementedError("SoftScorer.score")
