"""Milestone 2 tests for MSBuild runtime policy planning."""

import json
import subprocess
from pathlib import Path


OUT = Path("/app/out/msbuild-runtime-plan.json")
POLICY = Path("/app/policy/runtime-policy.json")
PROPS = Path("/app/Directory.Packages.props")
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


def cleanup_dynamic() -> None:
    """Remove dynamically added projects between tests."""
    for dynamic in [
        Path("/app/src/Fulfillment.Api"),
        Path("/app/src/Namespaced.Service"),
        Path("/app/src/Profiled.Api"),
    ]:
        if not dynamic.exists():
            continue
        for path in sorted(dynamic.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        dynamic.rmdir()


def reset_policy() -> None:
    """Restore the public runtime policy."""
    POLICY.write_text(json.dumps(BASE_POLICY), encoding="utf-8")


def run_plan(reset_dynamic: bool = True) -> dict:
    """Run the public plan command and parse the JSON report."""
    OUT.unlink(missing_ok=True)
    if reset_dynamic:
        cleanup_dynamic()
        reset_policy()
    subprocess.run(
        [
            "python3",
            "/app/tools/msbuild_audit.py",
            "plan",
            "/app/src",
            "/app/Directory.Packages.props",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone2:
    """Validate runtime policy action planning."""

    def test_plan_schema_sorting_and_summary(self) -> None:
        """Plan output must contain priority-sorted actions and counts."""
        report = run_plan()
        priority = {"retire": 0, "update": 1, "keep": 2}
        assert set(report) == {"actions", "summary"}
        assert report["actions"] == sorted(
            report["actions"], key=lambda row: (priority[row["action"]], row["path"])
        )
        actions_by_name = {row["name"]: row for row in report["actions"]}
        assert actions_by_name["Legacy.Import"]["path"] == "Legacy.Import/Legacy.Import.csproj"
        assert not actions_by_name["Legacy.Import"]["path"].startswith("/app/src/")
        assert all(set(row) == {"path", "name", "action", "reasons", "target"} for row in report["actions"])
        assert report["summary"] == {"retire": 2, "update": 6, "keep": 2}

    def test_plan_classifies_framework_rid_nullable_and_package_drift(self) -> None:
        """Policy decisions must expose each kind of runtime drift."""
        actions = {row["name"]: row for row in run_plan()["actions"]}
        assert actions["Billing.Api"]["action"] == "keep"
        assert actions["Billing.Api"]["path"] == "Billing.Api/Billing.Api.csproj"
        assert actions["Telemetry.Collector"]["action"] == "keep"
        assert actions["Reporting.Job"]["action"] == "retire"
        assert actions["Legacy.Import"]["action"] == "retire"
        assert actions["Billing.Worker"]["action"] == "update"
        assert any("target framework" in reason for reason in actions["Billing.Worker"]["reasons"])
        assert any("runtime identifiers" in reason for reason in actions["Identity.Api"]["reasons"])
        assert any("Microsoft.Extensions.Hosting" in reason for reason in actions["Edge.Gateway"]["reasons"])
        assert actions["Ops.Cli"]["target"]["runtime_identifiers"] == ["linux-x64", "win-x64"]
        assert actions["Tests.Integration"]["action"] == "update"
        assert any("allowed list" in reason for reason in actions["Tests.Integration"]["reasons"])
        assert actions["Tests.Integration"]["target"]["target_framework"] == "net8.0"
        assert actions["Tests.Integration"]["target"]["runtime_identifiers"] == []

    def test_plan_uses_changed_policy_and_added_projects(self) -> None:
        """Changing policy and adding a project must affect the next plan."""
        policy = dict(BASE_POLICY)
        policy["required_rids"] = ["linux-x64"]
        POLICY.write_text(json.dumps(policy), encoding="utf-8")
        dynamic = Path("/app/src/Fulfillment.Api")
        dynamic.mkdir(parents=True, exist_ok=True)
        (dynamic / "Fulfillment.Api.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        actions = {row["name"]: row for row in run_plan(reset_dynamic=False)["actions"]}
        assert actions["Fulfillment.Api"]["action"] == "keep"
        assert actions["Identity.Api"]["action"] == "keep"
        assert actions["Billing.Api"]["action"] == "update"
        assert actions["Billing.Api"]["target"]["runtime_identifiers"] == ["linux-x64"]

    def test_plan_reads_namespaced_projects_for_policy_decisions(self) -> None:
        """Namespaced MSBuild projects must still be classified against runtime policy."""
        reset_policy()
        dynamic = Path("/app/src/Namespaced.Service")
        dynamic.mkdir(parents=True, exist_ok=True)
        msbuild_ns = "http" + "://schemas.microsoft.com/developer/msbuild/2003"
        (dynamic / "Namespaced.Service.csproj").write_text(
            f"""<Project xmlns="{msbuild_ns}" Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <PackageReference Include="Serilog.AspNetCore" Version="7.0.0" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        actions = {row["name"]: row for row in run_plan(reset_dynamic=False)["actions"]}
        namespaced = actions["Namespaced.Service"]
        assert namespaced["action"] == "update"
        assert any("target framework" in reason for reason in namespaced["reasons"])
        assert any("nullable" in reason for reason in namespaced["reasons"])
        assert any("runtime identifiers" in reason for reason in namespaced["reasons"])

    def test_plan_uses_namespaced_central_package_versions_for_policy(self) -> None:
        """Namespaced central package versions and singular RID lists must feed policy decisions."""
        original_props = PROPS.read_text(encoding="utf-8")
        reset_policy()
        dynamic = Path("/app/src/Fulfillment.Api")
        dynamic.mkdir(parents=True, exist_ok=True)
        msbuild_ns = "http" + "://schemas.microsoft.com/developer/msbuild/2003"
        try:
            PROPS.write_text(
                f"""<Project xmlns="{msbuild_ns}">
  <ItemGroup>
    <PackageVersion Include="Microsoft.Extensions.Hosting" Version="7.0.9" />
    <PackageVersion Include="Serilog.AspNetCore" Version="8.0.3" />
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )
            (dynamic / "Fulfillment.Api.csproj").write_text(
                """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifier> linux-x64 ; ; win-x64 </RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )
            actions = {row["name"]: row for row in run_plan(reset_dynamic=False)["actions"]}
            fulfillment = actions["Fulfillment.Api"]
            assert fulfillment["action"] == "update"
            assert any("Microsoft.Extensions.Hosting" in reason for reason in fulfillment["reasons"])
            assert not any("runtime identifiers" in reason for reason in fulfillment["reasons"])
        finally:
            PROPS.write_text(original_props, encoding="utf-8")
            cleanup_dynamic()
            reset_policy()

    def test_plan_applies_runtime_profiles_from_property_and_path_prefix(self) -> None:
        """RuntimeProfile properties and path-profile overrides must resolve target policy."""
        policy = json.loads(json.dumps(BASE_POLICY))
        policy["runtime_profiles"] = {
            "edge": {
                "required_framework": "net9.0",
                "required_rids": ["linux-musl-x64"],
                "minimum_packages": {"Microsoft.Extensions.Hosting": "9.0.0"},
            },
            "cli": {
                "required_rids": ["linux-x64"],
            },
        }
        policy["path_profile_overrides"] = {"Ops.Cli/": "cli", "Edge.Gateway/": "edge"}
        POLICY.write_text(json.dumps(policy), encoding="utf-8")
        dynamic = Path("/app/src/Profiled.Api")
        dynamic.mkdir(parents=True, exist_ok=True)
        (dynamic / "Profiled.Api.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
    <RuntimeProfile>edge</RuntimeProfile>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <PackageReference Include="Serilog.AspNetCore" Version="7.0.0" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )

        actions = {row["name"]: row for row in run_plan(reset_dynamic=False)["actions"]}
        profiled = actions["Profiled.Api"]
        assert profiled["action"] == "update"
        assert profiled["target"] == {
            "target_framework": "net9.0",
            "nullable": "enable",
            "runtime_identifiers": ["linux-musl-x64"],
        }
        assert any("target framework" in reason and "runtime profile edge" in reason for reason in profiled["reasons"])
        assert any("runtime identifiers" in reason and "runtime profile edge" in reason for reason in profiled["reasons"])
        assert any("Microsoft.Extensions.Hosting" in reason and "runtime profile edge" in reason for reason in profiled["reasons"])
        assert any("Serilog.AspNetCore" in reason for reason in profiled["reasons"])
        assert actions["Edge.Gateway"]["target"]["target_framework"] == "net9.0"
        assert any("runtime profile edge" in reason for reason in actions["Edge.Gateway"]["reasons"])
        assert actions["Ops.Cli"]["action"] == "keep"
        assert actions["Ops.Cli"]["target"]["runtime_identifiers"] == ["linux-x64"]
