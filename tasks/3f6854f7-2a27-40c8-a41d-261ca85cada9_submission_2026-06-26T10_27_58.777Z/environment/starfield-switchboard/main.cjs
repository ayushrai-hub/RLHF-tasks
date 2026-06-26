const { parseArgs, readIds, readRun } = require("./reader.cjs");
const { newState, stepT6r } = require("./t6r.cjs");
const { stepN4a } = require("./n4a.cjs");
const { stepC3p } = require("./c3p.cjs");
const { stepL8m } = require("./l8m.cjs");
const { emitReport } = require("./report.cjs");

function applyEvent(ctx, e) {
  stepT6r(ctx, e);
  stepN4a(ctx, e);
  stepC3p(ctx, e);
  stepL8m(ctx, e);
}

function runRun(id, dirPath) {
  const ctx = newState();
  const events = readRun(dirPath, id);
  for (const e of events) {
    applyEvent(ctx, e);
  }
  return {
    id,
    rows: ctx.rows,
    totals: ctx.totals,
    jackpotCount: ctx.jackpotCount,
    savedDrains: ctx.savedDrains,
    tiltBalls: ctx.tiltBalls
  };
}

function main(argv) {
  const args = parseArgs(argv);
  const ids = readIds(args.ids);
  const results = ids.map((id) => runRun(id, args.sets));
  emitReport(results, args.out);
}

if (require.main === module) {
  main(process.argv.slice(2));
}

module.exports = { main, runRun, applyEvent };
