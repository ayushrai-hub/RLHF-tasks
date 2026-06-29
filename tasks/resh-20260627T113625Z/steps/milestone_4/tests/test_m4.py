"""Milestone 4 tests for applying MSBuild migration wave changes."""

import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


OUT = Path("/app/out/msbuild-apply-plan.json")
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
    Path("/app/src/Apply.Namespaced"),
    Path("/app/src/Apply.Tests"),
    Path("/app/src/Profiled.Api"),
]
BASE_PROJECTS = {
    "Billing.Api/Billing.Api.csproj": """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <PackageReference Include="Serilog.AspNetCore" />
    <ProjectReference Include="..\\Shared.Logging\\Shared.Logging.csproj" />
  </ItemGroup>
</Project>
""",
    "Billing.Worker/Billing.Worker.csproj": """<Project Sdk="Microsoft.NET.Sdk.Worker">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifiers>linux-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <PackageReference Include="Microsoft.Data.SqlClient" />
    <ProjectReference Include="..\\Shared.Logging\\Shared.Logging.csproj" />
  </ItemGroup>
</Project>
""",
    "Edge.Gateway/Edge.Gateway.csproj": """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="7.0.0" />
    <PackageReference Include="Serilog.AspNetCore" />
    <ProjectReference Include="..\\Billing.Api\\Billing.Api.csproj" />
    <ProjectReference Include="..\\Identity.Api\\Identity.Api.csproj" />
  </ItemGroup>
</Project>
""",
    "Identity.Api/Identity.Api.csproj": """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <PackageReference Include="Serilog.AspNetCore" />
    <ProjectReference Include="..\\Shared.Logging\\Shared.Logging.csproj" />
  </ItemGroup>
</Project>
""",
    "Legacy.Import/Legacy.Import.csproj": """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>win-x64</RuntimeIdentifier>
  </PropertyGroup>
</Project>
""",
    "Ops.Cli/Ops.Cli.csproj": """<Project Sdk="Microsoft.NET.Sdk">
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
    "Reporting.Job/Reporting.Job.csproj": """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Data.SqlClient" />
  </ItemGroup>
</Project>
""",
    "Shared.Logging/Shared.Logging.csproj": """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Serilog.AspNetCore" />
  </ItemGroup>
</Project>
""",
    "Telemetry.Collector/Telemetry.Collector.csproj": """<Project Sdk="Microsoft.NET.Sdk.Worker">
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
    "Tests.Integration/Tests.Integration.csproj": """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <IsTestProject>true</IsTestProject>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="xunit" />
    <PackageReference Include="coverlet.collector" />
  </ItemGroup>
</Project>
""",
}


def local_name(tag: str) -> str:
    """Return the XML local name for namespaced and plain MSBuild elements."""
    return tag.rsplit("}", 1)[-1]


def load_project(path: Path) -> ET.Element:
    """Load a project XML root."""
    return ET.parse(path).getroot()


def first_text(root: ET.Element, name: str) -> str | None:
    """Read the first property value by local element name."""
    for node in root.iter():
        if local_name(node.tag) == name:
            return (node.text or "").strip()
    return None


def package_ref(root: ET.Element, name: str) -> ET.Element:
    """Find a package reference by Include."""
    for node in root.iter():
        if local_name(node.tag) == "PackageReference" and node.attrib.get("Include") == name:
            return node
    raise AssertionError(f"missing package reference {name}")


def cleanup_dynamic() -> None:
    """Remove dynamic projects created by this milestone."""
    for directory in DYNAMIC_DIRS:
        if directory.exists():
            shutil.rmtree(directory)


def reset_policy() -> None:
    """Restore the public runtime policy."""
    POLICY.write_text(json.dumps(BASE_POLICY), encoding="utf-8")


def restore_base_projects() -> None:
    """Restore shipped project files so development runs cannot contaminate verifier state."""
    for rel_path, content in BASE_PROJECTS.items():
        path = Path("/app/src") / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def run_apply(reset: bool = True) -> dict:
    """Run the public apply-plan command and parse its JSON report."""
    OUT.unlink(missing_ok=True)
    if reset:
        cleanup_dynamic()
        reset_policy()
        restore_base_projects()
    subprocess.run(
        [
            "python3",
            "/app/tools/msbuild_audit.py",
            "apply-plan",
            "/app/src",
            "/app/Directory.Packages.props",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone4:
    """Validate source mutation, report shape, and idempotency."""

    def test_apply_updates_wave_projects_and_skips_retired_projects(self) -> None:
        """Base update projects are changed to their target state and retired projects are untouched."""
        cleanup_dynamic()
        reset_policy()
        restore_base_projects()
        protected_paths = [Path("/app/Directory.Packages.props"), POLICY]
        protected_paths.extend(sorted(Path("/app/src").rglob("*.cs")))
        before = {path: path.read_text(encoding="utf-8") for path in protected_paths}
        report = run_apply(reset=False)
        assert set(report) == {"applied", "blocked", "retire", "summary"}
        assert report["blocked"] == []
        assert report["retire"] == [
            "Legacy.Import/Legacy.Import.csproj",
            "Reporting.Job/Reporting.Job.csproj",
        ]
        assert [row["path"] for row in report["applied"]] == [
            path
            for _, path in sorted((row["wave"], row["path"]) for row in report["applied"])
        ]
        assert all(
            set(row) == {"path", "name", "wave", "changes", "target", "packages_updated"}
            for row in report["applied"]
        )
        assert report["summary"] == {
            "applied_count": 6,
            "blocked_count": 0,
            "retire_count": 2,
            "files_changed": 6,
            "package_versions_updated": 1,
            "wave_count": 3,
        }
        applied = {row["path"]: row for row in report["applied"]}
        assert applied["Billing.Worker/Billing.Worker.csproj"]["name"] == "Billing.Worker"
        assert applied["Billing.Worker/Billing.Worker.csproj"]["wave"] == 2
        assert applied["Billing.Worker/Billing.Worker.csproj"]["changes"] == [
            "target_framework",
            "nullable",
            "runtime_identifiers",
        ]
        assert applied["Edge.Gateway/Edge.Gateway.csproj"]["packages_updated"] == {
            "Microsoft.Extensions.Hosting": "8.0.0"
        }

        worker = load_project(Path("/app/src/Billing.Worker/Billing.Worker.csproj"))
        assert first_text(worker, "TargetFramework") == "net8.0"
        assert first_text(worker, "Nullable") == "enable"
        assert first_text(worker, "RuntimeIdentifiers") == "linux-x64;win-x64"

        edge = load_project(Path("/app/src/Edge.Gateway/Edge.Gateway.csproj"))
        assert package_ref(edge, "Microsoft.Extensions.Hosting").attrib["Version"] == "8.0.0"

        legacy = load_project(Path("/app/src/Legacy.Import/Legacy.Import.csproj"))
        assert first_text(legacy, "TargetFramework") == "net6.0"
        after = {path: path.read_text(encoding="utf-8") for path in protected_paths}
        assert after == before

    def test_apply_honors_dependency_blocks_runtime_profiles_and_idempotency(self) -> None:
        """Dynamic projects exercise wave order, retired-dependency blocks, profile targets, and no-op reruns."""
        cleanup_dynamic()
        policy = json.loads(json.dumps(BASE_POLICY))
        policy["runtime_profiles"] = {
            "edge": {
                "required_framework": "net9.0",
                "required_nullable": "enable",
                "required_rids": ["linux-musl-x64"],
                "minimum_packages": {"Microsoft.Extensions.Hosting": "9.0.0"},
            }
        }
        policy["path_profile_overrides"] = {
            "Apply.Root/": "edge",
            "Apply.Leaf/": "edge",
            "Apply.Central/": "edge",
        }
        POLICY.write_text(json.dumps(policy), encoding="utf-8")
        leaf = Path("/app/src/Apply.Leaf")
        root = Path("/app/src/Apply.Root")
        blocked = Path("/app/src/Apply.Blocked")
        central = Path("/app/src/Apply.Central")
        leaf.mkdir(parents=True, exist_ok=True)
        root.mkdir(parents=True, exist_ok=True)
        blocked.mkdir(parents=True, exist_ok=True)
        central.mkdir(parents=True, exist_ok=True)
        (leaf / "Apply.Leaf.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="8.0.0" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        (root / "Apply.Root.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifiers>linux-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="8.0.0" />
    <ProjectReference Include="..\\Apply.Leaf\\Apply.Leaf.csproj" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        (blocked / "Apply.Blocked.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <ProjectReference Include="..\\Legacy.Import\\Legacy.Import.csproj" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        (central / "Apply.Central.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )

        first = run_apply(reset=False)
        assert [row["path"] for row in first["blocked"]] == sorted(row["path"] for row in first["blocked"])
        assert all(set(row) == {"path", "name", "reasons", "unchanged"} for row in first["blocked"])
        applied = {row["path"]: row for row in first["applied"]}
        assert applied["Apply.Leaf/Apply.Leaf.csproj"]["wave"] < applied["Apply.Root/Apply.Root.csproj"]["wave"]
        assert applied["Apply.Root/Apply.Root.csproj"]["target"]["target_framework"] == "net9.0"
        assert applied["Apply.Root/Apply.Root.csproj"]["packages_updated"] == {
            "Microsoft.Extensions.Hosting": "9.0.0"
        }
        blocked_rows = {row["path"]: row for row in first["blocked"]}
        assert blocked_rows["Apply.Blocked/Apply.Blocked.csproj"]["name"] == "Apply.Blocked"
        assert blocked_rows["Apply.Blocked/Apply.Blocked.csproj"]["unchanged"] is True
        assert any("retired dependency" in reason for reason in blocked_rows["Apply.Blocked/Apply.Blocked.csproj"]["reasons"])

        root_xml = load_project(root / "Apply.Root.csproj")
        assert first_text(root_xml, "TargetFramework") == "net9.0"
        assert first_text(root_xml, "RuntimeIdentifiers") == "linux-musl-x64"
        assert package_ref(root_xml, "Microsoft.Extensions.Hosting").attrib["Version"] == "9.0.0"
        central_row = applied["Apply.Central/Apply.Central.csproj"]
        assert central_row["packages_updated"] == {}
        assert "package_versions" not in central_row["changes"]
        central_xml = load_project(central / "Apply.Central.csproj")
        assert first_text(central_xml, "RuntimeIdentifiers") == "linux-musl-x64"
        assert "Version" not in package_ref(central_xml, "Microsoft.Extensions.Hosting").attrib
        blocked_xml = load_project(blocked / "Apply.Blocked.csproj")
        assert first_text(blocked_xml, "TargetFramework") == "net7.0"

        second = run_apply(reset=False)
        assert second["applied"] == []
        assert second["summary"]["applied_count"] == 0
        assert second["summary"]["files_changed"] == 0
        assert second["summary"]["package_versions_updated"] == 0
        assert {row["path"] for row in second["blocked"]} >= {"Apply.Blocked/Apply.Blocked.csproj"}

    def test_apply_updates_namespaced_msbuild_projects(self) -> None:
        """Apply-plan must mutate namespaced project files using the same policy rules."""
        cleanup_dynamic()
        reset_policy()
        restore_base_projects()
        namespaced_dir = Path("/app/src/Apply.Namespaced")
        namespaced_dir.mkdir(parents=True, exist_ok=True)
        project_path = namespaced_dir / "Apply.Namespaced.csproj"
        msbuild_ns = "http" + "://schemas.microsoft.com/developer/msbuild/2003"
        project_path.write_text(
            f"""<Project xmlns="{msbuild_ns}" Sdk="Microsoft.NET.Sdk.Worker">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="7.0.0" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )

        report = run_apply(reset=False)
        applied = {row["path"]: row for row in report["applied"]}
        row = applied["Apply.Namespaced/Apply.Namespaced.csproj"]
        assert row["changes"] == [
            "target_framework",
            "nullable",
            "runtime_identifiers",
            "package_versions",
        ]
        assert row["packages_updated"] == {"Microsoft.Extensions.Hosting": "8.0.0"}
        root = load_project(project_path)
        assert first_text(root, "TargetFramework") == "net8.0"
        assert first_text(root, "Nullable") == "enable"
        assert first_text(root, "RuntimeIdentifier") is None
        assert first_text(root, "RuntimeIdentifiers") == "linux-x64;win-x64"
        assert package_ref(root, "Microsoft.Extensions.Hosting").attrib["Version"] == "8.0.0"

    def test_apply_removes_test_project_rids_and_blocks_cycles_without_edits(self) -> None:
        """Test-only RID cleanup must run while dependency cycles stay blocked and unchanged."""
        cleanup_dynamic()
        reset_policy()
        restore_base_projects()
        test_dir = Path("/app/src/Apply.Tests")
        cycle_a = Path("/app/src/Apply.CycleA")
        cycle_b = Path("/app/src/Apply.CycleB")
        test_dir.mkdir(parents=True, exist_ok=True)
        cycle_a.mkdir(parents=True, exist_ok=True)
        cycle_b.mkdir(parents=True, exist_ok=True)
        (test_dir / "Apply.Tests.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <IsTestProject>true</IsTestProject>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>win-x64</RuntimeIdentifier>
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="xunit" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        (cycle_a / "Apply.CycleA.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\\Apply.CycleB\\Apply.CycleB.csproj" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        cycle_b_initial = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\\Apply.CycleA\\Apply.CycleA.csproj" />
  </ItemGroup>
</Project>
"""
        (cycle_b / "Apply.CycleB.csproj").write_text(cycle_b_initial, encoding="utf-8")

        report = run_apply(reset=False)
        assert [row["path"] for row in report["blocked"]] == sorted(row["path"] for row in report["blocked"])
        applied = {row["path"]: row for row in report["applied"]}
        assert "Apply.Tests/Apply.Tests.csproj" in applied
        assert applied["Apply.Tests/Apply.Tests.csproj"]["name"] == "Apply.Tests"
        assert "runtime_identifiers" in applied["Apply.Tests/Apply.Tests.csproj"]["changes"]
        tests_xml = load_project(test_dir / "Apply.Tests.csproj")
        assert first_text(tests_xml, "TargetFramework") == "net8.0"
        assert first_text(tests_xml, "Nullable") == "enable"
        assert first_text(tests_xml, "RuntimeIdentifier") is None
        assert first_text(tests_xml, "RuntimeIdentifiers") is None

        blocked = {row["path"]: row for row in report["blocked"]}
        assert set(blocked) >= {
            "Apply.CycleA/Apply.CycleA.csproj",
            "Apply.CycleB/Apply.CycleB.csproj",
        }
        assert blocked["Apply.CycleA/Apply.CycleA.csproj"]["name"] == "Apply.CycleA"
        assert blocked["Apply.CycleB/Apply.CycleB.csproj"]["name"] == "Apply.CycleB"
        assert all(any("dependency cycle" in reason for reason in row["reasons"]) for row in blocked.values())
        assert (cycle_b / "Apply.CycleB.csproj").read_text(encoding="utf-8") == cycle_b_initial
