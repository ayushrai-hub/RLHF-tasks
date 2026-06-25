use tmpfiles_audit::{ConfigFile, EntryKind, FsEntry, TmpfilesConfig};

fn main() {
    let cfg = TmpfilesConfig {
        files: vec![ConfigFile {
            name: "10-demo.conf".to_string(),
            text: "d /run/demo 0755 root root - -\n".to_string(),
        }],
        entries: vec![FsEntry {
            path: "/tmp/old".to_string(),
            kind: EntryKind::File,
            mode: 0o644,
            user: "root".to_string(),
            group: "root".to_string(),
            mtime_hours_ago: 100,
            target: None,
        }],
    };
    let plan = cfg.compile_plan();
    println!("{plan:#?}");
}
