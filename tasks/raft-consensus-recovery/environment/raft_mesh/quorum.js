export function countVotes(votes) {
  return votes.filter((v) => v.granted).length;
}

export function hasQuorum(granted, quorumSize) {
  return granted >= quorumSize;
}
