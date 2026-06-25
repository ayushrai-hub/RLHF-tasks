import json
import subprocess
from pathlib import Path
from fnmatch import fnmatchcase


PKG_DIR = Path("/app/task_file")
HIDDEN_TEST = PKG_DIR / "tests" / "hidden_semantics.rs"
GENERATED_TEST = PKG_DIR / "tests" / "generated_reference.rs"


HIDDEN_TEST_SRC = r'''
use tmpfiles_audit::{Action, ConfigFile, EntryKind, FsEntry, TmpfilesConfig};

fn file(name: &str, text: &str) -> ConfigFile {
    ConfigFile { name: name.to_string(), text: text.to_string() }
}

fn ent(path: &str, kind: EntryKind, age: u64) -> FsEntry {
    FsEntry {
        path: path.to_string(),
        kind,
        mode: 0o644,
        user: "root".to_string(),
        group: "root".to_string(),
        mtime_hours_ago: age,
        target: None,
    }
}

fn paths(actions: &[Action]) -> Vec<String> {
    actions.iter().map(|a| match a {
        Action::Create { path, .. } => path.clone(),
        Action::Adjust { path, .. } => path.clone(),
        Action::Remove { path } => path.clone(),
    }).collect()
}

#[test]
fn config_file_order_normalization_and_first_match_hold() {
    let cfg = TmpfilesConfig {
        files: vec![
            file("20-local.conf", "d /run//svc/./data 0700 late late - -\n"),
            file("10-vendor.conf", "d /run/svc/data 0750 svc svc - -\n"),
        ],
        entries: vec![],
    };

    let plan = cfg.compile_plan();
    assert_eq!(plan.errors, vec![]);
    assert_eq!(plan.actions, vec![Action::Create {
        path: "/run/svc/data".to_string(),
        kind: EntryKind::Directory,
        mode: Some(0o750),
        user: Some("svc".to_string()),
        group: Some("svc".to_string()),
        argument: None,
    }]);
}

#[test]
fn quoted_fields_comments_and_symlink_targets_are_preserved() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-quoted.conf",
            "f \"/var/lib/my app/state file\" 0640 \"svc user\" 'svc group' - \"hello # still data\" # comment\n\
             L /run/current - root root - ../targets/current\n",
        )],
        entries: vec![],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty(), "{:?}", plan.errors);
    assert_eq!(plan.actions, vec![
        Action::Create {
            path: "/run/current".to_string(),
            kind: EntryKind::Symlink,
            mode: None,
            user: Some("root".to_string()),
            group: Some("root".to_string()),
            argument: Some("../targets/current".to_string()),
        },
        Action::Create {
            path: "/var/lib/my app/state file".to_string(),
            kind: EntryKind::File,
            mode: Some(0o640),
            user: Some("svc user".to_string()),
            group: Some("svc group".to_string()),
            argument: Some("hello # still data".to_string()),
        },
    ]);
}

#[test]
fn invalid_paths_are_reported_and_valid_paths_are_normalized() {
    let cfg = TmpfilesConfig {
        files: vec![
            file("20-bad.conf", "d relative/path 0755 root root - -\n"),
            file("10-mixed.conf", "d /var/../tmp 0755 root root - -\nd /var//tmp/./audit/ 0755 root root - -\n"),
        ],
        entries: vec![],
    };

    let plan = cfg.compile_plan();
    assert_eq!(plan.actions, vec![Action::Create {
        path: "/var/tmp/audit".to_string(),
        kind: EntryKind::Directory,
        mode: Some(0o755),
        user: Some("root".to_string()),
        group: Some("root".to_string()),
        argument: None,
    }]);
    assert_eq!(plan.errors.len(), 2);
    assert_eq!((plan.errors[0].file.as_str(), plan.errors[0].line), ("10-mixed.conf", 1));
    assert_eq!((plan.errors[1].file.as_str(), plan.errors[1].line), ("20-bad.conf", 1));
    assert!(plan.errors.iter().all(|e| !e.message.is_empty()));
}

#[test]
fn bracket_globs_adjust_existing_paths_and_late_excludes_still_protect_cleanup() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-clean.conf",
            "r /var/cache/app/[ab].log - - - 7d -\n\
             x /var/cache/app/b.log - - - - -\n\
             z /var/cache/app/?.tmp 0600 app app - -\n",
        )],
        entries: vec![
            ent("/var/cache/app/b.log", EntryKind::File, 240),
            ent("/var/cache/app/c.tmp", EntryKind::File, 240),
            ent("/var/cache/app/a.log", EntryKind::File, 240),
            ent("/var/cache/app/d.tmp", EntryKind::File, 12),
        ],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty(), "{:?}", plan.errors);
    assert_eq!(plan.actions, vec![
        Action::Remove { path: "/var/cache/app/a.log".to_string() },
        Action::Adjust {
            path: "/var/cache/app/c.tmp".to_string(),
            mode: Some(0o600),
            user: Some("app".to_string()),
            group: Some("app".to_string()),
        },
        Action::Adjust {
            path: "/var/cache/app/d.tmp".to_string(),
            mode: Some(0o600),
            user: Some("app".to_string()),
            group: Some("app".to_string()),
        },
    ]);
}

#[test]
fn age_units_are_inclusive_and_duplicate_entries_do_not_duplicate_removals() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-age.conf",
            "r /tmp/two-days - - - 2d -\n\
             r /tmp/two-weeks - - - 2w -\n\
             r /tmp/fresh - - - 0 -\n\
             r /tmp/dup - - - - -\n",
        )],
        entries: vec![
            ent("/tmp/two-days", EntryKind::File, 48),
            ent("/tmp/two-weeks", EntryKind::File, 336),
            ent("/tmp/fresh", EntryKind::File, 1),
            ent("/tmp/dup", EntryKind::File, 900),
            ent("/tmp/dup", EntryKind::File, 900),
        ],
    };

    let plan = cfg.compile_plan();
    assert_eq!(paths(&plan.actions), vec![
        "/tmp/dup",
        "/tmp/fresh",
        "/tmp/two-days",
        "/tmp/two-weeks",
    ]);
    assert_eq!(plan.actions.iter().filter(|a| matches!(a, Action::Remove { .. })).count(), 4);
}

#[test]
fn glob_adjust_claims_paths_once_and_final_actions_are_sorted() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-sort.conf",
            "z /etc/* 0640 root root - -\n\
             z /etc/a 0600 late late - -\n\
             d /aaa 0755 root root - -\n\
             r /zzz - - - - -\n",
        )],
        entries: vec![
            ent("/etc/b", EntryKind::File, 1),
            ent("/zzz", EntryKind::File, 100),
            ent("/etc/a", EntryKind::File, 1),
        ],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty(), "{:?}", plan.errors);
    assert_eq!(paths(&plan.actions), vec!["/aaa", "/etc/a", "/etc/b", "/zzz"]);
    let a = plan.actions.iter().find(|act| matches!(act, Action::Adjust { path, .. } if path == "/etc/a")).unwrap();
    assert_eq!(a, &Action::Adjust {
        path: "/etc/a".to_string(),
        mode: Some(0o640),
        user: Some("root".to_string()),
        group: Some("root".to_string()),
    });
}

#[test]
fn invalid_mode_age_and_symlink_target_are_reported_without_dropping_valid_lines() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-errors.conf",
            "d /bad-mode 888 root root - -\n\
             d /short-mode 75 root root - -\n\
             r /bad-age - - - 3m -\n\
             L /bad-link - root root - -\n\
             d /ok 0755 root root - -\n",
        )],
        entries: vec![ent("/bad-age", EntryKind::File, 10)],
    };

    let plan = cfg.compile_plan();
    assert_eq!(plan.actions, vec![Action::Create {
        path: "/ok".to_string(),
        kind: EntryKind::Directory,
        mode: Some(0o755),
        user: Some("root".to_string()),
        group: Some("root".to_string()),
        argument: None,
    }]);
    assert_eq!(plan.errors.len(), 4);
    assert_eq!(plan.errors.iter().map(|e| e.line).collect::<Vec<_>>(), vec![1, 2, 3, 4]);
}

#[test]
fn missing_trailing_fields_blank_lines_comments_and_escaped_fields_parse() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-parse.conf",
            "\n\
             # ignored comment\n\
             d /run/minimal\n\
             f /run/escaped 0644 root root - hello\\ world\n\
             f /run/hash 0644 root root - value\\#kept\n",
        )],
        entries: vec![],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty(), "{:?}", plan.errors);
    assert_eq!(plan.actions, vec![
        Action::Create {
            path: "/run/escaped".to_string(),
            kind: EntryKind::File,
            mode: Some(0o644),
            user: Some("root".to_string()),
            group: Some("root".to_string()),
            argument: Some("hello world".to_string()),
        },
        Action::Create {
            path: "/run/hash".to_string(),
            kind: EntryKind::File,
            mode: Some(0o644),
            user: Some("root".to_string()),
            group: Some("root".to_string()),
            argument: Some("value#kept".to_string()),
        },
        Action::Create {
            path: "/run/minimal".to_string(),
            kind: EntryKind::Directory,
            mode: None,
            user: None,
            group: None,
            argument: None,
        },
    ]);
}

#[test]
fn too_many_fields_empty_identity_and_unclosed_quote_are_errors() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-more-errors.conf",
            "d /too-many 0755 root root - - extra\n\
             d /empty-user 0755 '' root - -\n\
             f /bad-quote 0644 root root - \"unterminated\n\
             d /ok-short 755 root root\n",
        )],
        entries: vec![],
    };

    let plan = cfg.compile_plan();
    assert_eq!(plan.actions, vec![Action::Create {
        path: "/ok-short".to_string(),
        kind: EntryKind::Directory,
        mode: Some(0o755),
        user: Some("root".to_string()),
        group: Some("root".to_string()),
        argument: None,
    }]);
    assert_eq!(plan.errors.len(), 3);
    assert_eq!(plan.errors.iter().map(|e| e.line).collect::<Vec<_>>(), vec![1, 2, 3]);
}

#[test]
fn adjust_and_cleanup_only_consider_existing_snapshot_paths() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-existing.conf",
            "z /missing/path 0600 app app - -\n\
             r /also/missing - - - - -\n\
             z /present 0600 app app - -\n",
        )],
        entries: vec![ent("/present", EntryKind::File, 1)],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty(), "{:?}", plan.errors);
    assert_eq!(plan.actions, vec![Action::Adjust {
        path: "/present".to_string(),
        mode: Some(0o600),
        user: Some("app".to_string()),
        group: Some("app".to_string()),
    }]);
}

#[test]
fn action_kind_order_handles_create_or_adjust_before_remove_for_same_path() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-kind-order.conf",
            "r /adjusted - - - - -\n\
             z /adjusted 0600 app app - -\n\
             d /created 0755 root root - -\n",
        )],
        entries: vec![ent("/adjusted", EntryKind::File, 100)],
    };

    let plan = cfg.compile_plan();
    assert_eq!(plan.actions, vec![
        Action::Adjust {
            path: "/adjusted".to_string(),
            mode: Some(0o600),
            user: Some("app".to_string()),
            group: Some("app".to_string()),
        },
        Action::Remove { path: "/adjusted".to_string() },
        Action::Create {
            path: "/created".to_string(),
            kind: EntryKind::Directory,
            mode: Some(0o755),
            user: Some("root".to_string()),
            group: Some("root".to_string()),
            argument: None,
        },
    ]);
}

#[test]
fn basename_masking_uses_highest_priority_file_and_ignores_masked_errors() {
    let cfg = TmpfilesConfig {
        files: vec![
            file("/usr/lib/tmpfiles.d/50-cache.conf", "bad /vendor 0755 root root - -\n"),
            file("/run/tmpfiles.d/40-runtime.conf", "d /run/runtime 0755 root root - -\n"),
            file("/etc/tmpfiles.d/50-cache.conf", "d /run/etc-cache 0700 cache cache - -\n"),
            file("30-plain.conf", "d /run/plain 0755 root root - -\n"),
        ],
        entries: vec![],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty(), "{:?}", plan.errors);
    assert_eq!(paths(&plan.actions), vec!["/run/etc-cache", "/run/plain", "/run/runtime"]);
}

#[test]
fn ensure_rules_adjust_existing_matching_kind_and_error_on_wrong_kind() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-ensure.conf",
            "d /run/existing-dir 0750 svc svc - -\n\
             f /run/existing-file 0640 svc svc - replacement\n\
             L /run/existing-link - svc svc - ../target\n\
             d /run/wrong-kind 0755 root root - -\n\
             d /run/no-fields\n",
        )],
        entries: vec![
            ent("/run/wrong-kind", EntryKind::File, 1),
            ent("/run/existing-file", EntryKind::File, 1),
            ent("/run/existing-dir", EntryKind::Directory, 1),
            ent("/run/existing-link", EntryKind::Symlink, 1),
        ],
    };

    let plan = cfg.compile_plan();
    assert_eq!(plan.errors.len(), 1);
    assert_eq!((plan.errors[0].file.as_str(), plan.errors[0].line), ("10-ensure.conf", 4));
    assert_eq!(plan.actions, vec![
        Action::Adjust {
            path: "/run/existing-dir".to_string(),
            mode: Some(0o750),
            user: Some("svc".to_string()),
            group: Some("svc".to_string()),
        },
        Action::Adjust {
            path: "/run/existing-file".to_string(),
            mode: Some(0o640),
            user: Some("svc".to_string()),
            group: Some("svc".to_string()),
        },
        Action::Adjust {
            path: "/run/existing-link".to_string(),
            mode: None,
            user: Some("svc".to_string()),
            group: Some("svc".to_string()),
        },
        Action::Create {
            path: "/run/no-fields".to_string(),
            kind: EntryKind::Directory,
            mode: None,
            user: None,
            group: None,
            argument: None,
        },
    ]);
}

#[test]
fn recursive_cleanup_respects_excluded_and_young_descendants() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-recursive.conf",
            "x /var/tmp/app/keep - - - - -\n\
             R /var/tmp/app - - - 1w2d3h -\n",
        )],
        entries: vec![
            ent("/var/tmp/app/new.log", EntryKind::File, 100),
            ent("/var/tmp/app/cache/old.log", EntryKind::File, 500),
            ent("/var/tmp/app/keep/data", EntryKind::File, 500),
            ent("/var/tmp/app/cache", EntryKind::Directory, 500),
            ent("/var/tmp/app/keep", EntryKind::Directory, 500),
            ent("/var/tmp/app", EntryKind::Directory, 500),
        ],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty(), "{:?}", plan.errors);
    assert_eq!(plan.actions, vec![Action::Remove {
        path: "/var/tmp/app/cache".to_string(),
    }]);
}

#[test]
fn recursive_cleanup_can_remove_multiple_roots_and_skips_duplicate_descendants() {
    let cfg = TmpfilesConfig {
        files: vec![file(
            "10-recursive-glob.conf",
            "R /srv/cache/[ab] - - - 2d -\n",
        )],
        entries: vec![
            ent("/srv/cache/a", EntryKind::Directory, 48),
            ent("/srv/cache/a/file", EntryKind::File, 48),
            ent("/srv/cache/b", EntryKind::Directory, 72),
            ent("/srv/cache/b/file", EntryKind::File, 72),
            ent("/srv/cache/c", EntryKind::Directory, 72),
        ],
    };

    let plan = cfg.compile_plan();
    assert_eq!(plan.actions, vec![
        Action::Remove { path: "/srv/cache/a".to_string() },
        Action::Remove { path: "/srv/cache/b".to_string() },
    ]);
}
'''


def test_hidden_semantics():
    HIDDEN_TEST.write_text(HIDDEN_TEST_SRC)
    result = subprocess.run(
        ["cargo", "test", "--release"],
        cwd=PKG_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout


def _norm(path):
    if not path.startswith("/"):
        raise ValueError("path must be absolute")
    parts = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("path must not contain '..'")
        parts.append(part)
    return "/" + "/".join(parts) if parts else "/"


def _root_priority(name):
    roots = [
        ("/etc/tmpfiles.d/", 0),
        ("/run/tmpfiles.d/", 1),
        ("/usr/local/lib/tmpfiles.d/", 2),
        ("/usr/lib/tmpfiles.d/", 3),
    ]
    stripped = name.rstrip("/")
    base = stripped.rsplit("/", 1)[-1] if "/" in stripped else stripped
    for root, pri in roots:
        if stripped.startswith(root):
            return base, pri
    return base, 4


def _split_fields(line):
    fields = []
    cur = []
    quote = None
    in_field = False
    i = 0
    while i < len(line):
        ch = line[i]
        if quote is not None:
            if ch == "\\":
                i += 1
                cur.append(line[i] if i < len(line) else "\\")
            elif ch == quote:
                quote = None
            else:
                cur.append(ch)
            in_field = True
        elif ch == "#":
            break
        elif ch in ("'", '"'):
            quote = ch
            in_field = True
        elif ch == "\\":
            i += 1
            cur.append(line[i] if i < len(line) else "\\")
            in_field = True
        elif ch.isspace():
            if in_field:
                fields.append("".join(cur))
                cur = []
                in_field = False
        else:
            cur.append(ch)
            in_field = True
        i += 1
    if quote is not None:
        raise ValueError("unterminated quote")
    if in_field:
        fields.append("".join(cur))
    return fields


def _parse_mode(raw):
    if raw == "-":
        return None
    if len(raw) not in (3, 4) or any(c not in "01234567" for c in raw):
        raise ValueError("invalid mode")
    return int(raw, 8)


def _parse_identity(raw):
    if raw == "-":
        return None
    if raw == "":
        raise ValueError("empty identity field")
    return raw


def _parse_age(raw):
    if raw in ("-", "0"):
        return 0
    total = 0
    digits = ""
    seen = False
    for ch in raw:
        if ch.isdigit():
            digits += ch
            continue
        mult = {"h": 1, "d": 24, "w": 24 * 7}.get(ch)
        if mult is None or not digits:
            raise ValueError("invalid age")
        amount = int(digits)
        if amount <= 0:
            raise ValueError("invalid age")
        total += amount * mult
        digits = ""
        seen = True
    if digits or not seen:
        raise ValueError("invalid age")
    return total


def _parse_rule(file_name, line_no, text):
    fields = _split_fields(text)
    if not fields:
        return None
    if len(fields) < 2:
        raise ValueError("not enough fields")
    if len(fields) > 7:
        raise ValueError("too many fields")
    fields = fields + ["-"] * (7 - len(fields))
    kind = fields[0]
    if kind not in ("d", "f", "L", "z", "r", "R", "x"):
        raise ValueError("unknown rule type")
    path = _norm(fields[1])
    mode = _parse_mode(fields[2])
    user = _parse_identity(fields[3])
    group = _parse_identity(fields[4])
    age = _parse_age(fields[5])
    argument = None if fields[6] == "-" else fields[6]
    if kind == "L" and argument is None:
        raise ValueError("symlink target is required")
    return {
        "kind": kind,
        "file": file_name,
        "line": line_no,
        "path": path,
        "mode": mode,
        "user": user,
        "group": group,
        "age": age,
        "argument": argument,
    }


def _is_descendant(path, root):
    if root == "/":
        return path != "/"
    return len(path) > len(root) and path.startswith(root) and path[len(root)] == "/"


def _matches(pattern, path):
    return fnmatchcase(path, pattern)


def _entry(path, kind, age, mode=0o644, user="root", group="root", target=None):
    return {
        "path": path,
        "kind": kind,
        "mode": mode,
        "user": user,
        "group": group,
        "age": age,
        "target": target,
    }


def _selected_files(files):
    by_base = {}
    for file in files:
        base, pri = _root_priority(file["name"])
        prev = by_base.get(base)
        if prev is None or (pri, file["name"]) < (prev[0], prev[1]["name"]):
            by_base[base] = (pri, file)
    return [item[1] for _, item in sorted(by_base.items())]


def _reference_plan(files, entries):
    rules = []
    errors = []
    for file in _selected_files(files):
        for idx, line in enumerate(file["text"].splitlines(), start=1):
            try:
                rule = _parse_rule(file["name"], idx, line)
            except ValueError:
                errors.append((file["name"], idx))
                continue
            if rule is not None:
                rules.append(rule)
    errors.sort()

    by_path = {}
    for ent in entries:
        try:
            path = _norm(ent["path"])
        except ValueError:
            continue
        if path not in by_path:
            copy = dict(ent)
            copy["path"] = path
            by_path[path] = copy
    normalized_entries = [by_path[p] for p in sorted(by_path)]

    protected_exact = set()
    protected_dirs = set()
    for rule in rules:
        if rule["kind"] != "x":
            continue
        for ent in normalized_entries:
            if _matches(rule["path"], ent["path"]):
                protected_exact.add(ent["path"])
                if ent["kind"] == "Directory":
                    protected_dirs.add(ent["path"])

    def protected(path):
        return path in protected_exact or any(_is_descendant(path, root) for root in protected_dirs)

    actions = []
    claimed = set()

    def claim_ensure(rule, expected_kind):
        if rule["path"] in claimed:
            return
        claimed.add(rule["path"])
        existing = by_path.get(rule["path"])
        if existing is None:
            actions.append({
                "type": "Create",
                "path": rule["path"],
                "entry_kind": expected_kind,
                "mode": rule["mode"],
                "user": rule["user"],
                "group": rule["group"],
                "argument": rule["argument"] if expected_kind != "Directory" else None,
            })
        elif existing["kind"] != expected_kind:
            errors.append((rule["file"], rule["line"]))
        elif rule["mode"] is not None or rule["user"] is not None or rule["group"] is not None:
            actions.append({
                "type": "Adjust",
                "path": rule["path"],
                "mode": rule["mode"],
                "user": rule["user"],
                "group": rule["group"],
            })

    for rule in rules:
        if rule["kind"] == "d":
            claim_ensure(rule, "Directory")
        elif rule["kind"] == "f":
            claim_ensure(rule, "File")
        elif rule["kind"] == "L":
            claim_ensure(rule, "Symlink")
        elif rule["kind"] == "z":
            for ent in normalized_entries:
                if _matches(rule["path"], ent["path"]) and ent["path"] not in claimed:
                    claimed.add(ent["path"])
                    actions.append({
                        "type": "Adjust",
                        "path": ent["path"],
                        "mode": rule["mode"],
                        "user": rule["user"],
                        "group": rule["group"],
                    })

    removed = set()

    def age_ok(ent, rule):
        return ent["age"] >= rule["age"]

    def removed_ancestor(path):
        return any(_is_descendant(path, root) for root in removed)

    def blocking_descendant(root, rule):
        for ent in normalized_entries:
            if _is_descendant(ent["path"], root) and (protected(ent["path"]) or not age_ok(ent, rule)):
                return True
        return False

    for rule in rules:
        if rule["kind"] == "r":
            for ent in normalized_entries:
                if _matches(rule["path"], ent["path"]) and not protected(ent["path"]) and age_ok(ent, rule):
                    if ent["path"] not in removed:
                        removed.add(ent["path"])
                        actions.append({"type": "Remove", "path": ent["path"]})
        elif rule["kind"] == "R":
            candidates = {}
            for ent in normalized_entries:
                if _matches(rule["path"], ent["path"]):
                    candidates[ent["path"]] = ent
                    if ent["kind"] == "Directory":
                        for child in normalized_entries:
                            if _is_descendant(child["path"], ent["path"]):
                                candidates[child["path"]] = child
            ordered = sorted(candidates.values(), key=lambda e: (e["path"].count("/"), e["path"]))
            for ent in ordered:
                path = ent["path"]
                if removed_ancestor(path) or protected(path) or not age_ok(ent, rule):
                    continue
                if ent["kind"] == "Directory" and blocking_descendant(path, rule):
                    continue
                if path not in removed:
                    removed.add(path)
                    actions.append({"type": "Remove", "path": path})

    rank = {"Create": 0, "Adjust": 1, "Remove": 2}
    actions.sort(key=lambda a: (a["path"], rank[a["type"]]))
    errors.sort()
    return actions, errors


def _case(seed):
    root = f"/var/tmp/gen{seed}"
    files = [
        {
            "name": f"/usr/lib/tmpfiles.d/50-gen{seed}.conf",
            "text": "bad /masked 0755 root root - -\n",
        },
        {
            "name": f"/etc/tmpfiles.d/50-gen{seed}.conf" if seed % 2 == 0 else f"/run/tmpfiles.d/50-gen{seed}.conf",
            "text": "\n".join([
                f"d /run//gen{seed}/./dir 0750 svc svc - -",
                f"f /run/gen{seed}/state 0640 svc svc - data{seed}",
                f"L /run/gen{seed}/current - svc svc - ../targets/{seed}",
                f"d {root}/existing-dir 0755 daemon daemon - -",
                f"f {root}/existing-file 0640 daemon daemon - replace",
                f"L {root}/existing-link - daemon daemon - ../target",
                f"d {root}/wrong-kind 0755 root root - -",
                f"z {root}/cache/[ab]* 0600 cache cache - -",
                f"x {root}/cache/keep - - - - -",
                f"R {root}/cache - - - 2d3h -",
                f"r {root}/logs/*.log - - - 1w -",
                f"d relative-{seed} 0755 root root - -" if seed % 3 == 0 else f"# no selected path error {seed}",
                "",
            ]),
        },
        {
            "name": f"10-extra{seed}.conf",
            "text": "\n".join([
                f"z {root}/logs/?.log 0660 log log - -",
                f"r {root}/logs/stale.log - - - 0 -",
                f"d {root}/new-dir 0755 root root - -",
                "",
            ]),
        },
    ]
    entries = [
        _entry(f"{root}/wrong-kind", "File", 900),
        _entry(f"{root}/existing-dir", "Directory", 10),
        _entry(f"{root}/existing-file", "File", 10),
        _entry(f"{root}/existing-link", "Symlink", 10),
        _entry(f"{root}/cache", "Directory", 120 + seed),
        _entry(f"{root}/cache/a-node", "Directory", 120 + seed),
        _entry(f"{root}/cache/a-node/old.bin", "File", 120 + seed),
        _entry(f"{root}/cache/b-file", "File", 120 + seed),
        _entry(f"{root}/cache/keep", "Directory", 120 + seed),
        _entry(f"{root}/cache/keep/saved.db", "File", 120 + seed),
        _entry(f"{root}/cache/young", "File", 1 + seed % 12),
        _entry(f"{root}/logs/a.log", "File", 220 + seed),
        _entry(f"{root}/logs/b.log", "File", 3),
        _entry(f"{root}/logs/stale.log", "File", 350),
        _entry(f"{root}/logs/stale.log", "File", 999),
    ]
    if seed % 4 == 0:
        entries.append(_entry(f"{root}//logs/./c.log", "File", 220))
    return files, entries


def _rs_str(value):
    return json.dumps(value)


def _rs_opt_str(value):
    return "None" if value is None else f"Some({_rs_str(value)}.to_string())"


def _rs_opt_mode(value):
    return "None" if value is None else f"Some(0o{value:o})"


def _rs_kind(kind):
    return f"EntryKind::{kind}"


def _rs_entry(ent):
    target = _rs_opt_str(ent.get("target"))
    return (
        "FsEntry { "
        f"path: {_rs_str(ent['path'])}.to_string(), "
        f"kind: {_rs_kind(ent['kind'])}, "
        f"mode: 0o{ent['mode']:o}, "
        f"user: {_rs_str(ent['user'])}.to_string(), "
        f"group: {_rs_str(ent['group'])}.to_string(), "
        f"mtime_hours_ago: {ent['age']}, "
        f"target: {target} "
        "}"
    )


def _rs_action(action):
    if action["type"] == "Create":
        return (
            "Action::Create { "
            f"path: {_rs_str(action['path'])}.to_string(), "
            f"kind: {_rs_kind(action['entry_kind'])}, "
            f"mode: {_rs_opt_mode(action['mode'])}, "
            f"user: {_rs_opt_str(action['user'])}, "
            f"group: {_rs_opt_str(action['group'])}, "
            f"argument: {_rs_opt_str(action['argument'])} "
            "}"
        )
    if action["type"] == "Adjust":
        return (
            "Action::Adjust { "
            f"path: {_rs_str(action['path'])}.to_string(), "
            f"mode: {_rs_opt_mode(action['mode'])}, "
            f"user: {_rs_opt_str(action['user'])}, "
            f"group: {_rs_opt_str(action['group'])} "
            "}"
        )
    return f"Action::Remove {{ path: {_rs_str(action['path'])}.to_string() }}"


def _generated_rust_tests():
    blocks = [
        "use tmpfiles_audit::{Action, ConfigFile, EntryKind, FsEntry, TmpfilesConfig};",
        "",
        "fn error_pairs(plan: &tmpfiles_audit::Plan) -> Vec<(String, usize)> {",
        "    plan.errors.iter().map(|e| (e.file.clone(), e.line)).collect()",
        "}",
        "",
    ]
    for seed in range(24):
        files, entries = _case(seed)
        expected_actions, expected_errors = _reference_plan(files, entries)
        rs_files = ",\n            ".join(
            f"ConfigFile {{ name: {_rs_str(f['name'])}.to_string(), text: {_rs_str(f['text'])}.to_string() }}"
            for f in files
        )
        rs_entries = ",\n            ".join(_rs_entry(e) for e in entries)
        rs_actions = ",\n            ".join(_rs_action(a) for a in expected_actions)
        rs_errors = ", ".join(f"({_rs_str(f)}.to_string(), {line}usize)" for f, line in expected_errors)
        blocks.append(
            f"""
#[test]
fn generated_reference_case_{seed:02}() {{
    let cfg = TmpfilesConfig {{
        files: vec![
            {rs_files}
        ],
        entries: vec![
            {rs_entries}
        ],
    }};
    let plan = cfg.compile_plan();
    assert_eq!(plan.actions, vec![
            {rs_actions}
    ]);
    assert_eq!(error_pairs(&plan), vec![{rs_errors}]);
    assert!(plan.errors.iter().all(|e| !e.message.is_empty()));
}}
"""
        )
    return "\n".join(blocks)


def test_generated_reference_cases():
    GENERATED_TEST.write_text(_generated_rust_tests())
    result = subprocess.run(
        ["cargo", "test", "--release", "--test", "generated_reference"],
        cwd=PKG_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout


def test_fix_report():
    report_path = PKG_DIR / "output" / "fix_report.json"
    assert report_path.exists(), "missing /app/task_file/output/fix_report.json"
    data = json.loads(report_path.read_text())
    fixes = data.get("bugs_fixed")
    assert isinstance(fixes, list), "bugs_fixed must be a list"
    assert len(fixes) >= 10, "report must describe at least ten fixes"
    seen = set()
    for idx, item in enumerate(fixes):
        assert isinstance(item, dict), f"fix {idx} is not an object"
        for key in ("file", "method", "description"):
            assert isinstance(item.get(key), str) and item[key].strip(), f"fix {idx} has empty {key}"
        pair = (item["file"], item["method"])
        assert pair not in seen, f"duplicate fix entry for {pair}"
        seen.add(pair)
