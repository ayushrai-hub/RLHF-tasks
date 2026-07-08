use crate::args::parse;
use crate::cmd_admit;
use crate::cmd_bootstrap;
use crate::cmd_flush;
use crate::cmd_rewind;
use crate::cmd_uplift;
use crate::errors::GateError;
use crate::model::{Ctx, Mode, Root};

pub fn run() -> Result<(), GateError> {
    let parsed = parse()?;
    let root = Root::new(parsed.root);
    let mut ctx = Ctx::new(root);
    match parsed.mode {
        Mode::Open { sample } => cmd_bootstrap::run(&mut ctx, &sample),
        Mode::Offer { tag } => cmd_admit::run(&mut ctx, &tag),
        Mode::Cycle { partial } => cmd_rewind::run(&mut ctx, partial),
        Mode::Raise => cmd_uplift::run(&mut ctx),
        Mode::Sweep { again } => cmd_flush::run(&mut ctx, again),
    }
}
