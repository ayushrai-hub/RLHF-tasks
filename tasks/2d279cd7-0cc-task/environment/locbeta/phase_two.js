// Phase Two: Condition Evaluator
// Symbol: op_b
// Signature: function op_b(expr, flags)

function op_b(expr, flags) {
  if (!expr) return true;

  const cleaned = expr.replace(/\s+/g, "");
  let index = 0;

  function parseFactor() {
    let negate = false;
    while (index < cleaned.length && cleaned[index] === "!") {
      negate = !negate;
      index++;
    }

    let val;
    if (cleaned[index] === "(") {
      index++;
      val = parseExpr();
      if (cleaned[index] === ")") {
        index++;
      }
    } else {
      let varName = "";
      while (index < cleaned.length && /[a-zA-Z0-9_]/.test(cleaned[index])) {
        varName += cleaned[index];
        index++;
      }
      val = !!flags[varName];
      if (!(varName in flags)) {
        val = true;
      }
    }

    return negate ? !val : val;
  }

  function parseExpr() {
    let val = parseFactor();
    while (index < cleaned.length && (cleaned[index] === "|" || cleaned[index] === "&")) {
      const op = cleaned[index++];
      const nextVal = parseFactor();
      val = op === "&" ? val && nextVal : val || nextVal;
    }
    return val;
  }

  return parseExpr();
}

module.exports = op_b;
