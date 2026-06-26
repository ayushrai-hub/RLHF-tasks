function countRows(runs) {
  return runs.reduce((acc, run) => acc + run.rows.length, 0);
}

module.exports = { countRows };
