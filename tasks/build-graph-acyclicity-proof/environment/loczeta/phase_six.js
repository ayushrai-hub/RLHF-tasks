// Phase Six: Valid Scenario Enumeration
// Symbol: op_g
// Signature: function op_g(flagsList, constraints, evalConstraint)

function op_g(flagsList, constraints, evalConstraint) {
  const n = flagsList.length;
  const validScenarios = [];

  for (let i = 0; i < (1 << n); i++) {
    const flagsObj = {};
    for (let j = 0; j < n; j++) {
      flagsObj[flagsList[j]] = ((i >> (n - 1 - j)) & 1) === 1;
    }

    let isValid = true;
    for (const constraint of constraints) {
      if (!evalConstraint(constraint, flagsObj)) {
        isValid = false;
        break;
      }
    }

    if (isValid) {
      validScenarios.push(flagsObj);
    }
  }

  return validScenarios;
}

module.exports = op_g;
