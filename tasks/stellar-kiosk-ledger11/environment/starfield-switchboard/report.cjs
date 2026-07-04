const fs = require("fs");
const path = require("path");
const { foldS9x, digest } = require("./s9x.cjs");

function orderPlayers(totals) {
  return Object.keys(totals).sort((a, b) => {
    const byScore = totals[b] - totals[a];
    return byScore || b.localeCompare(a);
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
  const chain = digest(runs.map((r) => r.run_digest).join(":"), 24);
  const report = {
    table: "constellation-kiosk",
    runs,
    rollup: {
      run_count: runs.length,
      total_jackpots: runs.reduce((acc, r) => acc + r.jackpot_count, 0),
      saved_drains: runs.reduce((acc, r) => acc + r.saved_drains, 0),
      tilt_balls: runs.reduce((acc, r) => acc + r.tilt_balls, 0),
      chain_digest: chain,
      audit_latch: process.env.SF_AUDIT_STRICT ? "closed" : "open"
    }
  };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  return report;
}

module.exports = { emitReport, orderPlayers };
