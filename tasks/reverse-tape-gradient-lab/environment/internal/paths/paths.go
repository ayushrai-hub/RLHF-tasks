
package paths

const (
  Root       = "/app/environment"
  BuildDir   = "/app/environment/build"
  OutputDir  = "/app/output"
  VarDir     = "/app/var/grad"
  ReportPath = "/app/output/gradient_report.json"
  CSVPath    = "/app/output/node_trace.csv"
  JournalPath = "/app/output/pass_journal.jsonl"
  SessionPath = "/app/var/grad/session.json"
  PoolPath   = "/app/var/grad/pool_state.json"
  EpochPath  = "/app/var/grad/tape_epoch.json"
  CheckpointPath = "/app/var/grad/checkpoint.json"
)
