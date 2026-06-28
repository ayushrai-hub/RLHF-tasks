package scheduler.optimizer

import scheduler.models.*

object ConstraintChecker:

  /** Return true iff `assignment` may be appended to `existing` without violating
    * any of the six hard constraints, given the (now policy-filtered) inputs.
    *
    *   2. No room double-booking          (room+slot pair unique among existing)
    *   3. No instructor conflict          (instructor+slot pair unique among existing)
    *   4. Instructor availability         (slot NOT in instructor.unavailableSlots)
    *   5. Capacity                        (room.capacity >= demand.getOrElse(courseId, 0))
    *   6. Room type                       (caller is responsible for choosing the right room/course)
    *
    * Constraint 1 (every course exactly once) is checked at the schedule level only.
    */
  def isValidAssignment(
    assignment:  Assignment,
    existing:    List[Assignment],
    rooms:       Map[String, Room],
    instructors: Map[String, Instructor],
    demand:      Map[String, Int]
  ): Boolean =
    // TODO: implement constraint validation
    throw new NotImplementedError("ConstraintChecker.isValidAssignment")

  /** Walk the entire schedule and return a (possibly empty) list of human-readable
    * violation messages, covering all six hard constraints. */
  def checkHardConstraints(
    assignments: List[Assignment],
    courses:     List[Course],
    rooms:       Map[String, Room],
    instructors: Map[String, Instructor],
    demand:      Map[String, Int]
  ): List[String] =
    // TODO: implement full hard-constraint audit
    throw new NotImplementedError("ConstraintChecker.checkHardConstraints")
