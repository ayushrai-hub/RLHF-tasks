import os
import glob
import subprocess

import pytest

import bpt_ref as ref

APP = "/app"
BPT = os.path.join(APP, "bin", "bpt")
DATA = os.path.join(APP, "data")
WORK = "/tmp/bpt_m2"


def _build_binary():
    r = subprocess.run(["make"], cwd=APP, capture_output=True, text=True)
    assert r.returncode == 0, "build failed: %s" % r.stderr
    assert os.path.exists(BPT), "bpt binary not produced"


def _run(args, check=True):
    r = subprocess.run([BPT] + args, capture_output=True)
    if check:
        assert r.returncode == 0, "bpt %s exit %d: %s" % (args, r.returncode, r.stderr)
    return r


def _build_idx(ops_path, out_path):
    _run(["build", ops_path, "--out", out_path])
    assert os.path.exists(out_path)


def _apply_idx(in_path, ops_path, out_path):
    _run(["apply", in_path, ops_path, out_path])
    assert os.path.exists(out_path)


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _scenarios():
    fs = sorted(glob.glob(os.path.join(DATA, "apply", "*.build")))
    assert len(fs) >= 40
    out = []
    for bp in fs:
        ap = bp[:-len(".build")] + ".apply"
        if os.path.exists(ap):
            out.append((bp, ap))
    return out


def _check_invariants(t):
    keys_seen = []

    def walk(n, depth, leaf_depth):
        if n.leaf:
            if leaf_depth[0] is None:
                leaf_depth[0] = depth
            assert leaf_depth[0] == depth
            for k in n.keys:
                keys_seen.append(k)
            return
        assert len(n.children) == len(n.keys) + 1
        for c in n.children:
            walk(c, depth + 1, leaf_depth)

    walk(t.root, 0, [None])
    assert keys_seen == sorted(keys_seen)
    assert len(keys_seen) == len(set(keys_seen))

    def chain_keys():
        n = t.root
        while not n.leaf:
            n = n.children[0]
        out = []
        while n is not None:
            out.extend(n.keys)
            n = n.nxt
        return out

    assert chain_keys() == keys_seen


@pytest.fixture(scope="module", autouse=True)
def prepared():
    """Build the agent binary and a working directory once for milestone 2."""
    _build_binary()
    os.makedirs(WORK, exist_ok=True)


class TestMilestone2:
    def test_m1_build_still_byte_exact(self):
        """Milestone 2 depends on milestone 1: base builds must still serialize byte-exactly."""
        for i, (bp, _ap) in enumerate(_scenarios()[:30]):
            out = os.path.join(WORK, "base%d.idx" % i)
            _build_idx(bp, out)
            with open(bp) as f:
                t = ref.build(ref.parse_ops(f.read()))
            assert _read(out) == ref.serialize(t), "base build wrong on %s" % bp

    def test_apply_bytes_exact(self):
        """Applying inserts and deletes reserializes to the exact expected byte image."""
        for i, (bp, ap) in enumerate(_scenarios()):
            base = os.path.join(WORK, "ab_base%d.idx" % i)
            res = os.path.join(WORK, "ab_res%d.idx" % i)
            _build_idx(bp, base)
            _apply_idx(base, ap, res)
            with open(bp) as f:
                ops = ref.parse_ops(f.read())
            with open(ap) as f:
                ops += ref.parse_ops(f.read())
            t = ref.build(ops)
            assert _read(res) == ref.serialize(t), "apply bytes wrong on %s" % ap

    def test_apply_dump_matches(self):
        """The tree after apply matches the reference dump, node for node."""
        for i, (bp, ap) in enumerate(_scenarios()[::2]):
            base = os.path.join(WORK, "ad_base%d.idx" % i)
            res = os.path.join(WORK, "ad_res%d.idx" % i)
            _build_idx(bp, base)
            _apply_idx(base, ap, res)
            r = _run(["dump", res])
            with open(bp) as f:
                ops = ref.parse_ops(f.read())
            with open(ap) as f:
                ops += ref.parse_ops(f.read())
            t = ref.build(ops)
            assert r.stdout.decode("latin-1") == ref.dump(t), "apply dump wrong on %s" % ap

    def test_apply_preserves_invariants(self):
        """After apply, the tree satisfies B+tree ordering, uniform depth and leaf chaining."""
        for i, (bp, ap) in enumerate(_scenarios()):
            base = os.path.join(WORK, "inv_base%d.idx" % i)
            res = os.path.join(WORK, "inv_res%d.idx" % i)
            _build_idx(bp, base)
            _apply_idx(base, ap, res)
            with open(bp) as f:
                ops = ref.parse_ops(f.read())
            with open(ap) as f:
                ops += ref.parse_ops(f.read())
            t = ref.build(ops)
            _check_invariants(t)

    def test_apply_get_agrees(self):
        """Point lookups on the applied index agree with the surviving key set."""
        for i, (bp, ap) in enumerate(_scenarios()[::3]):
            base = os.path.join(WORK, "ag_base%d.idx" % i)
            res = os.path.join(WORK, "ag_res%d.idx" % i)
            _build_idx(bp, base)
            _apply_idx(base, ap, res)
            with open(bp) as f:
                ops = ref.parse_ops(f.read())
            with open(ap) as f:
                ops += ref.parse_ops(f.read())
            keymap = ref.present_keys(ops)
            for k, v in list(keymap.items())[:20]:
                r = _run(["get", res, str(k)])
                assert r.stdout.decode("latin-1") == v + "\n"
            probe = 800000
            miss = 0
            while miss < 3:
                if probe not in keymap:
                    r = _run(["get", res, str(probe)])
                    assert r.stdout.decode("latin-1") == "NOT-FOUND\n"
                    miss += 1
                probe += 1

    def test_range_matches_reference(self):
        """Range scans return exactly the entries in [lo,hi] via the leaf chain."""
        qfiles = sorted(glob.glob(os.path.join(DATA, "range", "*.queries")))
        assert len(qfiles) >= 10
        for qi, qf in enumerate(qfiles):
            bp = qf[:-len(".queries")] + ".build"
            idx = os.path.join(WORK, "rng%d.idx" % qi)
            _build_idx(bp, idx)
            with open(bp) as f:
                t = ref.build(ref.parse_ops(f.read()))
            with open(qf) as f:
                queries = [ln.split() for ln in f if ln.strip()]
            for lo, hi in queries:
                lo = int(lo)
                hi = int(hi)
                r = _run(["range", idx, str(lo), str(hi)])
                got = r.stdout.decode("latin-1")
                exp = "".join("%d\t%s\n" % (k, v) for k, v in ref.range_scan(t, lo, hi))
                assert got == exp, "range [%d,%d] on %s" % (lo, hi, bp)

    def test_range_empty_when_no_keys(self):
        """A range covering no present key prints nothing and exits cleanly."""
        bp = os.path.join(DATA, "range", "range_000.build")
        idx = os.path.join(WORK, "rngempty.idx")
        _build_idx(bp, idx)
        r = _run(["range", idx, "900000", "900100"])
        assert r.stdout == b""
        assert r.returncode == 0

    def test_range_single_point(self):
        """A degenerate range lo==hi returns just that key when present."""
        bp = os.path.join(DATA, "range", "range_003.build")
        idx = os.path.join(WORK, "rngpt.idx")
        _build_idx(bp, idx)
        with open(bp) as f:
            t = ref.build(ref.parse_ops(f.read()))
        keys = sorted(ref.present_keys(ref.parse_ops(open(bp).read())).keys())
        k = keys[len(keys) // 2]
        r = _run(["range", idx, str(k), str(k)])
        exp = "".join("%d\t%s\n" % (kk, v) for kk, v in ref.range_scan(t, k, k))
        assert r.stdout.decode("latin-1") == exp

    def test_delete_all_yields_empty_root_leaf(self):
        """Deleting every key collapses the tree to an empty root leaf of height one."""
        bp = os.path.join(DATA, "scenarios", "underflow_cascade.build")
        allops = ref.parse_ops(open(bp).read())
        keys = sorted(ref.present_keys(allops).keys())
        delops = os.path.join(WORK, "delall.ops")
        with open(delops, "w") as f:
            for k in keys:
                f.write("D %d\n" % k)
        base = os.path.join(WORK, "delall_base.idx")
        res = os.path.join(WORK, "delall_res.idx")
        _build_idx(bp, base)
        _apply_idx(base, delops, res)
        r = _run(["dump", res])
        assert r.stdout.decode("latin-1") == "height 1\nroot 1\nleaf page 1 next - entries\n"

    def test_root_collapse_scenario(self):
        """The scripted root-collapse scenario matches the reference exactly."""
        bp = os.path.join(DATA, "scenarios", "root_collapse.build")
        ap = os.path.join(DATA, "scenarios", "root_collapse.apply")
        base = os.path.join(WORK, "rc_base.idx")
        res = os.path.join(WORK, "rc_res.idx")
        _build_idx(bp, base)
        _apply_idx(base, ap, res)
        ops = ref.parse_ops(open(bp).read()) + ref.parse_ops(open(ap).read())
        t = ref.build(ops)
        assert _read(res) == ref.serialize(t)
        assert _run(["dump", res]).stdout.decode("latin-1") == ref.dump(t)

    def test_underflow_cascade_scenario(self):
        """The scripted underflow cascade matches the reference bytes and dump."""
        bp = os.path.join(DATA, "scenarios", "underflow_cascade.build")
        ap = os.path.join(DATA, "scenarios", "underflow_cascade.apply")
        base = os.path.join(WORK, "uc_base.idx")
        res = os.path.join(WORK, "uc_res.idx")
        _build_idx(bp, base)
        _apply_idx(base, ap, res)
        ops = ref.parse_ops(open(bp).read()) + ref.parse_ops(open(ap).read())
        t = ref.build(ops)
        assert _read(res) == ref.serialize(t)

    def test_apply_does_not_touch_input(self):
        """The apply command leaves its input index file unchanged."""
        bp, ap = _scenarios()[0]
        base = os.path.join(WORK, "immut_base.idx")
        res = os.path.join(WORK, "immut_res.idx")
        _build_idx(bp, base)
        before = _read(base)
        _apply_idx(base, ap, res)
        assert _read(base) == before

    def test_delete_absent_is_noop(self):
        """Deleting keys that are not present changes nothing."""
        bp = os.path.join(DATA, "range", "range_001.build")
        base = os.path.join(WORK, "noop_base.idx")
        res = os.path.join(WORK, "noop_res.idx")
        _build_idx(bp, base)
        delops = os.path.join(WORK, "noop.ops")
        with open(delops, "w") as f:
            f.write("D 999001\nD 999002\nD 999003\n")
        _apply_idx(base, delops, res)
        assert _read(res) == _read(base)

    def test_range_and_dump_consistent(self):
        """A full-span range returns every leaf entry in dump order."""
        bp = os.path.join(DATA, "range", "range_005.build")
        idx = os.path.join(WORK, "full.idx")
        _build_idx(bp, idx)
        r = _run(["range", idx, "0", "18446744073709551615"])
        got = [ln.split("\t")[0] for ln in r.stdout.decode("latin-1").split("\n") if ln]
        with open(bp) as f:
            t = ref.build(ref.parse_ops(f.read()))
        allk = [str(k) for k, _ in ref.range_scan(t, 0, 2**64 - 1)]
        assert got == allk
