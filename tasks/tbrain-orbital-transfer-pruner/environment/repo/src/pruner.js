function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function nextArrival(label, arc) {
  const depart = Number(arc.depart || 0);
  const period = Number(arc.period || 0);
  const launch = period > 0 && depart < label.arrival ? depart + period : depart;
  return launch + Number(arc.duration || 0);
}

function keyFor(label) {
  return `${label.body}:${label.dv}`;
}

export function computeFrontier(scenario) {
  const targets = new Set(asArray(scenario.targets));
  const byFrom = new Map();
  for (const arc of asArray(scenario.arcs)) {
    if (!byFrom.has(arc.from)) byFrom.set(arc.from, []);
    byFrom.get(arc.from).push(arc);
  }

  const start = {
    body: scenario.origin,
    arrival: Number(scenario.epoch || 0),
    dv: 0,
    dose: 0,
    tokens: new Set(),
    path: [scenario.origin],
  };
  const queue = [start];
  const seen = new Map([[keyFor(start), start]]);
  const frontier = [];

  while (queue.length) {
    queue.sort((a, b) => a.arrival - b.arrival || a.dv - b.dv || a.path.join("/").localeCompare(b.path.join("/")));
    const label = queue.shift();
    if (targets.has(label.body)) {
      frontier.push(label);
    }
    for (const arc of byFrom.get(label.body) || []) {
      const requires = new Set(asArray(arc.requires));
      if ([...requires].some((token) => !label.tokens.has(token))) continue;
      const next = {
        body: arc.to,
        arrival: nextArrival(label, arc),
        dv: label.dv + Number(arc.dv || 0),
        dose: label.dose + Number(arc.dose || 0),
        tokens: new Set([...label.tokens, ...asArray(arc.grants)]),
        path: [...label.path, arc.to],
      };
      const key = keyFor(next);
      const old = seen.get(key);
      if (!old || next.arrival < old.arrival || next.dose < old.dose) {
        seen.set(key, next);
        queue.push(next);
      }
    }
  }

  return {
    frontier: frontier
      .map((row) => ({
        target: row.body,
        arrival: row.arrival,
        dv: row.dv,
        dose: row.dose,
        path: row.path,
      }))
      .sort((a, b) => a.target.localeCompare(b.target) || a.dv - b.dv || a.arrival - b.arrival),
  };
}
