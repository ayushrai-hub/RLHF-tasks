import { advanceCommitIndex, applyCommitted, detectCommitRegression } from './append.js';
import { canGrantVote, isLogUpToDate, tallyElection } from './election.js';
import { RaftNode } from './node.js';
import { majorityAt, isIsolated } from './partition.js';
import { countVotes, hasQuorum } from './quorum.js';
import { detectSplitBrain } from './safety.js';

function buggyCanGrantVote(state, candidateTerm) {
  return candidateTerm >= state.currentTerm;
}

function buggyAdvanceCommit(log, commitIndex) {
  let next = commitIndex;
  for (const entry of log) {
    if (entry.index > commitIndex) {
      next = Math.max(next, entry.index);
    }
  }
  return next;
}

function buggyCountVotes(votes) {
  return votes.filter((v) => v.granted).length;
}

function buildNodes(cluster) {
  const nodes = new Map();
  for (const id of cluster.nodes) {
    nodes.set(id, new RaftNode(id));
  }
  return nodes;
}

function recordTimeline(timeline, phase, node, term, startTick, endTick, role, votes) {
  timeline.push({
    phase,
    node_id: node.id,
    term,
    start_tick: startTick,
    end_tick: endTick,
    role,
    votes_received: votes,
  });
}

function inlineDetectSplitBrain(leadersByTerm) {
  for (const [term, leaders] of leadersByTerm.entries()) {
    const unique = [...new Set(leaders)];
    if (unique.length > 1) {
      return { detected: true, term, leaders: unique };
    }
  }
  return { detected: false, term: 0, leaders: [] };
}

export function simulate(bundle, mode) {
  const cluster = bundle.cluster;
  const nodes = buildNodes(cluster);
  const leadersByTerm = new Map();
  const timeline = [];
  const votes = [];
  let electionRounds = 0;
  const ordered = [...bundle.commands].sort((a, b) => {
    const dt = a.tick - b.tick;
    if (dt !== 0) {
      return dt;
    }
    if (a.term !== b.term) {
      return a.term - b.term;
    }
    if (a.index !== b.index) {
      return a.index - b.index;
    }
    return a.nodeId.localeCompare(b.nodeId);
  });

  for (const cmd of ordered) {
    const node = nodes.get(cmd.nodeId);
    if (!node) {
      continue;
    }
    const primary = nodes.get('n1');
    const majority = majorityAt(bundle.partitions, cmd.tick);
    const isolated = isIsolated(bundle.partitions, cmd.tick, cmd.nodeId);

    if (mode === 'safe' && majority && !majority.has(cmd.nodeId)) {
      continue;
    }

    if (cmd.term > node.currentTerm) {
      electionRounds += 1;
      const candidateLastIndex = node.lastLogIndex;
      const candidateLastTerm = node.lastLogTerm;
      node.becomeCandidate(cmd.term);
      let granted = 1;
      for (const peer of cluster.nodes) {
        if (peer === cmd.nodeId) {
          continue;
        }
        const voter = nodes.get(peer);
        const peerIsolated = isIsolated(bundle.partitions, cmd.tick, peer);
        if (majority && (!majority.has(peer) || peerIsolated)) {
          continue;
        }
        let ok;
        if (mode === 'buggy') {
          ok = buggyCanGrantVote(voter, cmd.term);
        } else {
          voter.pendingCandidate = cmd.nodeId;
          ok = canGrantVote(voter, cmd.term, candidateLastIndex, candidateLastTerm);
        }
        if (ok) {
          voter.votedFor = cmd.nodeId;
          granted += 1;
          votes.push({ candidate: cmd.nodeId, granted: true, term: cmd.term, tick: cmd.tick });
        }
      }
      const quorumCount = mode === 'buggy'
        ? buggyCountVotes(votes.filter((v) => v.candidate === cmd.nodeId && v.tick === cmd.tick))
        : countVotes(votes.filter((v) => v.candidate === cmd.nodeId && v.tick === cmd.tick), cmd.term);
      if (hasQuorum(quorumCount, cluster.quorumSize) || (mode === 'buggy' && isolated && granted >= 2)) {
        node.becomeLeader(cmd.term);
        const list = leadersByTerm.get(cmd.term) ?? [];
        list.push(cmd.nodeId);
        leadersByTerm.set(cmd.term, list);
        recordTimeline(timeline, mode === 'buggy' ? 'before' : 'after', node, cmd.term, cmd.tick, cmd.tick, 'leader', quorumCount);
      }
    }

    primary.appendEntry(cmd);
    for (const n of nodes.values()) {
      const commit = mode === 'buggy'
        ? buggyAdvanceCommit(n.log, n.commitIndex)
        : advanceCommitIndex(n.log, n.currentTerm, n.commitIndex);
      const regression = detectCommitRegression(n.log, commit);
      if (!regression.ok && mode === 'safe') {
        return { issue: regression, metrics: null, timeline, applied: new Map() };
      }
      n.commitIndex = commit;
    }
  }

  const leaderNode = nodes.get('n1');
  const commitIndex = leaderNode ? leaderNode.commitIndex : 0;
  const log = leaderNode ? leaderNode.log : [];
  const applied = applyCommitted(log, commitIndex);
  const split = mode === 'buggy' ? inlineDetectSplitBrain(leadersByTerm) : detectSplitBrain(leadersByTerm);

  const metrics = {
    leaders_observed: [...new Set([...leadersByTerm.values()].flat())].length,
    split_brain_detected: split.detected,
    commands_committed: applied.size,
    commands_lost: mode === 'buggy' && split.detected ? 1 : 0,
    election_rounds: electionRounds,
    commit_index_max: commitIndex,
    linearizable_keys: applied.size,
  };

  return { metrics, timeline, applied, leadersByTerm, split };
}

export function buildCommandTrace(applied, stages = ['election', 'append', 'quorum', 'apply']) {
  const entries = [];
  for (const [key, value] of applied.entries()) {
    entries.push({
      key,
      index: 0,
      term: 0,
      value,
      stages: [...stages].sort(),
    });
  }
  for (const entry of entries) {
    const source = [...applied.keys()].indexOf(entry.key);
    entry.index = source + 1;
    entry.term = 1;
  }
  entries.sort((a, b) => a.key.localeCompare(b.key));
  return entries;
}
