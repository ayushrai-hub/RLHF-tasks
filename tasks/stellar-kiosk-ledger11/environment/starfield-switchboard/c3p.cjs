function modeDelta(cur, value) {
  if (!cur.modeOpen) {
    return 25000;
  }
  if (cur.targets.has(value)) {
    return 75000;
  }
  cur.targets.add(value);
  if (cur.targets.size >= 4) {
    cur.modeOpen = false;
    return 75000 * cur.multiplier;
  }
  return 75000;
}

function stepC3p(ctx, e) {
  const cur = ctx.active;
  if (!cur || cur.tilted) {
    return;
  }
  if (e.event === "MODE_START") {
    cur.modeOpen = true;
    cur.targets = new Set();
  } else if (e.event === "TARGET") {
    cur.mode += modeDelta(cur, e.value);
  }
}

module.exports = { stepC3p, modeDelta };
