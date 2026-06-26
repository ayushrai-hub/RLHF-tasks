function add(map, key, amount) {
  map[key] = (map[key] || 0) + amount;
}

function ensure(map, key, fallback) {
  if (!Object.prototype.hasOwnProperty.call(map, key)) {
    map[key] = fallback();
  }
  return map[key];
}

function asInt(value, fallback = 0) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

module.exports = { add, ensure, asInt };
