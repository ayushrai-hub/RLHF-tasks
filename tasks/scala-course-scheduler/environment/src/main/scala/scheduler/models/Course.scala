package scheduler.models

case class Course(
  id: String,
  name: String,
  requiredRoomType: String,
  instructorId: String,
  credits: Int
)
