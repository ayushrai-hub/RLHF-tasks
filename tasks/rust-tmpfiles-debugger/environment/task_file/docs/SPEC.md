# tmpfiles_audit contract

`TmpfilesConfig::compile_plan` consumes `self.files` and `self.entries` and
returns a deterministic `Plan`. It does not mutate the filesystem. It only
describes what would be created, adjusted, or removed.

Config files may be named either as plain basenames such as `10-cache.conf` or
as paths under one of these roots:

- `/etc/tmpfiles.d`
- `/run/tmpfiles.d`
- `/usr/local/lib/tmpfiles.d`
- `/usr/lib/tmpfiles.d`

Files with the same basename mask lower-priority files. Priority from highest
to lowest is `/etc`, `/run`, `/usr/local/lib`, `/usr/lib`, then any unknown or
plain name. After masking, the remaining files are processed by basename in
lexicographic order, using the highest-priority file for each basename. The
caller may provide files in any order. Lines are numbered from 1 inside each
file. Blank lines and comments are ignored. Parse errors are reported in
`Plan.errors` and the bad line is skipped; one bad line must not prevent other
valid lines from being planned.

All paths in rules and filesystem entries are normalized before matching:
repeated slashes collapse, `.` segments are removed, and a trailing slash is
removed unless the path is `/`. Paths must be absolute. Any path containing a
`..` segment is invalid and the rule is skipped with an error. Matching and
output always use normalized paths.

The supported rule types are:

- `d path mode user group - -`: ensure a directory exists.
- `f path mode user group - argument`: ensure a regular file exists. The
  `argument` field is the file contents used for a create action.
- `L path - user group - argument`: ensure a symlink exists. `argument` is the
  symlink target and must not be `-` or empty.
- `z path mode user group - -`: adjust an existing path, or all existing paths
  matched by a glob path. It does not create missing paths.
- `r path - - - age -`: remove existing paths matched by `path` when they are
  old enough for `age`.
- `R path - - - age -`: recursively remove existing paths matched by `path`,
  plus existing descendants of each matched directory, when they are old enough
  for `age`.
- `x path - - - - -`: exclude existing paths matched by `path` from every
  cleanup rule.

For `d`, `f`, `L`, and `z`, first match wins per normalized path. The first
create or adjust rule that claims a path determines the action for that path;
later create or adjust rules for the same path are ignored. This claim is only
for create/adjust precedence; it does not exempt the path from cleanup. A path
may therefore have both an `Adjust` action and a `Remove` action when it matches
an eligible cleanup rule. A glob `z` claims each matching existing path
individually in lexicographic path order.

Create rules are "ensure" rules. If the normalized path is missing, the plan
contains a `Create` action. If the path already exists with the expected kind,
the plan contains an `Adjust` action when at least one of mode, user, or group is
specified; otherwise it contains no action. If the path already exists with the
wrong kind, the rule reports an error and emits no action for that path.

Cleanup rules only consider paths already present in `self.entries`. Exclusions
from every `x` rule are collected before cleanup actions are produced, even if
the `x` line appears after an `r` line. An excluded path is never removed. For
recursive `R`, excluding a directory also protects every existing descendant,
and excluding a descendant prevents a removal action for any ancestor directory
that would otherwise remove it. In that case the planner may still remove other
eligible, unprotected descendants. When an eligible directory is removed by `R`,
that single parent removal absorbs its descendants: do not also emit `Remove`
actions for children below a removed ancestor. Each remaining path is removed at
most once, and only when the cleanup rule's age field is satisfied.

For example, with existing `/var/tmp/app`, `/var/tmp/app/old`, and
`/var/tmp/app/keep`, the rules `z /var/tmp/app/old ...`, `x /var/tmp/app/keep
...`, and `R /var/tmp/app ...` can produce both `Adjust(/var/tmp/app/old)` and
`Remove(/var/tmp/app/old)`, but must not remove `/var/tmp/app` because doing so
would delete the excluded `keep` path. If no protected or too-young descendant
exists, `Remove(/var/tmp/app)` is enough and child removes are omitted.

The filesystem snapshot may be unsorted. Duplicate normalized entry paths are
resolved by keeping the first entry in the caller-provided snapshot. Actions in
the final plan are sorted deterministically by normalized path, then by action
kind in this order: create, adjust, remove. Errors are sorted by file name and
line number. Errors refer to the selected config file name after masking.

The public structs, enum variants, field names, and
`TmpfilesConfig::compile_plan` signature are part of the grader contract.
