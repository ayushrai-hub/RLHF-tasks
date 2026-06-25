#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EntryKind {
    File,
    Directory,
    Symlink,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FsEntry {
    pub path: String,
    pub kind: EntryKind,
    pub mode: u32,
    pub user: String,
    pub group: String,
    pub mtime_hours_ago: u64,
    pub target: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ConfigFile {
    pub name: String,
    pub text: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TmpfilesConfig {
    pub files: Vec<ConfigFile>,
    pub entries: Vec<FsEntry>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Action {
    Create {
        path: String,
        kind: EntryKind,
        mode: Option<u32>,
        user: Option<String>,
        group: Option<String>,
        argument: Option<String>,
    },
    Adjust {
        path: String,
        mode: Option<u32>,
        user: Option<String>,
        group: Option<String>,
    },
    Remove {
        path: String,
    },
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RuleError {
    pub file: String,
    pub line: usize,
    pub message: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Plan {
    pub actions: Vec<Action>,
    pub errors: Vec<RuleError>,
}
