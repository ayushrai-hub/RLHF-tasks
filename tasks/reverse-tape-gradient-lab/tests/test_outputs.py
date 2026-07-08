"""Verifier for reverse-tape-gradient-lab."""

from __future__ import annotations

import csv
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

ENV = Path("/app/environment")
BUILD = ENV / "build"
GRAPHS = ENV / "data" / "graphs"
CONFIG = ENV / "data" / "config" / "grad.json"
POLICY = ENV / "data" / "policy.toml"
OUTPUT = Path("/app/output")
VAR = Path("/app/var/grad")
REPORT = OUTPUT / "gradient_report.json"
CSV_PATH = OUTPUT / "node_trace.csv"
JOURNAL = OUTPUT / "pass_journal.jsonl"
SESSION = VAR / "session.json"
POOL = VAR / "pool_state.json"
EPOCH = VAR / "tape_epoch.json"
CHECKPOINT = VAR / "checkpoint.json"

S1 = ("shared_square", "chain_mul")
S2 = ("broadcast_add", "matmul_vec")
S3 = ("second_order_scalar", "reduce_axes")
ALL = S1 + S2 + S3


def _sha(text: str) -> str:
    return (
        subprocess.run(["sha256sum"], input=text.encode(), capture_output=True, check=True)
        .stdout.decode()
        .split()[0]
    )


def _rebuild() -> None:
    subprocess.run(["bash", str(ENV / "scripts" / "rebuild.sh")], check=True)


def _run(args: list[str], env: dict[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run([str(BUILD / "gradctl-run"), *args], check=True, env=merged)


def _probe(mode: str, arg: str | None = None) -> str:
    cmd = [str(BUILD / "gradctl-probe"), mode]
    if arg is not None:
        cmd.append(arg)
    return subprocess.check_output(cmd, text=True).strip()


def _audit() -> str:
    return subprocess.check_output([str(BUILD / "gradctl-audit")], text=True).strip()


def _inspect() -> str:
    return subprocess.check_output([str(BUILD / "gradctl-inspect")], text=True).strip()


def _load_report() -> dict[str, Any]:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _load_cfg() -> dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


# --- independent tape evaluator (mirrors public contract) ---


def _num(v: Any) -> float:
    return float(v)


def _shape(spec: dict[str, Any]) -> list[int]:
    return [int(x) for x in spec["shape"]]


def _data(spec: dict[str, Any]) -> list[float]:
    return [float(x) for x in spec["data"]]


def _size(shape: list[int]) -> int:
    out = 1
    for d in shape:
        out *= d
    return max(out, 1)


def _broadcast_shapes(a: list[int], b: list[int]) -> list[int] | None:
    ra, rb = list(reversed(a)), list(reversed(b))
    n = max(len(ra), len(rb))
    out_rev: list[int] = []
    for i in range(n):
        da = ra[i] if i < len(ra) else 1
        db = rb[i] if i < len(rb) else 1
        if da == db or da == 1 or db == 1:
            out_rev.append(max(da, db))
        else:
            return None
    out = list(reversed(out_rev))
    return out if out else [1]


def _broadcast_to(data: list[float], frm: list[int], to: list[int]) -> list[float]:
    to_size = _size(to)
    out = [0.0] * to_size
    from_rank = len(frm)
    to_rank = len(to)
    offset = max(0, to_rank - from_rank)
    for flat in range(to_size):
        rem = flat
        coords = [0] * to_rank
        for i in range(to_rank - 1, -1, -1):
            coords[i] = rem % to[i]
            rem //= to[i]
        src_flat = 0
        stride = 1
        for i in range(from_rank - 1, -1, -1):
            to_axis = offset + i
            c = 0 if frm[i] == 1 else coords[to_axis]
            src_flat += c * stride
            stride *= frm[i]
        out[flat] = data[min(src_flat, len(data) - 1)]
    return out


def _norm_axes(shape: list[int], axes: list[int]) -> list[int]:
    norm: list[int] = []
    for ax in axes:
        idx = ax if ax >= 0 else len(shape) + ax
        if 0 <= idx < len(shape):
            norm.append(idx)
    norm = sorted(set(norm))
    return norm


def _reduce_sum(data: list[float], shape: list[int], axes: list[int]) -> tuple[list[float], list[int]]:
    norm = _norm_axes(shape, axes)
    out_shape = [d for i, d in enumerate(shape) if i not in norm]
    if not out_shape:
        out_shape = [1]
    out = [0.0] * _size(out_shape)
    for flat in range(_size(shape)):
        rem = flat
        coords = [0] * len(shape)
        for i in range(len(shape) - 1, -1, -1):
            coords[i] = rem % shape[i]
            rem //= shape[i]
        kept = [coords[i] for i in range(len(shape)) if i not in norm]
        oidx = 0
        if kept:
            stride = 1
            for i in range(len(out_shape) - 1, -1, -1):
                oidx += kept[i] * stride
                stride *= out_shape[i]
        out[min(oidx, len(out) - 1)] += data[flat]
    return out, out_shape


def _forward(graph: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, list[float]] = {}
    shapes: dict[str, list[int]] = {}
    for name, spec in graph["vars"].items():
        shapes[name] = _shape(spec)
        values[name] = _data(spec)
    trace: list[dict[str, Any]] = []
    for node in graph["nodes"]:
        nid = node["id"]
        op = node["op"]
        ins = node["inputs"]
        if op in {"add", "mul"}:
            sa, sb = shapes[ins[0]], shapes[ins[1]]
            out_shape = _broadcast_shapes(sa, sb)
            if out_shape is None:
                return {"ok": False, "error": "broadcast"}
            fa = _broadcast_to(values[ins[0]], sa, out_shape)
            fb = _broadcast_to(values[ins[1]], sb, out_shape)
            if op == "add":
                out = [a + b for a, b in zip(fa, fb)]
            else:
                out = [a * b for a, b in zip(fa, fb)]
        elif op == "matmul":
            sa, sb = shapes[ins[0]], shapes[ins[1]]
            m, k, n = sa[-2], sa[-1], sb[-1]
            batch = _size(sa[:-2]) if len(sa) > 2 else 1
            fa, fb = values[ins[0]], values[ins[1]]
            out_shape = sa[:-2] + [m, n]
            out = [0.0] * _size(out_shape)
            for bidx in range(batch):
                for i in range(m):
                    for j in range(n):
                        for t in range(k):
                            out[bidx * m * n + i * n + j] += (
                                fa[bidx * m * k + i * k + t] * fb[bidx * k * n + t * n + j]
                            )
        elif op == "reduce_sum":
            sa = shapes[ins[0]]
            out, out_shape = _reduce_sum(values[ins[0]], sa, node.get("axes", []))
        else:
            out, out_shape = [0.0], [1]
        values[nid] = out
        shapes[nid] = out_shape
        trace.append({"node_id": nid, "op": op, "forward": out})
    loss_id = graph.get("loss", "out")
    loss = values[loss_id][0] if values.get(loss_id) else 0.0
    return {"ok": True, "values": values, "shapes": shapes, "trace": trace, "loss": loss}


def _reduce_broadcast(grad: list[float], grad_shape: list[int], target: list[int]) -> list[float]:
    if grad_shape == target:
        return list(grad)
    work = list(grad)
    work_shape = list(grad_shape)
    max_rank = max(len(work_shape), len(target))
    axes: list[int] = []
    for i in range(max_rank):
        gdim = work_shape[-1 - i] if i < len(work_shape) else 1
        tdim = target[-1 - i] if i < len(target) else 1
        if gdim > tdim:
            axes.append(len(work_shape) - 1 - i)
    if axes:
        work, work_shape = _reduce_sum(work, work_shape, axes)
    if work_shape == target:
        return work
    return _broadcast_to(work, work_shape, target)


def _backward(graph: dict[str, Any], fwd: dict[str, Any]) -> dict[str, Any]:
    values = fwd["values"]
    shapes = fwd["shapes"]
    loss_id = graph.get("loss", "out")
    grads: dict[str, list[float]] = {}
    loss_shape = shapes[loss_id]
    seed = [0.0] * _size(loss_shape)
    seed[0] = 1.0
    grads[loss_id] = seed
    trace: list[dict[str, Any]] = []
    for node in reversed(graph["nodes"]):
        nid = node["id"]
        op = node["op"]
        ins = node["inputs"]
        if nid not in grads:
            continue
        gout = grads[nid]
        if op == "add":
            sa, sb = shapes[ins[0]], shapes[ins[1]]
            out_shape = _broadcast_shapes(sa, sb) or sa
            ga = _reduce_broadcast(gout, out_shape, sa)
            gb = _reduce_broadcast(gout, out_shape, sb)
            grads[ins[0]] = _acc(grads.get(ins[0]), ga)
            grads[ins[1]] = _acc(grads.get(ins[1]), gb)
        elif op == "mul":
            sa, sb = shapes[ins[0]], shapes[ins[1]]
            out_shape = _broadcast_shapes(sa, sb) or sa
            fa = _broadcast_to(values[ins[0]], sa, out_shape)
            fb = _broadcast_to(values[ins[1]], sb, out_shape)
            ga = _reduce_broadcast([g * y for g, y in zip(gout, fb)], out_shape, sa)
            gb = _reduce_broadcast([g * x for g, x in zip(gout, fa)], out_shape, sb)
            grads[ins[0]] = _acc(grads.get(ins[0]), ga)
            grads[ins[1]] = _acc(grads.get(ins[1]), gb)
        elif op == "matmul":
            sa, sb = shapes[ins[0]], shapes[ins[1]]
            m, k, n = sa[-2], sa[-1], sb[-1]
            batch = _size(sa[:-2]) if len(sa) > 2 else 1
            fa, fb = values[ins[0]], values[ins[1]]
            ga = [0.0] * len(fa)
            gb = [0.0] * len(fb)
            for bidx in range(batch):
                for i in range(m):
                    for j in range(n):
                        g = gout[bidx * m * n + i * n + j]
                        for t in range(k):
                            ga[bidx * m * k + i * k + t] += g * fb[bidx * k * n + t * n + j]
                            gb[bidx * k * n + t * n + j] += g * fa[bidx * m * k + i * k + t]
            grads[ins[0]] = _acc(grads.get(ins[0]), ga)
            grads[ins[1]] = _acc(grads.get(ins[1]), gb)
        elif op == "reduce_sum":
            sa = shapes[ins[0]]
            out_shape = shapes[nid]
            expanded = _broadcast_to(gout, out_shape, sa)
            grads[ins[0]] = _acc(grads.get(ins[0]), expanded)
        trace.append({"node_id": nid, "op": op, "backward": gout})
    var_grads = {name: grads[name] for name in graph["vars"] if name in grads}
    return {"ok": True, "var_grads": var_grads, "trace": trace}


def _acc(existing: list[float] | None, add: list[float]) -> list[float]:
    if existing is None:
        return list(add)
    out = list(existing)
    if len(add) > len(out):
        out.extend([0.0] * (len(add) - len(out)))
    for i, v in enumerate(add):
        out[i] += v
    return out


def _fd_check(graph: dict[str, Any], analytic: dict[str, list[float]], step: float, tol: float) -> tuple[float, bool]:
    max_delta = 0.0
    ok = True
    for name, spec in graph["vars"].items():
        data = _data(spec)
        ag = analytic.get(name, [])
        for i, base in enumerate(data):
            g = deepcopy(graph)
            g["vars"][name]["data"][i] = base + step
            l_plus = _forward(g)["loss"]
            g = deepcopy(graph)
            g["vars"][name]["data"][i] = base - step
            l_minus = _forward(g)["loss"]
            fd = (l_plus - l_minus) / (2 * step)
            a = ag[i] if i < len(ag) else 0.0
            d = abs(a - fd)
            max_delta = max(max_delta, d)
            if d > tol:
                ok = False
    return max_delta, ok


def _audit_trial(graph: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    fwd = _forward(graph)
    if not fwd["ok"]:
        return {"graph": graph["name"], "grad_ok": False, "loss": 0.0, "fd_max": 1.0}
    bwd = _backward(graph, fwd)
    fd_max, grad_ok = _fd_check(graph, bwd["var_grads"], cfg["fd_step"], cfg["grad_tol"])
    if graph.get("expect_ok") is False:
        grad_ok = False
    return {"graph": graph["name"], "loss": fwd["loss"], "grad_ok": grad_ok, "fd_max": fd_max}


# --- tests ---


def test_rebuild_and_reset_run_all():
    _rebuild()
    _run(["--reset", "--set", "all"])
    report = _load_report()
    assert report["grad_ok"] is True
    assert len(report["trials"]) == len(ALL)
    assert _probe("status") == "ok"


def test_cross_surface_alignment():
    _rebuild()
    _run(["--reset", "--set", "all"])
    assert _audit() == "aligned"
    report = _load_report()
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    assert len(rows) == sum(len(t.get("trace_rows", [])) for t in report["trials"])
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    assert pool["pool_checksum"] == _probe("pool")
    sess = json.loads(SESSION.read_text(encoding="utf-8"))
    assert sess["run_count"] == len(report["trials"])


def test_independent_gradient_audit():
    _rebuild()
    _run(["--reset", "--set", "all"])
    cfg = _load_cfg()
    report = _load_report()
    for trial in report["trials"]:
        graph = json.loads((GRAPHS / f"{trial['graph']}.json").read_text(encoding="utf-8"))
        expected = _audit_trial(graph, cfg)
        assert abs(expected["loss"] - trial["loss"]) < 1e-9
        assert trial["grad_ok"] == expected["grad_ok"]
        assert trial["fd_max"] <= expected["fd_max"] + 1e-6


def test_shared_square_probe_grad():
    _rebuild()
    _run(["--reset", "--graphs", "shared_square"])
    grad = _probe("grad", "x")
    assert grad == "4.000000,-3.000000"


def test_second_order_epoch_increment():
    _rebuild()
    _run(["--reset", "--graphs", "second_order_scalar"])
    epoch = int(_probe("epoch"))
    assert epoch >= 2
    grad = _probe("grad", "t")
    assert grad.startswith("2.")


def test_mutation_graph_dir_copy():
    _rebuild()
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(GRAPHS, tmp / "graphs")
    g = json.loads((tmp / "graphs" / "chain_mul.json").read_text(encoding="utf-8"))
    g["vars"]["a"]["data"][0] = 2.5
    (tmp / "graphs" / "chain_mul.json").write_text(json.dumps(g) + "\n", encoding="utf-8")
    _run(["--reset", "--graphs", "chain_mul"], env={"GRAD_GRAPH_DIR": str(tmp / "graphs")})
    report = _load_report()
    assert report["trials"][0]["graph"] == "chain_mul"
    assert report["grad_ok"] is True
    assert report["run_fingerprint"] != _sha("stale")


def test_negative_invalid_broadcast_graph():
    _rebuild()
    _run(["--reset", "--graphs", "invalid_broadcast"])
    report = _load_report()
    assert report["grad_ok"] is False
    assert _probe("status") == "fail"
    assert REPORT.exists() and CSV_PATH.exists()


def test_partial_set_s2_without_reset_carries_session():
    _rebuild()
    _run(["--reset", "--set", "s1"])
    fp1 = _probe("fingerprint")
    _run(["--set", "s2"])
    fp2 = _probe("fingerprint")
    assert fp1 != fp2
    inspect = _inspect()
    assert "run_count=" in inspect
    assert int(inspect.split("run_count=")[1].split()[0]) >= 4


def test_inspect_projection():
    _rebuild()
    _run(["--reset", "--set", "s3"])
    inspect = _inspect()
    assert "epoch=" in inspect
    assert "graphs=" in inspect
    assert all(name in inspect for name in S3)


def test_checkpoint_waterline():
    _rebuild()
    _run(["--reset", "--set", "s1"])
    cp = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    report = _load_report()
    assert cp["waterline"] == len(report["trials"])
    assert cp["fingerprint"] == report["run_fingerprint"]
    probe_cp = _probe("checkpoint")
    assert probe_cp == f"{cp['waterline']}:{cp['fingerprint']}"


def test_policy_env_grad_tol_override():
    _rebuild()
    _run(["--reset", "--graphs", "chain_mul"], env={"GRAD_GRAD_TOL": "1e-20"})
    tight = _load_report()
    assert tight["grad_ok"] is False
    _run(["--reset", "--graphs", "chain_mul"], env={"GRAD_GRAD_TOL": "1e-2"})
    loose = _load_report()
    assert loose["grad_ok"] is True
    cfg = _load_cfg()
    expected = _audit_trial(
        json.loads((GRAPHS / "chain_mul.json").read_text(encoding="utf-8")),
        {**cfg, "grad_tol": 1e-2},
    )
    assert loose["trials"][0]["grad_ok"] == expected["grad_ok"]
