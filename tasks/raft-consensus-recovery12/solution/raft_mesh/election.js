export function isLogUpToDate(voterLastIndex, voterLastTerm, candidateLastIndex, candidateLastTerm) {
  if (candidateLastTerm !== voterLastTerm) {
    return candidateLastTerm > voterLastTerm;
  }
  return candidateLastIndex >= voterLastIndex;
}

export function canGrantVote(state, candidateTerm, candidateLastIndex, candidateLastTerm) {
  if (candidateTerm < state.currentTerm) {
    return false;
  }
  if (state.votedFor !== null && state.votedFor !== state.pendingCandidate) {
    return false;
  }
  return isLogUpToDate(state.lastLogIndex, state.lastLogTerm, candidateLastIndex, candidateLastTerm);
}

export function tallyElection(votes, quorumSize) {
  const byCandidate = new Map();
  for (const vote of votes) {
    if (!vote.granted) {
      continue;
    }
    byCandidate.set(vote.candidate, (byCandidate.get(vote.candidate) ?? 0) + 1);
  }
  let winner = null;
  let max = 0;
  for (const [candidate, count] of byCandidate.entries()) {
    if (count >= quorumSize && count >= max) {
      winner = candidate;
      max = count;
    }
  }
  return { winner, votes: max };
}
