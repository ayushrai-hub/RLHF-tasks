
package bridge

import (
  "bytes"
  "encoding/json"
  "os/exec"
)

func RunTape(mode string, payload map[string]any) (map[string]any, error) {
  payload["mode"] = mode
  b, _ := json.Marshal(payload)
  cmd := exec.Command("/app/environment/build/corevm")
  cmd.Stdin = bytes.NewReader(b)
  out, err := cmd.Output()
  if err != nil {
    return nil, err
  }
  var resp map[string]any
  return resp, json.Unmarshal(out, &resp)
}
