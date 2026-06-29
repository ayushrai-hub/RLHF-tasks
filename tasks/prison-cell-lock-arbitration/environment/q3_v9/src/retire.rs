use crate::JournalEntry;

pub fn archive_cold(entries: &[JournalEntry], keep: usize) -> Vec<JournalEntry> {
    if entries.len() <= keep {
        return entries.to_vec();
    }
    entries[entries.len() - keep..].to_vec()
}
