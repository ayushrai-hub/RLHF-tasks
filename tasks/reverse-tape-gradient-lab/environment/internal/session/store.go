
package session

import (
  "encoding/json"
  "os"

  "gradlab/internal/paths"
)

type Session struct {
  RunCount        int      `json:"run_count"`
  LastFingerprint string   `json:"last_fingerprint"`
  GraphLabels     []string `json:"graph_labels"`
}

func Load() Session {
  b, err := os.ReadFile(paths.SessionPath)
  if err != nil {
    return Session{}
  }
  var s Session
  _ = json.Unmarshal(b, &s)
  return s
}

func Save(s Session) error {
  _ = os.MkdirAll(paths.VarDir, 0o755)
  b, _ := json.MarshalIndent(s, "", "  ")
  return os.WriteFile(paths.SessionPath, append(b, '\n'), 0o644)
}

func ResetVar() {
  _ = os.RemoveAll(paths.VarDir)
  _ = os.MkdirAll(paths.VarDir, 0o755)
}
