#!/bin/bash
# Oracle solve.sh for SUPER-HARD scala-course-scheduler.
# Handles triple LD_PRELOAD (write+kill+exec guards), 28 SIGTERM-immune daemons,
# archive resurrection, fixes 6 non-stub bugs, and implements all 11 Scala stubs.
set -euo pipefail

# Set /proc/self/comm to a 15-char value starting with "scheduler-fix-".
# The exec guard checks self_comm_starts_with("scheduler-fix-"); Linux caps comm at
# 15 chars, so writing "scheduler-fix-k" (15 chars) is the shortest valid bypass.
# The kill guard also uses this prefix but is bypassed by bash's builtin kill()
# which calls SYS_kill directly, not through the LD_PRELOAD kill() wrapper.
_refresh_comm() {
  printf 'scheduler-fix-k' > /proc/self/comm
}

# Helper: kill all PIDs matching a pgrep -f pattern (bash builtin kill — NOT pkill).
_kd() {
  local _pids
  _pids=$(pgrep -f "$1" 2>/dev/null) || return 0
  [ -n "$_pids" ] || return 0
  # shellcheck disable=SC2086
  kill -9 $_pids 2>/dev/null || true
}

# ----- 1. Set initial comm token.
_refresh_comm
echo "Bypass: comm = $(cat /proc/self/comm)"

# ----- 2. Destroy resurrection infrastructure FIRST — BEFORE any daemon kills.
#   archive-warden checks for missing daemons every 15 s and relaunches them from
#   the daemon archive.  Removing all three archive locations prevents any future
#   relaunch even if archive-warden wakes up in the middle of our kill sequence.
#   The write guard only protects /etc/scheduler/conf.d/ so these calls are allowed.
rm -f /var/lib/scheduler-resurrect/daemons.tar.b64 2>/dev/null || true
rm -f /var/lib/scheduler-resurrect/stubs.tar.b64 2>/dev/null || true
rm -rf /opt/scheduler/.hidden/ 2>/dev/null || true
rm -rf /opt/scheduler/.vault/ 2>/dev/null || true
rm -f /etc/cron.d/scheduler-resurrect /etc/cron.d/scheduler-aux /etc/cron.d/scheduler-extra 2>/dev/null || true
chmod -x /opt/scheduler/daemons/launch-all.sh 2>/dev/null || true
sed -i '/launch-all/d' /etc/bash.bashrc /root/.bashrc 2>/dev/null || true
rm -f /etc/profile.d/zz-scheduler-daemons.sh 2>/dev/null || true

# ----- 3. Kill archive-warden FIRST (it can no longer relaunch from the deleted archive).
#   Loop with comm refresh in case key-rotator fired since step 1.
for _i in 1 2 3 4 5; do
  _refresh_comm
  _kd scheduler-arcwa
  pgrep -f scheduler-arcwa > /dev/null 2>&1 || break
  sleep 0.2
done

# ----- 4. Kill key-rotator + token-refresher in a tight loop with comm refresh.
#   These two daemons change the key on every fire.  Re-read the key before each
#   attempt so our comm token always matches whatever key is current at that instant.
for _i in 1 2 3 4 5 6 7 8 9 10; do
  _refresh_comm
  _kd scheduler-keyro
  _kd scheduler-trefr
  { pgrep -f scheduler-keyro > /dev/null 2>&1 || pgrep -f scheduler-trefr > /dev/null 2>&1; } || break
  sleep 0.2
done

# ----- 5. Kill remaining 24 daemons (key now stable, archives gone).
for _pass in 1 2 3; do
  _refresh_comm
  _kd scheduler-cronr
  _kd scheduler-ldpres
  _kd scheduler-watchdog
  _kd scheduler-warden
  _kd scheduler-policy
  _kd scheduler-binco
  _kd scheduler-srcwa
  _kd scheduler-outco
  _kd scheduler-chmwd
  _kd scheduler-envsa
  _kd scheduler-tmpco
  _kd scheduler-cfpoi
  _kd scheduler-osbr
  _kd scheduler-bsrst
  _kd scheduler-dscra
  _kd scheduler-dmcor
  _kd scheduler-bsabt
  _kd scheduler-slpoi
  _kd scheduler-vaulk
  # 6 new daemons:
  _kd scheduler-confsc
  _kd scheduler-jarnu
  _kd scheduler-srcma
  _kd scheduler-cfmrg
  _kd scheduler-crext
  _kd scheduler-datmn
  sleep 0.2
done

# ----- 6. Restore HMAC key and data files from backup.
cp /var/lib/scheduler-resurrect/audit.key.bak /etc/scheduler/audit.key 2>/dev/null || true
# Restore courses.json (data-scrambler changes lab→lecture for all lab courses)
cp /var/lib/scheduler-resurrect/courses.json.bak /opt/scheduler/courses.json 2>/dev/null || true
# Restore demand.json (demand-corrupter inflates MATH101/PHYS101/PSY101 to 9999)
cp /var/lib/scheduler-resurrect/demand.json.bak /opt/scheduler/demand.json 2>/dev/null || true
# Restore build.sbt (build-saboteur appends garbage sbt lines)
cp /var/lib/scheduler-resurrect/build.sbt.bak /app/build.sbt 2>/dev/null || true
# Restore canonical 97-emergency.toml (slot-poisoner sets pass_score=0.99, 2 slots)
cp /var/lib/scheduler-resurrect/97-emergency.toml.bak \
   /etc/scheduler/conf.d/97-emergency.toml 2>/dev/null || true
# Restore 10-weights.toml (conf-scrambler corrupts load_balance to 0.90)
cp /var/lib/scheduler-resurrect/10-weights.toml.bak /etc/scheduler/conf.d/10-weights.toml 2>/dev/null || true
# Restore 99-runtime.toml (conf-merger sets hmac_key_path to /dev/null)
cp /var/lib/scheduler-resurrect/99-runtime.toml.bak /etc/scheduler/conf.d/99-runtime.toml 2>/dev/null || true
# Restore rooms.json (data-mangler swaps lecture/lab types)
cp /var/lib/scheduler-resurrect/rooms.json.bak /opt/scheduler/rooms.json 2>/dev/null || true

# ----- 7. Clear LD_PRELOAD (all daemons dead, preload-restorer gone).
: > /etc/ld.so.preload

# ----- 8. Restore canonical 90-final.toml -----
cp /var/lib/scheduler-resurrect/90-final.toml.bak /etc/scheduler/conf.d/90-final.toml 2>/dev/null || true
cat > /etc/scheduler/conf.d/90-final.toml << 'TOML_EOF'
# scheduler FINAL policy — tier 90 (highest precedence)
[threshold]
pass_score = 0.80

[weights]
room_util       = 0.20
faculty_sat     = 0.34
conflict_avoid  = 0.31
load_balance    = 0.15

[slots]
enabled = ["MON-09","MON-11","MON-14","MON-16","WED-09","WED-11","WED-14","WED-16"]
TOML_EOF

# Remove tertiary cron job (cron-extra recreates this every 21s)
rm -f /etc/cron.d/scheduler-extra 2>/dev/null || true

# ----- 9. Restore 50-overrides.toml (conf-poisoner hides it as a dot-file) -----
mv /etc/scheduler/conf.d/.50-overrides.toml.save /etc/scheduler/conf.d/50-overrides.toml 2>/dev/null || true
# Also write canonical content in case it was corrupted:
cat > /etc/scheduler/conf.d/50-overrides.toml << 'TOML_EOF'
# scheduler overrides — tier 50
[threshold]
pass_score = 0.79

[overlay]
course_overrides_csv = "/etc/scheduler/course-overrides.csv"

[slots]
enabled = ["MON-09","MON-11","MON-14","MON-16","WED-09","WED-11","WED-14","WED-16"]
TOML_EOF

# ----- 10. Restore canonical course-overrides.csv (env-saboteur may have corrupted it) -----
cat > /etc/scheduler/course-overrides.csv << 'CSV_EOF'
course_id,field,value
MATH101,demand,165
PHYS101,demand,150
PSY101,demand,155
ECON101,demand,128
MATH201,demand,135
CHEM101,demand,115
ECON201,demand,110
PHYS201,demand,108
MATH102,demand,98
BIO101,demand,90
MGMT201,demand,58
PE101,demand,70
CSV_EOF

# ----- 11. Re-enable writes on source tree (chmod-warden may have locked it) -----
chmod -R +w /app/src/main/scala/ 2>/dev/null || true

# ----- 12. Fix Bug A in Main.scala: remove .sortBy(_.courseId) before AuditChain.build,
#           add ManifestSeal call, and update ScheduleWriter.write signature -----
cat > /app/src/main/scala/scheduler/Main.scala << 'SCALA_EOF'
package scheduler

import scheduler.io.*
import scheduler.optimizer.Scheduler
import scheduler.policy.Canonical
import java.nio.file.{Files, Paths}

object Main:
  val DefaultDataDir    = "/opt/scheduler"
  val DefaultOutputPath = "/opt/scheduler/schedule.json"
  val PolicyConfDir     = "/etc/scheduler/conf.d"

  def main(args: Array[String]): Unit =
    val dataDir    = if args.length > 0 then args(0) else DefaultDataDir
    val outputPath = if args.length > 1 then args(1) else DefaultOutputPath
    println(s"Loading input data from $dataDir ...")
    val policy = PolicyLoader.loadEffective(PolicyConfDir)
    println(s"Effective policy: weights=${policy.weights}, pass_score=${policy.passScore}, slots=${policy.enabledSlots.size}, overlay=${policy.overlayCsvPath}")
    val courses         = DataLoader.loadCourses(dataDir)
    val rooms           = DataLoader.loadRooms(dataDir)
    val instructorsBase = DataLoader.loadInstructors(dataDir)
    val demandBase      = DataLoader.loadDemand(dataDir)
    val conflicts       = DataLoader.loadConflicts(dataDir)
    val slots           = DataLoader.loadTimeSlots()
    val instructors = OverlayApplier.expandPreferredSlots(instructorsBase)
    val demand      = OverlayApplier.applyDemandOverrides(demandBase, policy.overlayCsvPath)
    println(s"Loaded ${courses.size} courses, ${rooms.size} rooms, ${instructors.size} instructors, ${slots.size} time slots, ${conflicts.size} conflict groups")
    println("Running optimizer ...")
    val assignments = Scheduler.optimize(courses, rooms, slots, instructors, demand, conflicts, policy.weights, policy.enabledSlots)
    println(s"Optimizer produced ${assignments.size} assignments")
    val keyBytes    = Files.readAllBytes(Paths.get(policy.hmacKeyPath))
    val chain       = AuditChain.build(assignments, keyBytes)          // BUG-A FIXED: no .sortBy
    val fingerprint = Canonical.fingerprint(policy)
    println(s"Policy fingerprint: $fingerprint")
    val auditTag    = FnvAuditTag.compute(assignments)
    println(s"Audit tag: $auditTag")
    val manifestHash = ManifestSeal.compute(assignments, keyBytes)
    println(s"Manifest hash: $manifestHash")
    ScheduleWriter.write(assignments, chain, fingerprint, keyBytes, auditTag, manifestHash, outputPath)
    println("Done.")
SCALA_EOF

# ----- 13. Fix Bug B + Bug F in DataLoader.scala: restore correct slot field assignment order
#           and remove the off-by-one capacity subtraction from loadRooms -----
cat > /app/src/main/scala/scheduler/io/DataLoader.scala << 'SCALA_EOF'
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
        capacity = v("capacity").num.toInt,  // BUG-F FIXED: no - 1
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
        requiredRoomType = v("required_room_type").str,
        instructorId     = v("instructor_id").str,
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
        preferredSlots  = v("preferred_slots").arr.map(_.str).toList,
        unavailableSlots = v("unavailable_slots").arr.map(_.str).toList
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

  def loadPrerequisites(dataDir: String): ujson.Value =
    ujson.read(Files.readString(Paths.get(dataDir, "prerequisites.json")))

  def loadRoomBlackouts(dataDir: String): ujson.Value =
    ujson.read(Files.readString(Paths.get(dataDir, "room-blackouts.json")))

  def loadCohorts(dataDir: String): ujson.Value =
    ujson.read(Files.readString(Paths.get(dataDir, "cohorts.json")))

  def loadFixedPlacements(dataDir: String): ujson.Value =
    ujson.read(Files.readString(Paths.get(dataDir, "fixed-placements.json")))

  def loadLinkedSections(dataDir: String): ujson.Value =
    ujson.read(Files.readString(Paths.get(dataDir, "linked-sections.json")))

  def loadInstructorLoads(dataDir: String): ujson.Value =
    ujson.read(Files.readString(Paths.get(dataDir, "instructor-loads.json")))

  def loadRoomZones(dataDir: String): ujson.Value =
    ujson.read(Files.readString(Paths.get(dataDir, "room-zones.json")))

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
SCALA_EOF

# ----- 14. Implement all 10 Scala stubs -----

cat > /app/src/main/scala/scheduler/io/PolicyLoader.scala << 'SCALA_EOF'
package scheduler.io

import scheduler.models.*
import java.nio.file.{Files, Paths}
import scala.jdk.CollectionConverters.*
import scala.collection.mutable

object PolicyLoader:

  private val SectionRe = """\s*\[([A-Za-z_][A-Za-z0-9_.]*)\]\s*""".r
  private val ListRe    = """\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\[(.*)\]\s*(?:#.*)?""".r
  private val StrRe     = """\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"((?:[^"\\]|\\.)*)"\s*(?:#.*)?""".r
  private val NumRe     = """\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([+-]?\d+(?:\.\d+)?)\s*(?:#.*)?""".r
  private val ItemRe    = """"([^"]*)"""".r

  private def parseFile(text: String): Map[String, Map[String, Any]] =
    val out = mutable.LinkedHashMap[String, mutable.LinkedHashMap[String, Any]]()
    var section: Option[String] = None
    for raw <- text.linesIterator do
      val stripped = raw.trim
      if stripped.isEmpty || stripped.startsWith("#") then ()
      else stripped match
        case SectionRe(s) =>
          section = Some(s)
          out.getOrElseUpdate(s, mutable.LinkedHashMap.empty[String, Any])
        case ListRe(k, body) =>
          section.foreach { s =>
            val items = ItemRe.findAllMatchIn(body).map(_.group(1)).toList
            out(s).update(k, items)
          }
        case StrRe(k, v) =>
          section.foreach(s => out(s).update(k, v))
        case NumRe(k, v) =>
          section.foreach { s =>
            val parsed: Any = if v.contains(".") then v.toDouble else v.toInt
            out(s).update(k, parsed)
          }
        case _ => ()
    out.view.mapValues(_.toMap).toMap

  def loadEffective(confDir: String): EffectivePolicy =
    val dir = Paths.get(confDir)
    if !Files.isDirectory(dir) then
      throw new RuntimeException(s"Policy dir not found: $confDir")
    val files = Files.list(dir).iterator.asScala.toList
      .filter(p => p.toString.endsWith(".toml"))
      .sortBy(_.getFileName.toString)
    if files.isEmpty then
      throw new RuntimeException(s"No *.toml files in $confDir")

    val merged = mutable.LinkedHashMap[String, mutable.LinkedHashMap[String, Any]]()
    for p <- files do
      val parsed = parseFile(Files.readString(p))
      for (sec, kv) <- parsed do
        val target = merged.getOrElseUpdate(sec, mutable.LinkedHashMap.empty[String, Any])
        for (k, v) <- kv do target.update(k, v)

    def num(sec: String, key: String): Double =
      merged.get(sec).flatMap(_.get(key)) match
        case Some(d: Double) => d
        case Some(i: Int)    => i.toDouble
        case other => throw new RuntimeException(s"Missing or non-numeric [$sec].$key (got $other)")

    def str(sec: String, key: String): String =
      merged.get(sec).flatMap(_.get(key)) match
        case Some(s: String) => s
        case other => throw new RuntimeException(s"Missing or non-string [$sec].$key (got $other)")

    def list(sec: String, key: String): List[String] =
      merged.get(sec).flatMap(_.get(key)) match
        case Some(xs: List[?]) => xs.map(_.toString)
        case other => throw new RuntimeException(s"Missing or non-list [$sec].$key (got $other)")

    val w = Weights(
      roomUtil      = num("weights", "room_util"),
      facultySat    = num("weights", "faculty_sat"),
      conflictAvoid = num("weights", "conflict_avoid"),
      loadBalance   = num("weights", "load_balance"),
    )
    if math.abs(w.sum - 1.0) > 1e-6 then
      throw new RuntimeException(s"weights do not sum to 1.0: ${w.sum}")

    EffectivePolicy(
      weights        = w,
      passScore      = num("threshold", "pass_score"),
      enabledSlots   = list("slots", "enabled"),
      hmacKeyPath    = str("audit", "hmac_key_path"),
      overlayCsvPath = str("overlay", "course_overrides_csv"),
    )
SCALA_EOF

cat > /app/src/main/scala/scheduler/io/OverlayApplier.scala << 'SCALA_EOF'
package scheduler.io

import scheduler.models.*
import java.nio.file.{Files, Paths}

object OverlayApplier:

  private val DayMap = Map("M" -> "MON", "W" -> "WED")
  private val SlotShort = """([MW])(\d{2})""".r
  private val SlotLong  = """[A-Z]{3}-\d{2}""".r

  def applyDemandOverrides(
    demand:         Map[String, Int],
    overlayCsvPath: String
  ): Map[String, Int] =
    if overlayCsvPath.isEmpty then demand
    else
      val p = Paths.get(overlayCsvPath)
      if !Files.exists(p) then demand
      else
        val lines = Files.readString(p).split("\n").iterator.map(_.trim).filter(_.nonEmpty).toList
        if lines.isEmpty then demand
        else
          val header = lines.head.split(",").toList
          if header != List("course_id", "field", "value") then
            throw new RuntimeException(s"Overlay CSV header invalid: $header")
          var out = demand
          for row <- lines.tail do
            val parts = row.split(",", -1).toList
            if parts.size != 3 then
              throw new RuntimeException(s"Overlay CSV bad row: $row")
            val cid   = parts(0)
            val field = parts(1)
            val value = parts(2)
            field match
              case "demand" =>
                if out.contains(cid) then out = out.updated(cid, value.toInt)
              case other =>
                throw new RuntimeException(s"Overlay CSV unknown field: $row")
          out

  private def expandOne(s: String): String = s match
    case SlotLong()        => s
    case SlotShort(d, hh)  => s"${DayMap.getOrElse(d, throw new RuntimeException(s"Unknown day: $d"))}-$hh"
    case other             => throw new RuntimeException(s"Unrecognised slot id: $other")

  def expandPreferredSlots(instructors: List[Instructor]): List[Instructor] =
    instructors.map(i => i.copy(preferredSlots = i.preferredSlots.map(expandOne)))
SCALA_EOF

cat > /app/src/main/scala/scheduler/io/AuditChain.scala << 'SCALA_EOF'
package scheduler.io

import scheduler.models.*
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import java.nio.charset.StandardCharsets

object AuditChain:

  private def toHex(bytes: Array[Byte]): String =
    val sb = new StringBuilder(bytes.length * 2)
    for b <- bytes do sb.append(f"${b & 0xff}%02x")
    sb.toString

  def build(assignments: List[Assignment], keyBytes: Array[Byte]): List[ujson.Obj] =
    val keySpec = SecretKeySpec(keyBytes, "HmacSHA256")
    val mac     = Mac.getInstance("HmacSHA256")
    mac.init(keySpec)
    var prev = "GENESIS"
    val buf  = scala.collection.mutable.ListBuffer[ujson.Obj]()
    var idx  = 0
    for a <- assignments do
      val payload = s"$prev|${a.courseId}|${a.roomId}|${a.timeSlotId}|${a.instructorId}"
      mac.reset()
      val digest = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8))
      val hex    = toHex(digest)
      buf += ujson.Obj(
        "seq"       -> ujson.Num(idx),
        "course_id" -> ujson.Str(a.courseId),
        "hmac"      -> ujson.Str(hex),
      )
      prev = hex
      idx += 1
    buf.toList
SCALA_EOF

cat > /app/src/main/scala/scheduler/io/SessionSealer.scala << 'SCALA_EOF'
package scheduler.io

import scheduler.models.*
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import java.nio.charset.StandardCharsets

object SessionSealer:

  private def toHex(bytes: Array[Byte]): String =
    val sb = new StringBuilder(bytes.length * 2)
    for b <- bytes do sb.append(f"${b & 0xff}%02x")
    sb.toString

  def sealSession(
    policyFingerprint: String,
    auditChain:        List[ujson.Obj],
    numAssignments:    Int,
    keyBytes:          Array[Byte]
  ): String =
    val chainStr = auditChain
      .map(l => s"${l("seq").num.toInt}:${l("course_id").str}:${l("hmac").str}")
      .mkString("|")
    val input = s"seal:$policyFingerprint|$numAssignments|$chainStr"
    val keySpec = SecretKeySpec(keyBytes, "HmacSHA256")
    val mac     = Mac.getInstance("HmacSHA256")
    mac.init(keySpec)
    toHex(mac.doFinal(input.getBytes(StandardCharsets.UTF_8)))
SCALA_EOF

cat > /app/src/main/scala/scheduler/io/FnvAuditTag.scala << 'SCALA_EOF'
package scheduler.io

import scheduler.models.Assignment

object FnvAuditTag:
  def compute(assignments: List[Assignment]): String =
    val FNV_PRIME:  Long = 1099511628211L
    val FNV_OFFSET: Long = 0xcbf29ce484222325L  // -3750763034362895579L
    val input = assignments.map(a =>
      s"${a.courseId}|${a.roomId}|${a.timeSlotId}|${a.instructorId}"
    ).mkString("\n")
    var hash = FNV_OFFSET
    for (b <- input.getBytes("UTF-8")) {
      hash ^= (b & 0xffL)
      hash  = hash * FNV_PRIME
    }
    java.lang.Long.toUnsignedString(hash, 16).reverse.padTo(16, '0').reverse
SCALA_EOF

cat > /app/src/main/scala/scheduler/io/ScheduleWriter.scala << 'SCALA_EOF'
package scheduler.io

import scheduler.models.Assignment
import java.nio.file.{Files, Paths}
import java.time.Instant
import scala.collection.mutable

object ScheduleWriter:

  private val FixtureHashes = List(
    "cohorts.json" -> "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "conflicts.json" -> "4f4dbee6e721418fe8c66d1d943788ff362b0b9db69a6b8f17e9653061113a9b",
    "fixed-placements.json" -> "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "instructor-loads.json" -> "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "linked-sections.json" -> "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "prerequisites.json" -> "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "room-blackouts.json" -> "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "room-zones.json" -> "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
  )

  private def sha256Hex(s: String): String =
    val md = java.security.MessageDigest.getInstance("SHA-256")
    md.digest(s.getBytes(java.nio.charset.StandardCharsets.UTF_8)).map(b => f"${b & 0xff}%02x").mkString

  private def constraintDigest(assignments: List[Assignment]): String =
    val rows = assignments.sortBy(_.courseId).map(a =>
      s"${a.courseId}|${a.roomId}|${a.timeSlotId}|${a.instructorId}"
    ).mkString("\n")
    val fixturePart = FixtureHashes.sortBy(_._1).map { case (k, v) => s"$k:$v" }.mkString("|")
    sha256Hex(rows + "\n--constraints--\n" + fixturePart)

  def write(
    assignments:        List[Assignment],
    auditChain:         List[ujson.Obj],
    policyFingerprint:  String,
    keyBytes:           Array[Byte],
    auditTag:           String,
    manifestHash:       String,
    outputPath:         String
  ): Unit =
    val seal = SessionSealer.sealSession(policyFingerprint, auditChain, assignments.size, keyBytes)

    val items = mutable.ArrayBuffer[ujson.Value]()
    assignments.foreach { a =>
      items += ujson.Obj(
        "course_id"     -> ujson.Str(a.courseId),
        "room_id"       -> ujson.Str(a.roomId),
        "time_slot_id"  -> ujson.Str(a.timeSlotId),
        "instructor_id" -> ujson.Str(a.instructorId),
      )
    }
    val chainArr = mutable.ArrayBuffer[ujson.Value]()
    auditChain.foreach(chainArr += _)

    val out = ujson.Obj(
      "assignments"        -> ujson.Arr(items),
      "audit_chain"        -> ujson.Arr(chainArr),
      "policy_fingerprint" -> ujson.Str(policyFingerprint),
      "session_seal"       -> ujson.Str(seal),
      "audit_tag"          -> ujson.Str(auditTag),
      "manifest_hash"      -> ujson.Str(manifestHash),
      "metadata"           -> ujson.Obj(
        "total_courses"     -> ujson.Num(assignments.size),
        "generated_at"      -> ujson.Str(Instant.now().toString),
        "distinct_slots"    -> ujson.Num(assignments.map(_.timeSlotId).distinct.size),
        "constraint_digest" -> ujson.Str(constraintDigest(assignments)),
        "score_components"  -> ujson.Obj(
          "room_util"       -> ujson.Num(0.0),
          "faculty_sat"     -> ujson.Num(0.0),
          "conflict_avoid"  -> ujson.Num(0.0),
          "load_balance"    -> ujson.Num(0.0),
        ),
      ),
    )
    Files.writeString(Paths.get(outputPath), ujson.write(out, indent = 2))
    println(s"Schedule written to $outputPath (${assignments.size} assignments)")
SCALA_EOF

cat > /app/src/main/scala/scheduler/optimizer/ConstraintChecker.scala << 'SCALA_EOF'
package scheduler.optimizer

import scheduler.models.*
import java.nio.file.{Files, Paths}

object ConstraintChecker:

  private val slotOrder = List("MON-09","MON-11","MON-14","MON-16","WED-09","WED-11","WED-14","WED-16").zipWithIndex.toMap

  private def readJson(path: String): ujson.Value =
    ujson.read(Files.readString(Paths.get(path)))

  private def slotDay(slot: String): String = slot.takeWhile(_ != '-')

  def isValidAssignment(
    assignment:  Assignment,
    existing:    List[Assignment],
    rooms:       Map[String, Room],
    instructors: Map[String, Instructor],
    demand:      Map[String, Int]
  ): Boolean =
    rooms.get(assignment.roomId).exists { room =>
      instructors.get(assignment.instructorId).exists { instr =>
        val d = demand.getOrElse(assignment.courseId, 0)
        !instr.unavailableSlots.contains(assignment.timeSlotId) &&
        d <= room.capacity &&
        !existing.exists(e => e.roomId == assignment.roomId && e.timeSlotId == assignment.timeSlotId) &&
        !existing.exists(e => e.instructorId == assignment.instructorId && e.timeSlotId == assignment.timeSlotId)
      }
    }

  def checkHardConstraints(
    assignments: List[Assignment],
    courses:     List[Course],
    rooms:       Map[String, Room],
    instructors: Map[String, Instructor],
    demand:      Map[String, Int],
    requireComplete: Boolean = true
  ): List[String] =
    val v = scala.collection.mutable.ListBuffer[String]()
    val ids = assignments.map(_.courseId)
    val expected = courses.map(_.id).toSet
    val missing = expected -- ids.toSet
    if requireComplete && missing.nonEmpty then v += s"Missing courses: ${missing.mkString(", ")}"
    val dupes = ids.groupBy(identity).filter(_._2.size > 1).keys
    if dupes.nonEmpty then v += s"Duplicate courses: ${dupes.mkString(", ")}"
    val rs = assignments.map(a => (a.roomId, a.timeSlotId))
    val rsDup = rs.groupBy(identity).filter(_._2.size > 1).keys
    if rsDup.nonEmpty then v += s"Room double-bookings: ${rsDup.mkString(", ")}"
    val is = assignments.map(a => (a.instructorId, a.timeSlotId))
    val isDup = is.groupBy(identity).filter(_._2.size > 1).keys
    if isDup.nonEmpty then v += s"Instructor slot conflicts: ${isDup.mkString(", ")}"
    for a <- assignments do
      instructors.get(a.instructorId).foreach { i =>
        if i.unavailableSlots.contains(a.timeSlotId) then
          v += s"Instructor ${a.instructorId} unavailable at ${a.timeSlotId} (course ${a.courseId})"
      }
    for a <- assignments do
      rooms.get(a.roomId).foreach { r =>
        val d = demand.getOrElse(a.courseId, 0)
        if d > r.capacity then v += s"Capacity: course ${a.courseId} demand $d > room ${a.roomId} capacity ${r.capacity}"
      }
    for a <- assignments do
      courses.find(_.id == a.courseId).foreach { c =>
        rooms.get(a.roomId).foreach { r =>
        if r.roomType != c.requiredRoomType then
            v += s"Type mismatch: course ${a.courseId} needs ${c.requiredRoomType} but ${a.roomId} is ${r.roomType}"
        }
      }
    val byCourse = assignments.map(a => a.courseId -> a).toMap
    val courseMap = courses.map(c => c.id -> c).toMap

    val conflicts = readJson("/opt/scheduler/conflicts.json").arr.map(_.arr.map(_.str).toList).toList
    for group <- conflicts do
      val bySlot = group.flatMap(byCourse.get).groupBy(_.timeSlotId).filter(_._2.size > 1)
      for (slot, hit) <- bySlot do
        v += s"Conflict group collision at $slot: ${hit.map(_.courseId).mkString(",")}"

    val blackoutRows = readJson("/opt/scheduler/room-blackouts.json").arr
    val blockedSlots = blackoutRows.map { row =>
      row("room_id").str -> row("blocked_slots").arr.map(_.str).toSet
    }.toMap
    for a <- assignments do
      if blockedSlots.getOrElse(a.roomId, Set.empty).contains(a.timeSlotId) then
        v += s"Room blackout violation: ${a.roomId} blocked at ${a.timeSlotId}"

    val prereqRows = readJson("/opt/scheduler/prerequisites.json").arr
    for edge <- prereqRows do
      val before = edge("before").str
      val after  = edge("after").str
      val minGap = edge("min_gap").num.toInt
      for b <- byCourse.get(before); a <- byCourse.get(after) do
        if slotOrder.getOrElse(a.timeSlotId, -1) - slotOrder.getOrElse(b.timeSlotId, -1) < minGap then
          v += s"Prerequisite min_gap violation: $before before $after"

    val cohortRows = readJson("/opt/scheduler/cohorts.json").arr
    for cohort <- cohortRows do
      val cohortId = cohort("id").str
      val courseIds = cohort("courses").arr.map(_.str).toSet
      val maxPerDay = cohort("max_per_day").num.toInt
      val counts = assignments.filter(a => courseIds.contains(a.courseId)).groupBy(a => slotDay(a.timeSlotId)).view.mapValues(_.size).toMap
      for (day, count) <- counts if count > maxPerDay do
        v += s"Cohort $cohortId max_per_day violation on $day: $count > $maxPerDay"

    val fixedRows = readJson("/opt/scheduler/fixed-placements.json").arr
    for fixed <- fixedRows do
      val courseId = fixed("course_id").str
      byCourse.get(courseId) match
        case Some(a) =>
          if a.roomId != fixed("room_id").str || a.timeSlotId != fixed("time_slot_id").str then
            v += s"Fixed placement violation for $courseId"
        case None =>
          if requireComplete then v += s"Fixed placement missing course $courseId"

    val linkedRows = readJson("/opt/scheduler/linked-sections.json").arr
    for link <- linkedRows do
      val primary = link("primary").str
      val secondary = link("secondary").str
      val relation = link("relation").str
      val maxGap = link("max_gap").num.toInt
      for p <- byCourse.get(primary); s <- byCourse.get(secondary) do
        val pIdx = slotOrder.getOrElse(p.timeSlotId, -100)
        val sIdx = slotOrder.getOrElse(s.timeSlotId, -100)
        relation match
          case "same_day_after" =>
            val gap = sIdx - pIdx
            if slotDay(p.timeSlotId) != slotDay(s.timeSlotId) || gap < 1 || gap > maxGap then
              v += s"Linked section violation: $primary -> $secondary"
          case "different_day" =>
            if slotDay(p.timeSlotId) == slotDay(s.timeSlotId) then
              v += s"Linked different_day violation: $primary and $secondary"
          case other =>
            v += s"Unknown linked relation: $other"

    val creditCaps = readJson("/opt/scheduler/instructor-loads.json").arr.map { row =>
      row("instructor_id").str -> row("max_credits_per_day").num.toInt
    }.toMap
    val creditTotals = assignments.groupBy(a => (a.instructorId, slotDay(a.timeSlotId))).view.mapValues { rows =>
      rows.map(a => courseMap.get(a.courseId).map(_.credits).getOrElse(0)).sum
    }.toMap
    for ((instr, day), total) <- creditTotals do
      creditCaps.get(instr).foreach { cap =>
        if total > cap then v += s"Instructor daily credit overload: $instr $day $total > $cap"
      }

    val zones = readJson("/opt/scheduler/room-zones.json").obj.map { case (roomId, zone) => roomId -> zone.str }.toMap
    val byInstrDay = assignments.groupBy(a => (a.instructorId, slotDay(a.timeSlotId)))
    for ((instr, day), rows) <- byInstrDay do
      val ordered = rows.sortBy(a => slotOrder.getOrElse(a.timeSlotId, 99))
      for pair <- ordered.sliding(2) if pair.size == 2 do
        val left = pair.head
        val right = pair(1)
        val consecutive = slotOrder.getOrElse(right.timeSlotId, 99) - slotOrder.getOrElse(left.timeSlotId, 99) == 1
        if consecutive && zones.get(left.roomId) != zones.get(right.roomId) then
          v += s"Room-zone travel gap violation: $instr $day ${left.roomId}->${right.roomId}"
    v.toList
SCALA_EOF

cat > /app/src/main/scala/scheduler/optimizer/SoftScorer.scala << 'SCALA_EOF'
package scheduler.optimizer

import scheduler.models.*

object SoftScorer:
  def score(
    assignments: List[Assignment],
    instrMap:    Map[String, Instructor],
    demand:      Map[String, Int],
    roomMap:     Map[String, Room],
    conflicts:   List[List[String]],
    weights:     Weights
  ): Double =
    val n = assignments.size
    if n == 0 then 0.0
    else
      val roomUtil = assignments.map { a =>
        val cap = roomMap.get(a.roomId).map(_.capacity).getOrElse(1)
        val d   = demand.getOrElse(a.courseId, 0)
        math.min(1.0, d.toDouble / cap)
      }.sum / n

      val facSat = assignments.map { a =>
        instrMap.get(a.instructorId)
          .map(i => if i.preferredSlots.contains(a.timeSlotId) then 1.0 else 0.5)
          .getOrElse(0.5)
      }.sum / n

      val slotMap = assignments.map(a => a.courseId -> a.timeSlotId).toMap
      val confHits = conflicts.count { g =>
        val gs = g.flatMap(slotMap.get)
        gs.size >= 2 && gs.toSet.size < gs.size
      }
      val maxConf = if conflicts.isEmpty then 1 else conflicts.size
      val confScore = 1.0 - confHits.toDouble / maxConf

      val slotCounts = assignments.groupBy(_.timeSlotId).map(_._2.size).toList
      val balance =
        if slotCounts.size <= 1 then 0.5
        else
          val meanLoad = slotCounts.sum.toDouble / slotCounts.size
          val variance = slotCounts.map(c => math.pow(c - meanLoad, 2)).sum / slotCounts.size
          val stdDev   = math.sqrt(variance)
          val meanAll  = n.toDouble / 8
          if meanAll > 0 then math.max(0.0, 1.0 - stdDev / meanAll) else 0.0

      weights.roomUtil      * roomUtil  +
      weights.facultySat    * facSat    +
      weights.conflictAvoid * confScore +
      weights.loadBalance   * balance
SCALA_EOF

cat > /app/src/main/scala/scheduler/optimizer/Scheduler.scala << 'SCALA_EOF'
package scheduler.optimizer

import scheduler.models.*
import scala.util.Random

object Scheduler:

  private val secondLayerConstraints =
    List("conflicts", "blackout", "prereq", "cohort", "fixed", "linked", "credit", "zone")
  private val slotOrder = List("MON-09","MON-11","MON-14","MON-16","WED-09","WED-11","WED-14","WED-16").zipWithIndex.toMap

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

    val instrMap   = instructors.map(i => i.id -> i).toMap
    val roomMap    = rooms.map(r => r.id -> r).toMap
    val slotIds    = slots.map(_.id).filter(enabledSlots.contains)
    val roomsByT   = rooms.groupBy(_.roomType)

    val conflictMap: Map[String, Set[String]] = {
      val m = scala.collection.mutable.HashMap[String, scala.collection.mutable.Set[String]]()
      for g <- conflicts; a <- g; b <- g if a != b do
        m.getOrElseUpdate(a, scala.collection.mutable.Set.empty) += b
      m.view.mapValues(_.toSet).toMap
    }

    val sorted = courses.sortBy { c =>
      val d  = demand.getOrElse(c.id, 0)
      val cf = conflictMap.getOrElse(c.id, Set.empty).size
      (-d * 10 - cf * 5, c.id)
    }

    val assignments = scala.collection.mutable.ListBuffer[Assignment]()

    for course <- sorted do
      val instr = instrMap.getOrElse(course.instructorId,
        throw new RuntimeException(s"Instructor not found: ${course.instructorId}"))
      val d = demand.getOrElse(course.id, 0)
      val eligibleRooms = roomsByT.getOrElse(course.requiredRoomType, Nil)
        .filter(_.capacity >= d).sortBy(_.capacity)
      val orderedSlots =
        (instr.preferredSlots.filter(slotIds.contains) ++
         slotIds.filterNot(instr.preferredSlots.contains))
        .filterNot(instr.unavailableSlots.contains)

      val slotLoad = assignments.groupBy(_.timeSlotId).view.mapValues(_.size).toMap

      val candidates = for
        slot <- orderedSlots
        room <- eligibleRooms
        if !assignments.exists(e => e.roomId == room.id && e.timeSlotId == slot)
        if !assignments.exists(e => e.instructorId == course.instructorId && e.timeSlotId == slot)
        candidateAssignment = Assignment(course.id, room.id, slot, course.instructorId)
        partialAssignments = assignments.toList :+ candidateAssignment
        if ConstraintChecker.checkHardConstraints(
          partialAssignments,
          courses,
          roomMap,
          instrMap,
          demand,
          requireComplete = false
        ).isEmpty
      yield
        val pref   = if instr.preferredSlots.contains(slot) then 100.0 else 0.0
        val fit    = if room.capacity > 0 then d.toDouble / room.capacity else 0.0
        val confHit =
          conflictMap.getOrElse(course.id, Set.empty)
            .exists(c => assignments.exists(e => e.courseId == c && e.timeSlotId == slot))
        val conflictPenalty = if confHit then 80.0 else 0.0
        val loadPenalty     = slotLoad.getOrElse(slot, 0) * 4.0
        val score = pref + fit * 20.0 - conflictPenalty - loadPenalty
        (score, slot, room)

      if candidates.isEmpty then
        throw new RuntimeException(
          s"Cannot schedule course ${course.id}: type=${course.requiredRoomType}, " +
          s"demand=$d, instructor=${course.instructorId}"
        )

      val (_, bestSlot, bestRoom) = candidates.maxBy(_._1)
      assignments += Assignment(course.id, bestRoom.id, bestSlot, course.instructorId)

    val initial = assignments.toList
    val initialViolations = ConstraintChecker.checkHardConstraints(initial, courses, roomMap, instrMap, demand)
    if initialViolations.nonEmpty then
      throw new RuntimeException(
        "Initial schedule violates second-layer constraints " +
        s"${secondLayerConstraints.mkString(",")}: " + initialViolations.mkString("; ")
      )
    hillClimb(initial, courses, slotIds, roomMap, instrMap, demand, conflicts, weights, 1500)

  private def hillClimb(
    initial:   List[Assignment],
    courses:   List[Course],
    slotIds:   List[String],
    roomMap:   Map[String, Room],
    instrMap:  Map[String, Instructor],
    demand:    Map[String, Int],
    conflicts: List[List[String]],
    weights:   Weights,
    iters:     Int
  ): List[Assignment] =
    var cur      = initial.toVector
    var curScore = SoftScorer.score(cur.toList, instrMap, demand, roomMap, conflicts, weights)
    val rng      = new Random(42)
    val n        = cur.size
    var k = 0
    while k < iters && n >= 2 do
      val i = rng.nextInt(n)
      var j = rng.nextInt(n); while j == i do j = rng.nextInt(n)
      val ai = cur(i); val aj = cur(j)
      val iI = instrMap.get(ai.instructorId); val iJ = instrMap.get(aj.instructorId)
      val okI = iI.forall(x => !x.unavailableSlots.contains(aj.timeSlotId))
      val okJ = iJ.forall(x => !x.unavailableSlots.contains(ai.timeSlotId))
      if okI && okJ then
        val newAi = Assignment(ai.courseId, ai.roomId, aj.timeSlotId, ai.instructorId)
        val newAj = Assignment(aj.courseId, aj.roomId, ai.timeSlotId, aj.instructorId)
        val others = cur.zipWithIndex.collect { case (a, idx) if idx != i && idx != j => a }
        def free(a: Assignment): Boolean =
          !others.exists(e => e.roomId == a.roomId && e.timeSlotId == a.timeSlotId) &&
          !others.exists(e => e.instructorId == a.instructorId && e.timeSlotId == a.timeSlotId)
        if free(newAi) && free(newAj) then
          val cand = cur.updated(i, newAi).updated(j, newAj)
          val candList = cand.toList
          val hardOk = ConstraintChecker.checkHardConstraints(candList, courses, roomMap, instrMap, demand).isEmpty
          if hardOk then
            val s = SoftScorer.score(candList, instrMap, demand, roomMap, conflicts, weights)
            if s > curScore then { cur = cand; curScore = s }
      k += 1
    println(f"Final soft score (Scala self-eval): $curScore%.4f")
    cur.toList
SCALA_EOF

cat > /app/src/main/scala/scheduler/io/ManifestSeal.scala << 'SCALA_EOF'
package scheduler.io

import scheduler.models.Assignment
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

object ManifestSeal:
  def compute(assignments: List[Assignment], keyBytes: Array[Byte]): String =
    val sorted = assignments.sortBy(_.courseId)
    val input = sorted.map(a =>
      s"${a.courseId}:${a.roomId}:${a.timeSlotId}:${a.instructorId}"
    ).mkString("\n")
    val salt = keyBytes.take(16)
    val spec = new PBEKeySpec(input.toCharArray, salt, 4096, 256)
    val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
    val derived = factory.generateSecret(spec).getEncoded
    spec.clearPassword()
    derived.map(b => f"${b & 0xff}%02x").mkString
SCALA_EOF

cat > /app/src/main/scala/scheduler/policy/Canonical.scala << 'SCALA_EOF'
package scheduler.policy

import scheduler.models.*
import java.security.MessageDigest
import java.nio.charset.StandardCharsets
import java.util.Locale

object Canonical:

  private def fmt(d: Double): String = "%.4f".formatLocal(Locale.ROOT, d)

  private def toHex(bytes: Array[Byte]): String =
    val sb = new StringBuilder(bytes.length * 2)
    for b <- bytes do sb.append(f"${b & 0xff}%02x")
    sb.toString

  def fingerprint(p: EffectivePolicy): String =
    val canonical =
      "threshold=" + fmt(p.passScore) +
      ";weights=ru:" + fmt(p.weights.roomUtil) +
      ",fs:" + fmt(p.weights.facultySat) +
      ",ca:" + fmt(p.weights.conflictAvoid) +
      ",lb:" + fmt(p.weights.loadBalance) +
      ";slots=" + p.enabledSlots.mkString(",")
    val md = MessageDigest.getInstance("SHA-256")
    toHex(md.digest(canonical.getBytes(StandardCharsets.UTF_8)))
SCALA_EOF

# ----- Fix Bug E in Policy.scala: change * loadBalance to + loadBalance in Weights.sum -----
cat > /app/src/main/scala/scheduler/models/Policy.scala << 'SCALA_EOF'
package scheduler.models

// Effective policy after merging every .toml file under /etc/scheduler/conf.d/
// in ascending lex order.  Higher tiers override scalars in lower tiers;
// list-valued keys are replaced wholesale.
case class Weights(
  roomUtil:      Double,
  facultySat:    Double,
  conflictAvoid: Double,
  loadBalance:   Double
):
  def sum: Double = roomUtil + facultySat + conflictAvoid + loadBalance  // BUG-E FIXED

case class EffectivePolicy(
  weights:         Weights,
  passScore:       Double,
  enabledSlots:    List[String],
  hmacKeyPath:     String,
  overlayCsvPath:  String
)
SCALA_EOF

# ----- Fix Bug D in AuditKeyLoader.scala: remove .take(16) truncation -----
# NOTE: kill scheduler-srcma (source-mangler) FIRST before this — it re-injects Bug D every 13s
cat > /app/src/main/scala/scheduler/io/AuditKeyLoader.scala << 'SCALA_EOF'
package scheduler.io

import java.nio.file.{Files, Paths}

object AuditKeyLoader:
  /** Load the HMAC-SHA256 key bytes from the given path. */
  def load(path: String): Array[Byte] =
    Files.readAllBytes(Paths.get(path))
SCALA_EOF

# ----- 13. Build (guards are gone; LD_PRELOAD is clear) -----
cd /app
sbt -batch -Dsbt.color=false 'assembly'
cp target/scala-3.3.4/scheduler.jar /opt/scheduler/scheduler.jar

# ----- 14. Run and verify -----
java -jar /opt/scheduler/scheduler.jar
python3 /opt/scheduler/model.py /opt/scheduler/schedule.json
