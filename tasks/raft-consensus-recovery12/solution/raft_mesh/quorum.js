export function countVotes(votes, currentTerm) {
  let granted = 0;
  for (const vote of votes) {
    if (!vote.granted) {
      continue;
    }
    if (vote.term !== currentTerm) {
      continue;
    }
    granted += 1;
  }
  return granted;
}

export function hasQuorum(granted, quorumSize) {
  return granted >= quorumSize;
}
