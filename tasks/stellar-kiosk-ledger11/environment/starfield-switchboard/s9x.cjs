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
    row.row_total
  ].join("|");
  return digest(material, 16);
}

module.exports = { foldS9x, digest };
