"""Milestone 1 tests for bundle inventory and entitlement normalization."""

import json
import plistlib
import shutil
import subprocess
from pathlib import Path


OUT = Path("/app/out/entitlement-inventory.json")
DYNAMIC = Path("/app/bundles/DynamicClip")


def write_plist(path: Path, data: dict) -> None:
    """Write a public plist fixture used by runtime-generated checks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        plistlib.dump(data, fh, sort_keys=False)


def cleanup_dynamic() -> None:
    """Remove the dynamic bundle so tests do not share generated state."""
    if DYNAMIC.exists():
        shutil.rmtree(DYNAMIC)


def run_inventory(reset_dynamic: bool = True) -> dict:
    """Run the public inventory command and parse its JSON report."""
    OUT.unlink(missing_ok=True)
    if reset_dynamic:
        cleanup_dynamic()
    subprocess.run(
        [
            "python3",
            "/app/tools/entitlement_audit.py",
            "inventory",
            "/app/bundles",
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone1:
    """Validate milestone 1 inventory behavior."""

    def test_inventory_schema_sorting_and_summary(self) -> None:
        """Inventory output must contain sorted bundle rows and aggregate counts."""
        report = run_inventory()
        assert set(report) == {"bundles", "summary"}
        rows = report["bundles"]
        assert [row["bundle_id"] for row in rows] == sorted(row["bundle_id"] for row in rows)
        assert all(
            set(row)
            == {
                "path",
                "bundle_id",
                "display_name",
                "executable",
                "platform",
                "profile",
                "entitlements",
            }
            for row in rows
        )
        assert report["summary"] == {
            "total": 5,
            "by_platform": {"ios": 3, "macos": 2},
            "with_push": 5,
            "missing_team_identifier": 1,
        }
        paths = {row["bundle_id"]: row["path"] for row in rows}
        assert paths == {
            "com.acme.bank": "/app/bundles/AcmeBank",
            "com.acme.legacybridge": "/app/bundles/LegacyBridge",
            "com.acme.ops": "/app/bundles/AcmeOps",
            "com.acme.wallet": "/app/bundles/AcmeWallet",
            "com.partner.portal": "/app/bundles/PartnerPortal",
        }

    def test_inventory_normalizes_entitlement_fields(self) -> None:
        """Known bundles must expose normalized platform and entitlement values."""
        rows = {row["bundle_id"]: row for row in run_inventory()["bundles"]}
        assert {
            bundle_id: (row["display_name"], row["executable"])
            for bundle_id, row in rows.items()
        } == {
            "com.acme.bank": ("Acme Bank", "AcmeBank"),
            "com.acme.legacybridge": ("Legacy Bridge", "LegacyBridge"),
            "com.acme.ops": ("Acme Ops", "AcmeOps"),
            "com.acme.wallet": ("Acme Wallet", "AcmeWallet"),
            "com.partner.portal": ("Partner Portal", "PartnerPortal"),
        }
        bank = rows["com.acme.bank"]
        assert bank["platform"] == "ios"
        assert bank["profile"] == "ios-prod"
        assert bank["entitlements"] == {
            "app_groups": ["group.com.acme.bank", "group.com.acme.shared"],
            "keychain_groups": ["9JA89QQLNQ.com.acme.bank"],
            "associated_domains": ["applinks:bank.acme.example"],
            "aps_environment": "production",
            "team_identifier": "9JA89QQLNQ",
        }
        legacy = rows["com.acme.legacybridge"]
        assert legacy["platform"] == "macos"
        assert legacy["entitlements"]["team_identifier"] is None
        assert legacy["entitlements"]["associated_domains"] == []

    def test_inventory_reads_runtime_added_bundle(self) -> None:
        """A bundle added during verification must appear in the next inventory."""
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
                "com.apple.security.application-groups": [
                    "group.com.acme.clip",
                    "group.com.acme.shared",
                ],
                "keychain-access-groups": ["9JA89QQLNQ.com.acme.clip"],
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        report = run_inventory(reset_dynamic=False)
        rows = {row["bundle_id"]: row for row in report["bundles"]}
        assert rows["com.acme.clip"]["entitlements"]["app_groups"] == [
            "group.com.acme.clip",
            "group.com.acme.shared",
        ]
        assert rows["com.acme.clip"]["entitlements"]["aps_environment"] is None
        assert report["summary"]["total"] == 6
        assert report["summary"]["by_platform"]["ios"] == 4
        assert report["summary"]["with_push"] == 5

    def test_inventory_prefers_executable_sidecar_then_alphabetical_fallback(self) -> None:
        """Entitlements come from the executable-named sidecar before alphabetical fallback."""
        write_plist(
            DYNAMIC / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.sidecar",
                "CFBundleDisplayName": "Acme Sidecar",
                "CFBundleExecutable": "SidecarApp",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            DYNAMIC / "Z-last.entitlements",
            {"com.apple.security.application-groups": ["group.com.acme.z"]},
        )
        write_plist(
            DYNAMIC / "A-first.entitlements",
            {"com.apple.security.application-groups": ["group.com.acme.a"]},
        )
        write_plist(
            DYNAMIC / "SidecarApp.entitlements",
            {
                "com.apple.security.application-groups": ["group.com.acme.preferred"],
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        rows = {row["bundle_id"]: row for row in run_inventory(reset_dynamic=False)["bundles"]}
        assert rows["com.acme.sidecar"]["entitlements"]["app_groups"] == [
            "group.com.acme.preferred"
        ]

        (DYNAMIC / "SidecarApp.entitlements").unlink()
        rows = {row["bundle_id"]: row for row in run_inventory(reset_dynamic=False)["bundles"]}
        assert rows["com.acme.sidecar"]["entitlements"]["app_groups"] == ["group.com.acme.a"]

    def test_inventory_sorts_entitlement_arrays_from_unsorted_input(self) -> None:
        """Array-valued entitlement fields must be sorted even when plist input is not."""
        write_plist(
            DYNAMIC / "Info.plist",
            {
                "CFBundleIdentifier": "com.acme.unsorted",
                "CFBundleDisplayName": "Acme Unsorted",
                "CFBundleExecutable": "UnsortedApp",
                "DTPlatformName": "iphoneos",
                "ProvisioningProfile": "ios-internal",
            },
        )
        write_plist(
            DYNAMIC / "UnsortedApp.entitlements",
            {
                "com.apple.security.application-groups": [
                    "group.com.acme.zeta",
                    "group.com.acme.alpha",
                ],
                "keychain-access-groups": [
                    "9JA89QQLNQ.com.acme.zeta",
                    "9JA89QQLNQ.com.acme.alpha",
                ],
                "com.apple.developer.associated-domains": [
                    "applinks:z.acme.example",
                    "applinks:a.acme.example",
                ],
                "com.apple.developer.team-identifier": "9JA89QQLNQ",
            },
        )
        row = {
            row["bundle_id"]: row for row in run_inventory(reset_dynamic=False)["bundles"]
        }["com.acme.unsorted"]
        assert row["entitlements"]["app_groups"] == [
            "group.com.acme.alpha",
            "group.com.acme.zeta",
        ]
        assert row["entitlements"]["keychain_groups"] == [
            "9JA89QQLNQ.com.acme.alpha",
            "9JA89QQLNQ.com.acme.zeta",
        ]
        assert row["entitlements"]["associated_domains"] == [
            "applinks:a.acme.example",
            "applinks:z.acme.example",
        ]
