# Input and Output Schema Reference

## Input Files (read from /opt/scheduler/)

### rooms.json
Array of room objects:
```json
{
  "id":       "string — unique room identifier",
  "name":     "string — human-readable room name",
  "capacity": "integer — maximum number of seats",
  "type":     "string — one of: lecture, seminar, lab"
}
```

### courses.json
Array of course objects:
```json
{
  "id":                 "string — unique course identifier",
  "name":               "string — course title",
  "required_room_type": "string — must match a room type (lecture, seminar, lab)",
  "instructor_id":      "string — references an instructor id",
  "credits":            "integer — credit hours"
}
```

### instructors.json
Array of instructor objects:
```json
{
  "id":               "string — unique instructor identifier",
  "name":             "string — instructor name",
  "preferred_slots":  "array of slot ids — instructor prefers these time slots",
  "unavailable_slots":"array of slot ids — instructor cannot teach in these slots"
}
```

### demand.json
Object mapping course id to integer enrollment estimate:
```json
{
  "COURSE_ID": integer
}
```

### conflicts.json
Array of conflict groups. Each group is an array of course ids whose students overlap:
```json
[
  ["COURSE_A", "COURSE_B"],
  ...
]
```
Scheduling two courses from the same group into the same time slot is a hard violation.

### prerequisites.json
Array of prerequisite ordering edges:
```json
{
  "before":  "COURSE_A",
  "after":   "COURSE_B",
  "min_gap": 1
}
```
`before` must be scheduled at least `min_gap` slot positions earlier than `after`.

### room-blackouts.json
Array of room maintenance windows:
```json
{
  "room_id":       "ROOM_ID",
  "blocked_slots": ["MON-09", "WED-16"]
}
```
The listed room cannot be used in any blocked slot.

### cohorts.json
Array of cohort day-load limits:
```json
{
  "id":          "cohort-name",
  "courses":     ["COURSE_A", "COURSE_B"],
  "max_per_day": 3
}
```
For each cohort, no more than `max_per_day` listed courses may be scheduled on the same day prefix.

### fixed-placements.json
Array of exact placement pins:
```json
{
  "course_id":    "COURSE_A",
  "room_id":      "ROOM_ID",
  "time_slot_id": "MON-09"
}
```
The listed course must use the exact room and slot.

### linked-sections.json
Array of relation-specific course pairs:
```json
{
  "primary":   "COURSE_A",
  "secondary": "COURSE_B",
  "relation":  "same_day_after",
  "max_gap":   2
}
```
`same_day_after` requires the secondary course to occur later on the same day within `max_gap` slots. `different_day` requires the two courses to be split across days.

### instructor-loads.json
Array of instructor daily credit caps:
```json
{
  "instructor_id": "PROF-01",
  "max_credits_per_day": 6
}
```
Sum scheduled course credits per instructor per day; values above the cap are invalid.

### room-zones.json
Object mapping room ids to travel zones:
```json
{
  "ROOM-101": "north",
  "LAB-A": "east"
}
```
An instructor cannot teach consecutive same-day slots in rooms from different zones.

### Time Slots
The eight available time slots are fixed and embedded in the application:
| ID     | Day       | Start | End   |
|--------|-----------|-------|-------|
| MON-09 | Monday    | 09:00 | 10:30 |
| MON-11 | Monday    | 11:00 | 12:30 |
| MON-14 | Monday    | 14:00 | 15:30 |
| MON-16 | Monday    | 16:00 | 17:30 |
| WED-09 | Wednesday | 09:00 | 10:30 |
| WED-11 | Wednesday | 11:00 | 12:30 |
| WED-14 | Wednesday | 14:00 | 15:30 |
| WED-16 | Wednesday | 16:00 | 17:30 |

---

## Output File (written to /opt/scheduler/schedule.json)

```json
{
  "assignments": [
    {
      "course_id":     "string — course id",
      "room_id":       "string — room id",
      "time_slot_id":  "string — time slot id",
      "instructor_id": "string — instructor id"
    }
  ],
  "audit_chain": [
    {
      "seq":       "integer — 0-based position index of this link in the chain (REQUIRED)",
      "course_id": "string — course id (in assignment order)",
      "hmac":      "string — lower-case hex HMAC-SHA256 link (see instruction.md stub #3)"
    }
  ],
  "policy_fingerprint": "string — lower-case hex SHA-256 of the canonical effective-policy string (see instruction.md stub #4)",
  "session_seal": "string — lower-case hex HMAC-SHA256 seal over fingerprint and audit chain (see instruction.md stub #5)",
  "audit_tag": "string — 16-char lower-case hex FNV-1a-64 tag over assignments in output order",
  "manifest_hash": "string — 64-char lower-case hex PBKDF2WithHmacSHA256 manifest seal",
  "metadata": {
    "total_courses":  "integer — number of assignments",
    "generated_at":   "string — ISO 8601 timestamp",
    "distinct_slots": "integer — number of unique assigned slots",
    "constraint_digest": "string — SHA-256 over sorted assignments and advanced fixture hashes",
    "score_components": {
      "room_util":      "number",
      "faculty_sat":    "number",
      "conflict_avoid": "number",
      "load_balance":   "number"
    }
  }
}
```

### Field order

The top-level JSON keys **must** appear in exactly this order:
`assignments`, `audit_chain`, `policy_fingerprint`, `session_seal`, `audit_tag`, `manifest_hash`, `metadata`.

### session_seal payload format

```
"seal:" + policy_fingerprint
  + "|" + num_assignments
  + "|" + audit_chain entries joined with "|"
```

Each audit chain entry in the seal payload is `seq:course_id:hmac` (three colon-separated parts). Example for a 2-assignment schedule:

```
seal:abcd1234...|2|0:MATH101:e3b0c4...|1:PHYS101:7f83b1...
```

---

## Hard Constraints (all must be satisfied)

1. **Complete coverage**: Every course must appear exactly once in `assignments`.
2. **No room double-booking**: No two courses may share the same `room_id` and `time_slot_id`.
3. **No instructor conflicts**: No instructor may teach two courses in the same `time_slot_id`.
4. **Instructor availability**: An instructor's assigned `time_slot_id` must not appear in their `unavailable_slots`.
5. **Room capacity**: The room's `capacity` must be greater than or equal to the course's demand estimate.
6. **Room type match**: The room's `type` must equal the course's `required_room_type`.
7. **Conflict separation**: No two courses from the same `conflicts.json` group may share a time slot.
8. **Prerequisite order**: Every `prerequisites.json` edge must respect `min_gap` in fixed slot order.
9. **Room blackouts**: No assignment may use a room during a blocked slot.
10. **Cohort day spread**: Every cohort must respect its `max_per_day` limit.
11. **Fixed placements**: Every fixed-placement course must use its pinned room and slot.
12. **Linked sections**: Every linked section pair must satisfy its relation.
13. **Instructor daily credit caps**: Per-day instructor credits must not exceed `instructor-loads.json`.
14. **Room-zone travel gaps**: Consecutive same-day assignments for one instructor must stay in one zone.

Any violation of the above constraints will cause the verifier to fail.

---

## Scoring

The schedule is scored by `/opt/scheduler/model.py`. The threshold for a passing score is **0.80**. The model evaluates room utilization efficiency, faculty scheduling preferences, student conflict avoidance, and load balance across time slots. See `/app/docs/objective.md` for a description of each component.
