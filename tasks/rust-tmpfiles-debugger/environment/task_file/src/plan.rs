use crate::glob;
use crate::parser::{parse_line, Rule, RuleKind};
use crate::types::{Action, EntryKind, FsEntry, Plan, RuleError, TmpfilesConfig};
use std::collections::HashSet;

impl TmpfilesConfig {
    pub fn compile_plan(&self) -> Plan {
        let mut rules = Vec::new();
        let mut errors = Vec::new();

        for file in &self.files {
            for (idx, line) in file.text.lines().enumerate() {
                match parse_line(&file.name, idx + 1, line) {
                    Ok(Some(rule)) => rules.push(rule),
                    Ok(None) => {}
                    Err(e) => errors.push(e),
                }
            }
        }

        let mut actions = Vec::new();
        let mut claimed = HashSet::new();

        for rule in &rules {
            match rule.kind {
                RuleKind::Directory => {
                    if claimed.insert(rule.path.clone()) {
                        actions.push(Action::Create {
                            path: rule.path.clone(),
                            kind: EntryKind::Directory,
                            mode: rule.mode,
                            user: rule.user.clone(),
                            group: rule.group.clone(),
                            argument: None,
                        });
                    }
                }
                RuleKind::File => {
                    if claimed.insert(rule.path.clone()) {
                        actions.push(Action::Create {
                            path: rule.path.clone(),
                            kind: EntryKind::File,
                            mode: rule.mode,
                            user: rule.user.clone(),
                            group: rule.group.clone(),
                            argument: rule.argument.clone(),
                        });
                    }
                }
                RuleKind::Symlink => {
                    if claimed.insert(rule.path.clone()) {
                        actions.push(Action::Create {
                            path: rule.path.clone(),
                            kind: EntryKind::Symlink,
                            mode: rule.mode,
                            user: rule.user.clone(),
                            group: rule.group.clone(),
                            argument: rule.argument.clone(),
                        });
                    }
                }
                RuleKind::Adjust => {
                    for ent in matching_entries(&self.entries, &rule.path) {
                        if claimed.insert(ent.path.clone()) {
                            actions.push(Action::Adjust {
                                path: ent.path.clone(),
                                mode: rule.mode,
                                user: rule.user.clone(),
                                group: rule.group.clone(),
                            });
                        }
                    }
                }
                RuleKind::Remove => {
                    for ent in matching_entries(&self.entries, &rule.path) {
                        if age_ok(ent, rule) {
                            actions.push(Action::Remove {
                                path: ent.path.clone(),
                            });
                        }
                    }
                }
                RuleKind::Exclude => {}
            }
        }

        Plan { actions, errors }
    }
}

fn matching_entries<'a>(entries: &'a [FsEntry], pattern: &str) -> Vec<&'a FsEntry> {
    entries
        .iter()
        .filter(|e| glob::matches(pattern, &e.path))
        .collect()
}

fn age_ok(ent: &FsEntry, rule: &Rule) -> bool {
    match rule.age_hours {
        Some(hours) => ent.mtime_hours_ago >= hours,
        None => true,
    }
}

#[allow(dead_code)]
fn sort_errors(_errors: &mut [RuleError]) {}
