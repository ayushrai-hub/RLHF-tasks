"""Milestone 3: the loader plays each save state to a winning transcript."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import qcref  # noqa: E402

APP_DIR = os.environ.get("QCAP_APP_DIR", "/app")
OUT = os.path.join(APP_DIR, "out")


def run_solve(name):
    r = subprocess.run(
        ["php", os.path.join(APP_DIR, "bin", "qcap.php"), "solve", name],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"solve {name} failed: {r.stderr}"


def expected_text(name, seed_value):
    graph = qcref.build_graph(name)
    steps = qcref.solve_run(graph, seed_value)
    assert steps is not None, f"reference could not solve {name}/{seed_value}"
    return qcref.run_text(graph, steps)


class TestMilestone3:
    """Verify the emitted transcripts match the deterministic winning runs."""

    def test_one_run_file_per_seed(self):
        """Solving a capsule writes one transcript per save state."""
        for name in qcref.capsules():
            run_solve(name)
            for seed in qcref.seeds(name):
                path = os.path.join(OUT, f"{name}.{seed['seed_id']}.run")
                assert os.path.isfile(path), f"missing run for {name} seed {seed['seed_id']}"

    def test_transcripts_match_byte_for_byte(self):
        """Each transcript equals the reference winning run exactly."""
        for name in qcref.capsules():
            run_solve(name)
            for seed in qcref.seeds(name):
                path = os.path.join(OUT, f"{name}.{seed['seed_id']}.run")
                with open(path) as fh:
                    got = fh.read()
                assert got == expected_text(name, seed["seed_value"]), (name, seed["seed_id"])

    def test_first_line_is_entry_title(self):
        """The transcript starts with the entry room's title."""
        for name in qcref.capsules():
            run_solve(name)
            graph = qcref.build_graph(name)
            entry_title = next(r["title"] for r in graph["rooms"] if r["id"] == graph["entry"])
            for seed in qcref.seeds(name):
                path = os.path.join(OUT, f"{name}.{seed['seed_id']}.run")
                with open(path) as fh:
                    first = fh.readline().rstrip("\n")
                assert first == entry_title, (name, seed["seed_id"])

    def test_seed_changes_route(self):
        """Different seeds can produce different routes for the same capsule."""
        varied = False
        for name in qcref.capsules():
            texts = {expected_text(name, s["seed_value"]) for s in qcref.seeds(name)}
            if len(texts) > 1:
                varied = True
        assert varied, "expected at least one capsule whose seeds yield different routes"

    def test_guarded_route_collects_key_first(self):
        """A winning route through a guarded exit collects its token in an earlier room."""
        import sqlite3
        con = sqlite3.connect(qcref._db())
        checked = False
        try:
            for name in qcref.capsules():
                graph = qcref.build_graph(name)
                rooms = {r["id"]: r for r in graph["rooms"]}
                guarded = {(r["id"], x["to"]): x["guard"]
                           for r in graph["rooms"] for x in r["exits"] if x["guard"]}
                if not guarded:
                    continue
                for seed in qcref.seeds(name):
                    steps = qcref.solve_run(graph, seed["seed_value"])
                    held = set(qcref._grants(rooms[graph["entry"]]["body"]))
                    cur = graph["entry"]
                    for s in steps:
                        key = (cur, s["to"])
                        if key in guarded:
                            assert guarded[key] in held, (name, seed["seed_id"], key)
                            checked = True
                        held |= set(qcref._grants(rooms[s["to"]]["body"]))
                        cur = s["to"]
        finally:
            con.close()
        assert checked, "expected at least one winning route to traverse a guarded exit"
