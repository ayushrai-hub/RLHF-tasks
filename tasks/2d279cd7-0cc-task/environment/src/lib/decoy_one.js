// Decoy One
// Buffers task nodes and exports them to dot graph format for visualization.

function exportToDot(nodes, edges) {
  let dot = "digraph BuildGraph {\n";
  for (const node of nodes) {
    dot += `  "${node}" [shape=box];\n`;
  }
  for (const [from, to] of edges) {
    dot += `  "${from}" -> "${to}";\n`;
  }
  dot += "}\n";
  return dot;
}

module.exports = { exportToDot };
