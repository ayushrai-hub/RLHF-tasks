use tmpfiles_audit::{Action, ConfigFile, EntryKind, FsEntry, TmpfilesConfig};

fn entry(path: &str, age: u64) -> FsEntry {
    FsEntry {
        path: path.to_string(),
        kind: EntryKind::File,
        mode: 0o644,
        user: "root".to_string(),
        group: "root".to_string(),
        mtime_hours_ago: age,
        target: None,
    }
}

#[test]
fn creates_a_directory_and_file() {
    let cfg = TmpfilesConfig {
        files: vec![ConfigFile {
            name: "10-runtime.conf".to_string(),
            text: "d /run/app 0750 app app - -\nf /run/app/state 0640 app app - empty\n"
                .to_string(),
        }],
        entries: vec![],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty());
    assert_eq!(plan.actions.len(), 2);
    assert_eq!(
        plan.actions[0],
        Action::Create {
            path: "/run/app".to_string(),
            kind: EntryKind::Directory,
            mode: Some(0o750),
            user: Some("app".to_string()),
            group: Some("app".to_string()),
            argument: None,
        }
    );
}

#[test]
fn removes_aged_glob_matches() {
    let cfg = TmpfilesConfig {
        files: vec![ConfigFile {
            name: "20-clean.conf".to_string(),
            text: "r /var/cache/app/*.log - - - 7d -\n".to_string(),
        }],
        entries: vec![
            entry("/var/cache/app/old.log", 200),
            entry("/var/cache/app/new.log", 12),
            entry("/var/cache/app/old.tmp", 200),
        ],
    };

    let plan = cfg.compile_plan();
    assert!(plan.errors.is_empty());
    assert_eq!(
        plan.actions,
        vec![Action::Remove {
            path: "/var/cache/app/old.log".to_string()
        }]
    );
}

#[test]
fn reports_unknown_rule_type_but_keeps_valid_lines() {
    let cfg = TmpfilesConfig {
        files: vec![ConfigFile {
            name: "bad.conf".to_string(),
            text: "q /bad - - - - -\nd /run/ok 0755 root root - -\n".to_string(),
        }],
        entries: vec![],
    };

    let plan = cfg.compile_plan();
    assert_eq!(plan.errors.len(), 1);
    assert_eq!(plan.errors[0].line, 1);
    assert_eq!(plan.actions.len(), 1);
}
