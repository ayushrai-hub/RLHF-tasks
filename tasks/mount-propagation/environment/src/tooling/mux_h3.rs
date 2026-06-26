use crate::h3::h3::bind_q;
use crate::n5::n5::rel_q::{LedgerV, RowV};

pub fn reconcile_rows(rows: Vec<RowV>, ledger: &LedgerV) -> Result<Vec<RowV>, String> {
    bind_q::apply_a(rows, ledger)
}
