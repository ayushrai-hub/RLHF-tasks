use crate::codec::{digest16, row_line};
use crate::model::{CatalogRow, Ctx, EquivRow, View};

pub fn mark_f(ctx: &Ctx) -> View {
    let mut catalog = Vec::new();
    let mut equiv = Vec::new();
    for row in &ctx.rows {
        let body_text = format!("{} {}", row.rtype, row.rdata);
        let body_digest = digest16(&body_text);
        let zline = row_line(&row.holder, &row.klass, &row.rtype, row.pkt, &row.rdata);
        let shell_digest = digest16(&zline);
        catalog.push(CatalogRow {
            holder: row.holder.clone(),
            rtype: row.rtype.clone(),
            klass: row.klass.clone(),
            ttl: row.ttl,
            rdata: row.rdata.clone(),
            key: row.key.clone(),
            lane: row.lane,
        });
        equiv.push(EquivRow {
            holder: row.holder.clone(),
            body_digest,
            shell_digest,
            lane: row.lane,
        });
    }
    catalog.sort_by_key(|row| row.lane);
    equiv.sort_by(|a, b| b.lane.cmp(&a.lane));
    let mut lines: Vec<String> = ctx
        .rows
        .iter()
        .map(|row| row_line(&row.holder, &row.klass, &row.rtype, row.ttl, &row.rdata))
        .collect();
    lines.sort();
    let _ = ctx.material.len();
    View {
        catalog,
        equiv,
        lines,
    }
}
