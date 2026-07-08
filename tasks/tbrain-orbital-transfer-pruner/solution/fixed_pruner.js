function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function tokenKey(tokens) {
  return [...tokens].sort().join(",");
}

function pathKey(path) {
  return path.join("/");
}

function hasAll(tokens, required) {
  return asArray(required).every((token) => tokens.has(token));
}

function hasNone(tokens, forbidden) {
  return asArray(forbidden).every((token) => !tokens.has(token));
}

function applyTokens(tokens, arc) {
  const next = new Set(tokens);
  for (const token of asArray(arc.consumes)) {
    next.delete(token);
  }
  for (const token of asArray(arc.grants)) {
    next.add(token);
  }
  return next;
}

function targetConstraint(scenario, body) {
  return (scenario.targetConstraints || {})[body] || {};
}

function satisfiesTarget(label, constraint) {
  if (constraint.maxArrival !== undefined && label.arrival > Number(constraint.maxArrival)) return false;
  if (constraint.maxDv !== undefined && label.dv > Number(constraint.maxDv)) return false;
  if (constraint.maxDose !== undefined && label.dose > Number(constraint.maxDose)) return false;
  return hasAll(label.tokens, constraint.requires) && hasNone(label.tokens, constraint.forbids);
}

function isSuperset(left, right) {
  for (const token of right) {
    if (!left.has(token)) return false;
  }
  return true;
}

function sameTokens(left, right) {
  return left.size === right.size && isSuperset(left, right);
}

function dominatesLabel(left, right) {
  const metricsNoWorse =
    left.arrival <= right.arrival && left.dv <= right.dv && left.dose <= right.dose;
  const better =
    left.arrival < right.arrival ||
    left.dv < right.dv ||
    left.dose < right.dose;
  return metricsNoWorse && sameTokens(left.tokens, right.tokens) && better;
}

function dominatesPlan(left, right) {
  const metricsNoWorse =
    left.arrival <= right.arrival && left.dv <= right.dv && left.dose <= right.dose;
  const better = left.arrival < right.arrival || left.dv < right.dv || left.dose < right.dose;
  return left.target === right.target && metricsNoWorse && better;
}

function nextDeparture(arrival, arc) {
  const depart = Number(arc.depart || 0);
  const period = Number(arc.period || 0);
  if (period <= 0 || depart >= arrival) {
    return depart;
  }
  return depart + Math.ceil((arrival - depart) / period) * period;
}

function sortedFrontier(rows) {
  return rows.sort(
    (a, b) =>
      a.target.localeCompare(b.target) ||
      a.dv - b.dv ||
      a.arrival - b.arrival ||
      a.dose - b.dose ||
      pathKey(a.path).localeCompare(pathKey(b.path)),
  );
}

export function computeFrontier(scenario) {
  const targets = new Set(asArray(scenario.targets));
  const byFrom = new Map();
  for (const arc of asArray(scenario.arcs)) {
    if (!byFrom.has(arc.from)) byFrom.set(arc.from, []);
    byFrom.get(arc.from).push(arc);
  }
  for (const arcs of byFrom.values()) {
    arcs.sort((a, b) => String(a.to).localeCompare(String(b.to)) || Number(a.dv || 0) - Number(b.dv || 0));
  }

  const start = {
    body: scenario.origin,
    arrival: Number(scenario.epoch || 0),
    dv: 0,
    dose: 0,
    tokens: new Set(),
    path: [scenario.origin],
  };
  const labelsByBody = new Map([[scenario.origin, [start]]]);
  const queue = [start];
  const finished = [];
  const maxLegs = Number(scenario.maxLegs || 12);

  while (queue.length) {
    queue.sort(
      (a, b) =>
        a.arrival - b.arrival ||
        a.dv - b.dv ||
        a.dose - b.dose ||
        tokenKey(a.tokens).localeCompare(tokenKey(b.tokens)) ||
        pathKey(a.path).localeCompare(pathKey(b.path)),
    );
    const label = queue.shift();
    if (targets.has(label.body) && satisfiesTarget(label, targetConstraint(scenario, label.body))) {
      finished.push(label);
    }
    if (label.path.length > maxLegs) {
      continue;
    }
    for (const arc of byFrom.get(label.body) || []) {
      if (!hasAll(label.tokens, arc.requires) || !hasAll(label.tokens, arc.consumes) || !hasNone(label.tokens, arc.forbids)) continue;
      const launch = nextDeparture(label.arrival, arc);
      const next = {
        body: arc.to,
        arrival: launch + Number(arc.duration || 0),
        dv: label.dv + Number(arc.dv || 0),
        dose: label.dose + Number(arc.dose || 0),
        tokens: applyTokens(label.tokens, arc),
        path: [...label.path, arc.to],
      };
      const labels = labelsByBody.get(next.body) || [];
      if (labels.some((old) => dominatesLabel(old, next))) {
        continue;
      }
      const kept = labels.filter((old) => !dominatesLabel(next, old));
      kept.push(next);
      labelsByBody.set(next.body, kept);
      queue.push(next);
    }
  }

  const rows = finished.map((row) => ({
    target: row.body,
    arrival: row.arrival,
    dv: row.dv,
    dose: row.dose,
    path: row.path,
  }));
  const frontier = [];
  for (const row of sortedFrontier(rows)) {
    if (frontier.some((old) => dominatesPlan(old, row))) {
      continue;
    }
    for (let index = frontier.length - 1; index >= 0; index -= 1) {
      if (dominatesPlan(row, frontier[index])) {
        frontier.splice(index, 1);
      }
    }
    frontier.push(row);
  }
  return { frontier: sortedFrontier(frontier) };
}
