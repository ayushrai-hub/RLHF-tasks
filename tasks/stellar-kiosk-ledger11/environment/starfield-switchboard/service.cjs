function serviceLabel(code) {
  return String(code || "").trim().toUpperCase();
}

module.exports = { serviceLabel };
