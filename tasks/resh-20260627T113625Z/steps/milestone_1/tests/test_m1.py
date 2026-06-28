"""Milestone 1 tests for MSBuild project inventory output."""

import json
import subprocess
from pathlib import Path


OUT = Path("/app/out/msbuild-inventory.json")
PROPS = Path("/app/Directory.Packages.props")


def cleanup_dynamic() -> None:
    """Remove dynamically added projects between tests."""
    for dynamic in [
        Path("/app/src/Fulfillment.Api"),
        Path("/app/src/Namespaced.Service"),
        Path("/app/src/Deferred.Nullable"),
        Path("/app/src/Rid.Matrix.Api"),
        Path("/app/src/Rid.Matrix.Tests"),
    ]:
        if dynamic.exists():
            for path in sorted(dynamic.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            dynamic.rmdir()


def run_inventory(reset_dynamic: bool = True) -> dict:
    """Run the public inventory command and parse the JSON report."""
    OUT.unlink(missing_ok=True)
    if reset_dynamic:
        cleanup_dynamic()
    subprocess.run(
        [
            "python3",
            "/app/tools/msbuild_audit.py",
            "inventory",
            "/app/src",
            "/app/Directory.Packages.props",
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone1:
    """Validate MSBuild inventory discovery and package resolution."""

    def test_inventory_schema_sorting_and_summary(self) -> None:
        """Inventory output must contain sorted project rows and framework counts."""
        report = run_inventory()
        assert set(report) == {"projects", "summary"}
        rows = report["projects"]
        assert [row["path"] for row in rows] == sorted(row["path"] for row in rows)
        rows_by_name = {row["name"]: row for row in rows}
        assert rows_by_name["Legacy.Import"]["path"] == "Legacy.Import/Legacy.Import.csproj"
        assert not rows_by_name["Legacy.Import"]["path"].startswith("/app/src/")
        assert all(
            set(row)
            == {
                "path",
                "name",
                "target_framework",
                "nullable",
                "runtime_identifiers",
                "packages",
                "test_only",
            }
            for row in rows
        )
        assert report["summary"] == {
            "total": 10,
            "by_framework": {"net6.0": 2, "net7.0": 2, "net8.0": 6},
            "test_projects": 1,
            "missing_required_rids": 6,
        }

    def test_inventory_resolves_central_and_inline_package_versions(self) -> None:
        """PackageReference versions must resolve from central props or inline overrides."""
        rows = {row["name"]: row for row in run_inventory()["projects"]}
        assert rows["Billing.Api"]["path"] == "Billing.Api/Billing.Api.csproj"
        assert rows["Billing.Api"]["packages"]["Microsoft.Extensions.Hosting"] == "8.0.1"
        assert rows["Billing.Api"]["runtime_identifiers"] == ["linux-x64", "win-x64"]
        assert rows["Billing.Worker"]["nullable"] == "disable"
        assert rows["Edge.Gateway"]["packages"]["Microsoft.Extensions.Hosting"] == "7.0.0"
        assert rows["Tests.Integration"]["test_only"] is True
        assert rows["Tests.Integration"]["packages"]["xunit"] == "2.6.6"

    def test_inventory_reads_added_projects_each_run(self) -> None:
        """A project added during verification must appear in the next inventory."""
        dynamic = Path("/app/src/Fulfillment.Api")
        dynamic.mkdir(parents=True, exist_ok=True)
        (dynamic / "Fulfillment.Api.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        report = run_inventory(reset_dynamic=False)
        rows = {row["name"]: row for row in report["projects"]}
        assert rows["Fulfillment.Api"]["packages"]["Microsoft.Extensions.Hosting"] == "8.0.1"
        assert report["summary"]["total"] == 11
        assert report["summary"]["by_framework"]["net8.0"] == 7

    def test_inventory_reads_namespaced_msbuild_projects(self) -> None:
        """MSBuild XML namespaces must not hide project properties or package references."""
        dynamic = Path("/app/src/Namespaced.Service")
        dynamic.mkdir(parents=True, exist_ok=True)
        msbuild_ns = "http" + "://schemas.microsoft.com/developer/msbuild/2003"
        (dynamic / "Namespaced.Service.csproj").write_text(
            f"""<Project xmlns="{msbuild_ns}" Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Serilog.AspNetCore" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        rows = {row["name"]: row for row in run_inventory(reset_dynamic=False)["projects"]}
        assert rows["Namespaced.Service"]["target_framework"] == "net8.0"
        assert rows["Namespaced.Service"]["nullable"] == "enable"
        assert rows["Namespaced.Service"]["runtime_identifiers"] == ["linux-x64", "win-x64"]
        assert rows["Namespaced.Service"]["packages"]["Serilog.AspNetCore"] == "8.0.1"

    def test_inventory_reports_unspecified_nullable_for_namespaced_project_without_property(self) -> None:
        """Missing Nullable should be explicit while namespace, RID, and package parsing still work."""
        dynamic = Path("/app/src/Deferred.Nullable")
        dynamic.mkdir(parents=True, exist_ok=True)
        msbuild_ns = "http" + "://schemas.microsoft.com/developer/msbuild/2003"
        (dynamic / "Deferred.Nullable.csproj").write_text(
            f"""<Project xmlns="{msbuild_ns}" Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <RuntimeIdentifier> linux-x64 ; ; win-x64 </RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        report = run_inventory(reset_dynamic=False)
        rows = {row["name"]: row for row in report["projects"]}
        row = rows["Deferred.Nullable"]
        assert row["nullable"] == "unspecified"
        assert row["runtime_identifiers"] == ["linux-x64", "win-x64"]
        assert row["packages"]["Microsoft.Extensions.Hosting"] == "8.0.1"
        assert report["summary"]["missing_required_rids"] == 6
        cleanup_dynamic()

    def test_inventory_reads_namespaced_central_package_versions(self) -> None:
        """Namespaced Directory.Packages.props files must still resolve PackageVersion items."""
        original_props = PROPS.read_text(encoding="utf-8")
        dynamic = Path("/app/src/Fulfillment.Api")
        dynamic.mkdir(parents=True, exist_ok=True)
        msbuild_ns = "http" + "://schemas.microsoft.com/developer/msbuild/2003"
        try:
            PROPS.write_text(
                f"""<Project xmlns="{msbuild_ns}">
  <ItemGroup>
    <PackageVersion Include="Microsoft.Extensions.Hosting" Version="8.0.5" />
    <PackageVersion Include="Serilog.AspNetCore" Version="8.0.2" />
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
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <PackageReference Include="Serilog.AspNetCore" />
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )
            rows = {row["name"]: row for row in run_inventory(reset_dynamic=False)["projects"]}
            assert rows["Fulfillment.Api"]["packages"] == {
                "Microsoft.Extensions.Hosting": "8.0.5",
                "Serilog.AspNetCore": "8.0.2",
            }
        finally:
            PROPS.write_text(original_props, encoding="utf-8")
            cleanup_dynamic()

    def test_inventory_resolves_update_attribute_package_versions(self) -> None:
        """PackageVersion Update entries must be treated like Include entries in inventory."""
        original_props = PROPS.read_text(encoding="utf-8")
        dynamic = Path("/app/src/Fulfillment.Api")
        dynamic.mkdir(parents=True, exist_ok=True)
        try:
            PROPS.write_text(
                """<Project>
  <ItemGroup>
    <PackageVersion Update="Microsoft.Extensions.Hosting" Version="8.0.7" />
    <PackageVersion Include="Serilog.AspNetCore" Version="8.0.4" />
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
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <PackageReference Include="Serilog.AspNetCore" />
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )
            rows = {row["name"]: row for row in run_inventory(reset_dynamic=False)["projects"]}
            assert rows["Fulfillment.Api"]["packages"] == {
                "Microsoft.Extensions.Hosting": "8.0.7",
                "Serilog.AspNetCore": "8.0.4",
            }
        finally:
            PROPS.write_text(original_props, encoding="utf-8")
            cleanup_dynamic()

    def test_inventory_splits_singular_runtime_identifier_lists_with_whitespace(self) -> None:
        """Singular RuntimeIdentifier values may still contain semicolon-delimited RID lists."""
        dynamic = Path("/app/src/Fulfillment.Api")
        dynamic.mkdir(parents=True, exist_ok=True)
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
        report = run_inventory(reset_dynamic=False)
        rows = {row["name"]: row for row in report["projects"]}
        assert rows["Fulfillment.Api"]["runtime_identifiers"] == ["linux-x64", "win-x64"]
        assert rows["Fulfillment.Api"]["packages"]["Microsoft.Extensions.Hosting"] == "8.0.1"
        assert report["summary"]["missing_required_rids"] == 6
        cleanup_dynamic()

    def test_inventory_counts_required_rids_without_test_projects_or_empty_entries(self) -> None:
        """missing_required_rids uses required_rids and ignores test projects with bad RID metadata."""
        service = Path("/app/src/Rid.Matrix.Api")
        test_project = Path("/app/src/Rid.Matrix.Tests")
        service.mkdir(parents=True, exist_ok=True)
        test_project.mkdir(parents=True, exist_ok=True)
        (service / "Rid.Matrix.Api.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifier> ; linux-x64 ; ; win-x64 ; </RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        (test_project / "Rid.Matrix.Tests.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsTestProject>true</IsTestProject>
    <RuntimeIdentifier>osx-arm64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="xunit" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        report = run_inventory(reset_dynamic=False)
        rows = {row["name"]: row for row in report["projects"]}
        assert rows["Rid.Matrix.Api"]["runtime_identifiers"] == ["linux-x64", "win-x64"]
        assert rows["Rid.Matrix.Tests"]["test_only"] is True
        assert rows["Rid.Matrix.Tests"]["runtime_identifiers"] == ["osx-arm64"]
        assert report["summary"]["total"] == 12
        assert report["summary"]["test_projects"] == 2
        assert report["summary"]["missing_required_rids"] == 6
        cleanup_dynamic()
