use crate::args::parse;
use crate::check::layout_ok;
use crate::cmd_normalize;
use crate::cmd_reload;
use crate::errors::Err;
use crate::io;
use crate::model::{Cmd, Ctx, Root, Snap};
use crate::walk::{fixture_path, scope_path};

pub fn run() -> Result<(), Err> {
    let parsed = parse()?;
    let root = Root::new(parsed.root);
    let mut ctx = Ctx::new(root);
    match parsed.cmd {
        Cmd::Init { case_id } => cmd_init(&mut ctx, &case_id),
        Cmd::ApplyScope { scope_id } => cmd_apply_scope(&mut ctx, &scope_id),
        Cmd::Normalize => cmd_normalize::run(&mut ctx),
        Cmd::Reload => cmd_reload::run(&mut ctx),
    }
}

fn cmd_init(ctx: &mut Ctx, case_id: &str) -> Result<(), Err> {
    let src = fixture_path(case_id)?;
    io::copy_tree(&src, &ctx.root.src_dir())?;
    io::ensure_dir(&ctx.root.state_dir())?;
    Ok(())
}

fn cmd_apply_scope(ctx: &mut Ctx, scope_id: &str) -> Result<(), Err> {
    layout_ok(&ctx.root.base)?;
    let seed_file = scope_path(scope_id)?;
    ctx.snap.seed_rows = io::read_scope_seed(&seed_file)?;
    ctx.snap.floor = ctx
        .snap
        .seed_rows
        .iter()
        .map(|r| r.pkt)
        .min()
        .unwrap_or(0)
        / 5;
    persist_snap(&ctx.root, &ctx.snap)?;
    Ok(())
}

fn persist_snap(root: &Root, snap: &Snap) -> Result<(), Err> {
    let path = root.state_dir().join("scope-snap.bin");
    io::ensure_dir(&root.state_dir())?;
    let mut buf = Vec::new();
    buf.extend_from_slice(b"ZNSN");
    buf.push(1u8);
    let count = snap.seed_rows.len() as u16;
    buf.extend_from_slice(&count.to_le_bytes());
    for row in &snap.seed_rows {
        let id = row.key.as_bytes();
        buf.push(id.len() as u8);
        buf.extend_from_slice(id);
        buf.extend_from_slice(&row.pkt.to_le_bytes());
        buf.extend_from_slice(&row.byte.to_le_bytes());
        buf.push(row.lane as u8);
    }
    buf.extend_from_slice(&snap.floor.to_le_bytes());
    io::write_blob(&path, &buf)
}

fn load_snap(root: &Root) -> Result<Snap, Err> {
    let path = root.state_dir().join("scope-snap.bin");
    if !path.is_file() {
        return Ok(Snap {
            seed_rows: Vec::new(),
            floor: 0,
        });
    }
    let raw = std::fs::read(&path).map_err(|e| Err::new(70, e.to_string()))?;
    if raw.len() < 7 || &raw[0..4] != b"ZNSN" {
        return Err(Err::new(71, "bad snap magic"));
    }
    let count = u16::from_le_bytes([raw[5], raw[6]]) as usize;
    let mut off = 7usize;
    let mut rows = Vec::new();
    for _ in 0..count {
        let id_len = raw[off] as usize;
        off += 1;
        let key = String::from_utf8_lossy(&raw[off..off + id_len]).to_string();
        off += id_len;
        let pkt = u64::from_le_bytes(raw[off..off + 8].try_into().unwrap());
        off += 8;
        let byte = u64::from_le_bytes(raw[off..off + 8].try_into().unwrap());
        off += 8;
        let lane = raw[off] as u32;
        off += 1;
        rows.push(crate::model::Row {
            key,
            mark: String::new(),
            holder: String::new(),
            rtype: String::new(),
            klass: String::new(),
            ttl: 0,
            rdata: String::new(),
            body: String::new(),
            pkt,
            byte,
            lane,
            visit_ord: 0,
            anchor: "scope".to_string(),
            src_rel: "scope".to_string(),
        });
    }
    let floor = if off + 8 <= raw.len() {
        u64::from_le_bytes(raw[off..off + 8].try_into().unwrap())
    } else {
        0
    };
    Ok(Snap {
        seed_rows: rows,
        floor,
    })
}

pub fn hydrate_snap(ctx: &mut Ctx) -> Result<(), Err> {
    ctx.snap = load_snap(&ctx.root)?;
    Ok(())
}
