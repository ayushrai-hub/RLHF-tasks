function majorDelta(ctx, cur) {
  if (!ctx.multi[cur.player]) {
    return 0;
  }
  ctx.jackpotCount += 1;
  return 500000;
}

function stepL8m(ctx, e) {
  const cur = ctx.active;
  if (!cur || cur.tilted) {
    return;
  }
  if (e.event === "LOCK") {
    ctx.locks[cur.player] = (ctx.locks[cur.player] || 0) + 1;
    cur.base += 50000;
    if (ctx.locks[cur.player] >= 2) {
      ctx.multi[cur.player] = true;
    }
  } else if (e.event === "SIDEWALL") {
    ctx.lit[cur.player] = true;
  } else if (e.event === "JACKPOT") {
    cur.jackpot += majorDelta(ctx, cur);
  }
}

module.exports = { stepL8m, majorDelta };
