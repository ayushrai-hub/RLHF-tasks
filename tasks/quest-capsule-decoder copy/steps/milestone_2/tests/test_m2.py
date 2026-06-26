"""Milestone 2: the loader reconstructs the decoded room graph for each capsule."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import qcref  # noqa: E402

APP_DIR = os.environ.get("QCAP_APP_DIR", "/app")
OUT = os.path.join(APP_DIR, "out")


def run_graph(name):
    r = subprocess.run(
        ["php", os.path.join(APP_DIR, "bin", "qcap.php"), "graph", name],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"graph {name} failed: {r.stderr}"
    path = os.path.join(OUT, name + ".graph.json")
    assert os.path.isfile(path), f"missing graph artifact for {name}"
    with open(path) as fh:
        return json.load(fh)


class TestMilestone2:
    """Verify the reconstructed graph matches the decoded cartridge."""

    def test_entry_and_room_ids(self):
        """Graph reports the entry room and the full set of room ids and kinds."""
        for name in qcref.capsules():
            got = run_graph(name)
            exp = qcref.build_graph(name)
            assert got["entry"] == exp["entry"], name
            assert [r["id"] for r in got["rooms"]] == [r["id"] for r in exp["rooms"]], name
            assert [r["kind"] for r in got["rooms"]] == [r["kind"] for r in exp["rooms"]], name

    def test_titles_and_bodies_decoded(self):
        """Room titles and bodies are decoded text, not raw glyph payloads."""
        for name in qcref.capsules():
            got = run_graph(name)
            exp = {r["id"]: r for r in qcref.build_graph(name)["rooms"]}
            for room in got["rooms"]:
                e = exp[room["id"]]
                assert room["title"] == e["title"], (name, room["id"])
                assert room["body"] == e["body"], (name, room["id"])

    def test_exits_match_and_ordered(self):
        """Each room's exits decode and are ordered by label then target."""
        for name in qcref.capsules():
            got = run_graph(name)
            exp = {r["id"]: r for r in qcref.build_graph(name)["rooms"]}
            for room in got["rooms"]:
                e = exp[room["id"]]
                got_exits = [(x["label"], x["to"], x["guard"]) for x in room["exits"]]
                exp_exits = [(x["label"], x["to"], x["guard"]) for x in e["exits"]]
                assert got_exits == exp_exits, (name, room["id"])

    def test_guards_decoded(self):
        """Guard tokens decode to text and unguarded exits report null."""
        for name in qcref.capsules():
            got = run_graph(name)
            exp = {r["id"]: r for r in qcref.build_graph(name)["rooms"]}
            for room in got["rooms"]:
                e = exp[room["id"]]
                assert [x["guard"] for x in room["exits"]] == [x["guard"] for x in e["exits"]], name

    def test_single_entry_single_exit(self):
        """Every capsule has exactly one entry room and one exit room."""
        for name in qcref.capsules():
            got = run_graph(name)
            kinds = [r["kind"] for r in got["rooms"]]
            assert kinds.count("entry") == 1, name
            assert kinds.count("exit") == 1, name
