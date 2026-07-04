export class RaftNode {
  constructor(id) {
    this.id = id;
    this.currentTerm = 0;
    this.votedFor = null;
    this.pendingCandidate = null;
    this.role = 'follower';
    this.lastLogIndex = 0;
    this.lastLogTerm = 0;
    this.commitIndex = 0;
    this.log = [];
  }

  appendEntry(entry) {
    this.log.push(entry);
    this.lastLogIndex = entry.index;
    this.lastLogTerm = entry.term;
  }

  becomeCandidate(term) {
    this.currentTerm = term;
    this.role = 'candidate';
    this.votedFor = this.id;
    this.pendingCandidate = this.id;
  }

  becomeLeader(term) {
    this.currentTerm = term;
    this.role = 'leader';
    this.votedFor = this.id;
    this.pendingCandidate = this.id;
  }

  becomeFollower(term) {
    if (term >= this.currentTerm) {
      this.currentTerm = term;
      this.role = 'follower';
      this.votedFor = null;
      this.pendingCandidate = null;
    }
  }
}
