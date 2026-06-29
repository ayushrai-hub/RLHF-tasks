package scheduler.models

case class Assignment(
  courseId: String,
  roomId: String,
  timeSlotId: String,
  instructorId: String
)
