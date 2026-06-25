"""Milestone 2 tests for signing policy action planning."""

import json
import plistlib
import shutil
import subprocess
from pathlib import Path


OUT = Path("/app/out/entitlement-plan.json")
POLICY = Path("/app/policy/signing-policy.json")
DYNAMIC = Path("/app/bundles/DynamicClip")
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
    """Write a public plist fixture used by runtime-generated checks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        plistlib.dump(data, fh, sort_keys=False)


def cleanup_dynamic() -> None:
    """Remove the dynamic bundle so tests do not share generated state."""
    if DYNAMIC.exists():
        shutil.rmtree(DYNAMIC)


def reset_policy() -> None:
    """Restore the public signing policy before plan tests."""
    POLICY.write_text(json.dumps(BASE_POLICY, indent=2), encoding="utf-8")


def run_plan(reset_dynamic: bool = True) -> dict:
    """Run the public plan command and parse its JSON report."""
    OUT.unlink(missing_ok=True)
    if reset_dynamic:
        cleanup_dynamic()
        reset_policy()
    subprocess.run(
        [
            "python3",
            "/app/tools/entitlement_audit.py",
            "plan",
            "/app/bundles",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone2:
    """Validate milestone 2 policy planning behavior."""

    def test_plan_schema_sorting_and_summary(self) -> None:
        """Plan output must contain severity-sorted actions and action counts."""
        report = run_plan()
        priority = {"block": 0, "update": 1, "keep": 2}
        assert set(report) == {"actions", "summary"}
        assert report["actions"] == sorted(
            report["actions"], key=lambda row: (priority[row["action"]], row["bundle_id"])
        )
        assert all(
            set(row)
            == {
                "bundle_id",
                "display_name",
                "platform",
                "profile",
                "action",
                "reasons",
                "target",
            }
            for row in report["actions"]
        )
        assert report["summary"] == {"block": 2, "update": 1, "keep": 2}
        public_fields = {
            row["bundle_id"]: (row["display_name"], row["platform"], row["profile"])
            for row in report["actions"]
        }
        assert public_fields == {
            "com.acme.bank": ("Acme Bank", "ios", "ios-prod"),
            "com.acme.legacybridge": ("Legacy Bridge", "macos", "macos-prod"),
            "com.acme.ops": ("Acme Ops", "macos", "macos-dev"),
            "com.acme.wallet": ("Acme Wallet", "ios", "adhoc-qa"),
            "com.partner.portal": ("Partner Portal", "ios", "ios-internal"),
        }

    def test_plan_classifies_profile_team_domain_and_app_group_drift(self) -> None:
        """Bundled fixtures must be classified with the documented reason labels."""
        actions = {row["bundle_id"]: row for row in run_plan()["actions"]}
        assert actions["com.acme.bank"]["action"] == "keep"
        assert actions["com.acme.ops"]["action"] == "keep"
        assert actions["com.acme.wallet"]["action"] == "block"
        assert actions["com.acme.wallet"]["reasons"] == ["profile not allowed for platform"]
        assert actions["com.acme.legacybridge"]["action"] == "block"
        assert actions["com.acme.legacybridge"]["reasons"] == ["team identifier missing"]
        assert actions["com.partner.portal"]["action"] == "update"
        assert actions["com.partner.portal"]["reasons"] == [
            "app group prefix violation",
            "associated domain not allowed",
        ]
        assert actions["com.partner.portal"]["target"] == {
            "team_identifier": "9JA89QQLNQ",
            "allowed_profiles": ["ios-prod", "ios-internal"],
            "expected_push_environment": "development",
        }

    def test_plan_uses_changed_policy_and_added_bundle(self) -> None:
        """Changing the policy and adding a bundle must affect the next plan."""
        policy = dict(BASE_POLICY)
        policy["push_profile_environments"] = dict(BASE_POLICY["push_profile_environments"])
        policy["push_profile_environments"]["ios-internal"] = "production"
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        write_plist(
            DYNAMIC / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.clip",
                "CFBundleDisplayName": "Acme Clip",
                "CFBundleExecutable": "AcmeClip",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            DYNAMIC / "Clip.entitlements",
            {
                "com.apple.security.application-groups": ["group.com.acme.clip"],
                "keychain-access-groups": ["9JA89QQLNQ.com.acme.clip"],
                "aps-environment": "development",
                "com.apple.developer.associated-domains": ["applinks:clip.acme.test"],
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        actions = {row["bundle_id"]: row for row in run_plan(reset_dynamic=False)["actions"]}
        assert actions["com.acme.clip"]["action"] == "update"
        assert actions["com.acme.clip"]["reasons"] == ["push environment profile mismatch"]
        assert actions["com.acme.clip"]["target"]["expected_push_environment"] == "production"
        assert actions["com.partner.portal"]["reasons"] == [
            "app group prefix violation",
            "associated domain not allowed",
            "push environment profile mismatch",
        ]

    def test_plan_preserves_policy_profile_order_with_combined_update_reasons(self) -> None:
        """Policy profile order and multiple update reasons must be preserved together."""
        policy = dict(BASE_POLICY)
        policy["allowed_profiles"] = dict(BASE_POLICY["allowed_profiles"])
        policy["allowed_profiles"]["ios"] = ["ios-internal", "ios-prod", "ios-beta"]
        policy["push_profile_environments"] = dict(BASE_POLICY["push_profile_environments"])
        policy["push_profile_environments"]["ios-internal"] = "production"
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        write_plist(
            DYNAMIC / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.orderprobe",
                "CFBundleDisplayName": "Acme Order Probe",
                "CFBundleExecutable": "OrderProbe",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            DYNAMIC / "OrderProbe.entitlements",
            {
                "com.apple.security.application-groups": [
                    "group.com.acme.orderprobe",
                    "group.partner.orderprobe",
                ],
                "keychain-access-groups": ["9JA89QQLNQ.com.acme.orderprobe"],
                "aps-environment": "development",
                "com.apple.developer.associated-domains": [
                    "applinks:order.external.example",
                    "applinks:order.acme.test",
                ],
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        actions = {row["bundle_id"]: row for row in run_plan(reset_dynamic=False)["actions"]}
        probe = actions["com.acme.orderprobe"]
        assert probe["action"] == "update"
        assert probe["reasons"] == [
            "app group prefix violation",
            "associated domain not allowed",
            "push environment profile mismatch",
        ]
        assert probe["target"] == {
            "team_identifier": "9JA89QQLNQ",
            "allowed_profiles": ["ios-internal", "ios-prod", "ios-beta"],
            "expected_push_environment": "production",
        }

    def test_plan_applies_bundle_overrides_to_effective_policy(self) -> None:
        """Per-bundle policy overrides must replace global defaults for classification."""
        policy = dict(BASE_POLICY)
        policy["bundle_overrides"] = {
            "com.partner.portal": {
                "allowed_profiles": ["ios-internal"],
                "required_app_group_prefix": "group.partner.",
                "allowed_associated_domain_suffixes": [".partner.example"],
                "expected_push_environment": "development",
            },
            "com.partner.special": {
                "required_team_id": "44PARTNER9",
                "allowed_profiles": ["ios-partner", "ios-internal"],
                "required_app_group_prefix": "group.partner.",
                "allowed_associated_domain_suffixes": [".partner.example"],
                "expected_push_environment": "production",
            },
        }
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        write_plist(
            DYNAMIC / "Info.plist",
            {
                "CFBundleIdentifier": "com.partner.special",
                "CFBundleDisplayName": "Partner Special",
                "CFBundleExecutable": "PartnerSpecial",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-partner",
            },
        )
        write_plist(
            DYNAMIC / "PartnerSpecial.entitlements",
            {
                "com.apple.security.application-groups": ["group.partner.special"],
                "keychain-access-groups": ["44PARTNER9.com.partner.special"],
                "aps-environment": "production",
                "com.apple.developer.associated-domains": ["applinks:special.partner.example"],
                "com.apple.developer.team-identifier": "44PARTNER9",
            },
        )
        actions = {row["bundle_id"]: row for row in run_plan(reset_dynamic=False)["actions"]}
        portal = actions["com.partner.portal"]
        assert portal["action"] == "keep"
        assert portal["reasons"] == []
        assert portal["target"] == {
            "team_identifier": "9JA89QQLNQ",
            "allowed_profiles": ["ios-internal"],
            "expected_push_environment": "development",
        }
        special = actions["com.partner.special"]
        assert special["action"] == "keep"
        assert special["reasons"] == []
        assert special["target"] == {
            "team_identifier": "44PARTNER9",
            "allowed_profiles": ["ios-partner", "ios-internal"],
            "expected_push_environment": "production",
        }
        assert actions["com.acme.wallet"]["action"] == "block"
        assert actions["com.acme.legacybridge"]["reasons"] == ["team identifier missing"]

    def test_plan_blocks_team_identifier_mismatch(self) -> None:
        """A present but wrong entitlement team identifier must produce the mismatch reason."""
        write_plist(
            DYNAMIC / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.badteam",
                "CFBundleDisplayName": "Acme Bad Team",
                "CFBundleExecutable": "BadTeam",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            DYNAMIC / "BadTeam.entitlements",
            {
                "com.apple.security.application-groups": ["group.com.acme.badteam"],
                "keychain-access-groups": ["44WRONGTEAM.com.acme.badteam"],
                "aps-environment": "development",
                "com.apple.developer.associated-domains": ["applinks:badteam.acme.example"],
                "com.apple.developer.team-identifier": "44WRONGTEAM",
            },
        )
        actions = {row["bundle_id"]: row for row in run_plan(reset_dynamic=False)["actions"]}
        assert actions["com.acme.badteam"]["action"] == "block"
        assert actions["com.acme.badteam"]["reasons"] == ["team identifier mismatch"]

    def test_plan_uses_null_expected_push_environment_without_policy_value(self) -> None:
        """Expected push environment is null when no global or override policy value applies."""
        policy = dict(BASE_POLICY)
        policy["allowed_profiles"] = dict(BASE_POLICY["allowed_profiles"])
        policy["allowed_profiles"]["ios"] = ["ios-exempt"]
        policy["push_profile_environments"] = dict(BASE_POLICY["push_profile_environments"])
        policy["push_profile_environments"].pop("ios-exempt", None)
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        write_plist(
            DYNAMIC / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.nopushpolicy",
                "CFBundleDisplayName": "Acme No Push Policy",
                "CFBundleExecutable": "NoPushPolicy",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-exempt",
            },
        )
        write_plist(
            DYNAMIC / "NoPushPolicy.entitlements",
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
        actions = {row["bundle_id"]: row for row in run_plan(reset_dynamic=False)["actions"]}
        assert actions["com.acme.nopushpolicy"]["action"] == "keep"
        assert actions["com.acme.nopushpolicy"]["reasons"] == []
        assert actions["com.acme.nopushpolicy"]["target"]["expected_push_environment"] is None
