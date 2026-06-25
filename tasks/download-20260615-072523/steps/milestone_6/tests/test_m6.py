"""Milestone 6 tests for source-aware entitlement risk reporting."""

import json
import plistlib
import shutil
import subprocess
from pathlib import Path


OUT = Path("/app/out/entitlement-risk-register.json")
APPLY_OUT = Path("/app/out/entitlement-apply.json")
POLICY = Path("/app/policy/signing-policy.json")
PARTNER_ENT = Path("/app/bundles/PartnerPortal/PartnerPortal.entitlements")
LEGACY_ENT = Path("/app/bundles/LegacyBridge/LegacyBridge.entitlements")
DYNAMIC_DIRS = [
    Path("/app/bundles/DynamicClip"),
    Path("/app/bundles/RemediateProbe"),
    Path("/app/bundles/NoPushPolicy"),
    Path("/app/bundles/ApplyProbe"),
    Path("/app/bundles/VerifyProbe"),
    Path("/app/bundles/RiskProbe"),
    Path("/app/bundles/RiskDrift"),
    Path("/app/bundles/RiskMixed"),
]
RISK = DYNAMIC_DIRS[-3]
RISK_DRIFT = DYNAMIC_DIRS[-2]
RISK_MIXED = DYNAMIC_DIRS[-1]
BASE_POLICY = {
    "required_team_id": "9JA89QQLNQ",
    "allowed_profiles": {
        "ios": ["ios-prod", "ios-internal"],
        "macos": ["macos-prod", "macos-dev"],
    },
    "required_app_group_prefix": "group.com.acme.",
    "allowed_associated_domain_suffixes": [".acme.example", ".acme.test"],
    "push_profile_environments": {
        "ios-prod": "production",
        "ios-internal": "development",
        "macos-prod": "production",
        "macos-dev": "development",
    },
    "bundle_overrides": {},
}
PARTNER_BASE = {
    "com.apple.security.application-groups": ["group.partner.portal"],
    "keychain-access-groups": ["9JA89QQLNQ.com.partner.portal"],
    "com.apple.developer.associated-domains": ["applinks:portal.partner.example"],
    "aps-environment": "development",
    "com.apple.developer.team-identifier": "9JA89QQLNQ",
}
LEGACY_BASE = {
    "com.apple.security.application-groups": ["group.com.acme.legacy"],
    "keychain-access-groups": ["9JA89QQLNQ.com.acme.legacybridge"],
    "aps-environment": "production",
}


def write_plist(path: Path, data: dict) -> None:
    """Write a plist fixture used by risk-register checks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        plistlib.dump(data, fh, sort_keys=False)


def read_plist(path: Path) -> dict:
    """Read a mutable entitlement fixture after commands run."""
    with path.open("rb") as fh:
        return plistlib.load(fh)


def reset_state() -> None:
    """Restore policy, mutable entitlements, and dynamic bundles."""
    OUT.unlink(missing_ok=True)
    APPLY_OUT.unlink(missing_ok=True)
    POLICY.write_text(json.dumps(BASE_POLICY, indent=2), encoding="utf-8")
    write_plist(PARTNER_ENT, dict(PARTNER_BASE))
    write_plist(LEGACY_ENT, dict(LEGACY_BASE))
    for path in DYNAMIC_DIRS:
        if path.exists():
            shutil.rmtree(path)


def run_risk(reset: bool = True) -> dict:
    """Run risk-register and parse the JSON report."""
    if reset:
        reset_state()
    OUT.unlink(missing_ok=True)
    subprocess.run(
        [
            "python3",
            "/app/tools/entitlement_audit.py",
            "risk-register",
            "/app/bundles",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


def run_apply() -> None:
    """Run apply-remediation without resetting state."""
    APPLY_OUT.unlink(missing_ok=True)
    subprocess.run(
        [
            "python3",
            "/app/tools/entitlement_audit.py",
            "apply-remediation",
            "/app/bundles",
            str(POLICY),
            str(APPLY_OUT),
        ],
        check=True,
    )


class TestMilestone6:
    """Validate source-aware entitlement risk register behavior."""

    def test_base_register_schema_sorting_and_counts(self) -> None:
        """Base bundles must be risk-sorted with zero-count capability indexes."""
        report = run_risk()
        assert set(report) == {"risks", "summary", "source_index"}
        assert [row["bundle_id"] for row in report["risks"]] == [
            "com.acme.legacybridge",
            "com.acme.wallet",
            "com.partner.portal",
            "com.acme.bank",
            "com.acme.ops",
        ]
        assert [row["risk_level"] for row in report["risks"]] == [
            "medium",
            "medium",
            "medium",
            "low",
            "low",
        ]
        assert report["summary"] == {
            "total": 5,
            "by_risk_level": {"critical": 0, "high": 0, "medium": 3, "low": 2},
            "by_status": {"blocked": 2, "drift": 1, "compliant": 2},
            "bundles_with_source_usage": 0,
            "missing_runtime_support_count": 0,
            "policy_conflict_count": 4,
        }
        assert report["source_index"] == {
            "push": [],
            "app_group": [],
            "associated_domain": [],
            "keychain": [],
        }
        portal = {row["bundle_id"]: row for row in report["risks"]}["com.partner.portal"]
        assert portal["status"] == "drift"
        assert portal["policy_conflicts"] == [
            "app group prefix violation",
            "associated domain not allowed",
        ]
        assert portal["remediation_required"] is True
        assert portal["evidence"] == []

    def test_dynamic_source_capabilities_create_critical_missing_support(self) -> None:
        """Runtime source markers must be correlated with current entitlement support."""
        reset_state()
        write_plist(
            RISK / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.riskprobe",
                "CFBundleDisplayName": "Acme Risk Probe",
                "CFBundleExecutable": "RiskProbe",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            RISK / "RiskProbe.entitlements",
            {
                "keychain-access-groups": ["9JA89QQLNQ.com.acme.riskprobe"],
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        (RISK / "RiskProbe.m").write_text(
            "\n".join(
                [
                    "#import <Foundation/Foundation.h>",
                    "void Probe(void) {",
                    "  [[UIApplication sharedApplication] registerForRemoteNotifications];",
                    "  [[NSFileManager defaultManager] containerURLForSecurityApplicationGroupIdentifier:@\"group.acme.probe\"];",
                    "  NSUserActivity *activity = [[NSUserActivity alloc] initWithActivityType:NSUserActivityTypeBrowsingWeb];",
                    "  SecItemCopyMatching((__bridge CFDictionaryRef)@{}, NULL);",
                    "}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        report = run_risk(reset=False)
        probe = {row["bundle_id"]: row for row in report["risks"]}["com.acme.riskprobe"]
        assert probe["status"] == "compliant"
        assert probe["risk_level"] == "critical"
        assert probe["capabilities_used"] == [
            "push",
            "app_group",
            "associated_domain",
            "keychain",
        ]
        assert probe["missing_runtime_support"] == [
            "push",
            "app_group",
            "associated_domain",
        ]
        assert probe["policy_conflicts"] == []
        assert probe["remediation_required"] is True
        assert probe["source_files"] == ["RiskProbe.m"]
        assert probe["evidence"] == [
            {
                "capability": "push",
                "file": "RiskProbe.m",
                "line": 3,
                "marker": "registerForRemoteNotifications",
            },
            {
                "capability": "app_group",
                "file": "RiskProbe.m",
                "line": 4,
                "marker": "containerURLForSecurityApplicationGroupIdentifier",
            },
            {
                "capability": "associated_domain",
                "file": "RiskProbe.m",
                "line": 5,
                "marker": "NSUserActivityTypeBrowsingWeb",
            },
            {
                "capability": "keychain",
                "file": "RiskProbe.m",
                "line": 6,
                "marker": "SecItemCopyMatching",
            },
        ]
        assert report["summary"]["total"] == 6
        assert report["summary"]["by_risk_level"] == {
            "critical": 1,
            "high": 0,
            "medium": 3,
            "low": 2,
        }
        assert report["summary"]["bundles_with_source_usage"] == 1
        assert report["summary"]["missing_runtime_support_count"] == 3
        assert report["source_index"] == {
            "push": ["com.acme.riskprobe"],
            "app_group": ["com.acme.riskprobe"],
            "associated_domain": ["com.acme.riskprobe"],
            "keychain": ["com.acme.riskprobe"],
        }

    def test_drift_bundle_with_objective_cxx_capability_usage_is_high_risk(self) -> None:
        """Drift bundles with entitlement-backed .mm capability usage must be high risk."""
        reset_state()
        write_plist(
            RISK_DRIFT / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.riskdrift",
                "CFBundleDisplayName": "Acme Risk Drift",
                "CFBundleExecutable": "RiskDrift",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            RISK_DRIFT / "RiskDrift.entitlements",
            {
                "com.apple.security.application-groups": [
                    "group.com.acme.riskdrift",
                    "group.external.riskdrift",
                ],
                "keychain-access-groups": ["9JA89QQLNQ.com.acme.riskdrift"],
                "com.apple.developer.associated-domains": [
                    "applinks:riskdrift.acme.example"
                ],
                "aps-environment": "development",
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        (RISK_DRIFT / "RiskDrift.mm").write_text(
            "\n".join(
                [
                    "#import <Foundation/Foundation.h>",
                    "void Drift(void) {",
                    "  [[NSFileManager defaultManager] containerURLForSecurityApplicationGroupIdentifier:@\"group.com.acme.riskdrift\"];",
                    "}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        report = run_risk(reset=False)
        drift = {row["bundle_id"]: row for row in report["risks"]}["com.acme.riskdrift"]
        assert drift["status"] == "drift"
        assert drift["risk_level"] == "high"
        assert drift["capabilities_used"] == ["app_group"]
        assert drift["missing_runtime_support"] == []
        assert drift["policy_conflicts"] == ["app group prefix violation"]
        assert drift["source_files"] == ["RiskDrift.mm"]
        assert drift["evidence"] == [
            {
                "capability": "app_group",
                "file": "RiskDrift.mm",
                "line": 3,
                "marker": "containerURLForSecurityApplicationGroupIdentifier",
            }
        ]

    def test_normalized_support_and_direct_source_scan_boundaries(self) -> None:
        """Runtime support checks must use normalized entitlements and ignore nested source."""
        reset_state()
        write_plist(
            RISK_MIXED / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.riskmixed",
                "CFBundleDisplayName": "Acme Risk Mixed",
                "CFBundleExecutable": "RiskMixed",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            RISK_MIXED / "RiskMixed.entitlements",
            {
                "com.apple.security.application-groups": ["group.com.acme.riskmixed"],
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        (RISK_MIXED / "RiskMixed.h").write_text(
            "\n".join(
                [
                    "#import <Security/Security.h>",
                    "void StoreSecret(void) {",
                    "  SecItemAdd((__bridge CFDictionaryRef)@{}, NULL);",
                    "}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (RISK_MIXED / "RiskMixed.mm").write_text(
            "\n".join(
                [
                    "#import <Foundation/Foundation.h>",
                    "void Share(void) {",
                    "  [[NSUserDefaults alloc] initWithSuiteName:@\"group.com.acme.riskmixed\"];",
                    "}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        nested = RISK_MIXED / "Nested"
        nested.mkdir()
        (nested / "Ignored.m").write_text(
            "[[UIApplication sharedApplication] registerForRemoteNotifications];\n",
            encoding="utf-8",
        )
        report = run_risk(reset=False)
        mixed = {row["bundle_id"]: row for row in report["risks"]}["com.acme.riskmixed"]
        assert mixed["status"] == "compliant"
        assert mixed["risk_level"] == "critical"
        assert mixed["capabilities_used"] == ["app_group", "keychain"]
        assert mixed["missing_runtime_support"] == ["keychain"]
        assert mixed["source_files"] == ["RiskMixed.h", "RiskMixed.mm"]
        assert mixed["evidence"] == [
            {
                "capability": "app_group",
                "file": "RiskMixed.mm",
                "line": 3,
                "marker": "initWithSuiteName",
            },
            {
                "capability": "keychain",
                "file": "RiskMixed.h",
                "line": 3,
                "marker": "SecItemAdd",
            },
        ]
        assert report["source_index"]["app_group"] == ["com.acme.riskmixed"]
        assert report["source_index"]["keychain"] == ["com.acme.riskmixed"]
        assert "com.acme.riskmixed" not in report["source_index"]["push"]

    def test_register_reflects_state_after_apply_without_mutating(self) -> None:
        """Risk-register must read current post-apply state and leave plists unchanged."""
        reset_state()
        run_apply()
        before = read_plist(PARTNER_ENT)
        report = run_risk(reset=False)
        assert read_plist(PARTNER_ENT) == before
        assert report["summary"]["by_status"] == {
            "blocked": 2,
            "drift": 0,
            "compliant": 3,
        }
        assert report["summary"]["by_risk_level"] == {
            "critical": 0,
            "high": 0,
            "medium": 2,
            "low": 3,
        }
        portal = {row["bundle_id"]: row for row in report["risks"]}["com.partner.portal"]
        assert portal["status"] == "compliant"
        assert portal["risk_level"] == "low"
        assert portal["policy_conflicts"] == []
        assert portal["remediation_required"] is False
