function blankCard(id) {
  return {
    id,
    started_at: new Date(0).toISOString(),
    machine: "league"
  };
}

module.exports = { blankCard };
