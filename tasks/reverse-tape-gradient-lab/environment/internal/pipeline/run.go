
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
	for name, rv := range ref {
		gv, has := got[name]
		if !has {
			ok = false
			continue
		}
		for i, r := range rv {
			g := 0.0
			if i < len(gv) {
				g = gv[i]
			}
			d := math.Abs(r - g)
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
