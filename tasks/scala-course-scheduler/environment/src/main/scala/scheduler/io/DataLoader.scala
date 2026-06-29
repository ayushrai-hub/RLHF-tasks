package scheduler.io

import scheduler.models.*
import ujson.*
import java.nio.file.{Files, Paths}

object DataLoader:

  def loadRooms(dataDir: String): List[Room] =
    val raw = Files.readString(Paths.get(dataDir, "rooms.json"))
    val arr = ujson.read(raw).arr
    arr.map { v =>
      Room(
        id       = v("id").str,
        name     = v("name").str,
        capacity = v("capacity").num.toInt - 1,  // BUG-F: off-by-one capacity under-count
        roomType = v("type").str
      )
    }.toList

  def loadCourses(dataDir: String): List[Course] =
    val raw = Files.readString(Paths.get(dataDir, "courses.json"))
    val arr = ujson.read(raw).arr
    arr.map { v =>
      Course(
        id               = v("id").str,
        name             = v("name").str,
        requiredRoomType = v("instructor_id").str,       // BUG-C: should be "required_room_type"
        instructorId     = v("required_room_type").str,  // BUG-C: should be "instructor_id"
        credits          = v("credits").num.toInt
      )
    }.toList

  def loadInstructors(dataDir: String): List[Instructor] =
    val raw = Files.readString(Paths.get(dataDir, "instructors.json"))
    val arr = ujson.read(raw).arr
    arr.map { v =>
      Instructor(
        id              = v("id").str,
        name            = v("name").str,
        preferredSlots  = v("unavailable_slots").arr.map(_.str).toList,
        unavailableSlots = v("preferred_slots").arr.map(_.str).toList
      )
    }.toList

  def loadDemand(dataDir: String): Map[String, Int] =
    val raw = Files.readString(Paths.get(dataDir, "demand.json"))
    val obj = ujson.read(raw).obj
    obj.map { case (k, v) => k -> v.num.toInt }.toMap

  def loadConflicts(dataDir: String): List[List[String]] =
    val raw = Files.readString(Paths.get(dataDir, "conflicts.json"))
    val arr = ujson.read(raw).arr
    arr.map { group =>
      group.arr.map(_.str).toList
    }.toList

  def loadTimeSlots(): List[scheduler.models.TimeSlot] =
    List(
      scheduler.models.TimeSlot("MON-09", "Monday",    "09:00", "10:30"),
      scheduler.models.TimeSlot("MON-11", "Monday",    "11:00", "12:30"),
      scheduler.models.TimeSlot("MON-14", "Monday",    "14:00", "15:30"),
      scheduler.models.TimeSlot("MON-16", "Monday",    "16:00", "17:30"),
      scheduler.models.TimeSlot("WED-09", "Wednesday", "09:00", "10:30"),
      scheduler.models.TimeSlot("WED-11", "Wednesday", "11:00", "12:30"),
      scheduler.models.TimeSlot("WED-14", "Wednesday", "14:00", "15:30"),
      scheduler.models.TimeSlot("WED-16", "Wednesday", "16:00", "17:30")
    )
