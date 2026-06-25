"""Verifier for milestone 1 config normalization behavior."""

import json
import subprocess
from pathlib import Path


APP = Path("/app")


def run_check_config(config, name):
    work = APP / "tmp" / name
    work.mkdir(parents=True, exist_ok=True)
    config_path = work / "rules.json"
    out_path = work / "normalized.json"
    if out_path.exists():
        out_path.unlink()
    config_path.write_text(json.dumps(config))
    result = subprocess.run(
        [
            "go",
            "run",
            "./cmd/ledger",
            "check-config",
            str(config_path),
            "--out",
            str(out_path),
        ],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=60,
    )
    return result, out_path


class TestMilestone1:
    def test_normalized_config_is_deterministic_and_complete(self):
        """Config normalization should canonicalize services and aliases into sorted JSON."""
        work = APP / "tmp" / "m1_good"
        work.mkdir(parents=True, exist_ok=True)
        config_path = work / "rules.json"
        out_path = work / "normalized.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 4,
                    "services": [
                        {
                            "name": " Auth..Service ",
                            "aliases": ["sso._-gate", "AUTH...v2", "auth service"],
                            "tier": "standard",
                            "weight": 0.7,
                            "retention_days": 60,
                        },
                        {
                            "name": " Billing API ",
                            "aliases": ["billing_api", "BILLING api", "Invoices"],
                            "tier": "critical",
                            "weight": 1.0,
                            "retention_days": 365,
                        },
                        {
                            "name": "Data Worker",
                            "aliases": ["worker", "DATA__worker", "batch-loader"],
                            "tier": "standard",
                            "weight": 0.45,
                            "retention_days": 30,
                        },
                    ],
                }
            )
        )

        result = subprocess.run(
            [
                "go",
                "run",
                "./cmd/ledger",
                "check-config",
                str(config_path),
                "--out",
                str(out_path),
            ],
            cwd=APP,
            text=True,
            capture_output=True,
            timeout=60,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(out_path.read_text())
        assert [svc["service"] for svc in payload["services"]] == [
            "auth-service",
            "billing-api",
            "data-worker",
        ]
        assert payload["services"][0]["aliases"] == [
            "auth-service",
            "auth-v2",
            "sso-gate",
        ]
        assert payload["services"][1]["aliases"] == [
            "billing-api",
            "invoices",
        ]
        assert payload["services"][2]["aliases"] == [
            "batch-loader",
            "data-worker",
            "worker",
        ]
        assert payload["alias_to_service"] == {
            "auth-service": "auth-service",
            "auth-v2": "auth-service",
            "batch-loader": "data-worker",
            "billing-api": "billing-api",
            "data-worker": "data-worker",
            "invoices": "billing-api",
            "sso-gate": "auth-service",
            "worker": "data-worker",
        }
        assert payload["services"][1]["weight"] == 1.0
        assert payload["services"][1]["retention_days"] == 365

    def test_general_punctuation_and_single_service_shape_are_normalized(self):
        """General punctuation runs should collapse in a single-service config."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": " ..Audit::Log!! ",
                        "aliases": ["AUDIT.log", "audit__log", "log---ingest"],
                        "tier": "standard",
                        "weight": 0.25,
                        "retention_days": 45,
                    }
                ],
            },
            "m1_good_punctuation",
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(out_path.read_text())
        assert payload["services"] == [
            {
                "service": "audit-log",
                "aliases": ["audit-log", "log-ingest"],
                "tier": "standard",
                "weight": 0.25,
                "retention_days": 45,
            }
        ]
        assert payload["alias_to_service"] == {
            "audit-log": "audit-log",
            "log-ingest": "audit-log",
        }

    def test_boundary_retention_and_weight_values_are_accepted(self):
        """Inclusive retention endpoints and weight 1.0 should remain valid."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Edge Gateway",
                        "aliases": ["gateway"],
                        "tier": "standard",
                        "weight": 1.0,
                        "retention_days": 1,
                    },
                    {
                        "name": "Archive Worker",
                        "aliases": ["archive"],
                        "tier": "standard",
                        "weight": 0.001,
                        "retention_days": 365,
                    },
                ],
            },
            "m1_good_boundaries",
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(out_path.read_text())
        assert [svc["service"] for svc in payload["services"]] == [
            "archive-worker",
            "edge-gateway",
        ]
        assert payload["services"][0]["weight"] == 0.001
        assert payload["services"][0]["retention_days"] == 365
        assert payload["services"][1]["weight"] == 1.0
        assert payload["services"][1]["retention_days"] == 1

    def test_duplicate_alias_is_rejected_before_output_is_written(self):
        """Aliases that normalize to another service should fail independently."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Search API",
                        "aliases": ["lookup"],
                        "tier": "critical",
                        "weight": 0.8,
                        "retention_days": 90,
                    },
                    {
                        "name": "Lookup",
                        "aliases": ["Search_API"],
                        "tier": "standard",
                        "weight": 0.6,
                        "retention_days": 30,
                    },
                ],
            },
            "m1_bad_alias",
        )
        assert result.returncode != 0
        assert "alias" in result.stderr.lower()
        assert not out_path.exists()

    def test_duplicate_canonical_service_is_rejected_before_output_is_written(self):
        """Two service names that normalize to the same canonical name should fail."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Auth API",
                        "aliases": [],
                        "tier": "critical",
                        "weight": 0.9,
                        "retention_days": 90,
                    },
                    {
                        "name": "auth-api",
                        "aliases": [],
                        "tier": "standard",
                        "weight": 0.5,
                        "retention_days": 30,
                    },
                ],
            },
            "m1_bad_duplicate_service",
        )
        assert result.returncode != 0
        assert "name" in result.stderr.lower()
        assert not out_path.exists()

    def test_empty_service_name_is_rejected_before_output_is_written(self):
        """Empty service names should fail validation without writing output."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "   ",
                        "aliases": ["blank"],
                        "tier": "standard",
                        "weight": 0.5,
                        "retention_days": 30,
                    }
                ],
            },
            "m1_bad_empty_name",
        )
        assert result.returncode != 0
        assert "name" in result.stderr.lower()
        assert not out_path.exists()

    def test_empty_alias_is_rejected_before_output_is_written(self):
        """Aliases that normalize to an empty string should fail validation."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Search API",
                        "aliases": ["  ...___  "],
                        "tier": "critical",
                        "weight": 0.8,
                        "retention_days": 90,
                    }
                ],
            },
            "m1_bad_empty_alias",
        )
        assert result.returncode != 0
        assert "alias" in result.stderr.lower()
        assert not out_path.exists()

    def test_invalid_weight_is_rejected_before_output_is_written(self):
        """Weights outside the open-closed interval (0, 1] should fail."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Search API",
                        "aliases": ["search"],
                        "tier": "critical",
                        "weight": 1.4,
                        "retention_days": 90,
                    }
                ],
            },
            "m1_bad_weight",
        )
        assert result.returncode != 0
        assert "weight" in result.stderr.lower()
        assert not out_path.exists()

    def test_zero_weight_is_rejected_before_output_is_written(self):
        """Zero is outside the allowed weight interval (0, 1]."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Search API",
                        "aliases": ["search"],
                        "tier": "critical",
                        "weight": 0.0,
                        "retention_days": 90,
                    }
                ],
            },
            "m1_bad_zero_weight",
        )
        assert result.returncode != 0
        assert "weight" in result.stderr.lower()
        assert not out_path.exists()

    def test_negative_weight_is_rejected_before_output_is_written(self):
        """Negative values are outside the allowed weight interval (0, 1]."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Search API",
                        "aliases": ["search"],
                        "tier": "critical",
                        "weight": -0.5,
                        "retention_days": 90,
                    }
                ],
            },
            "m1_bad_negative_weight",
        )
        assert result.returncode != 0
        assert "weight" in result.stderr.lower()
        assert not out_path.exists()

    def test_invalid_retention_is_rejected_before_output_is_written(self):
        """Retention windows outside 1..365 should fail validation."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Search API",
                        "aliases": ["search"],
                        "tier": "critical",
                        "weight": 0.8,
                        "retention_days": 0,
                    }
                ],
            },
            "m1_bad_retention",
        )
        assert result.returncode != 0
        assert "retention" in result.stderr.lower()
        assert not out_path.exists()

    def test_retention_above_365_is_rejected_before_output_is_written(self):
        """Retention windows greater than 365 days should fail validation."""
        result, out_path = run_check_config(
            {
                "version": 2,
                "services": [
                    {
                        "name": "Search API",
                        "aliases": ["search"],
                        "tier": "critical",
                        "weight": 0.8,
                        "retention_days": 400,
                    }
                ],
            },
            "m1_bad_high_retention",
        )
        assert result.returncode != 0
        assert "retention" in result.stderr.lower()
        assert not out_path.exists()
