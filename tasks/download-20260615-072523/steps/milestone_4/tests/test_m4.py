"""Milestone 4 tests for applying entitlement remediation changes."""

import json
import plistlib
import shutil
import subprocess
from pathlib import Path


OUT = Path("/app/out/entitlement-apply.json")
POLICY = Path("/app/policy/signing-policy.json")
PARTNER_ENT = Path("/app/bundles/PartnerPortal/PartnerPortal.entitlements")
LEGACY_ENT = Path("/app/bundles/LegacyBridge/LegacyBridge.entitlements")
DYNAMIC_DIRS = [
    Path("/app/bundles/DynamicClip"),
    Path("/app/bundles/RemediateProbe"),
    Path("/app/bundles/NoPushPolicy"),
    Path("/app/bundles/ApplyProbe"),
]
DYNAMIC = DYNAMIC_DIRS[-1]
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
    """Write a plist fixture for runtime apply-remediation checks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        plistlib.dump(data, fh, sort_keys=False)


def read_plist(path: Path) -> dict:
    """Load a plist fixture after the command mutates it."""
    with path.open("rb") as fh:
        return plistlib.load(fh)


def reset_state() -> None:
    """Restore mutable policy and entitlement fixtures before each test."""
    OUT.unlink(missing_ok=True)
    POLICY.write_text(json.dumps(BASE_POLICY, indent=2), encoding="utf-8")
    write_plist(PARTNER_ENT, dict(PARTNER_BASE))
    write_plist(LEGACY_ENT, dict(LEGACY_BASE))
    for path in DYNAMIC_DIRS:
        if path.exists():
            shutil.rmtree(path)


def run_apply(reset: bool = True) -> dict:
    """Run the public apply-remediation command and return the JSON report."""
    if reset:
        reset_state()
    OUT.unlink(missing_ok=True)
    subprocess.run(
        [
            "python3",
            "/app/tools/entitlement_audit.py",
            "apply-remediation",
            "/app/bundles",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone4:
    """Validate entitlement sidecar mutation and apply report behavior."""

    def test_apply_mutates_only_update_sidecars_and_reports_blocks(self) -> None:
        """Base update rows are changed, while blocked bundle entitlements remain untouched."""
        reset_state()
        info_before = {
            name: read_plist(Path(f"/app/bundles/{name}/Info.plist"))
            for name in ["AcmeBank", "AcmeOps", "AcmeWallet", "LegacyBridge", "PartnerPortal"]
        }
        policy_before = POLICY.read_text(encoding="utf-8")
        report = run_apply(reset=False)
        assert set(report) == {"applied", "blocked", "summary"}
        assert report["applied"] == [
            {
                "bundle_id": "com.partner.portal",
                "path": str(PARTNER_ENT),
                "changes": ["remove_app_groups", "remove_associated_domains"],
                "removed_app_groups": ["group.partner.portal"],
                "removed_associated_domains": ["applinks:portal.partner.example"],
                "set_aps_environment": None,
            }
        ]
        assert [row["bundle_id"] for row in report["blocked"]] == [
            "com.acme.legacybridge",
            "com.acme.wallet",
        ]
        blocked = {row["bundle_id"]: row for row in report["blocked"]}
        assert blocked["com.acme.legacybridge"]["path"] == str(LEGACY_ENT)
        assert blocked["com.acme.legacybridge"]["reasons"] == ["team identifier missing"]
        assert blocked["com.acme.wallet"]["path"] == (
            "/app/bundles/AcmeWallet/AcmeWallet.entitlements"
        )
        assert blocked["com.acme.wallet"]["reasons"] == ["profile not allowed for platform"]
        assert all(row["reasons"] for row in report["blocked"])
        assert all(row["unchanged"] is True for row in report["blocked"])
        assert report["summary"] == {
            "applied_count": 1,
            "blocked_count": 2,
            "files_changed": 1,
            "app_groups_removed": 1,
            "associated_domains_removed": 1,
            "push_environments_set": 0,
        }
        partner = read_plist(PARTNER_ENT)
        assert partner["com.apple.security.application-groups"] == []
        assert partner["com.apple.developer.associated-domains"] == []
        assert partner["aps-environment"] == "development"
        assert read_plist(LEGACY_ENT) == LEGACY_BASE
        assert POLICY.read_text(encoding="utf-8") == policy_before
        assert {
            name: read_plist(Path(f"/app/bundles/{name}/Info.plist"))
            for name in info_before
        } == info_before

    def test_apply_sets_push_environment_from_changed_policy_and_is_idempotent(self) -> None:
        """Runtime policy changes must drive plist edits, and repeated runs are no-ops."""
        reset_state()
        policy = dict(BASE_POLICY)
        policy["push_profile_environments"] = dict(BASE_POLICY["push_profile_environments"])
        policy["push_profile_environments"]["ios-internal"] = "production"
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        write_plist(
            DYNAMIC / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.applyprobe",
                "CFBundleDisplayName": "Acme Apply Probe",
                "CFBundleExecutable": "ApplyProbe",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            DYNAMIC / "ApplyProbe.entitlements",
            {
                "com.apple.security.application-groups": [
                    "group.com.acme.applyprobe",
                    "group.external.applyprobe",
                ],
                "keychain-access-groups": ["9JA89QQLNQ.com.acme.applyprobe"],
                "com.apple.developer.associated-domains": [
                    "applinks:apply.acme.example",
                    "applinks:apply.external.example",
                ],
                "aps-environment": "development",
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        first = run_apply(reset=False)
        rows = {row["bundle_id"]: row for row in first["applied"]}
        probe = rows["com.acme.applyprobe"]
        assert probe["changes"] == [
            "remove_app_groups",
            "remove_associated_domains",
            "set_push_environment",
        ]
        assert probe["removed_app_groups"] == ["group.external.applyprobe"]
        assert probe["removed_associated_domains"] == ["applinks:apply.external.example"]
        assert probe["set_aps_environment"] == "production"
        plist = read_plist(DYNAMIC / "ApplyProbe.entitlements")
        assert plist["com.apple.security.application-groups"] == ["group.com.acme.applyprobe"]
        assert plist["com.apple.developer.associated-domains"] == [
            "applinks:apply.acme.example"
        ]
        assert plist["aps-environment"] == "production"

        second = run_apply(reset=False)
        assert second["applied"] == []
        assert second["summary"]["applied_count"] == 0
        assert second["summary"]["files_changed"] == 0
        assert second["summary"]["app_groups_removed"] == 0
        assert second["summary"]["associated_domains_removed"] == 0
        assert second["summary"]["push_environments_set"] == 0
        assert [row["bundle_id"] for row in second["blocked"]] == [
            "com.acme.legacybridge",
            "com.acme.wallet",
        ]

    def test_apply_leaves_push_environment_when_policy_has_no_expected_value(self) -> None:
        """A null push expectation must not rewrite aps-environment."""
        reset_state()
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
        entitlements = {
            "com.apple.security.application-groups": ["group.com.acme.nopushpolicy"],
            "keychain-access-groups": ["9JA89QQLNQ.com.acme.nopushpolicy"],
            "com.apple.developer.associated-domains": [
                "applinks:nopushpolicy.acme.example"
            ],
            "aps-environment": "development",
            "com.apple.developer.team-identifier": "9JA89QQLNQ",
        }
        write_plist(bundle / "NoPushPolicy.entitlements", entitlements)
        report = run_apply(reset=False)
        assert "com.acme.nopushpolicy" not in {
            row["bundle_id"] for row in report["applied"] + report["blocked"]
        }
        assert read_plist(bundle / "NoPushPolicy.entitlements")["aps-environment"] == (
            "development"
        )
