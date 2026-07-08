// Phase Four: Output Canonical Formatter
// Symbol: op_d
// Signature: function op_d(scenarios)

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function op_d(scenarios) {
  const sortedScenarios = [...scenarios];
  
  const formattedScenarios = sortedScenarios.map(s => {
    const cycleNodes = s.cycle_nodes || []; 
    const ordering = s.ordering || [];
    const implicitEdges = s.implicit_edges ? [...s.implicit_edges] : [];
    
    return {
      flags: s.flags,
      cycle_nodes: cycleNodes,
      ordering: ordering,
      implicit_edges: implicitEdges
    };
  });
  
  const scenariosChecked = formattedScenarios.length;
  const cyclicCount = formattedScenarios.filter(s => s.cycle_nodes.length > 0).length;
  const acyclicCount = scenariosChecked - cyclicCount;
  
  // Signature calculation
  const sigParts = formattedScenarios.map(s => {
    if (s.cycle_nodes.length > 0) {
      return `cycle:${s.cycle_nodes.join(',')}`;
    } else {
      return s.ordering.join(',');
    }
  });
  const sigString = sigParts.join(';');
  const signatureHash = crypto.createHash('sha256').update(sigString).digest('hex');
  
  const results = {
    scenarios: formattedScenarios,
    summary: {
      scenarios_checked: scenariosChecked,
      cyclic_count: cyclicCount,
      acyclic_count: acyclicCount,
      signature_hash: signatureHash
    }
  };
  
  // Write output
  const outPath = '/app/output/results.json';
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
  
  return results;
}

module.exports = op_d;
