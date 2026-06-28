package scheduler.models

case class Instructor(
  id: String,
  name: String,
  preferredSlots: List[String],
  unavailableSlots: List[String]
)
