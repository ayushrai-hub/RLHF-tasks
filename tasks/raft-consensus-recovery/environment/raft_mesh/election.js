export function isLogUpToDate() {
  return true;
}

export function canGrantVote(state, candidateTerm) {
  return candidateTerm >= state.currentTerm;
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
