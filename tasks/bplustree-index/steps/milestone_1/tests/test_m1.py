import os
import glob
import struct
import subprocess

import pytest

import bpt_ref as ref

APP = "/app"
BPT = os.path.join(APP, "bin", "bpt")
DATA = os.path.join(APP, "data")
WORK = "/tmp/bpt_m1"


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
    r = _run(["build", ops_path, "--out", out_path])
    assert os.path.exists(out_path)
    return r


def _ops_files():
    fs = sorted(glob.glob(os.path.join(DATA, "build", "*.ops")))
    assert len(fs) >= 100
    return fs


def _ref_from_file(ops_path):
    with open(ops_path, "r") as f:
        ops = ref.parse_ops(f.read())
    return ref.build(ops), ops


@pytest.fixture(scope="module", autouse=True)
def prepared():
    """Build the agent binary and a working directory once for milestone 1."""
    _build_binary()
    os.makedirs(WORK, exist_ok=True)


class TestMilestone1:
    def test_serialize_bytes_exact(self):
        """Every build fixture serializes to the exact byte image the format dictates."""
        for i, ops_path in enumerate(_ops_files()):
            out = os.path.join(WORK, "b%d.idx" % i)
            _build_idx(ops_path, out)
            with open(out, "rb") as f:
                got = f.read()
            t, _ = _ref_from_file(ops_path)
            expected = ref.serialize(t)
            assert got == expected, "byte mismatch on %s" % ops_path

    def test_file_length_multiple_of_page(self):
        """Every produced index is a whole number of 4096-byte pages."""
        for i, ops_path in enumerate(_ops_files()[:40]):
            out = os.path.join(WORK, "len%d.idx" % i)
            _build_idx(ops_path, out)
            assert os.path.getsize(out) % 4096 == 0
            assert os.path.getsize(out) >= 4096

    def test_superblock_fields(self):
        """The superblock carries the magic and the fixed capacity constants."""
        for i, ops_path in enumerate(_ops_files()[:40]):
            out = os.path.join(WORK, "sb%d.idx" % i)
            _build_idx(ops_path, out)
            with open(out, "rb") as f:
                sb = f.read(4096)
            assert sb[0:4] == b"BPT1"
            assert struct.unpack_from(">I", sb, 4)[0] == 4096
            assert struct.unpack_from(">H", sb, 16)[0] == 4
            assert struct.unpack_from(">H", sb, 18)[0] == 5
            pc = struct.unpack_from(">I", sb, 12)[0]
            assert os.path.getsize(out) == pc * 4096

    def test_dump_matches_reference(self):
        """The canonical dump matches the reference tree structure exactly."""
        for i, ops_path in enumerate(_ops_files()):
            out = os.path.join(WORK, "d%d.idx" % i)
            _build_idx(ops_path, out)
            r = _run(["dump", out])
            got = r.stdout.decode("latin-1")
            t, _ = _ref_from_file(ops_path)
            assert got == ref.dump(t), "dump mismatch on %s" % ops_path

    def test_get_present_and_absent(self):
        """Point lookups return the last inserted value, or NOT-FOUND for absent keys."""
        for i, ops_path in enumerate(_ops_files()[::3]):
            out = os.path.join(WORK, "g%d.idx" % i)
            _build_idx(ops_path, out)
            t, ops = _ref_from_file(ops_path)
            keymap = ref.present_keys(ops)
            some = list(keymap.items())[:20]
            for k, v in some:
                r = _run(["get", out, str(k)])
                assert r.stdout.decode("latin-1") == v + "\n", "get %d on %s" % (k, ops_path)
            absent = 0
            probe = 700000
            while absent < 5:
                if probe not in keymap:
                    r = _run(["get", out, str(probe)])
                    assert r.stdout.decode("latin-1") == "NOT-FOUND\n"
                    absent += 1
                probe += 1

    def test_dump_header_lines(self):
        """The dump begins with a height line and a root line naming page 1."""
        out = os.path.join(WORK, "hdr.idx")
        _build_idx(os.path.join(DATA, "build", "bound_asc_000.ops"), out)
        r = _run(["dump", out])
        lines = r.stdout.decode("latin-1").split("\n")
        assert lines[0].startswith("height ")
        assert lines[1] == "root 1"

    def test_leaf_split_boundary_five(self):
        """Inserting five ascending keys splits the root leaf into a height-two tree."""
        out = os.path.join(WORK, "five.idx")
        _build_idx(os.path.join(DATA, "build", "bound_asc_000.ops"), out)
        r = _run(["dump", out])
        got = r.stdout.decode("latin-1")
        with open(os.path.join(DATA, "build", "bound_asc_000.ops")) as f:
            t = ref.build(ref.parse_ops(f.read()))
        assert got == ref.dump(t)
        assert t.height == 2
        assert not t.root.leaf

    def test_single_key_tree_is_one_leaf(self):
        """A one-key tree is a single root leaf with height one and no successor."""
        ops = os.path.join(WORK, "one.ops")
        with open(ops, "w") as f:
            f.write("I 42 answer\n")
        out = os.path.join(WORK, "one.idx")
        _build_idx(ops, out)
        r = _run(["dump", out])
        got = r.stdout.decode("latin-1")
        assert got == "height 1\nroot 1\nleaf page 1 next - entries 42:answer\n"

    def test_overwrite_keeps_structure(self):
        """Re-inserting an existing key overwrites its value without changing the shape."""
        ops = os.path.join(WORK, "ow.ops")
        with open(ops, "w") as f:
            for k in range(1, 13):
                f.write("I %d a%d\n" % (k, k))
            f.write("I 5 REPLACED\n")
        out = os.path.join(WORK, "ow.idx")
        _build_idx(ops, out)
        with open(out, "rb") as f:
            got = f.read()
        with open(ops) as f:
            t = ref.build(ref.parse_ops(f.read()))
        assert got == ref.serialize(t)
        r = _run(["get", out, "5"])
        assert r.stdout.decode("latin-1") == "REPLACED\n"

    def test_reference_roundtrip_get_all(self):
        """For a mid-size fixture, every present key is retrievable with its exact value."""
        ops_path = os.path.join(DATA, "build", "bound_asc_014.ops")
        out = os.path.join(WORK, "all.idx")
        _build_idx(ops_path, out)
        t, ops = _ref_from_file(ops_path)
        for k, v in ref.present_keys(ops).items():
            r = _run(["get", out, str(k)])
            assert r.stdout.decode("latin-1") == v + "\n"

    def test_leaf_chain_left_to_right(self):
        """Leaf pages appear in ascending key order and their next pointers chain forward."""
        for ops_path in [os.path.join(DATA, "build", "bound_asc_020.ops"),
                         os.path.join(DATA, "build", "bound_desc_020.ops")]:
            out = os.path.join(WORK, "chain.idx")
            _build_idx(ops_path, out)
            r = _run(["dump", out])
            leaves = [ln for ln in r.stdout.decode("latin-1").split("\n") if ln.startswith("leaf ")]
            firsts = []
            for ln in leaves:
                tail = ln.split(" entries")[1].strip()
                if tail:
                    firsts.append(int(tail.split()[0].split(":")[0]))
            assert firsts == sorted(firsts)

    def test_usage_errors_nonzero_no_stdout(self):
        """Malformed invocations print nothing to stdout and exit non-zero."""
        cases = [
            [],
            ["build"],
            ["build", "/no/such/file.ops", "--out", os.path.join(WORK, "x.idx")],
            ["get", os.path.join(WORK, "x.idx")],
            ["dump"],
            ["frobnicate"],
        ]
        for c in cases:
            r = _run(c, check=False)
            assert r.returncode != 0, "expected failure for %s" % c
            assert r.stdout == b"", "expected empty stdout for %s" % c

    def test_deterministic_rebuild(self):
        """Building the same fixture twice yields byte-identical files."""
        ops_path = os.path.join(DATA, "build", "build_012.ops")
        a = os.path.join(WORK, "det_a.idx")
        b = os.path.join(WORK, "det_b.idx")
        _build_idx(ops_path, a)
        _build_idx(ops_path, b)
        with open(a, "rb") as f:
            da = f.read()
        with open(b, "rb") as f:
            db = f.read()
        assert da == db
