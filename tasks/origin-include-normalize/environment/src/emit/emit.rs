use crate::model::Ctx;

pub fn format_banner(ctx: &Ctx, label: &str) -> String {
    format!("{} epoch={} rows={}", label, ctx.epoch, ctx.rows.len())
}
