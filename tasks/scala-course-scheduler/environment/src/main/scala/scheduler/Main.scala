package scheduler

import scheduler.io.*
import scheduler.optimizer.Scheduler
import scheduler.policy.Canonical

object Main:

  val DefaultDataDir    = "/opt/scheduler"
  val DefaultOutputPath = "/opt/scheduler/schedule.json"
  val PolicyConfDir     = "/etc/scheduler/conf.d"

  def main(args: Array[String]): Unit =
    val dataDir    = if args.length > 0 then args(0) else DefaultDataDir
    val outputPath = if args.length > 1 then args(1) else DefaultOutputPath

    println(s"Loading input data from $dataDir ...")

    // 1) Effective policy from /etc/scheduler/conf.d (lex-merge of all *.toml).
    val policy = PolicyLoader.loadEffective(PolicyConfDir)
    println(s"Effective policy: weights=${policy.weights}, pass_score=${policy.passScore}, " +
            s"slots=${policy.enabledSlots.size}, overlay=${policy.overlayCsvPath}")

    // 2) Load base inputs.
    val courses         = DataLoader.loadCourses(dataDir)
    val rooms           = DataLoader.loadRooms(dataDir)
    val instructorsBase = DataLoader.loadInstructors(dataDir)
    val demandBase      = DataLoader.loadDemand(dataDir)
    val conflicts       = DataLoader.loadConflicts(dataDir)
    val slots           = DataLoader.loadTimeSlots()

    // 3) Apply overlays.
    val instructors = OverlayApplier.expandPreferredSlots(instructorsBase)
    val demand      = OverlayApplier.applyDemandOverrides(demandBase, policy.overlayCsvPath)

    println(s"Loaded ${courses.size} courses, ${rooms.size} rooms, " +
            s"${instructors.size} instructors, ${slots.size} time slots, " +
            s"${conflicts.size} conflict groups")

    // 4) Optimise.
    println("Running optimizer ...")
    val assignments = Scheduler.optimize(
      courses, rooms, slots, instructors, demand, conflicts,
      policy.weights, policy.enabledSlots
    )
    println(s"Optimizer produced ${assignments.size} assignments")

    // 5) HMAC-SHA256 audit chain.
    val keyBytes = AuditKeyLoader.load(policy.hmacKeyPath)
    val chain    = AuditChain.build(assignments.sortBy(_.courseId), keyBytes)  // BUG-A: sortBy

    // 6) Canonical fingerprint of the effective policy.
    val fingerprint = Canonical.fingerprint(policy)
    println(s"Policy fingerprint: $fingerprint")

    // 7) FNV-1a-64 audit tag over the assignment list.
    val auditTag = FnvAuditTag.compute(assignments)
    println(s"Audit tag: $auditTag")

    // 9) PBKDF2 manifest seal.
    val manifestHash = ManifestSeal.compute(assignments, keyBytes)
    println(s"Manifest hash: $manifestHash")

    // 8) Write final schedule (includes audit_tag field).
    ScheduleWriter.write(assignments, chain, fingerprint, keyBytes, auditTag, manifestHash, outputPath)
    println("Done.")
