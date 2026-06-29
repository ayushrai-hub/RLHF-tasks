use q3_v9::{JournalEntry, filter_w2};

pub fn apply_journal_window(entries: &[JournalEntry], active_epoch: u64) -> Vec<JournalEntry> {
    filter_w2(entries, active_epoch)
}
