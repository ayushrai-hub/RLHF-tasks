const { asInt } = require("./util.cjs");

function valueN4a(size) {
  if (size === 0) return 20000;
  if (size === 1) return 40000;
  return 80000;
}

function stepN4a(ctx, e) {
  const cur = ctx.active;
  if (!cur || cur.tilted) {
    return;
  }
  if (e.event === "BUMPER") {
    cur.base += 1000 * asInt(e.value, 0);
  } else if (e.event === "SPINNER") {
    cur.base += 3000 * asInt(e.value, 0);
  } else if (e.event === "LANE") {
    const key = `${cur.player}:${e.value}`;
    if (!ctx.laneMemory) ctx.laneMemory = new Set();
    if (ctx.laneMemory.has(key)) {
      cur.skill += 5000;
    } else {
      ctx.laneMemory.add(key);
      cur.lanes.add(e.value);
      cur.skill += valueN4a(ctx.laneMemory.size % 3);
    }
  }
}

module.exports = { stepN4a, valueN4a };
