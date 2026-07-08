// Decoy Three
// Constructs adjacency and reachability matrices for diagnostic printing.

function buildAdjacencyMatrix(nodes, edges) {
  const size = nodes.length;
  const nodeIndex = {};
  nodes.forEach((n, idx) => {
    nodeIndex[n] = idx;
  });

  const matrix = Array(size).fill(0).map(() => Array(size).fill(0));
  for (const [from, to] of edges) {
    const fIdx = nodeIndex[from];
    const tIdx = nodeIndex[to];
    if (fIdx !== undefined && tIdx !== undefined) {
      matrix[fIdx][tIdx] = 1;
    }
  }
  return matrix;
}

module.exports = { buildAdjacencyMatrix };
