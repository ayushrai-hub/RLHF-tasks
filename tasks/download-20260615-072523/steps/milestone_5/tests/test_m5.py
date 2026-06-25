"""Milestone 5 tests for current-state entitlement verification."""

import json
import plistlib
import shutil
import subprocess
from pathlib import Path


OUT = Path("/app/out/entitlement-verification.json")
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
]
VERIFY = DYNAMIC_DIRS[-1]
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
REASONS = [
    "team identifier missing",
    "team identifier mismatch",
    "profile not allowed for platform",
    "app group prefix violation",
    "associated domain not allowed",
    "push environment profile mismatch",
]


def write_plist(path: Path, data: dict) -> None:
    """Write a plist fixture for verification checks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        plistlib.dump(data, fh, sort_keys=False)


def read_plist(path: Path) -> dict:
    """Read a plist fixture after commands run."""
    with path.open("rb") as fh:
        return plistlib.load(fh)


def reset_state() -> None:
    """Restore mutable policy and entitlement fixtures before each test."""
    OUT.unlink(missing_ok=True)
    APPLY_OUT.unlink(missing_ok=True)
    POLICY.write_text(json.dumps(BASE_POLICY, indent=2), encoding="utf-8")
    write_plist(PARTNER_ENT, dict(PARTNER_BASE))
    write_plist(LEGACY_ENT, dict(LEGACY_BASE))
    for path in DYNAMIC_DIRS:
        if path.exists():
            shutil.rmtree(path)


def run_verify(reset: bool = True) -> dict:
    """Run the public verify-remediation command and parse the report."""
    if reset:
        reset_state()
    OUT.unlink(missing_ok=True)
    subprocess.run(
        [
            "python3",
            "/app/tools/entitlement_audit.py",
            "verify-remediation",
            "/app/bundles",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


def run_apply() -> dict:
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
    return json.loads(APPLY_OUT.read_text(encoding="utf-8"))


class TestMilestone5:
    """Validate current-state verification after planning and remediation."""

    def test_verify_reports_base_drift_blocks_and_reason_counts(self) -> None:
        """Base verification must classify current bundles without mutating sidecars."""
        reset_state()
        before = read_plist(PARTNER_ENT)
        report = run_verify(reset=False)
        assert set(report) == {"bundles", "summary", "violation_counts"}
        assert [row["status"] for row in report["bundles"]] == [
            "blocked",
            "blocked",
            "drift",
            "compliant",
            "compliant",
        ]
        assert [row["bundle_id"] for row in report["bundles"]] == [
            "com.acme.legacybridge",
            "com.acme.wallet",
            "com.partner.portal",
            "com.acme.bank",
            "com.acme.ops",
        ]
        assert report["summary"] == {
            "total": 5,
            "compliant": 2,
            "drift": 1,
            "blocked": 2,
            "files_needing_changes": 1,
            "safe_change_count": 2,
            "blocked_with_sidecar": 2,
        }
        assert set(report["violation_counts"]) == set(REASONS)
        assert report["violation_counts"] == {
            "team identifier missing": 1,
            "team identifier mismatch": 0,
            "profile not allowed for platform": 1,
            "app group prefix violation": 1,
            "associated domain not allowed": 1,
            "push environment profile mismatch": 0,
        }
        rows = {row["bundle_id"]: row for row in report["bundles"]}
        assert {
            bundle_id: (row["platform"], row["profile"])
            for bundle_id, row in rows.items()
        } == {
            "com.acme.bank": ("ios", "ios-prod"),
            "com.acme.legacybridge": ("macos", "macos-prod"),
            "com.acme.ops": ("macos", "macos-dev"),
            "com.acme.wallet": ("ios", "adhoc-qa"),
            "com.partner.portal": ("ios", "ios-internal"),
        }
        assert {bundle_id: row["reasons"] for bundle_id, row in rows.items()} == {
            "com.acme.bank": [],
            "com.acme.legacybridge": ["team identifier missing"],
            "com.acme.ops": [],
            "com.acme.wallet": ["profile not allowed for platform"],
            "com.partner.portal": [
                "app group prefix violation",
                "associated domain not allowed",
            ],
        }
        assert {
            bundle_id: row["current"]
            for bundle_id, row in rows.items()
        } == {
            "com.acme.bank": {
                "team_identifier": "9JA89QQLNQ",
                "app_groups": ["group.com.acme.bank", "group.com.acme.shared"],
                "associated_domains": ["applinks:bank.acme.example"],
                "aps_environment": "production",
            },
            "com.acme.legacybridge": {
                "team_identifier": None,
                "app_groups": ["group.com.acme.legacy"],
                "associated_domains": [],
                "aps_environment": "production",
            },
            "com.acme.ops": {
                "team_identifier": "9JA89QQLNQ",
                "app_groups": ["group.com.acme.ops"],
                "associated_domains": ["applinks:ops.acme.test"],
                "aps_environment": "development",
            },
            "com.acme.wallet": {
                "team_identifier": "9JA89QQLNQ",
                "app_groups": ["group.com.acme.wallet"],
                "associated_domains": [],
                "aps_environment": "development",
            },
            "com.partner.portal": {
                "team_identifier": "9JA89QQLNQ",
                "app_groups": ["group.partner.portal"],
                "associated_domains": ["applinks:portal.partner.example"],
                "aps_environment": "development",
            },
        }
        assert {
            bundle_id: row["effective_policy"]
            for bundle_id, row in rows.items()
        }["com.acme.bank"] == {
            "team_identifier": "9JA89QQLNQ",
            "allowed_profiles": ["ios-prod", "ios-internal"],
            "expected_push_environment": "production",
            "required_app_group_prefix": "group.com.acme.",
            "allowed_associated_domain_suffixes": [".acme.example", ".acme.test"],
        }
        portal = rows["com.partner.portal"]
        assert portal["selected_sidecar"] == str(PARTNER_ENT)
        assert portal["needs_changes"] is True
        assert portal["blocked"] is False
        assert portal["pending_changes"] == {
            "set_team_identifier": None,
            "remove_app_groups": ["group.partner.portal"],
            "remove_associated_domains": ["applinks:portal.partner.example"],
            "set_aps_environment": None,
        }
        assert portal["current"]["app_groups"] == ["group.partner.portal"]
        assert read_plist(PARTNER_ENT) == before

    def test_verify_reflects_current_state_after_apply_remediation(self) -> None:
        """After safe remediations are applied, verification must not report stale drift."""
        reset_state()
        first_apply = run_apply()
        assert first_apply["summary"]["files_changed"] == 1
        report = run_verify(reset=False)
        assert report["summary"] == {
            "total": 5,
            "compliant": 3,
            "drift": 0,
            "blocked": 2,
            "files_needing_changes": 0,
            "safe_change_count": 0,
            "blocked_with_sidecar": 2,
        }
        assert report["violation_counts"]["app group prefix violation"] == 0
        assert report["violation_counts"]["associated domain not allowed"] == 0
        portal = {row["bundle_id"]: row for row in report["bundles"]}["com.partner.portal"]
        assert portal["status"] == "compliant"
        assert portal["pending_changes"]["remove_app_groups"] == []
        assert portal["pending_changes"]["remove_associated_domains"] == []

    def test_verify_uses_overrides_push_targets_and_does_not_mutate(self) -> None:
        """Dynamic override drift must include pending push changes without editing files."""
        reset_state()
        policy = dict(BASE_POLICY)
        policy["bundle_overrides"] = {
            "com.partner.verify": {
                "allowed_profiles": ["ios-verify"],
                "required_app_group_prefix": "group.partner.",
                "allowed_associated_domain_suffixes": [".partner.example"],
                "expected_push_environment": "production",
            }
        }
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        write_plist(
            VERIFY / "Info.plist",
            {
                "CFBundleIdentifier": "com.partner.verify",
                "CFBundleDisplayName": "Partner Verify",
                "CFBundleExecutable": "PartnerVerify",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-verify",
            },
        )
        entitlements = {
            "com.apple.security.application-groups": [
                "group.partner.verify",
                "group.external.verify",
            ],
            "keychain-access-groups": ["9JA89QQLNQ.com.partner.verify"],
            "com.apple.developer.associated-domains": [
                "applinks:verify.partner.example",
                "applinks:verify.external.example",
            ],
            "aps-environment": "development",
            "com.apple.developer.team-identifier": "9JA89QQLNQ",
        }
        write_plist(VERIFY / "PartnerVerify.entitlements", entitlements)
        report = run_verify(reset=False)
        probe = {row["bundle_id"]: row for row in report["bundles"]}["com.partner.verify"]
        assert probe["status"] == "drift"
        assert probe["effective_policy"]["team_identifier"] == "9JA89QQLNQ"
        assert probe["effective_policy"]["allowed_profiles"] == ["ios-verify"]
        assert probe["effective_policy"]["required_app_group_prefix"] == "group.partner."
        assert probe["effective_policy"]["allowed_associated_domain_suffixes"] == [
            ".partner.example"
        ]
        assert probe["effective_policy"]["expected_push_environment"] == "production"
        assert probe["pending_changes"] == {
            "set_team_identifier": None,
            "remove_app_groups": ["group.external.verify"],
            "remove_associated_domains": ["applinks:verify.external.example"],
            "set_aps_environment": "production",
        }
        assert report["summary"]["safe_change_count"] == 5
        assert report["violation_counts"]["push environment profile mismatch"] == 1
        assert read_plist(VERIFY / "PartnerVerify.entitlements") == entitlements
