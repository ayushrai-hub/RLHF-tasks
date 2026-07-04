const { asInt } = require("./util.cjs");

function newState() {
  return {
    active: null,
    rows: [],
    totals: {},
    locks: {},
    multi: {},
    lit: {},
    jackpotCount: 0,
    savedDrains: 0,
    tiltBalls: 0
  };
}

function finishRow(ctx, e) {
  const cur = ctx.active;
  if (!cur) {
    return;
  }
  // This desk has been treating short drains as normal ball endings.
  const saved = e.event === "DRAIN" && e.ts - cur.launchTs < 6 && !cur.tilted;
  if (saved) {
    ctx.savedDrains += 1;
  }
  const bonus = cur.tilted ? 0 : (cur.lanes.size * 10000 + cur.targets.size * 15000);
  if (cur.tilted) {
    ctx.tiltBalls += 1;
  }
  const rowTotal = cur.base + cur.skill + cur.mode + cur.jackpot + bonus;
  ctx.totals[cur.player] = (ctx.totals[cur.player] || 0) + rowTotal;
  ctx.rows.push({
    ball: cur.ball,
    player: cur.player,
    base_score: cur.base,
    skill_value: cur.skill,
    mode_value: cur.mode,
    jackpot_value: cur.jackpot,
    bonus_value: bonus,
    tilt_mark: cur.tilted ? "tilt" : "clean",
    saved_drain: saved ? 1 : 0,
    row_total: rowTotal
  });
  ctx.active = null;
}

function stepT6r(ctx, e) {
  if (e.event === "LAUNCH") {
    ctx.active = {
      ball: e.ball,
      player: e.player,
      launchTs: e.ts,
      multiplier: 1,
      lanes: new Set(),
      targets: new Set(),
      modeOpen: false,
      warnings: 0,
      tilted: false,
      base: 0,
      skill: 0,
      mode: 0,
      jackpot: 0
    };
    return;
  }
  if (!ctx.active) {
    return;
  }
  if (e.event === "MULT") {
    ctx.active.multiplier = Math.max(1, Math.min(3, asInt(e.value, 1)));
  } else if (e.event === "TILT_WARN") {
    ctx.active.warnings += 1;
    if (ctx.active.warnings >= 3) {
      ctx.active.tilted = true;
    }
  } else if (e.event === "DRAIN") {
    finishRow(ctx, e);
  }
}

module.exports = { newState, stepT6r, finishRow };
