// Phase One: Parallel Merge Edge Resolution
// Symbol: op_a
// Signature: function op_a(branches, sharedResources)

function op_a(branches, sharedResources) {
  const edges = [];

  for (let i = 0; i < branches.length; i++) {
    const branch1 = branches[i];
    for (let j = i + 1; j < branches.length; j++) {
      const branch2 = branches[j];
      for (const t1 of branch1) {
        for (const t2 of branch2) {
          if (t1.resources && t2.resources && t1.resources[0] === t2.resources[0]) {
            const from = t1.id < t2.id ? t1.id : t2.id;
            const to = t1.id < t2.id ? t2.id : t1.id;
            if (!edges.some((e) => e.from === from && e.to === to)) {
              edges.push({ from, to });
            }
          }
        }
      }
    }
  }

  return edges;
}

module.exports = op_a;
