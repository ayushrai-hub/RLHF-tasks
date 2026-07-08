#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/environment/build /app/output /app/var/grad

cat > /app/environment/xk9/src/backward.rs <<'RS'
use crate::ops::{broadcast_shapes, broadcast_to, data_of, num, reduce_sum, shape_of, size};
use serde_json::{json, Map, Value};
use std::collections::HashMap;

fn reduce_broadcast(grad: &[f64], grad_shape: &[usize], target: &[usize]) -> Vec<f64> {
    if grad_shape == target {
        return grad.to_vec();
    }
    let mut work = grad.to_vec();
    let mut work_shape = grad_shape.to_vec();
    let max_rank = work_shape.len().max(target.len());
    let mut axes: Vec<i64> = Vec::new();
    for i in 0..max_rank {
        let gi = work_shape.len().saturating_sub(1 + i);
        let ti = target.len().saturating_sub(1 + i);
        let gdim = if i < work_shape.len() { work_shape[work_shape.len() - 1 - i] } else { 1 };
        let tdim = if i < target.len() { target[target.len() - 1 - i] } else { 1 };
        if gdim > tdim {
            axes.push(gi as i64);
        }
    }
    if !axes.is_empty() {
        let (reduced, new_shape) = reduce_sum(&work, &work_shape, &axes);
        work = reduced;
        work_shape = new_shape;
    }
    if work_shape == target {
        return work;
    }
    broadcast_to(&work, &work_shape, target)
}

fn acc_grad(grads: &mut HashMap<String, Vec<f64>>, key: &str, add: Vec<f64>) {
    if let Some(existing) = grads.get(key) {
        let mut out = existing.clone();
        if add.len() > out.len() {
            out.resize(add.len(), 0.0);
        }
        for (i, v) in add.iter().enumerate() {
            if i < out.len() {
                out[i] += v;
            }
        }
        grads.insert(key.to_string(), out);
    } else {
        grads.insert(key.to_string(), add);
    }
}

pub fn run_backward(input: &Value) -> Value {
    let graph = input.get("graph").unwrap_or(input);
    let empty = json!({});
    let forward = input.get("forward").unwrap_or(&empty);
    let values = forward.get("values").and_then(|v| v.as_object()).cloned().unwrap_or_default();
    let shapes_val = forward.get("shapes").and_then(|v| v.as_object()).cloned().unwrap_or_default();
    let mut shapes: HashMap<String, Vec<usize>> = HashMap::new();
    for (k, v) in shapes_val {
        shapes.insert(k.clone(), shape_of(&v));
    }

    let loss_id = graph.get("loss").and_then(|v| v.as_str()).unwrap_or("out");
    let mut grads: HashMap<String, Vec<f64>> = HashMap::new();
    let loss_shape = shapes.get(loss_id).cloned().unwrap_or(vec![1]);
    let mut seed = vec![0.0; size(&loss_shape)];
    if !seed.is_empty() {
        seed[0] = 1.0;
    }
    grads.insert(loss_id.to_string(), seed);

    let nodes: Vec<Value> = graph
        .get("nodes")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default()
        .into_iter()
        .rev()
        .collect();

    let mut trace = Vec::new();
    for node in nodes {
        let id = node.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let op = node.get("op").and_then(|v| v.as_str()).unwrap_or("");
        let inputs: Vec<String> = node
            .get("inputs")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().filter_map(|x| x.as_str().map(str::to_string)).collect())
            .unwrap_or_default();
        let gout = match grads.get(&id) {
            Some(v) => v.clone(),
            None => continue,
        };
        match op {
            "add" => {
                let sa = shapes.get(&inputs[0]).cloned().unwrap_or_default();
                let sb = shapes.get(&inputs[1]).cloned().unwrap_or_default();
                let out_shape = broadcast_shapes(&sa, &sb).unwrap_or(sa.clone());
                let ga = reduce_broadcast(&gout, &out_shape, &sa);
                let gb = reduce_broadcast(&gout, &out_shape, &sb);
                acc_grad(&mut grads, &inputs[0], ga);
                acc_grad(&mut grads, &inputs[1], gb);
            }
            "mul" => {
                let a = values.get(&inputs[0]).cloned().unwrap_or(json!([]));
                let b = values.get(&inputs[1]).cloned().unwrap_or(json!([]));
                let sa = shapes.get(&inputs[0]).cloned().unwrap_or_default();
                let sb = shapes.get(&inputs[1]).cloned().unwrap_or_default();
                let out_shape = broadcast_shapes(&sa, &sb).unwrap_or(sa.clone());
                let fa: Vec<f64> = a.as_array().unwrap().iter().map(num).collect();
                let fb: Vec<f64> = b.as_array().unwrap().iter().map(num).collect();
                let ba = broadcast_to(&fa, &sa, &out_shape);
                let bb = broadcast_to(&fb, &sb, &out_shape);
                let ga_raw: Vec<f64> = gout.iter().zip(bb.iter()).map(|(g, y)| g * y).collect();
                let gb_raw: Vec<f64> = gout.iter().zip(ba.iter()).map(|(g, x)| g * x).collect();
                let ga = reduce_broadcast(&ga_raw, &out_shape, &sa);
                let gb = reduce_broadcast(&gb_raw, &out_shape, &sb);
                acc_grad(&mut grads, &inputs[0], ga);
                acc_grad(&mut grads, &inputs[1], gb);
            }
            "matmul" => {
                let a = values.get(&inputs[0]).cloned().unwrap_or(json!([]));
                let b = values.get(&inputs[1]).cloned().unwrap_or(json!([]));
                let sa = shapes.get(&inputs[0]).cloned().unwrap_or_default();
                let sb = shapes.get(&inputs[1]).cloned().unwrap_or_default();
                let m = sa[sa.len() - 2];
                let k = sa[sa.len() - 1];
                let n = sb[sb.len() - 1];
                let batch = sa[..sa.len() - 2].iter().product::<usize>().max(1);
                let fa: Vec<f64> = a.as_array().unwrap().iter().map(num).collect();
                let fb: Vec<f64> = b.as_array().unwrap().iter().map(num).collect();
                let mut ga = vec![0.0; fa.len()];
                let mut gb = vec![0.0; fb.len()];
                for bidx in 0..batch {
                    for i in 0..m {
                        for j in 0..n {
                            let g = gout[bidx * m * n + i * n + j];
                            for t in 0..k {
                                let a_idx = bidx * m * k + i * k + t;
                                let b_idx = bidx * k * n + t * n + j;
                                ga[a_idx] += g * fb[b_idx];
                                gb[b_idx] += g * fa[a_idx];
                            }
                        }
                    }
                }
                acc_grad(&mut grads, &inputs[0], ga);
                acc_grad(&mut grads, &inputs[1], gb);
            }
            "reduce_sum" => {
                let sa = shapes.get(&inputs[0]).cloned().unwrap_or_default();
                let out_shape = shapes.get(&id).cloned().unwrap_or(vec![1]);
                let expanded = broadcast_to(&gout, &out_shape, &sa);
                acc_grad(&mut grads, &inputs[0], expanded);
            }
            _ => {}
        }
        trace.push(json!({"node_id": id, "op": op, "backward": gout}));
    }

    let mut var_grads = Map::new();
    if let Some(vars) = graph.get("vars").and_then(|v| v.as_object()) {
        for name in vars.keys() {
            if let Some(g) = grads.get(name) {
                var_grads.insert(name.clone(), json!(g));
            }
        }
    }

    json!({"ok": true, "var_grads": var_grads, "trace": trace})
}
RS

cat > /app/environment/internal/carrier/merge.go <<'GO'
package carrier

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"sort"

	"gradlab/internal/paths"
)

type Carrier struct {
	Variables map[string][]float64 `json:"variables"`
}

func Load() Carrier {
	b, err := os.ReadFile(paths.PoolPath)
	if err != nil {
		return Carrier{Variables: map[string][]float64{}}
	}
	var p Carrier
	_ = json.Unmarshal(b, &p)
	if p.Variables == nil {
		p.Variables = map[string][]float64{}
	}
	return p
}

func (p *Carrier) MergeAssign(grads map[string][]float64) {
	for k, v := range grads {
		if existing, ok := p.Variables[k]; ok {
			out := make([]float64, len(existing))
			copy(out, existing)
			for i, val := range v {
				if i < len(out) {
					out[i] += val
				}
			}
			p.Variables[k] = out
		} else {
			cp := make([]float64, len(v))
			copy(cp, v)
			p.Variables[k] = cp
		}
	}
}

func (p *Carrier) Clear() {
	p.Variables = map[string][]float64{}
}

func (p *Carrier) Checksum() string {
	keys := make([]string, 0, len(p.Variables))
	for k := range p.Variables {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	canon := map[string]any{"variables": p.Variables}
	b, _ := json.Marshal(canon)
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}

func (p Carrier) Save() error {
	_ = os.MkdirAll(paths.VarDir, 0o755)
	b, _ := json.MarshalIndent(map[string]any{
		"variables":     p.Variables,
		"pool_checksum": p.Checksum(),
	}, "", "  ")
	return os.WriteFile(paths.PoolPath, append(b, '\n'), 0o644)
}
GO

cat > /app/environment/internal/epochctl/follow.go <<'GO'
package epochctl

import (
	"encoding/json"
	"os"

	"gradlab/internal/carrier"
	"gradlab/internal/paths"
)

type Ledger struct {
	Current int `json:"current"`
}

func LoadLedger() Ledger {
	b, err := os.ReadFile(paths.EpochPath)
	if err != nil {
		return Ledger{Current: 1}
	}
	var l Ledger
	_ = json.Unmarshal(b, &l)
	if l.Current == 0 {
		l.Current = 1
	}
	return l
}

func (l Ledger) Save() error {
	_ = os.MkdirAll(paths.VarDir, 0o755)
	b, _ := json.MarshalIndent(l, "", "  ")
	return os.WriteFile(paths.EpochPath, append(b, '\n'), 0o644)
}

func BeginFollowPass(l *Ledger, clearCarrier bool, c *carrier.Carrier) {
	l.Current++
	if clearCarrier && c != nil {
		c.Clear()
	}
}
GO

cat > /app/environment/internal/knobs/resolve.go <<'GO'
package knobs

import (
	"os"
	"strconv"
	"strings"
)

type Knobs struct {
	FDStep           float64
	GradTol          float64
	PoolClearSecond  bool
	PassOrderDefault string
}

func ResolveKnobs(cfg map[string]any, pol map[string]string) Knobs {
	out := Knobs{
		FDStep:           1e-5,
		GradTol:          1e-4,
		PoolClearSecond:  true,
		PassOrderDefault: "first",
	}
	if v, ok := cfg["fd_step"].(float64); ok && v > 0 {
		out.FDStep = v
	}
	if v, ok := cfg["grad_tol"].(float64); ok && v > 0 {
		out.GradTol = v
	}
	if v, ok := pol["pass_order_default"]; ok && v != "" {
		out.PassOrderDefault = v
	}
	if v, ok := pol["pool_clear_on_second"]; ok {
		out.PoolClearSecond = v == "true"
	}
	if v := os.Getenv("GRAD_FD_STEP"); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil && f > 0 {
			out.FDStep = f
		}
	}
	if v := os.Getenv("GRAD_GRAD_TOL"); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil && f > 0 {
			out.GradTol = f
		}
	}
	if v := os.Getenv("GRAD_POOL_CLEAR"); v != "" {
		out.PoolClearSecond = strings.EqualFold(v, "true") || v == "1"
	}
	return out
}
GO

cat > /app/environment/internal/validate/gate.go <<'GO'
package validate

import "fmt"

func intShape(spec map[string]any) []int {
	raw, _ := spec["shape"].([]any)
	out := make([]int, len(raw))
	for i, v := range raw {
		switch x := v.(type) {
		case float64:
			out[i] = int(x)
		case int:
			out[i] = x
		default:
			out[i] = 1
		}
	}
	return out
}

func broadcastShapes(a, b []int) ([]int, bool) {
	ra, rb := make([]int, len(a)), make([]int, len(b))
	copy(ra, a)
	copy(rb, b)
	for len(ra) < len(rb) {
		ra = append([]int{1}, ra...)
	}
	for len(rb) < len(ra) {
		rb = append([]int{1}, rb...)
	}
	out := make([]int, len(ra))
	for i := range ra {
		da, db := ra[i], rb[i]
		if da == db || da == 1 || db == 1 {
			out[i] = max(da, db)
		} else {
			return nil, false
		}
	}
	if len(out) == 0 {
		return []int{1}, true
	}
	return out, true
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func Feasible(graph map[string]any) (bool, string) {
	shapes := map[string][]int{}
	vars, _ := graph["vars"].(map[string]any)
	for name, raw := range vars {
		shapes[name] = intShape(raw.(map[string]any))
	}
	nodes, _ := graph["nodes"].([]any)
	for _, raw := range nodes {
		node, _ := raw.(map[string]any)
		op, _ := node["op"].(string)
		ins, _ := node["inputs"].([]any)
		id, _ := node["id"].(string)
		switch op {
		case "add", "mul":
			if len(ins) < 2 {
				return false, "inputs"
			}
			sa := shapes[fmt.Sprint(ins[0])]
			sb := shapes[fmt.Sprint(ins[1])]
			out, ok := broadcastShapes(sa, sb)
			if !ok {
				return false, "broadcast"
			}
			shapes[id] = out
		case "matmul":
			if len(ins) < 2 {
				return false, "inputs"
			}
			sa := shapes[fmt.Sprint(ins[0])]
			sb := shapes[fmt.Sprint(ins[1])]
			if len(sa) < 2 || len(sb) < 2 || sa[len(sa)-1] != sb[len(sb)-2] {
				return false, "matmul"
			}
			m, _, n := sa[len(sa)-2], sa[len(sa)-1], sb[len(sb)-1]
			out := append(append([]int{}, sa[:len(sa)-2]...), m, n)
			shapes[id] = out
		case "reduce_sum":
			sa := shapes[fmt.Sprint(ins[0])]
			axes, _ := node["axes"].([]any)
			reduced := map[int]bool{}
			for _, ax := range axes {
				idx := int(ax.(float64))
				if idx < 0 {
					idx = len(sa) + idx
				}
				if idx >= 0 && idx < len(sa) {
					reduced[idx] = true
				}
			}
			out := []int{}
			for i, d := range sa {
				if !reduced[i] {
					out = append(out, d)
				}
			}
			if len(out) == 0 {
				out = []int{1}
			}
			shapes[id] = out
		}
	}
	return true, ""
}
GO

# pipeline must pass pool to BeginSecondPass
cat > /app/environment/internal/pipeline/run.go <<'GO'
package pipeline

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"strings"

	"gradlab/internal/carrier"
	"gradlab/internal/bridge"
	"gradlab/internal/export"
	"gradlab/internal/ingest"
	"gradlab/internal/knobs"
	"gradlab/internal/epochctl"
	"gradlab/internal/session"
	"gradlab/internal/shape"
	"gradlab/internal/validate"
)

func RunSet(name string, reset bool) error {
	return RunNames(ingest.SetMap[name], reset)
}

func RunNames(names []string, reset bool) error {
	if reset {
		session.ResetVar()
	}
	cfg, err := ingest.LoadConfig()
	if err != nil {
		return err
	}
	pol, err := ingest.LoadPolicy()
	if err != nil {
		return err
	}
	knobs := knobs.ResolveKnobs(cfg, pol)
	graphs, err := ingest.LoadGraphs(names)
	if err != nil {
		return err
	}
	sess := session.Load()
	led := epochctl.LoadLedger()
	carr := carrier.Load()
	envOrder := os.Getenv("GRAD_PASS_ORDER")
	var trials []map[string]any
	var journal []map[string]any

	for _, graph := range graphs {
		if ok, reason := validate.Feasible(graph); !ok {
			pass := shape.ResolvePass(graph, pol, envOrder)
			trial := failTrial(graph, pass, reason)
			trials = append(trials, trial)
			sess.RunCount++
			continue
		}
		sess.RunCount++
		pass := shape.ResolvePass(graph, pol, envOrder)
		fwd, err := bridge.RunTape("forward", map[string]any{"graph": graph})
		if err != nil || fwd["ok"] != true {
			trial := failTrial(graph, pass, "forward")
			trials = append(trials, trial)
			continue
		}
		loss, _ := fwd["loss"].(float64)
		bwd, err := bridge.RunTape("backward", map[string]any{"graph": graph, "forward": fwd})
		if err != nil || bwd["ok"] != true {
			trial := failTrial(graph, pass, "backward")
			trials = append(trials, trial)
			continue
		}
    varGrad := extractVarGrad(bwd)
    firstGrad := varGrad
    carr.MergeAssign(varGrad)
    var fdMax float64
    var gradOK bool
    if pass == "second" {
      epochctl.BeginFollowPass(&led, knobs.PoolClearSecond, &carr)
      varGrad = fdSecondOrder(graph, firstGrad, knobs.FDStep)
      carr.MergeAssign(varGrad)
      ref := fdSecondOrder(graph, firstGrad, knobs.FDStep*0.1)
      fdMax, gradOK = compareGrad(ref, varGrad, knobs.GradTol)
    } else {
      fdMax, gradOK = fdCheck(graph, varGrad, knobs.FDStep, knobs.GradTol)
    }
		if exp, ok := graph["expect_ok"].(bool); ok && !exp {
			gradOK = false
		}
		traceRows := buildTrace(fwd, bwd)
		trial := map[string]any{
			"graph": graph["name"], "pass": pass, "loss": loss, "grad_ok": gradOK,
			"fd_max": fdMax, "var_grads": carr.Variables, "trace_rows": traceRows,
		}
		trials = append(trials, trial)
		journal = append(journal, map[string]any{
			"graph": graph["name"], "pass": pass, "loss": loss, "grad_ok": gradOK,
			"epoch": led.Current, "pool_checksum": carr.Checksum(),
		})
		_ = carr.Save()
		_ = led.Save()
	}
	report := export.Emit(cfg, trials, journal, map[string]any{
		"variables": carr.Variables, "pool_checksum": carr.Checksum(),
	})
	if fp, ok := report["run_fingerprint"].(string); ok {
		sess.LastFingerprint = fp
	}
	labels := make([]string, len(trials))
	for i, t := range trials {
		labels[i] = t["graph"].(string)
	}
	sess.GraphLabels = labels
	_ = session.Save(sess)
	cp := session.Checkpoint{
		Waterline:   sess.RunCount,
		Fingerprint: report["run_fingerprint"].(string),
		GraphSet:    strings.Join(labels, ","),
	}
	return session.SaveCheckpoint(cp)
}

func failTrial(graph map[string]any, pass, phase string) map[string]any {
	return map[string]any{
		"graph": graph["name"], "pass": pass, "loss": 0.0, "grad_ok": false,
		"fd_max": 1.0, "var_grads": map[string][]float64{}, "trace_rows": []map[string]any{},
		"error": phase,
	}
}

func extractVarGrad(bwd map[string]any) map[string][]float64 {
	out := map[string][]float64{}
	raw, _ := bwd["var_grads"].(map[string]any)
	for k, v := range raw {
		arr, _ := v.([]any)
		vals := make([]float64, len(arr))
		for i, x := range arr {
			vals[i], _ = x.(float64)
		}
		out[k] = vals
	}
	return out
}

func buildTrace(fwd, bwd map[string]any) []map[string]any {
	ftrace, _ := fwd["trace"].([]any)
	bmap := map[string][]float64{}
	btrace, _ := bwd["trace"].([]any)
	for _, raw := range btrace {
		row, _ := raw.(map[string]any)
		id, _ := row["node_id"].(string)
		if arr, ok := row["backward"].([]any); ok {
			vals := make([]float64, len(arr))
			for i, x := range arr {
				vals[i], _ = x.(float64)
			}
			bmap[id] = vals
		}
	}
	out := []map[string]any{}
	for _, raw := range ftrace {
		row, _ := raw.(map[string]any)
		id, _ := row["node_id"].(string)
		op, _ := row["op"].(string)
		fwdVal := 0.0
		if arr, ok := row["forward"].([]any); ok && len(arr) > 0 {
			fwdVal, _ = arr[0].(float64)
		}
		bwdVal := 0.0
		if g, ok := bmap[id]; ok && len(g) > 0 {
			bwdVal = g[0]
		}
		out = append(out, map[string]any{
			"node_id": id, "op": op,
			"forward_6": fmt.Sprintf("%.6f", fwdVal),
			"backward_6": fmt.Sprintf("%.6f", bwdVal),
		})
	}
	return out
}

func evalFirstGradAt(graph map[string]any, varName string, idx int, delta float64) float64 {
  g := deepCopy(graph)
  vars := g["vars"].(map[string]any)
  spec := vars[varName].(map[string]any)
  data := spec["data"].([]any)
  base, _ := data[idx].(float64)
  data[idx] = base + delta
  spec["data"] = data
  fwd, err := bridge.RunTape("forward", map[string]any{"graph": g})
  if err != nil || fwd["ok"] != true {
    return 0
  }
  bwd, err := bridge.RunTape("backward", map[string]any{"graph": g, "forward": fwd})
  if err != nil || bwd["ok"] != true {
    return 0
  }
  vg := extractVarGrad(bwd)
  if arr, ok := vg[varName]; ok && idx < len(arr) {
    return arr[idx]
  }
  return 0
}

func fdSecondOrder(graph map[string]any, firstGrad map[string][]float64, step float64) map[string][]float64 {
  out := map[string][]float64{}
  vars, _ := graph["vars"].(map[string]any)
  for name := range vars {
    fg := firstGrad[name]
    arr := make([]float64, len(fg))
    for i := range fg {
      gPlus := evalFirstGradAt(graph, name, i, step)
      gMinus := evalFirstGradAt(graph, name, i, -step)
      arr[i] = (gPlus - gMinus) / (2 * step)
    }
    out[name] = arr
  }
  return out
}

func compareGrad(ref, got map[string][]float64, tol float64) (float64, bool) {
  maxDelta := 0.0
  ok := true
  for name, want := range ref {
    have, exists := got[name]
    if !exists {
      ok = false
      continue
    }
    for i, w := range want {
      g := 0.0
      if i < len(have) {
        g = have[i]
      }
      d := math.Abs(g - w)
      if d > maxDelta {
        maxDelta = d
      }
      if d > tol {
        ok = false
      }
    }
  }
  return maxDelta, ok
}

func fdCheck(graph map[string]any, grads map[string][]float64, step, tol float64) (float64, bool) {
	maxDelta := 0.0
	ok := true
	vars, _ := graph["vars"].(map[string]any)
	for name, spec := range vars {
		sm, _ := spec.(map[string]any)
		data, _ := sm["data"].([]any)
		analytic, has := grads[name]
		if !has {
			ok = false
			continue
		}
		for i, raw := range data {
			base, _ := raw.(float64)
			plus := perturbVar(graph, name, i, base+step)
			minus := perturbVar(graph, name, i, base-step)
			lPlus := evalLoss(plus)
			lMinus := evalLoss(minus)
			fd := (lPlus - lMinus) / (2 * step)
			ag := 0.0
			if i < len(analytic) {
				ag = analytic[i]
			}
			d := math.Abs(ag - fd)
			if d > maxDelta {
				maxDelta = d
			}
			if d > tol {
				ok = false
			}
		}
	}
	return maxDelta, ok
}

func perturbVar(graph map[string]any, name string, idx int, val float64) map[string]any {
	g := deepCopy(graph)
	vars := g["vars"].(map[string]any)
	spec := vars[name].(map[string]any)
	data := spec["data"].([]any)
	data[idx] = val
	spec["data"] = data
	return g
}

func deepCopy(graph map[string]any) map[string]any {
	b, _ := json.Marshal(graph)
	var out map[string]any
	_ = json.Unmarshal(b, &out)
	return out
}

func evalLoss(graph map[string]any) float64 {
	fwd, err := bridge.RunTape("forward", map[string]any{"graph": graph})
	if err != nil || fwd["ok"] != true {
		return 0
	}
	loss, _ := fwd["loss"].(float64)
	return loss
}

func SurfaceQuery(mode, arg string) string {
	b, err := os.ReadFile("/app/output/gradient_report.json")
	if err != nil {
		return "missing"
	}
	var report map[string]any
	_ = json.Unmarshal(b, &report)
	switch mode {
	case "digest":
		return report["report_digest_hex"].(string)
	case "fingerprint":
		return report["run_fingerprint"].(string)
	case "status":
		if report["grad_ok"].(bool) {
			return "ok"
		}
		return "fail"
	case "epoch":
		eb, err := os.ReadFile("/app/var/grad/tape_epoch.json")
		if err != nil {
			return "missing"
		}
		var epoch map[string]any
		_ = json.Unmarshal(eb, &epoch)
		return fmt.Sprintf("%v", epoch["current"])
	case "pool":
		pb, err := os.ReadFile("/app/var/grad/pool_state.json")
		if err != nil {
			return "missing"
		}
		var pool map[string]any
		_ = json.Unmarshal(pb, &pool)
		return pool["pool_checksum"].(string)
	case "checkpoint":
		cp := session.LoadCheckpoint()
		if cp.Waterline == 0 {
			return "missing"
		}
		return fmt.Sprintf("%d:%s", cp.Waterline, cp.Fingerprint)
	case "grad":
		trials := report["trials"].([]any)
		if len(trials) == 0 {
			return "missing"
		}
		last := trials[len(trials)-1].(map[string]any)
		vg := last["var_grads"].(map[string]any)
		arr, ok := vg[arg].([]any)
		if !ok {
			return "missing"
		}
		parts := make([]string, len(arr))
		for i, x := range arr {
			parts[i] = fmt.Sprintf("%.6f", x.(float64))
		}
		return strings.Join(parts, ",")
	default:
		return "missing"
	}
}

func SurfaceCheck() string {
	b, err := os.ReadFile("/app/output/gradient_report.json")
	if err != nil {
		return "drift"
	}
	var existing map[string]any
	_ = json.Unmarshal(b, &existing)
	cfg, _ := ingest.LoadConfig()
	pol, _ := ingest.LoadPolicy()
	knobs := knobs.ResolveKnobs(cfg, pol)
	var names []string
	for _, t := range existing["trials"].([]any) {
		names = append(names, t.(map[string]any)["graph"].(string))
	}
	graphs, _ := ingest.LoadGraphs(names)
	for i, graph := range graphs {
		old := existing["trials"].([]any)[i].(map[string]any)
		if ok, _ := validate.Feasible(graph); !ok {
			if old["grad_ok"].(bool) {
				return "drift"
			}
			continue
		}
		pass := shape.ResolvePass(graph, pol, os.Getenv("GRAD_PASS_ORDER"))
		fwd, _ := bridge.RunTape("forward", map[string]any{"graph": graph})
		if fwd["ok"] != true {
			if old["grad_ok"].(bool) {
				return "drift"
			}
			continue
		}
		loss := fwd["loss"].(float64)
		if fmt.Sprintf("%.9f", loss) != fmt.Sprintf("%.9f", old["loss"].(float64)) {
			return "drift"
		}
		_ = pass
		if strings.ToLower(fmt.Sprintf("%v", old["grad_ok"])) == "true" {
			bwd, _ := bridge.RunTape("backward", map[string]any{"graph": graph, "forward": fwd})
			vg := extractVarGrad(bwd)
			fdMax, gradOK := fdCheck(graph, vg, knobs.FDStep, knobs.GradTol)
			if !gradOK || fdMax > old["fd_max"].(float64)+1e-9 {
				return "drift"
			}
		}
	}
	cp := session.LoadCheckpoint()
	if fp, ok := existing["run_fingerprint"].(string); ok && cp.Fingerprint != fp {
		return "drift"
	}
	return "aligned"
}
GO

bash /app/environment/scripts/rebuild.sh
/app/environment/build/gradctl-run --reset --set all
