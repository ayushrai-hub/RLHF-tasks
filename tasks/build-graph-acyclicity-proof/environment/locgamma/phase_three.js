// Phase Three: Joint SAT Cycle Checker
// Symbol: op_c
// Signature: function op_c(edges, conditions)

const op_b = require('../locbeta/phase_two');

function extractFlags(cond) {
  if (!cond) return [];
  const matches = cond.match(/[a-zA-Z0-9_]+/g);
  return matches ? Array.from(new Set(matches)) : [];
}

function isIndependentlySatisfiable(cond) {
  if (!cond || cond.trim() === "") return true;
  const flags = extractFlags(cond);
  const n = flags.length;
  for (let i = 0; i < (1 << n); i++) {
    const flagVals = {};
    for (let j = 0; j < n; j++) {
      flagVals[flags[j]] = ((i >> j) & 1) === 1;
    }
    if (op_b(cond, flagVals)) {
      return true;
    }
  }
  return false;
}

function findAllCycles(edges) {
  const adj = {};
  for (const [u, v] of edges) {
    if (!adj[u]) adj[u] = [];
    adj[u].push(v);
  }
  
  const cycles = [];
  const path = [];
  const visited = new Set();
  
  function dfs(node, startNode) {
    path.push(node);
    visited.add(node);
    
    const neighbors = adj[node] || [];
    for (const neighbor of neighbors) {
      if (neighbor === startNode) {
        const cycle = [...path];
        const minNode = cycle.reduce((min, n) => n < min ? n : min, cycle[0]);
        if (startNode === minNode) {
          cycles.push(cycle);
        }
      } else if (!visited.has(neighbor)) {
        dfs(neighbor, startNode);
      }
    }
    
    path.pop();
    visited.delete(node);
  }
  
  const nodes = Array.from(new Set(edges.flat()));
  for (const node of nodes) {
    dfs(node, node);
  }
  
  return cycles;
}

function op_c(edges, conditions) {
  const cycles = findAllCycles(edges);
  const validCycles = [];
  
  for (const cycle of cycles) {
    let independentlySatisfiable = true;
    for (let i = 0; i < cycle.length; i++) {
      const u = cycle[i];
      const v = cycle[(i + 1) % cycle.length];
      const edgeKey = `${u}->${v}`;
      const cond = conditions[edgeKey];
      
      if (cond && !isIndependentlySatisfiable(cond)) {
        independentlySatisfiable = false;
        break;
      }
    }
    if (independentlySatisfiable) {
      validCycles.push(cycle);
    }
  }
  return validCycles;
}

module.exports = op_c;
