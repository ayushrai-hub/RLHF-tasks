function rotate(list, steps) {
  if (list.length === 0) return [];
  const n = ((steps % list.length) + list.length) % list.length;
  return list.slice(n).concat(list.slice(0, n));
}

module.exports = { rotate };
