use crate::h3::h3::shadow_a;
use crate::n5::n5::rel_q::{LedgerV, RowV};

pub fn fn_h3(rows: Vec<RowV>, ledger: &LedgerV) -> Result<Vec<RowV>, String> {
    let mut out = Vec::with_capacity(rows.len());
    for row in rows {
        let mut next = row.clone();
        let ledger_cell = ledger.cells.get(&next.entity).cloned().unwrap_or_default();
        next.book_cell = shadow_a::resolve_book(
            &ledger_cell,
            &next.cache_cell,
            &next.book_cell,
        );
        next.cache_cell.clear();
        out.push(next);
    }
    Ok(out)
}

pub fn apply_a(rows: Vec<RowV>, ledger: &LedgerV) -> Result<Vec<RowV>, String> {
    fn_h3(rows, ledger)
}
