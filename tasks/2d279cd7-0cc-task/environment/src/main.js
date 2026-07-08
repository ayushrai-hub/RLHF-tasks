const fs = require('fs');
const path = require('path');
const utils = require('./lib/utils');
const phaseOne = require('../localpha/phase_one');
const phaseTwo = require('../locbeta/phase_two');
const phaseThree = require('../locgamma/phase_three');
const phaseFour = require('../locdelta/phase_four');
const { op_e, op_f, enumerateScenarios } = require('../locepsilon/phase_five');

const decoy_one = require('./lib/decoy_one');
const decoy_two = require('./lib/decoy_two');
const decoy_three = require('./lib/decoy_three');
const decoy_four = require('./lib/decoy_four');

function main() {
  const inputPath = path.join(__dirname, '..', 'data', 'input.json');
  const extraPath = path.join(__dirname, '..', 'data', 'extra.json');
  const outputPath = path.join(__dirname, '..', 'output', 'results.json');

  let baseConfig = utils.readJsonFile(inputPath);
  if (!baseConfig) {
    console.error("Error: input.json not found or invalid");
    process.exit(1);
  }

  const extraConfig = utils.readJsonFile(extraPath);
  const config = op_e(baseConfig, extraConfig);
  const mergedDigest = op_f('digest', config);
  const baseDigest = op_f('digest', baseConfig);

  const ckpt = op_f('read');
  let scenarioOffset = 0;
  if (ckpt.digest === baseDigest && ckpt.offset > 0) {
    scenarioOffset = ckpt.offset;
  }

  const flagsList = config.flags || [];
  const constraints = config.constraints || [];
  const tasks = config.tasks || [];
  const parallelGroups = config.parallel_groups || [];

  const validScenarios = enumerateScenarios(flagsList, constraints, (expr, flagsObj) => phaseTwo(expr, flagsObj));

  const allPossibleEdges = [];
  const edgeConditions = {};

  function addPossibleEdge(from, to, cond) {
    const edgeKey = `${from}->${to}`;
    if (!edgeConditions[edgeKey]) {
      allPossibleEdges.push([from, to]);
      edgeConditions[edgeKey] = cond || "";
    }
  }

  for (const t of tasks) {
    if (t.depends_on) {
      for (const dep of t.depends_on) {
        addPossibleEdge(dep.task, t.id, dep.condition);
      }
    }
  }

  for (const group of parallelGroups) {
    for (const branch of group.branches) {
      for (let i = 0; i < branch.length - 1; i++) {
        addPossibleEdge(branch[i], branch[i + 1], "");
      }
      if (branch.length > 0) {
        addPossibleEdge(branch[branch.length - 1], group.merge_node, "");
      }
    }

    for (let i = 0; i < group.branches.length; i++) {
      for (let j = i + 1; j < group.branches.length; j++) {
        const b1 = group.branches[i];
        const b2 = group.branches[j];
        for (const id1 of b1) {
          for (const id2 of b2) {
            const t1 = tasks.find((t) => t.id === id1);
            const t2 = tasks.find((t) => t.id === id2);
            if (t1 && t2 && t1.resources && t2.resources) {
              if (t1.resources[0] === t2.resources[0]) {
                const from = t1.id < t2.id ? t1.id : t2.id;
                const to = t1.id < t2.id ? t2.id : t1.id;
                addPossibleEdge(from, to, "");
              }
            }
          }
        }
      }
    }
  }

  const satisfiableCycles = phaseThree(allPossibleEdges, edgeConditions);

  function isCycleActive(cycle, activeEdgesSet) {
    for (let i = 0; i < cycle.length; i++) {
      const u = cycle[i];
      const v = cycle[(i + 1) % cycle.length];
      if (!activeEdgesSet.has(`${u}->${v}`)) {
        return false;
      }
    }
    return true;
  }

  const scenarioResults = [];
  const scenariosToProcess = validScenarios.slice(scenarioOffset);

  for (const flags of scenariosToProcess) {
    const activeEdges = [];
    const activeEdgesSet = new Set();

    function addActiveEdge(from, to) {
      const edge = `${from}->${to}`;
      if (!activeEdgesSet.has(edge)) {
        activeEdges.push([from, to]);
        activeEdgesSet.add(edge);
      }
    }

    for (const t of tasks) {
      if (t.depends_on) {
        for (const dep of t.depends_on) {
          if (phaseTwo(dep.condition, flags)) {
            addActiveEdge(dep.task, t.id);
          }
        }
      }
    }

    for (const group of parallelGroups) {
      for (const branch of group.branches) {
        for (let i = 0; i < branch.length - 1; i++) {
          addActiveEdge(branch[i], branch[i + 1]);
        }
        if (branch.length > 0) {
          addActiveEdge(branch[branch.length - 1], group.merge_node);
        }
      }
    }

    let scenarioImplicitEdges = [];
    for (const group of parallelGroups) {
      const branchesOfTasks = group.branches.map((branchIds) => {
        return branchIds.map((id) => {
          const t = tasks.find((x) => x.id === id);
          return t || { id, resources: [] };
        });
      });
      const resolved = phaseOne(branchesOfTasks, []);
      scenarioImplicitEdges = [...scenarioImplicitEdges, ...resolved];
    }

    const uniqueImplicit = [];
    for (const edge of scenarioImplicitEdges) {
      if (!uniqueImplicit.some((e) => e.from === edge.from && e.to === edge.to)) {
        uniqueImplicit.push(edge);
      }
    }
    uniqueImplicit.sort((e1, e2) => {
      if (e1.from !== e2.from) return e1.from < e2.from ? -1 : 1;
      return e1.to < e2.to ? -1 : 1;
    });

    for (const edge of uniqueImplicit) {
      addActiveEdge(edge.from, edge.to);
    }

    const activeSatisfiableCycles = satisfiableCycles.filter((cycle) =>
      isCycleActive(cycle, activeEdgesSet)
    );

    let cycleNodes = [];
    let ordering = [];

    if (activeSatisfiableCycles.length > 0) {
      const nodesSet = new Set();
      for (const cycle of activeSatisfiableCycles) {
        for (const node of cycle) {
          nodesSet.add(node);
        }
      }
      cycleNodes = Array.from(nodesSet).sort();
    } else {
      const allNodes = Array.from(new Set(tasks.map((t) => t.id)));
      const inDegree = {};
      const adj = {};
      for (const node of allNodes) {
        inDegree[node] = 0;
        adj[node] = [];
      }

      for (const [from, to] of activeEdges) {
        if (adj[from] && !adj[from].includes(to)) {
          adj[from].push(to);
          inDegree[to] = (inDegree[to] || 0) + 1;
        }
      }

      const zeroInDegree = allNodes.filter((node) => inDegree[node] === 0);
      zeroInDegree.sort();

      while (zeroInDegree.length > 0) {
        const u = zeroInDegree.shift();
        ordering.push(u);
        const neighbors = adj[u] || [];
        for (const v of neighbors) {
          inDegree[v]--;
          if (inDegree[v] === 0) {
            zeroInDegree.push(v);
          }
        }
      }

      if (ordering.length < allNodes.length) {
        const remainingNodes = allNodes.filter((node) => !ordering.includes(node));
        cycleNodes = remainingNodes.sort();
        ordering = [];
      }
    }

    scenarioResults.push({
      flags: flags,
      cycle_nodes: cycleNodes,
      ordering: ordering,
      implicit_edges: uniqueImplicit,
    });
  }

  op_f('write', { offset: validScenarios.length, digest: baseDigest });

  const finalReport = phaseFour(scenarioResults);

  utils.writeJsonFile(outputPath, finalReport);
  console.log("Verification report written successfully to /app/output/results.json");
}

if (require.main === module) {
  main();
}

module.exports = main;
