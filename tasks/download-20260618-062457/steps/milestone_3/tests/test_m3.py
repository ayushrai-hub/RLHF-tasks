"""Milestone 3 tests for signing remediation generation."""

import json
import plistlib
import shutil
import subprocess
from pathlib import Path


OUT = Path("/app/out/entitlement-remediation.json")
POLICY = Path("/app/policy/signing-policy.json")
DYNAMIC_DIRS = [
    Path("/app/bundles/DynamicClip"),
    Path("/app/bundles/RemediateProbe"),
    Path("/app/bundles/NoPushPolicy"),
]
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


def write_plist(path: Path, data: dict) -> None:
    """Write a plist fixture used by runtime remediation checks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        plistlib.dump(data, fh, sort_keys=False)


def cleanup_dynamic() -> None:
    """Remove dynamic bundles from previous tests and milestones."""
    for path in DYNAMIC_DIRS:
        if path.exists():
            shutil.rmtree(path)


def reset_policy() -> None:
    """Restore public signing policy defaults."""
    POLICY.write_text(json.dumps(BASE_POLICY, indent=2), encoding="utf-8")


def run_remediate(reset_dynamic: bool = True) -> dict:
    """Run the public remediate command and parse JSON output."""
    OUT.unlink(missing_ok=True)
    if reset_dynamic:
        cleanup_dynamic()
        reset_policy()
    subprocess.run(
        [
            "python3",
            "/app/tools/entitlement_audit.py",
            "remediate",
            "/app/bundles",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone3:
    """Validate remediation output."""

    def test_remediation_schema_summary_and_base_fixes(self) -> None:
        """Base remediation output must explain every non-keep action."""
        report = run_remediate()
        assert set(report) == {"fixes", "summary"}
        assert [row["bundle_id"] for row in report["fixes"]] == [
            "com.acme.legacybridge",
            "com.acme.wallet",
            "com.partner.portal",
        ]
        assert report["summary"] == {
            "fix_count": 3,
            "blocked_count": 2,
            "update_count": 1,
            "team_identifier_fix_count": 1,
            "app_groups_to_remove_count": 1,
            "associated_domains_to_remove_count": 1,
            "push_environment_fix_count": 0,
        }
        fixes = {row["bundle_id"]: row for row in report["fixes"]}
        assert fixes["com.acme.legacybridge"]["action"] == "block"
        assert fixes["com.acme.legacybridge"]["reasons"] == ["team identifier missing"]
        assert fixes["com.acme.legacybridge"]["set_team_identifier"] == "9JA89QQLNQ"
        assert fixes["com.acme.legacybridge"]["blocked"] is True
        assert fixes["com.acme.wallet"]["action"] == "block"
        assert fixes["com.acme.wallet"]["reasons"] == ["profile not allowed for platform"]
        assert fixes["com.acme.wallet"]["allowed_profiles"] == ["ios-prod", "ios-internal"]
        assert fixes["com.acme.wallet"]["expected_push_environment"] is None
        assert fixes["com.partner.portal"]["action"] == "update"
        assert fixes["com.partner.portal"]["reasons"] == [
            "app group prefix violation",
            "associated domain not allowed",
        ]
        assert fixes["com.partner.portal"]["remove_app_groups"] == ["group.partner.portal"]
        assert fixes["com.partner.portal"]["remove_associated_domains"] == [
            "applinks:portal.partner.example"
        ]

    def test_remediation_uses_policy_overrides_and_push_targets(self) -> None:
        """Override policy values must drive concrete remediation fields."""
        cleanup_dynamic()
        policy = dict(BASE_POLICY)
        policy["bundle_overrides"] = {
            "com.partner.portal": {
                "allowed_profiles": ["ios-internal"],
                "required_app_group_prefix": "group.partner.",
                "allowed_associated_domain_suffixes": [".partner.example"],
                "expected_push_environment": "production",
            }
        }
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        report = run_remediate(reset_dynamic=False)
        portal = {row["bundle_id"]: row for row in report["fixes"]}["com.partner.portal"]
        assert portal["action"] == "update"
        assert portal["reasons"] == ["push environment profile mismatch"]
        assert portal["allowed_profiles"] == ["ios-internal"]
        assert portal["expected_push_environment"] == "production"
        assert portal["remove_app_groups"] == []
        assert portal["remove_associated_domains"] == []
        assert report["summary"]["push_environment_fix_count"] == 1

    def test_remediation_keeps_null_push_policy_as_no_constraint(self) -> None:
        """A missing push profile policy must not create push remediation."""
        cleanup_dynamic()
        policy = dict(BASE_POLICY)
        policy["allowed_profiles"] = dict(BASE_POLICY["allowed_profiles"])
        policy["allowed_profiles"]["ios"] = ["ios-exempt"]
        policy["push_profile_environments"] = dict(BASE_POLICY["push_profile_environments"])
        policy["push_profile_environments"].pop("ios-exempt", None)
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        bundle = Path("/app/bundles/NoPushPolicy")
        write_plist(
            bundle / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.nopushpolicy",
                "CFBundleDisplayName": "Acme No Push Policy",
                "CFBundleExecutable": "NoPushPolicy",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-exempt",
            },
        )
        write_plist(
            bundle / "NoPushPolicy.entitlements",
            {
                "com.apple.security.application-groups": ["group.com.acme.nopushpolicy"],
                "keychain-access-groups": ["9JA89QQLNQ.com.acme.nopushpolicy"],
                "aps-environment": "development",
                "com.apple.developer.associated-domains": [
                    "applinks:nopushpolicy.acme.example"
                ],
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        report = run_remediate(reset_dynamic=False)
        assert "com.acme.nopushpolicy" not in {row["bundle_id"] for row in report["fixes"]}
        assert report["summary"]["push_environment_fix_count"] == 0
