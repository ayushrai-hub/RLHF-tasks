use crate::pool::Engine;

pub fn apply(engine: &mut Engine, ceiling: u32) {
    engine.rows.retain(|r| r.seq <= ceiling);
}

pub fn apply_floor_cut(engine: &mut Engine, floor: u32) {
    engine.rows.retain(|r| r.seq >= floor);
}

pub fn apply_modulo_prune(engine: &mut Engine, modulo: u32) {
    engine.rows.retain(|r| r.seq % modulo != 0);
}
