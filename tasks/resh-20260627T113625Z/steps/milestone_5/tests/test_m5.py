"""Milestone 5 tests for current-state MSBuild migration verification."""

import json
import shutil
import subprocess
from pathlib import Path


OUT = Path("/app/out/msbuild-verification.json")
POLICY = Path("/app/policy/runtime-policy.json")
BASE_POLICY = {
    "required_framework": "net8.0",
    "retire_frameworks": ["net6.0"],
    "required_nullable": "enable",
    "required_rids": ["linux-x64", "win-x64"],
    "allowed_test_frameworks": ["net8.0"],
    "minimum_packages": {
        "Microsoft.Extensions.Hosting": "8.0.0",
        "Serilog.AspNetCore": "8.0.0",
        "Microsoft.Data.SqlClient": "5.1.0",
    },
}
DYNAMIC_DIRS = [
    Path("/app/src/Apply.Root"),
    Path("/app/src/Apply.Leaf"),
    Path("/app/src/Apply.Blocked"),
    Path("/app/src/Apply.Central"),
    Path("/app/src/Apply.CycleA"),
    Path("/app/src/Apply.CycleB"),
    Path("/app/src/Apply.Tests"),
    Path("/app/src/Cycle.A"),
    Path("/app/src/Cycle.B"),
    Path("/app/src/Deferred.Nullable"),
    Path("/app/src/Dependency.Blocked"),
    Path("/app/src/Dependency.Leaf"),
    Path("/app/src/Dependency.Middle"),
    Path("/app/src/Dependency.Root"),
    Path("/app/src/External.Ref"),
    Path("/app/src/Fulfillment.Api"),
    Path("/app/src/Macro.Blocked"),
    Path("/app/src/Macro.Leaf"),
    Path("/app/src/Macro.Root"),
    Path("/app/src/Namespaced.Service"),
    Path("/app/src/ProfileWave.Leaf"),
    Path("/app/src/ProfileWave.Middle"),
    Path("/app/src/ProfileWave.Root"),
    Path("/app/src/Profiled.Api"),
    Path("/app/src/Rid.Matrix.Api"),
    Path("/app/src/Rid.Matrix.Tests"),
    Path("/app/src/RidPolicy.Blocked"),
    Path("/app/src/RidPolicy.Leaf"),
    Path("/app/src/RidPolicy.Middle"),
    Path("/app/src/RidPolicy.Root"),
    Path("/app/src/UpdateAttr.Leaf"),
    Path("/app/src/UpdateAttr.Middle"),
    Path("/app/src/UpdateAttr.Root"),
    Path("/app/src/Verifier.Active"),
    Path("/app/src/Verifier.Retired"),
    Path("/app/src/Profiled"),
    Path("/app/src/Verifier.CycleA"),
    Path("/app/src/Verifier.CycleB"),
]


def cleanup_dynamic() -> None:
    """Remove projects created by milestone verifiers."""
    for directory in DYNAMIC_DIRS:
        if directory.exists():
            shutil.rmtree(directory)


def reset_policy() -> None:
    """Restore the public runtime policy."""
    POLICY.write_text(json.dumps(BASE_POLICY, indent=2), encoding="utf-8")


def run_verify(reset: bool = True) -> dict:
    """Run verify-apply and parse the JSON report."""
    OUT.unlink(missing_ok=True)
    if reset:
        cleanup_dynamic()
        reset_policy()
    subprocess.run(
        [
            "python3",
            "/app/tools/msbuild_audit.py",
            "verify-apply",
            "/app/src",
            "/app/Directory.Packages.props",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


def run_apply_plan() -> dict:
    """Prepare the base repository state by running the public apply-plan command."""
    apply_out = Path("/app/out/msbuild-apply-plan.json")
    apply_out.unlink(missing_ok=True)
    subprocess.run(
        [
            "python3",
            "/app/tools/msbuild_audit.py",
            "apply-plan",
            "/app/src",
            "/app/Directory.Packages.props",
            str(POLICY),
            str(apply_out),
        ],
        check=True,
    )
    return json.loads(apply_out.read_text(encoding="utf-8"))


def write_project(path: Path, body: str) -> None:
    """Create a dynamic MSBuild project file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


class TestMilestone5:
    """Validate read-only verification of migration state."""

    def test_verify_base_post_apply_state_has_no_stale_pending_work(self) -> None:
        """After milestone 4 apply-plan, verification must not report stale pending edits."""
        cleanup_dynamic()
        reset_policy()
        run_apply_plan()
        report = run_verify(reset=False)
        assert set(report) == {"projects", "summary", "dependency_risks"}
        status_order = {"blocked": 0, "pending": 1, "retire": 2, "compliant": 3}
        assert report["projects"] == sorted(
            report["projects"], key=lambda row: (status_order[row["status"]], row["path"])
        )
        assert report["summary"] == {
            "total": 10,
            "blocked": 0,
            "pending": 0,
            "retire": 2,
            "compliant": 8,
            "wave_count": 0,
            "files_with_remaining_changes": 0,
            "package_versions_below_minimum": 0,
        }
        assert report["dependency_risks"] == []
        rows = {row["path"]: row for row in report["projects"]}
        assert rows["Billing.Worker/Billing.Worker.csproj"]["status"] == "compliant"
        assert rows["Billing.Worker/Billing.Worker.csproj"]["changes_remaining"] == []
        edge = rows["Edge.Gateway/Edge.Gateway.csproj"]
        assert edge["status"] == "compliant"
        assert edge["changes_remaining"] == []
        assert edge["packages_below_minimum"] == {}
        assert edge["current"]["packages"]["Microsoft.Extensions.Hosting"] == "8.0.0"
        assert rows["Legacy.Import/Legacy.Import.csproj"]["status"] == "retire"
        assert rows["Reporting.Job/Reporting.Job.csproj"]["status"] == "retire"

    def test_verify_reports_retired_dependency_blocks(self) -> None:
        """Blocked projects must preserve retired-dependency reasons and risk rows."""
        cleanup_dynamic()
        reset_policy()
        write_project(
            Path("/app/src/Verifier.Retired/Verifier.Retired.csproj"),
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
</Project>
""",
        )
        write_project(
            Path("/app/src/Verifier.Active/Verifier.Active.csproj"),
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <ProjectReference Include="..\\Verifier.Retired\\Verifier.Retired.csproj" />
  </ItemGroup>
</Project>
""",
        )
        report = run_verify(reset=False)
        rows = {row["path"]: row for row in report["projects"]}
        active = rows["Verifier.Active/Verifier.Active.csproj"]
        assert active["status"] == "blocked"
        assert active["wave"] is None
        assert active["changes_remaining"] == []
        assert active["packages_below_minimum"] == {}
        assert any("retired dependency: Verifier.Retired/Verifier.Retired.csproj" == reason for reason in active["reasons"])
        assert report["summary"]["blocked"] == 1
        assert report["summary"]["retire"] == 3
        assert report["dependency_risks"] == [
            {
                "path": "Verifier.Active/Verifier.Active.csproj",
                "name": "Verifier.Active",
                "blocked_by_retired": ["Verifier.Retired/Verifier.Retired.csproj"],
                "has_cycle": False,
                "reasons": ["retired dependency: Verifier.Retired/Verifier.Retired.csproj"],
            }
        ]

    def test_verify_uses_runtime_profile_targets_and_minimum_packages(self) -> None:
        """Profile-selected projects must show effective target state and remaining package drift."""
        cleanup_dynamic()
        policy = dict(BASE_POLICY)
        policy["runtime_profiles"] = {
            "linux-only": {
                "required_framework": "net8.0",
                "required_nullable": "enable",
                "required_rids": ["linux-x64"],
                "minimum_packages": {"Microsoft.Extensions.Hosting": "8.0.9"},
            }
        }
        policy["path_profile_overrides"] = {"Profiled/": "linux-only"}
        POLICY.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        write_project(
            Path("/app/src/Profiled/Profiled.csproj"),
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifiers>win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="7.0.0" />
  </ItemGroup>
</Project>
""",
        )
        report = run_verify(reset=False)
        profiled = {row["path"]: row for row in report["projects"]}["Profiled/Profiled.csproj"]
        assert profiled["status"] == "pending"
        assert profiled["wave"] == 1
        assert profiled["target"] == {
            "target_framework": "net8.0",
            "nullable": "enable",
            "runtime_identifiers": ["linux-x64"],
        }
        assert profiled["current"] == {
            "target_framework": "net7.0",
            "nullable": "disable",
            "runtime_identifiers": ["win-x64"],
            "packages": {"Microsoft.Extensions.Hosting": "7.0.0"},
        }
        assert profiled["changes_remaining"] == [
            "target_framework",
            "nullable",
            "runtime_identifiers",
            "package_versions",
        ]
        assert profiled["packages_below_minimum"] == {
            "Microsoft.Extensions.Hosting": {"current": "7.0.0", "minimum": "8.0.9"}
        }
        assert any("target framework" in reason for reason in profiled["reasons"])
        assert any("nullable" in reason for reason in profiled["reasons"])
        assert any("runtime identifiers" in reason for reason in profiled["reasons"])
        assert any("Microsoft.Extensions.Hosting" in reason for reason in profiled["reasons"])
        assert any("runtime profile linux-only" in reason for reason in profiled["reasons"])
        assert report["summary"]["files_with_remaining_changes"] == 1
        assert report["summary"]["package_versions_below_minimum"] == 1

    def test_verify_reports_true_cycles_and_does_not_modify_files(self) -> None:
        """Cycle-only dependency risks must set has_cycle and verification must be read-only."""
        cleanup_dynamic()
        reset_policy()
        project_a = Path("/app/src/Verifier.CycleA/Verifier.CycleA.csproj")
        project_b = Path("/app/src/Verifier.CycleB/Verifier.CycleB.csproj")
        write_project(
            project_a,
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\\Verifier.CycleB\\Verifier.CycleB.csproj" />
  </ItemGroup>
</Project>
""",
        )
        write_project(
            project_b,
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\\Verifier.CycleA\\Verifier.CycleA.csproj" />
  </ItemGroup>
</Project>
""",
        )
        before = {
            path: path.read_text(encoding="utf-8")
            for path in [project_a, project_b, POLICY, Path("/app/Directory.Packages.props")]
        }
        report = run_verify(reset=False)
        assert [row["path"] for row in report["dependency_risks"]] == sorted(
            row["path"] for row in report["dependency_risks"]
        )
        after = {
            path: path.read_text(encoding="utf-8")
            for path in [project_a, project_b, POLICY, Path("/app/Directory.Packages.props")]
        }

        assert after == before
        rows = {row["path"]: row for row in report["projects"]}
        assert rows["Verifier.CycleA/Verifier.CycleA.csproj"]["status"] == "blocked"
        assert rows["Verifier.CycleB/Verifier.CycleB.csproj"]["status"] == "blocked"
        risks = {row["path"]: row for row in report["dependency_risks"]}
        assert set(risks) >= {
            "Verifier.CycleA/Verifier.CycleA.csproj",
            "Verifier.CycleB/Verifier.CycleB.csproj",
        }
        for path in ["Verifier.CycleA/Verifier.CycleA.csproj", "Verifier.CycleB/Verifier.CycleB.csproj"]:
            assert risks[path]["blocked_by_retired"] == []
            assert risks[path]["has_cycle"] is True
            assert any("dependency cycle" in reason for reason in risks[path]["reasons"])
        assert report["summary"]["blocked"] == 2
