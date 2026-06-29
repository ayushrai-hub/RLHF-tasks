from __future__ import annotations
import json
from pathlib import Path

REFS_PATH = Path(__file__).resolve().parent / "_refs.json"
REFS = json.loads(REFS_PATH.read_text())

def assert_manifest(data, expected):
    assert data["bundle_id"] == expected["bundle_id"]
    assert data["train_count"] == expected["train_count"]
    assert data["test_count"] == expected["test_count"]
    assert data["column_codec"] == expected["column_codec"]
    assert data["sample_persistence_id"] == expected["sample_persistence_id"]
    assert data["policy"]["train_ratio"] == expected["policy"]["train_ratio"]
    assert data["policy"]["export_order"] == expected["policy"]["export_order"]

def assert_train(data, expected):
    assert data["bundle_id"] == expected["bundle_id"]
    assert data["train_count"] == expected["train_count"]
    got = {r["row_id"]: r["score_vector"] for r in data["score_vectors"]}
    exp = {r["row_id"]: r["score_vector"] for r in expected["score_vectors"]}
    assert got.keys() == exp.keys()
    for rid, vec in exp.items():
        assert len(got[rid]) == len(vec)
        for a, b in zip(got[rid], vec):
            assert abs(a - b) < 1e-9

def assert_export(data, expected):
    assert data["bundle_id"] == expected["bundle_id"]
    assert data["export_order"] == expected["export_order"]
    assert data["export_digest"] == expected["export_digest"]
    assert data["blocks"] == expected["blocks"]

def assert_audit(data, expected):
    assert data["bundle_id"] == expected["bundle_id"]
    assert data["audit_digest"] == expected["audit_digest"]
    assert len(data["parity_flags"]) == len(expected["parity_flags"])
