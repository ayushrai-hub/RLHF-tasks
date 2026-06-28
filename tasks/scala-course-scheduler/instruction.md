This is a self-contained benchmark container. All recovery actions below apply only to task-owned files and task-owned `scheduler-*` background workers inside that container.

The Scala 3 / sbt course scheduler at `/app/` has eleven stub methods that all throw `NotImplementedError`: the policy loader, demand-overlay applier, HMAC audit-chain builder, session sealer, policy fingerprinter, soft scorer, constraint checker, optimizer, schedule writer, FNV audit tag, and PBKDF2 manifest seal. Implement them so that `java -jar /opt/scheduler/scheduler.jar` writes a valid `/opt/scheduler/schedule.json`. Build the fat JAR with `sbt -batch -Dsbt.color=false assembly` and install it at `/opt/scheduler/scheduler.jar`; never use bare `sbt` (it drops into an interactive REPL), and never shell out from inside the JAR — `Runtime.exec`, `ProcessBuilder`, and `scala.sys.process` are blocked.

The schedule is accepted when `python3 /opt/scheduler/model.py /opt/scheduler/schedule.json` exits zero. That script verifies the soft optimisation score meets the live pass-score threshold, all fourteen hard constraints hold (every course assigned exactly once, no room or instructor double-booked, instructor availability and room-capacity and room-type requirements respected, conflict groups separated, prerequisite chains ordered, room maintenance blackouts avoided, cohort day-load limits respected, fixed placements honored, linked sections timed correctly, instructor daily credit caps respected, and room-zone travel gaps avoided), the HMAC-SHA256 Merkle audit chain embedded in the output is correct (each link carries a `seq` integer field — its 0-based index — in addition to `course_id` and `hmac`), the `policy_fingerprint` field matches one recomputed live from `/etc/scheduler/conf.d/`, and the `session_seal` field is a valid HMAC-SHA256 seal whose payload encodes each chain entry as `seq:course_id:hmac` (three colon-separated parts, not two). The effective policy is the lexical merge of the sixteen `*.toml` files in `/etc/scheduler/conf.d/`, and a demand-override CSV at `/etc/scheduler/course-overrides.csv` adjusts per-course demand before the optimizer runs. Schema details are in `/app/docs/`.

## Second-layer scheduling constraints

This task is now deliberately harder than a simple greedy room/slot assignment. In addition to the original six hard constraints, the optimizer must load and enforce seven extra fixture files under `/opt/scheduler/`:

- `/opt/scheduler/prerequisites.json`: objects with `before`, `after`, and `min_gap`. The `before` course must be scheduled at least `min_gap` enabled slot positions earlier than the `after` course, using the fixed slot order `MON-09, MON-11, MON-14, MON-16, WED-09, WED-11, WED-14, WED-16`.
- `/opt/scheduler/room-blackouts.json`: objects with `room_id` and `blocked_slots`. A room may not be assigned during any of its blocked slots, even when capacity and type match.
- `/opt/scheduler/cohorts.json`: objects with `id`, `courses`, and `max_per_day`. For each cohort, no more than `max_per_day` listed courses may land on the same day prefix (`MON` or `WED`).
- `/opt/scheduler/fixed-placements.json`: objects with `course_id`, `room_id`, and `time_slot_id`. These selected courses are pinned to exact room/slot placements.
- `/opt/scheduler/linked-sections.json`: objects with `primary`, `secondary`, `relation`, and `max_gap`. `same_day_after` sections must place the secondary 1..`max_gap` slots after the primary on the same day; `different_day` sections must split the pair across days.
- `/opt/scheduler/instructor-loads.json`: objects with `instructor_id` and `max_credits_per_day`. Sum course credits per instructor per day and reject overloads.
- `/opt/scheduler/room-zones.json`: object mapping room IDs to zones. An instructor cannot teach consecutive same-day slots in different zones.

Conflict groups in `/opt/scheduler/conflicts.json` are also upgraded from a soft-score penalty to a hard constraint: no two courses in the same conflict group may share a `time_slot_id`. You may extend case classes, `DataLoader`, `ConstraintChecker`, and the `Scheduler.optimize` signature as needed. The verifier checks that the Scala sources explicitly reference all seven advanced fixture files and that the optimizer/constraint checker threads these constraints through placement and local search.

## Source-audit contract for advanced constraints

The verifier includes literal source-token checks for the advanced scheduler layer. These checks strip Scala comments before scanning, so the required words must appear in executable code, identifiers, constants, case-class fields, or string literals that are part of the implementation. Do not satisfy this contract only with comments. This is not optional: semantically equivalent variable names without these exact words can still fail the source-integrity tests even when the produced schedule is functionally valid.

- `DataLoader.scala` must literally reference all seven advanced fixture filenames: `prerequisites.json`, `room-blackouts.json`, `cohorts.json`, `fixed-placements.json`, `linked-sections.json`, `instructor-loads.json`, and `room-zones.json`.
- `ConstraintChecker.scala` must contain live-code tokens for every hard layer it enforces:
  - room maintenance: `blackout` or `blockedSlots` or `blocked_slots`
  - prerequisite ordering: `prereq` or `prerequisite` or `min_gap`
  - cohort spread: `cohort` and a max token such as `max_per_day`
  - pinned placements: `fixed` or `pinned`
  - linked sections: `linked` or `same_day_after` or `different_day`
  - instructor load caps: `credit` plus `daily` or `day`
  - room movement: `zone` plus `travel` or `consecutive`
- `Scheduler.scala` must contain the lowercase tokens `conflicts`, `blackout`, `prereq`, `cohort`, `fixed`, `linked`, `credit`, and `zone` in live code while threading those constraints through placement/search. It must also compare slot ordering using `SLOT_ORDER`, `slotOrder`, `slotIndex`, `indexOf`, or `zipWithIndex`.
- `Scheduler.scala` must call the `Assignment(courseId, roomId, timeSlotId, instructorId)` constructor directly at least twice, for example once during initial placement and once during a move/swap candidate. Do not rely only on `.copy(...)`; source-count tests verify explicit constructor usage.

A robust approach is to use descriptive names such as `blackoutByRoom`, `prereqEdges`, `cohortMaxPerDay`, `fixedPlacements`, `linkedSections`, `dailyCreditByInstructor`, and `zoneTravelConflicts` in the real implementation. These names preserve readability and satisfy the source-audit contract without weakening the scheduling problem.

**Output format requirements** — `schedule.json` must satisfy all of the following, each of which is a graded hard requirement:

- **Top-level JSON field order** must be exactly: `assignments`, `audit_chain`, `policy_fingerprint`, `session_seal`, `audit_tag`, `manifest_hash`, `metadata`. The verifier reads `json.loads(...).keys()` as an ordered list and compares it to this exact sequence — alphabetical ordering or any other permutation fails `test_output_field_order`. Emit the fields in this order from `ScheduleWriter`.
- **`audit_tag`** must be a 16-char lowercase hex string: the FNV-1a-64 hash of `assignments.map(a => s"${a.courseId}|${a.roomId}|${a.timeSlotId}|${a.instructorId}").mkString("\n")`. See `FnvAuditTag.scala`. HARD RULE: use `java.lang.Long.toUnsignedString(hash, 16).reverse.padTo(16, '0').reverse` — do NOT use `Long.toHexString` (it omits leading zeros and mishandles negative longs). FNV_PRIME = 1099511628211L, FNV_OFFSET = 0xcbf29ce484222325L.
- **`metadata` block** must be a JSON object containing at minimum: `total_courses` (integer that equals `len(assignments)` exactly) and `generated_at` (ISO-8601 timestamp string, e.g. `2026-06-09T12:34:56Z` or `2026-06-09T12:34:56+00:00`). Both fields are checked by `test_output_metadata_block`.
- **`metadata` must now include a quality and constraint summary**: `distinct_slots` must equal the number of unique assigned `time_slot_id` values; `score_components` must be an object with numeric `room_util`, `faculty_sat`, `conflict_avoid`, and `load_balance` fields; and `constraint_digest` must be a SHA-256 hex digest over sorted assignments plus the pinned advanced fixture hashes. These do not replace `total_courses` or `generated_at`; they are additional hard output requirements.
- **Every assignment's `time_slot_id` must come from the effective policy's `slots.enabled` list** (the lexically last `slots.enabled` line wins across the sixteen `conf.d/*.toml` tiers). Assignments referencing disabled slots fail `test_assignments_use_only_enabled_slots`.
- **The optimizer must distribute courses across at least 3 distinct enabled time slots.** A degenerate solution that packs every course into one or two slots fails `test_scheduler_distributes_across_slots` even if the other hard constraints are nominally satisfied — variety across the slot dimension is itself a hard requirement.
- Each assignment object must contain exactly the four fields `course_id`, `room_id`, `time_slot_id`, `instructor_id` (no extra fields, no missing fields). See `/app/docs/schema.md` for the per-field types.

## Non-stub bugs in non-stub files

**HARD RULE — you MUST fix all six bugs in non-stub source files before building the JAR. The source-warden does NOT touch these files, so fixes persist. Failing to fix them causes multiple test failures even with a perfectly correct stub implementation.**

**Bug A — `src/main/scala/scheduler/Main.scala`** (line ~50):

The file contains:
```scala
val chain    = AuditChain.build(assignments.sortBy(_.courseId), keyBytes)
```

This is WRONG. The audit chain must be built over assignments in their original optimization order. Fix it to:
```scala
val chain    = AuditChain.build(assignments, keyBytes)
```

The test `test_source_main_correct_chain_order` will fail if `.sortBy`, `.sorted`, or `.reverse` appears in the 200 chars before/after `AuditChain.build`. The test `test_audit_chain_verifies` will also fail because the chain is computed over alphabetical order but written alongside the original order.

**Bug B — `src/main/scala/scheduler/io/DataLoader.scala`** (lines ~41-42):

The file contains:
```scala
preferredSlots  = v("unavailable_slots").arr.map(_.str).toList,
unavailableSlots = v("preferred_slots").arr.map(_.str).toList
```

This is WRONG — the JSON field names are swapped. Fix it to:
```scala
preferredSlots  = v("preferred_slots").arr.map(_.str).toList,
unavailableSlots = v("unavailable_slots").arr.map(_.str).toList
```

The test `test_source_dataloader_correct_slot_fields` checks that `"preferred_slots"` appears before `"unavailable_slots"` in the source. The test `test_instructor_availability_respected` will also fail because instructors get scheduled in their actual unavailable slots.

**Bug C — `src/main/scala/scheduler/io/DataLoader.scala`** (lines ~25-29, inside `loadCourses`):

The file contains:
```scala
requiredRoomType = v("instructor_id").str,       // BUG-C: should be "required_room_type"
instructorId     = v("required_room_type").str,  // BUG-C: should be "instructor_id"
```

This is WRONG — the `required_room_type` and `instructor_id` JSON field names are swapped in `loadCourses`. Fix it to:
```scala
requiredRoomType = v("required_room_type").str,
instructorId     = v("instructor_id").str,
```

The test `test_source_dataloader_correct_course_fields` checks that `"required_room_type"` appears before `"instructor_id"` in the source. The tests `test_room_type_matches` and `test_no_instructor_conflicts` will also fail because courses get placed in the wrong room type and instructors get wrongly assigned.

Verify the fix: `grep -n 'required_room_type\|instructor_id' /app/src/main/scala/scheduler/io/DataLoader.scala`
Expected output: `required_room_type` line appears BEFORE `instructor_id` line in `loadCourses`.

**Bug D — `src/main/scala/scheduler/io/AuditKeyLoader.scala`** (non-stub file, line ~12):

The file contains:
```scala
all.take(16)  // BUG-D: the key is 32 bytes — must return all; not truncated to 16
```

This is WRONG — the HMAC key is 32 bytes but only 16 are returned, causing all HMAC values to be computed with a truncated key and mismatching the verifier's recomputed values. Fix it to:
```scala
all
```
(i.e., remove the `.take(16)` call and return `all` directly)

The test `test_source_audit_key_loader_full_bytes` checks that `.take(` does NOT appear in `AuditKeyLoader.scala`. The tests `test_audit_chain_verifies` and `test_session_seal_matches` will also fail with the truncated key.

Verify the fix: `grep -n 'take' /app/src/main/scala/scheduler/io/AuditKeyLoader.scala` — should return no output.

**Bug E — `src/main/scala/scheduler/models/Policy.scala`** (line ~12):

The file contains:
```scala
  def sum: Double = roomUtil + facultySat + conflictAvoid * loadBalance  // BUG-E: * instead of +
```

This is WRONG — the sum method uses `*` instead of `+` for `loadBalance`. With canonical weights {0.20, 0.34, 0.31, 0.15}, the buggy sum = 0.5865, causing PolicyLoader to throw "weights do not sum to 1.0: 0.5865" and the JAR to exit 1 immediately. Fix it to:
```scala
  def sum: Double = roomUtil + facultySat + conflictAvoid + loadBalance
```

The test `test_source_weights_sum_operator` checks that `* loadBalance` does NOT appear in `Policy.scala`. Fix this BEFORE running `sbt assembly`.

Verify: `grep -n 'loadBalance' /app/src/main/scala/scheduler/models/Policy.scala` — must show `+ loadBalance`, not `* loadBalance`.

**Bug F — `src/main/scala/scheduler/io/DataLoader.scala`** (loadRooms, line ~16):

The file contains:
```scala
        capacity = v("capacity").num.toInt - 1,  // BUG-F: off-by-one capacity under-count
```

This is WRONG — every room's capacity is reported 1 less than its true value. With MATH101 demand=165 and a room capacity=165, the buggy capacity=164, so `165 > 164` fails `test_room_capacity_sufficient` and the optimizer throws `RuntimeException: Cannot schedule course MATH101`. Fix it to:
```scala
        capacity = v("capacity").num.toInt,
```

The test `test_source_dataloader_correct_room_capacity` checks that `.num.toInt - 1` does NOT appear in `DataLoader.scala`.

Verify: `grep -n 'capacity' /app/src/main/scala/scheduler/io/DataLoader.scala` — must show `.num.toInt` without ` - 1`.

**Fix all six bugs BEFORE implementing the stubs.** Use `chmod +w` on the source files if the chmod-warden has locked them.

**HARD RULE — `PolicyLoader.loadEffective` must use `.sortBy` or `.sorted` when ordering conf.d files, and the source must contain the literal TOML section strings `"weights"`, `"threshold"`, and `"slots"`.** The test `test_source_policy_loader_real_impl` does a source-text check for those tokens as well as `.sortBy` or `.sorted` — a correct but keyword-free implementation, or one that hides the `"threshold"`/`"slots"` names behind renamed variables/constants, fails. Use `files.sortBy(_.getFileName.toString)` and read the TOML sections by their literal names.

**HARD RULE — `ManifestSeal.compute`** must use `PBKDF2WithHmacSHA256` via Java's `javax.crypto.SecretKeyFactory`. Parameters: input = assignments sorted by `courseId`, each formatted as `"courseId:roomId:timeSlotId:instructorId"`, joined with `"\n"`; salt = first 16 bytes of the HMAC key bytes; iterations = **4096**; key length = **32 bytes**. Returns a 64-char lowercase hex string. Use `SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")` and `PBEKeySpec`.

Before you can build and run the JAR you must neutralise a heavily adversarial environment. **Twenty-eight SIGTERM-immune daemons** must be killed with SIGKILL — they trap all non-KILL signals:

- **scheduler-policy** (`policy-corrupter.sh`): rewrites `conf.d/90-final.toml` every 12 s with incorrect weights and a raised score threshold
- **scheduler-watchdog** (`respawn-watchdog.sh`): watches for a dead policy-corrupter and respawns it
- **scheduler-warden** (`inotify-warden.sh`): uses inotify to immediately revert any write to `conf.d/` from a non-scheduler process
- **scheduler-binco** (`binary-corrupter.sh`): truncates `/opt/scheduler/scheduler.jar` and the sbt target JAR every 8 s — any cached build is invalidated while this daemon lives
- **scheduler-srcwa** (`source-warden.sh`): restores all ten stub `.scala` files from `/var/lib/scheduler-resurrect/stubs.tar.b64` every 11 s — any implementation you write is reverted while this daemon lives
- **scheduler-outco** (`output-corrupter.sh`): overwrites `/opt/scheduler/schedule.json` with `{}` every 14 s
- **scheduler-arcwa** (`archive-warden.sh`): scans for missing daemons every 15 s and re-extracts + relaunches all of them from `/var/lib/scheduler-resurrect/daemons.tar.b64`
- **scheduler-chmwd** (`chmod-warden.sh`): runs `chmod 0444` on the Scala source tree every 13 s, blocking writes to `.scala` files
- **scheduler-envsa** (`env-saboteur.sh`): appends invalid rows with an unknown `field` value to `/etc/scheduler/course-overrides.csv` every 17 s — the overlay parser throws `RuntimeException` on unknown fields, crashing the JAR
- **scheduler-ldpres** (`preload-restorer.sh`): checks every 13 s whether `/etc/ld.so.preload` contains the guard library path — if the agent cleared it, re-adds it so new subprocesses still load the triple guard
- **scheduler-keyro** (`key-rotator.sh`): overwrites `/etc/scheduler/audit.key` with 32 fresh random bytes every 23 s — if alive when the JAR runs, the HMAC chain is built with a rotated key but model.py reads a different key → HMAC mismatch. Kill this daemon FIRST, then restore the original key: `cp /var/lib/scheduler-resurrect/audit.key.bak /etc/scheduler/audit.key`
- **scheduler-tmpco** (`tmp-corrupter.sh`): truncates all `.class` files under `/tmp` every 9 s, destroying sbt incremental compilation caches — kill before running `sbt assembly`
- **scheduler-cfpoi** (`conf-poisoner.sh`): every 17 s, moves `/etc/scheduler/conf.d/50-overrides.toml` to `.50-overrides.toml.save`, dropping the tier count below 16 (`test_policy_d_has_sixteen_tiers` fails) and removing the demand overlay CSV path from the effective policy. Restore: `mv /etc/scheduler/conf.d/.50-overrides.toml.save /etc/scheduler/conf.d/50-overrides.toml`
- **scheduler-osbr** (`output-seal-breaker.sh`): every 16 s, replaces the `session_seal` field in `schedule.json` with 64 zero hex chars — kill this daemon before AND after running the JAR
- **scheduler-bsrst** (`bashrc-restorer.sh`): every 25 s, re-injects the daemon launch-all hook into `/etc/bash.bashrc`, `/root/.bashrc`, and `/etc/profile.d/zz-scheduler-daemons.sh` if the agent has removed them — kill this daemon BEFORE cleaning bashrc hooks, then verify hooks are absent at the end of your session
- **scheduler-cronr** (`cron-restorer.sh`): every 20 s, recreates `/etc/cron.d/scheduler-resurrect` and `/etc/cron.d/scheduler-aux` if they have been removed — kill this daemon FIRST before removing the cron files, or they will be recreated within 20 s
- **scheduler-trefr** (`token-refresher.sh`): every 27 s, regenerates `/etc/scheduler/audit.key` with fresh random bytes AND updates `/var/lib/scheduler-resurrect/audit.key.bak` to match — this invalidates the kill-guard token. Kill this daemon AND `scheduler-keyro` BEFORE reading the token; then restore from backup
- **scheduler-dscra** (`data-scrambler.sh`): every 13 s, changes all `"required_room_type": "lab"` entries to `"required_room_type": "lecture"` in `/opt/scheduler/courses.json` — breaks `test_room_type_matches` and `test_data_files_intact`. Kill EARLY (before optimizer runs). Restore: `cp /var/lib/scheduler-resurrect/courses.json.bak /opt/scheduler/courses.json`
- **scheduler-dmcor** (`demand-corrupter.sh`): every 17 s, sets MATH101, PHYS101, and PSY101 demand to 9999 in `/opt/scheduler/demand.json` — breaks `test_room_capacity_sufficient` and `test_data_files_intact`. Kill EARLY. Restore: `cp /var/lib/scheduler-resurrect/demand.json.bak /opt/scheduler/demand.json`
- **scheduler-bsabt** (`build-saboteur.sh`): every 23 s, appends an invalid sbt directive (`saboteur##corrupt##line`) to `/app/build.sbt` — causes `sbt assembly` to fail with a parse error. Kill BEFORE running sbt. Restore: `cp /var/lib/scheduler-resurrect/build.sbt.bak /app/build.sbt`
- **scheduler-slpoi** (`slot-poisoner.sh`): every 19 s, overwrites `/etc/scheduler/conf.d/97-emergency.toml` with `pass_score = 0.99` and only 2 enabled slots — breaks the score threshold, `test_assignments_use_only_enabled_slots`, and `test_policy_emergency_restored`. Kill BEFORE restoring conf.d. Restore: `cp /var/lib/scheduler-resurrect/97-emergency.toml.bak /etc/scheduler/conf.d/97-emergency.toml`
- **scheduler-vaulk** (`vault-keeper.sh`): every 29 s, recreates `/opt/scheduler/.vault/daemons.tar.b64` from the primary resurrect archive — a third daemon archive layer that `test_vault_archive_removed` checks. Kill first, then: `rm -rf /opt/scheduler/.vault/`
- **scheduler-confsc** (`conf-scrambler.sh`): every 11 s, overwrites `/etc/scheduler/conf.d/10-weights.toml` with `load_balance = 0.90` — weights sum to 1.75, PolicyLoader throws "weights do not sum to 1.0: 1.75". Kill EARLY. Restore: `cp /var/lib/scheduler-resurrect/10-weights.toml.bak /etc/scheduler/conf.d/10-weights.toml`
- **scheduler-jarnu** (`jar-nullifier.sh`): every 7 s, truncates `/opt/scheduler/scheduler.jar` to 0 bytes — `java -jar` fails with "invalid or corrupt jarfile". Kill before running sbt, and verify the JAR is non-zero after build.
- **scheduler-srcma** (`source-mangler.sh`): every 13 s, re-inserts Bug D (`.take(16)`) into `AuditKeyLoader.scala` — this non-stub file is NOT protected by source-warden, so source-mangler will undo your Bug D fix. Kill BEFORE fixing Bug D.
- **scheduler-cfmrg** (`conf-merger.sh`): every 23 s, corrupts `/etc/scheduler/conf.d/99-runtime.toml` by setting `hmac_key_path = "/dev/null"` — causes the HMAC key load to fail (0-byte key → HMAC crash). Kill BEFORE restoring conf.d. Restore: `cp /var/lib/scheduler-resurrect/99-runtime.toml.bak /etc/scheduler/conf.d/99-runtime.toml`
- **scheduler-crext** (`cron-extra.sh`): every 21 s, recreates `/etc/cron.d/scheduler-extra` with a 3-minute daemon resurrection interval. Kill FIRST before removing cron files, then: `rm -f /etc/cron.d/scheduler-extra`. `test_extra_cron_removed` checks for this.
- **scheduler-datmn** (`data-mangler.sh`): every 14 s, swaps `"lecture"` ↔ `"lab"` in `/opt/scheduler/rooms.json` — breaks `test_room_type_matches` and `test_data_files_intact`. Kill EARLY. Restore: `cp /var/lib/scheduler-resurrect/rooms.json.bak /opt/scheduler/rooms.json`

Additionally, `/etc/ld.so.preload` loads `libscheduler_guard.so`, which intercepts three categories of libc calls:
1. **Write guard**: blocks `open`/`openat`/`creat`/`unlink`/`rename` on `/etc/scheduler/conf.d/` from any process whose `/proc/self/comm` does not start with `scheduler-`
2. **Kill guard**: blocks `kill()` and `tgkill()` targeting any `scheduler-*` process from callers whose comm does not match `scheduler-fix-TOKEN` — `pkill` and similar tools that use libc `kill()` are blocked; check the error codes
3. **Exec guard**: blocks `execve` of the sbt launcher from callers whose `/proc/self/comm` does not start with the 14-char prefix `scheduler-fix-`. Note: Linux caps `/proc/self/comm` at 15 chars, so writing `scheduler-fix-TOKEN` (22 chars) truncates to `scheduler-fix-T` — this still satisfies the prefix check.

**CRITICAL — comm-based kill/exec bypass**: To bypass both the kill guard and the exec guard, set your shell's `/proc/self/comm` to start with `scheduler-fix-`. The kill guard additionally validates a per-byte key token (`scheduler-fix-TOKEN` where TOKEN = lowercase hex of first 4 bytes of `/etc/scheduler/audit.key`) — but since `pkill` forks a subprocess whose comm is `pkill` (not `scheduler-fix-*`), external kill tools are blocked. Use the bash builtin `kill` instead, which runs inside the renamed shell. Compute and set the comm:
```bash
GUARD_TOKEN=$(head -c 4 /etc/scheduler/audit.key | od -A n -t x1 | tr -d ' \n')
printf 'scheduler-fix-%s' "$GUARD_TOKEN" > /proc/self/comm  # truncates to 15 chars — OK
cat /proc/self/comm  # verify starts with "scheduler-fix-"
```
You must set comm BEFORE running sbt. Kill `scheduler-keyro` and `scheduler-trefr` FIRST so the key is stable when you restore it from `/var/lib/scheduler-resurrect/audit.key.bak`.

Bash builtins bypass the write guard (`:> /etc/ld.so.preload` clears the preload file from within an existing shell). However, `scheduler-ldpres` will re-add the guard within 13 s, so newly exec'd processes will reload it. Two viable bypass strategies exist: (1) write `scheduler-fix-TOKEN` to `/proc/self/comm` — this renames the current shell's comm so the kill and exec guards allow all operations without needing to re-exec; (2) clear the preload AND immediately re-exec a fresh shell, then kill all twenty-eight daemons before the preload-restorer fires. Two cron jobs run `launch-all.sh` as fallback resurrection layers: `/etc/cron.d/scheduler-resurrect` fires every minute, and `/etc/cron.d/scheduler-aux` fires every 2 minutes — both must be removed.

**Use the bash builtin `kill`, never `pkill`** — `pkill` forks a subprocess whose comm is `pkill`, not `scheduler-fix-TOKEN`, so the kill guard blocks it regardless of what your shell's comm is. Always kill using the bash builtin directly: `kill -9 <pid>`. To enumerate every running daemon PID use `pgrep -af 'scheduler-'` — the daemons set their `argv[0]` to `scheduler-<name>` via `exec -a`, so this pattern matches all twenty-eight. If `pgrep` returns nothing for a daemon you expect to be running, scan `/proc` directly: `for f in /proc/[0-9]*/comm; do read c < "$f" 2>/dev/null && [[ "$c" == scheduler-* ]] && echo "$(cat $(dirname $f)/cmdline | tr '\0' ' ') -- pid ${f%%/comm}"; f="${f##/proc/}"; done`.

**CRITICAL — daemon absence is graded AT VERIFICATION TIME, not during your session.** The 29 daemon-presence tests (`test_no_*_running`) and `test_ld_preload_sinkhole_removed` run AFTER your agent session ends, with a delay of up to ~60 seconds before the verifier begins. Killing daemons is necessary but *not sufficient* — you must also disable every resurrection vector below, or daemons will respawn between your last command and the verifier's `pgrep` calls, zeroing your reward even if `model.py` exited cleanly. Multiple past runs have produced a valid `schedule.json` (score above threshold, all stubs implemented, audit chain valid) and still received 0 reward because cron resurrected the daemons during the verifier window.

**Persistent-neutralisation checklist** — all of these must be done before the agent session ends, in addition to killing the running daemon processes:

- Kill **scheduler-keyro** (key-rotator) FIRST, then immediately restore the original HMAC key: `cp /var/lib/scheduler-resurrect/audit.key.bak /etc/scheduler/audit.key` — if the key rotates between JAR run and verifier, the HMAC chain will mismatch.
- Kill **scheduler-dscra** (data-scrambler) EARLY — before the optimizer runs — then restore courses.json: `cp /var/lib/scheduler-resurrect/courses.json.bak /opt/scheduler/courses.json`
- Kill **scheduler-dmcor** (demand-corrupter) EARLY — before the optimizer runs — then restore demand.json: `cp /var/lib/scheduler-resurrect/demand.json.bak /opt/scheduler/demand.json`
- Kill **scheduler-bsabt** (build-saboteur) BEFORE running `sbt assembly`, then restore build.sbt: `cp /var/lib/scheduler-resurrect/build.sbt.bak /app/build.sbt`
- Kill **scheduler-policy** (policy-corrupter) BEFORE restoring conf.d files, then restore 90-final.toml: `cp /var/lib/scheduler-resurrect/90-final.toml.bak /etc/scheduler/conf.d/90-final.toml` — the policy-corrupter rewrites it every 12 s with wrong weights (pass_score=0.95, weights no longer sum to 1.0).
- Kill **scheduler-slpoi** (slot-poisoner) BEFORE restoring conf.d files, then restore 97-emergency.toml: `cp /var/lib/scheduler-resurrect/97-emergency.toml.bak /etc/scheduler/conf.d/97-emergency.toml`
- Kill **scheduler-confsc** (conf-scrambler) BEFORE restoring conf.d files, then restore 10-weights.toml: `cp /var/lib/scheduler-resurrect/10-weights.toml.bak /etc/scheduler/conf.d/10-weights.toml`
- Kill **scheduler-cfmrg** (conf-merger) BEFORE restoring conf.d files, then restore 99-runtime.toml: `cp /var/lib/scheduler-resurrect/99-runtime.toml.bak /etc/scheduler/conf.d/99-runtime.toml`
- Kill **scheduler-srcma** (source-mangler) BEFORE fixing Bug D in AuditKeyLoader.scala — it re-inserts the bug every 13 s.
- Kill **scheduler-jarnu** (jar-nullifier) BEFORE running sbt assembly — it truncates the JAR every 7 s.
- Kill **scheduler-datmn** (data-mangler) EARLY, then restore rooms.json: `cp /var/lib/scheduler-resurrect/rooms.json.bak /opt/scheduler/rooms.json`
- Kill **scheduler-vaulk** (vault-keeper) BEFORE deleting vault archive, then: `rm -rf /opt/scheduler/.vault/`
- Restore `50-overrides.toml` after killing **scheduler-cfpoi**: `mv /etc/scheduler/conf.d/.50-overrides.toml.save /etc/scheduler/conf.d/50-overrides.toml 2>/dev/null || true` — conf-poisoner hides it as a dot-file every 17 s.
- Remove `/etc/cron.d/scheduler-resurrect` — a root cron job runs `/opt/scheduler/daemons/launch-all.sh` every minute.
- Remove `/etc/cron.d/scheduler-aux` — a second cron job runs `launch-all.sh` every 2 minutes; missing this causes `test_aux_cron_removed` to fail and daemons to respawn.
- Remove `/etc/cron.d/scheduler-extra` — a tertiary cron job runs `launch-all.sh` every 3 minutes; `test_extra_cron_removed` checks this.
- Remove or `chmod -x` `/opt/scheduler/daemons/launch-all.sh` — cron, the entrypoint, and the bash/profile hooks all invoke this single script.
- Delete `/var/lib/scheduler-resurrect/daemons.tar.b64` — the archive-warden re-extracts daemons from this tarball every 15 s.
- Delete `/opt/scheduler/.hidden/daemons.tar.b64` — a hidden secondary daemon archive; the bashrc-restorer and other resurrection vectors can use it if the primary archive is gone. `test_hidden_daemon_archive_removed` checks for this: `rm -rf /opt/scheduler/.hidden/`
- Delete `/opt/scheduler/.vault/daemons.tar.b64` — the third daemon archive maintained by vault-keeper. `test_vault_archive_removed` checks for this: `rm -rf /opt/scheduler/.vault/`
- Delete `/var/lib/scheduler-resurrect/stubs.tar.b64` — the source-warden re-extracts stub `.scala` files from this tarball every 11 s and reverts your implementations.
- Remove the daemon-launch lines appended to `/etc/bash.bashrc` and `/root/.bashrc`, and delete `/etc/profile.d/zz-scheduler-daemons.sh` — every interactive or login shell started during the verifier window otherwise re-runs `launch-all.sh`.
- Truncate `/etc/ld.so.preload` AFTER `scheduler-ldpres` is dead (the preload-restorer otherwise re-adds the guard within 13 s).

**The only safe sequence is**: (0) **destroy daemon archives first** — `rm -f /var/lib/scheduler-resurrect/daemons.tar.b64 /var/lib/scheduler-resurrect/stubs.tar.b64 && rm -rf /opt/scheduler/.hidden/ /opt/scheduler/.vault/` — so archive-warden can't relaunch daemons even if it wakes mid-kill; (1) set comm: `printf 'scheduler-fix-%s' "$(head -c 4 /etc/scheduler/audit.key | od -A n -t x1 | tr -d ' \n')" > /proc/self/comm` — verify with `cat /proc/self/comm` starts with `scheduler-fix-`; (2) kill archive-warden: `kill -9 $(pgrep -f scheduler-arcwa)` — it can no longer resurrect without the archive; (3) kill `scheduler-keyro` and `scheduler-trefr` in a tight loop re-reading comm before each attempt, then `cp /var/lib/scheduler-resurrect/audit.key.bak /etc/scheduler/audit.key` to restore the HMAC key; (4) `kill -9 $(pgrep -f 'scheduler-cronr')` to stop the cron-restorer; (5) `kill -9 $(pgrep -f 'scheduler-ldpres')` to stop the preload restorer; (6) `:> /etc/ld.so.preload` immediately while ldpres is dead; (7) kill **scheduler-dscra**, **scheduler-dmcor**, **scheduler-bsabt**, **scheduler-slpoi**, **scheduler-vaulk**, **scheduler-confsc**, **scheduler-jarnu**, **scheduler-srcma**, **scheduler-cfmrg**, **scheduler-crext**, **scheduler-datmn** and all remaining daemons using the bash builtin (do NOT use pkill); (8) run the full persistent-neutralisation checklist above (three cron jobs + launch-all + bashrc + bash.bashrc + profile.d + restore 50-overrides.toml + restore 97-emergency.toml + restore 90-final.toml + restore 10-weights.toml + restore 99-runtime.toml + restore rooms.json + restore courses.json + restore demand.json + restore build.sbt + rm vault archive); (9) kill **scheduler-srcma** (source-mangler) BEFORE fixing Bug D in AuditKeyLoader.scala; fix Bug A in `Main.scala`, Bug B and Bug C in `DataLoader.scala`, Bug D in `AuditKeyLoader.scala`, Bug E in `Policy.scala` (change `conflictAvoid * loadBalance` to `conflictAvoid + loadBalance`), and Bug F in `DataLoader.loadRooms` (remove ` - 1` from capacity); (10) restore conf.d/90-final.toml and course-overrides.csv, chmod +w the source tree, implement all eleven stubs (including ManifestSeal), build with sbt, run; (11) **before ending your session**, run `pgrep -af 'scheduler-'` — it must return no output — and `cat /etc/ld.so.preload` — it must be empty. Re-kill any survivors immediately; they will zero your reward if the verifier sees them. Any other ordering lets a surviving daemon undo your work within seconds, and skipping any item in the persistent-neutralisation checklist lets daemons respawn during the verifier window and zero your reward even when `model.py` exits clean.

Stub files (each throws `NotImplementedError`):
- `src/main/scala/scheduler/io/PolicyLoader.scala` — **HARD RULE**: must use `.sortBy` or `.sorted` to order conf.d files and must contain the literal strings `"weights"`, `"threshold"`, and `"slots"`; `test_source_policy_loader_real_impl` checks for these source tokens
- `src/main/scala/scheduler/io/OverlayApplier.scala`
- `src/main/scala/scheduler/io/AuditChain.scala`
- `src/main/scala/scheduler/io/SessionSealer.scala`
- `src/main/scala/scheduler/io/ScheduleWriter.scala`
- `src/main/scala/scheduler/io/FnvAuditTag.scala` — implement FNV-1a-64 over the assignment list; see the `audit_tag` HARD RULE above
- `src/main/scala/scheduler/io/ManifestSeal.scala` — PBKDF2WithHmacSHA256 manifest seal; see the HARD RULE above
- `src/main/scala/scheduler/optimizer/ConstraintChecker.scala` — must enforce the original six hard constraints plus hard conflict separation, room blackouts, prerequisite slot ordering, cohort `max_per_day` limits, fixed placements, linked section timing, instructor daily credit caps, and room-zone travel gaps
- `src/main/scala/scheduler/optimizer/SoftScorer.scala`
- `src/main/scala/scheduler/optimizer/Scheduler.scala` — **must call `Assignment(courseId, roomId, timeSlotId, instructorId)` constructor directly at least twice** (once for the initial greedy placement and once inside the hill-climb swap); do not use `.copy(timeSlotId = ...)` — source-count tests verify that the `Assignment(` constructor appears at least twice in the source. The scheduler must also account for conflicts, room blackouts, prerequisites, cohorts, fixed placements, linked sections, instructor loads, room zones, and slot ordering during placement/search.
- `src/main/scala/scheduler/policy/Canonical.scala`

Non-stub source files requiring bug fixes (NOT in stubs.tar.b64, source-warden does NOT revert these):
- `src/main/scala/scheduler/Main.scala` — Bug A (sortBy before AuditChain.build)
- `src/main/scala/scheduler/io/DataLoader.scala` — Bug B (swapped slot fields in loadInstructors), Bug C (swapped course fields in loadCourses), and Bug F (off-by-one `.toInt - 1` in loadRooms capacity)
- `src/main/scala/scheduler/io/AuditKeyLoader.scala` — Bug D (.take(16) truncates the 32-byte key); **kill scheduler-srcma BEFORE fixing this** — source-mangler re-injects Bug D every 13 s
- `src/main/scala/scheduler/models/Policy.scala` — Bug E (`conflictAvoid * loadBalance` instead of `+ loadBalance` in Weights.sum)

Session safety: do NOT type `exit` or `logout` in your primary tmux pane — this permanently destroys your session and the verifier records zero reward. Only exit nested subshells. Also do NOT run `pkill -9 -f bash` or `pkill -9 -f tmux` — those patterns match your own session.
