#!/bin/bash
set -euo pipefail

cat > /app/environment/starfield-switchboard/t6r.cjs <<'EOF'
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
  const saved = e.event === "DRAIN" && e.ts - cur.launchTs <= 12 && !cur.tilted;
  if (saved) {
    ctx.savedDrains += 1;
    return;
  }
  const lockCount = ctx.locks[cur.player] || 0;
  const bonus = cur.tilted ? 0 : (cur.lanes.size * 10000 + cur.targets.size * 15000 + lockCount * 25000);
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
    saved_drain: 0,
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
  if (e.event === "MULT" && !ctx.active.tilted) {
    ctx.active.multiplier = Math.max(1, Math.min(3, asInt(e.value, 1)));
  } else if (e.event === "TILT_WARN") {
    ctx.active.warnings += 1;
    if (ctx.active.warnings >= 2) {
      ctx.active.tilted = true;
    }
  } else if (e.event === "DRAIN") {
    finishRow(ctx, e);
  }
}

module.exports = { newState, stepT6r, finishRow };
EOF

cat > /app/environment/starfield-switchboard/n4a.cjs <<'EOF'
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
    cur.base += 3000 * asInt(e.value, 0) * cur.multiplier;
  } else if (e.event === "LANE") {
    if (cur.lanes.has(e.value)) {
      cur.skill += 5000;
    } else {
      cur.skill += valueN4a(cur.lanes.size);
      cur.lanes.add(e.value);
    }
  }
}

module.exports = { stepN4a, valueN4a };
EOF

cat > /app/environment/starfield-switchboard/c3p.cjs <<'EOF'
function modeDelta(cur, value) {
  if (!cur.modeOpen) {
    return 25000;
  }
  if (cur.targets.has(value)) {
    return 10000;
  }
  cur.targets.add(value);
  const targetScore = 75000 * cur.multiplier;
  if (cur.targets.size >= 4) {
    cur.modeOpen = false;
    return targetScore + 300000;
  }
  return targetScore;
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
EOF

cat > /app/environment/starfield-switchboard/l8m.cjs <<'EOF'
function majorDelta(ctx, cur) {
  if (!ctx.multi[cur.player] || !ctx.lit[cur.player]) {
    return 0;
  }
  ctx.jackpotCount += 1;
  ctx.lit[cur.player] = false;
  return 500000 * cur.multiplier;
}

function stepL8m(ctx, e) {
  const cur = ctx.active;
  if (!cur || cur.tilted) {
    return;
  }
  if (e.event === "LOCK") {
    ctx.locks[cur.player] = Math.min(2, (ctx.locks[cur.player] || 0) + 1);
    cur.base += 50000;
    if (ctx.locks[cur.player] >= 2) {
      ctx.multi[cur.player] = true;
      ctx.lit[cur.player] = true;
    }
  } else if (e.event === "SIDEWALL") {
    if (ctx.multi[cur.player]) {
      ctx.lit[cur.player] = true;
    }
  } else if (e.event === "JACKPOT") {
    cur.jackpot += majorDelta(ctx, cur);
  }
}

module.exports = { stepL8m, majorDelta };
EOF

cat > /app/environment/starfield-switchboard/s9x.cjs <<'EOF'
const crypto = require("crypto");

function digest(text, n) {
  return crypto.createHash("sha256").update(text).digest("hex").slice(0, n);
}

function foldS9x(row) {
  const material = [
    row.run_id,
    row.ball,
    row.player,
    row.base_score,
    row.skill_value,
    row.mode_value,
    row.jackpot_value,
    row.bonus_value,
    row.tilt_mark,
    row.saved_drain,
    row.row_total
  ].join("|");
  return digest(material, 16);
}

module.exports = { foldS9x, digest };
EOF

cat > /app/environment/starfield-switchboard/report.cjs <<'EOF'
const fs = require("fs");
const path = require("path");
const { foldS9x, digest } = require("./s9x.cjs");

function orderPlayers(totals) {
  return Object.keys(totals).sort((a, b) => {
    const byScore = totals[b] - totals[a];
    return byScore || a.localeCompare(b);
  });
}

function emitReport(results, outPath) {
  const runs = results.map((item) => {
    const rows = item.rows.map((row) => {
      const enriched = { run_id: item.id, ...row };
      return { ...row, row_digest: foldS9x(enriched) };
    });
    return {
      id: item.id,
      rows,
      player_totals: item.totals,
      final_order: orderPlayers(item.totals),
      jackpot_count: item.jackpotCount,
      saved_drains: item.savedDrains,
      tilt_balls: item.tiltBalls,
      run_digest: digest(rows.map((row) => row.row_digest).join(":"), 20)
    };
  });
  const ordered = [...runs].sort((a, b) => a.id.localeCompare(b.id));
  const chain = digest(ordered.map((r) => r.run_digest).join(":"), 24);
  const report = {
    table: "constellation-kiosk",
    runs,
    rollup: {
      run_count: runs.length,
      total_jackpots: runs.reduce((acc, r) => acc + r.jackpot_count, 0),
      saved_drains: runs.reduce((acc, r) => acc + r.saved_drains, 0),
      tilt_balls: runs.reduce((acc, r) => acc + r.tilt_balls, 0),
      chain_digest: chain,
      audit_latch: process.env.SF_AUDIT_STRICT === "1" ? "sealed" : "open"
    }
  };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  return report;
}

module.exports = { emitReport, orderPlayers };
EOF

npm run build --prefix /app/environment
/app/ops/sfdesk
