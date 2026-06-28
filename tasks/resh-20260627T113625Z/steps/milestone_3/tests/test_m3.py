"""Milestone 3 tests for dependency-aware migration wave planning."""

import json
import subprocess
from pathlib import Path


OUT = Path("/app/out/msbuild-migration-waves.json")
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


def cleanup_dynamic() -> None:
    """Remove dynamically added projects between tests."""
    for dynamic in [
        Path("/app/src/Fulfillment.Api"),
        Path("/app/src/Namespaced.Service"),
        Path("/app/src/Profiled.Api"),
        Path("/app/src/Cycle.A"),
        Path("/app/src/Cycle.B"),
        Path("/app/src/External.Ref"),
        Path("/app/src/Dependency.Root"),
        Path("/app/src/Dependency.Middle"),
        Path("/app/src/Dependency.Leaf"),
        Path("/app/src/Dependency.Blocked"),
        Path("/app/src/RidPolicy.Root"),
        Path("/app/src/RidPolicy.Middle"),
        Path("/app/src/RidPolicy.Leaf"),
        Path("/app/src/RidPolicy.Blocked"),
        Path("/app/src/Macro.Root"),
        Path("/app/src/Macro.Leaf"),
        Path("/app/src/Macro.Blocked"),
        Path("/app/src/UpdateAttr.Root"),
        Path("/app/src/UpdateAttr.Middle"),
        Path("/app/src/UpdateAttr.Leaf"),
        Path("/app/src/ProfileWave.Root"),
        Path("/app/src/ProfileWave.Middle"),
        Path("/app/src/ProfileWave.Leaf"),
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


def run_waves(reset_dynamic: bool = True) -> dict:
    """Run the public waves command and parse the JSON report."""
    OUT.unlink(missing_ok=True)
    if reset_dynamic:
        cleanup_dynamic()
        reset_policy()
    subprocess.run(
        [
            "python3",
            "/app/tools/msbuild_audit.py",
            "waves",
            "/app/src",
            "/app/Directory.Packages.props",
            str(POLICY),
            str(OUT),
        ],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone3:
    """Validate dependency-aware migration wave output."""

    def test_waves_schema_and_dependency_order(self) -> None:
        """Update projects must be wave-ordered after referenced update dependencies."""
        report = run_waves()
        assert set(report) == {"waves", "blocked", "retire", "summary"}
        assert all(set(row) == {"wave", "projects"} for row in report["waves"])
        assert all(row["projects"] == sorted(row["projects"]) for row in report["waves"])
        assert [row["wave"] for row in report["waves"]] == list(range(1, len(report["waves"]) + 1))
        assert report["blocked"] == []
        assert report["retire"] == [
            "Legacy.Import/Legacy.Import.csproj",
            "Reporting.Job/Reporting.Job.csproj",
        ]
        assert report["summary"] == {
            "wave_count": 3,
            "update_projects": 6,
            "blocked_projects": 0,
            "retire_projects": 2,
        }
        assert report["waves"] == [
            {
                "wave": 1,
                "projects": [
                    "Ops.Cli/Ops.Cli.csproj",
                    "Shared.Logging/Shared.Logging.csproj",
                    "Tests.Integration/Tests.Integration.csproj",
                ],
            },
            {
                "wave": 2,
                "projects": [
                    "Billing.Worker/Billing.Worker.csproj",
                    "Identity.Api/Identity.Api.csproj",
                ],
            },
            {"wave": 3, "projects": ["Edge.Gateway/Edge.Gateway.csproj"]},
        ]

    def test_waves_blocks_projects_that_reference_retired_dependencies(self) -> None:
        """A project that references a retired project is blocked and excluded from waves."""
        dynamic = Path("/app/src/Fulfillment.Api")
        dynamic.mkdir(parents=True, exist_ok=True)
        (dynamic / "Fulfillment.Api.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <ProjectReference Include="..\\Billing.Worker\\Billing.Worker.csproj" />
    <ProjectReference Include="..\\Legacy.Import\\Legacy.Import.csproj" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        report = run_waves(reset_dynamic=False)
        assert [row["path"] for row in report["blocked"]] == sorted(row["path"] for row in report["blocked"])
        assert all(set(row) == {"path", "name", "reasons"} for row in report["blocked"])
        blocked = {row["path"]: row for row in report["blocked"]}
        assert "Fulfillment.Api/Fulfillment.Api.csproj" in blocked
        assert blocked["Fulfillment.Api/Fulfillment.Api.csproj"]["name"] == "Fulfillment.Api"
        assert any("retired dependency" in reason for reason in blocked["Fulfillment.Api/Fulfillment.Api.csproj"]["reasons"])
        assert all(
            "Fulfillment.Api/Fulfillment.Api.csproj" not in wave["projects"]
            for wave in report["waves"]
        )
        assert report["summary"]["blocked_projects"] == 1
        assert report["summary"]["update_projects"] == 7

    def test_waves_reads_namespaced_project_references_and_policy_changes(self) -> None:
        """Namespaced ProjectReference entries and changed policy must affect wave planning."""
        cleanup_dynamic()
        policy = dict(BASE_POLICY)
        policy["required_rids"] = ["linux-x64"]
        POLICY.write_text(json.dumps(policy), encoding="utf-8")
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
    <ProjectReference Include="..\\Billing.Api\\Billing.Api.csproj" />
    <ProjectReference Include="..\\Shared.Logging\\Shared.Logging.csproj" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        report = run_waves(reset_dynamic=False)
        projects_by_wave = {
            project: row["wave"]
            for row in report["waves"]
            for project in row["projects"]
        }
        assert projects_by_wave["Shared.Logging/Shared.Logging.csproj"] < projects_by_wave["Namespaced.Service/Namespaced.Service.csproj"]
        assert "Billing.Api/Billing.Api.csproj" in projects_by_wave
        assert report["summary"]["update_projects"] == 7
        assert report["blocked"] == []

    def test_waves_blocks_update_dependency_cycles(self) -> None:
        """Update projects in a dependency cycle are blocked with cycle reasons."""
        cleanup_dynamic()
        reset_policy()
        cycle_a = Path("/app/src/Cycle.A")
        cycle_b = Path("/app/src/Cycle.B")
        cycle_a.mkdir(parents=True, exist_ok=True)
        cycle_b.mkdir(parents=True, exist_ok=True)
        (cycle_a / "Cycle.A.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <ProjectReference Include="..\\Cycle.B\\Cycle.B.csproj" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        (cycle_b / "Cycle.B.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <ProjectReference Include="..\\Cycle.A\\Cycle.A.csproj" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )

        report = run_waves(reset_dynamic=False)
        assert [row["path"] for row in report["blocked"]] == sorted(row["path"] for row in report["blocked"])
        assert all("name" in row for row in report["blocked"])
        blocked = {row["path"]: row for row in report["blocked"]}
        assert set(blocked) >= {"Cycle.A/Cycle.A.csproj", "Cycle.B/Cycle.B.csproj"}
        assert blocked["Cycle.A/Cycle.A.csproj"]["name"] == "Cycle.A"
        assert blocked["Cycle.B/Cycle.B.csproj"]["name"] == "Cycle.B"
        assert all(any("dependency cycle" in reason for reason in row["reasons"]) for row in blocked.values())
        wave_projects = {project for wave in report["waves"] for project in wave["projects"]}
        assert "Cycle.A/Cycle.A.csproj" not in wave_projects
        assert "Cycle.B/Cycle.B.csproj" not in wave_projects
        assert report["summary"]["update_projects"] == 8
        assert report["summary"]["blocked_projects"] == 2

    def test_waves_ignores_external_and_undiscovered_project_references(self) -> None:
        """References outside /app/src or to undiscovered projects do not block waves."""
        cleanup_dynamic()
        reset_policy()
        dynamic = Path("/app/src/External.Ref")
        dynamic.mkdir(parents=True, exist_ok=True)
        (dynamic / "External.Ref.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <ProjectReference Include="..\\Billing.Worker\\Billing.Worker.csproj" />
    <ProjectReference Include="..\\Missing.Project\\Missing.Project.csproj" />
    <ProjectReference Include="..\\..\\outside\\Ghost.csproj" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )

        report = run_waves(reset_dynamic=False)
        projects_by_wave = {
            project: row["wave"]
            for row in report["waves"]
            for project in row["projects"]
        }
        assert projects_by_wave["Billing.Worker/Billing.Worker.csproj"] < projects_by_wave["External.Ref/External.Ref.csproj"]
        assert "External.Ref/External.Ref.csproj" in projects_by_wave
        assert report["blocked"] == []
        assert report["retire"] == [
            "Legacy.Import/Legacy.Import.csproj",
            "Reporting.Job/Reporting.Job.csproj",
        ]

    def test_waves_orders_generated_chain_and_blocks_retired_dependency_together(self) -> None:
        """A mixed generated fixture must order update chains while blocking retired references."""
        cleanup_dynamic()
        reset_policy()
        fixtures = {
            "Dependency.Root": [],
            "Dependency.Middle": ["Dependency.Root"],
            "Dependency.Leaf": ["Dependency.Middle"],
            "Dependency.Blocked": ["Dependency.Middle", "Legacy.Import"],
        }
        for name, references in fixtures.items():
            project_dir = Path("/app/src") / name
            project_dir.mkdir(parents=True, exist_ok=True)
            reference_xml = "\n".join(
                f'    <ProjectReference Include="..\\{ref}\\{ref}.csproj" />' for ref in references
            )
            project_dir.joinpath(f"{name}.csproj").write_text(
                f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
{reference_xml}
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )

        report = run_waves(reset_dynamic=False)
        projects_by_wave = {
            project: row["wave"]
            for row in report["waves"]
            for project in row["projects"]
        }
        assert projects_by_wave["Dependency.Root/Dependency.Root.csproj"] < projects_by_wave[
            "Dependency.Middle/Dependency.Middle.csproj"
        ]
        assert projects_by_wave["Dependency.Middle/Dependency.Middle.csproj"] < projects_by_wave[
            "Dependency.Leaf/Dependency.Leaf.csproj"
        ]
        blocked = {row["path"]: row for row in report["blocked"]}
        assert "Dependency.Blocked/Dependency.Blocked.csproj" in blocked
        assert any(
            "retired dependency" in reason and "Legacy.Import/Legacy.Import.csproj" in reason
            for reason in blocked["Dependency.Blocked/Dependency.Blocked.csproj"]["reasons"]
        )
        assert "Dependency.Blocked/Dependency.Blocked.csproj" not in projects_by_wave
        assert report["summary"]["update_projects"] == 10
        assert report["summary"]["blocked_projects"] == 1
        assert report["summary"]["retire_projects"] == 2

    def test_waves_combines_exact_rid_policy_dependency_order_and_retired_blocks(self) -> None:
        """Changed RID policy must use exact matching while still ordering and blocking."""
        cleanup_dynamic()
        policy = dict(BASE_POLICY)
        policy["required_rids"] = ["linux-x64"]
        POLICY.write_text(json.dumps(policy), encoding="utf-8")
        fixtures = {
            "RidPolicy.Root": {
                "framework": "net8.0",
                "nullable": "enable",
                "rid_property": "<RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>",
                "references": [],
            },
            "RidPolicy.Middle": {
                "framework": "net7.0",
                "nullable": "disable",
                "rid_property": "<RuntimeIdentifier>linux-x64</RuntimeIdentifier>",
                "references": ["RidPolicy.Root"],
            },
            "RidPolicy.Leaf": {
                "framework": "net7.0",
                "nullable": "disable",
                "rid_property": "<RuntimeIdentifier>linux-x64</RuntimeIdentifier>",
                "references": ["RidPolicy.Middle"],
            },
            "RidPolicy.Blocked": {
                "framework": "net7.0",
                "nullable": "disable",
                "rid_property": "<RuntimeIdentifier>linux-x64</RuntimeIdentifier>",
                "references": ["RidPolicy.Middle", "Legacy.Import"],
            },
        }
        for name, config in fixtures.items():
            project_dir = Path("/app/src") / name
            project_dir.mkdir(parents=True, exist_ok=True)
            reference_xml = "\n".join(
                f'    <ProjectReference Include="..\\{ref}\\{ref}.csproj" />'
                for ref in config["references"]
            )
            project_dir.joinpath(f"{name}.csproj").write_text(
                f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>{config["framework"]}</TargetFramework>
    <Nullable>{config["nullable"]}</Nullable>
    {config["rid_property"]}
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
{reference_xml}
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )

        report = run_waves(reset_dynamic=False)
        projects_by_wave = {
            project: row["wave"]
            for row in report["waves"]
            for project in row["projects"]
        }
        assert projects_by_wave["RidPolicy.Root/RidPolicy.Root.csproj"] < projects_by_wave[
            "RidPolicy.Middle/RidPolicy.Middle.csproj"
        ]
        assert projects_by_wave["RidPolicy.Middle/RidPolicy.Middle.csproj"] < projects_by_wave[
            "RidPolicy.Leaf/RidPolicy.Leaf.csproj"
        ]
        blocked = {row["path"]: row for row in report["blocked"]}
        assert "RidPolicy.Blocked/RidPolicy.Blocked.csproj" in blocked
        assert any(
            "retired dependency" in reason and "Legacy.Import/Legacy.Import.csproj" in reason
            for reason in blocked["RidPolicy.Blocked/RidPolicy.Blocked.csproj"]["reasons"]
        )
        assert "RidPolicy.Blocked/RidPolicy.Blocked.csproj" not in projects_by_wave
        assert report["summary"]["update_projects"] == 10
        assert report["summary"]["blocked_projects"] == 1
        assert report["summary"]["retire_projects"] == 2

    def test_waves_expands_msbuild_directory_macro_before_ordering_and_blocking(self) -> None:
        """ProjectReference paths using MSBuildThisFileDirectory must normalize before wave planning."""
        cleanup_dynamic()
        reset_policy()
        fixtures = {
            "Macro.Root": [],
            "Macro.Leaf": [
                "$(MSBuildThisFileDirectory)..\\Macro.Root\\Macro.Root.csproj",
                "$(MSBuildThisFileDirectory)..\\Missing.Macro\\Missing.Macro.csproj",
            ],
            "Macro.Blocked": [
                "$(MSBuildThisFileDirectory)..\\Macro.Root\\Macro.Root.csproj",
                "$(MSBuildThisFileDirectory)..\\Legacy.Import\\Legacy.Import.csproj",
            ],
        }
        for name, references in fixtures.items():
            project_dir = Path("/app/src") / name
            project_dir.mkdir(parents=True, exist_ok=True)
            reference_xml = "\n".join(
                f'    <ProjectReference Include="{reference}" />' for reference in references
            )
            project_dir.joinpath(f"{name}.csproj").write_text(
                f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net7.0</TargetFramework>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>linux-x64</RuntimeIdentifier>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
{reference_xml}
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )

        report = run_waves(reset_dynamic=False)
        projects_by_wave = {
            project: row["wave"]
            for row in report["waves"]
            for project in row["projects"]
        }
        assert projects_by_wave["Macro.Root/Macro.Root.csproj"] < projects_by_wave[
            "Macro.Leaf/Macro.Leaf.csproj"
        ]
        blocked = {row["path"]: row for row in report["blocked"]}
        assert "Macro.Blocked/Macro.Blocked.csproj" in blocked
        assert any(
            "retired dependency" in reason and "Legacy.Import/Legacy.Import.csproj" in reason
            for reason in blocked["Macro.Blocked/Macro.Blocked.csproj"]["reasons"]
        )
        assert "Macro.Blocked/Macro.Blocked.csproj" not in projects_by_wave
        assert report["summary"]["update_projects"] == 9
        assert report["summary"]["blocked_projects"] == 1

    def test_waves_orders_update_attribute_central_versions_in_generated_chain(self) -> None:
        """PackageVersion Update entries must feed policy decisions before wave ordering."""
        cleanup_dynamic()
        original_props = Path("/app/Directory.Packages.props").read_text(encoding="utf-8")
        try:
            Path("/app/Directory.Packages.props").write_text(
                """<Project>
  <ItemGroup>
    <PackageVersion Update="Microsoft.Extensions.Hosting" Version="7.0.9" />
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )
            fixtures = {
                "UpdateAttr.Root": [],
                "UpdateAttr.Middle": ["UpdateAttr.Root"],
                "UpdateAttr.Leaf": ["UpdateAttr.Middle"],
            }
            for name, references in fixtures.items():
                project_dir = Path("/app/src") / name
                project_dir.mkdir(parents=True, exist_ok=True)
                reference_xml = "\n".join(
                    f'    <ProjectReference Include="..\\{ref}\\{ref}.csproj" />'
                    for ref in references
                )
                project_dir.joinpath(f"{name}.csproj").write_text(
                    f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
{reference_xml}
  </ItemGroup>
</Project>
""",
                    encoding="utf-8",
                )

            report = run_waves(reset_dynamic=False)
            projects_by_wave = {
                project: row["wave"]
                for row in report["waves"]
                for project in row["projects"]
            }
            assert projects_by_wave["UpdateAttr.Root/UpdateAttr.Root.csproj"] < projects_by_wave[
                "UpdateAttr.Middle/UpdateAttr.Middle.csproj"
            ]
            assert projects_by_wave["UpdateAttr.Middle/UpdateAttr.Middle.csproj"] < projects_by_wave[
                "UpdateAttr.Leaf/UpdateAttr.Leaf.csproj"
            ]
            actions = {project for wave in report["waves"] for project in wave["projects"]}
            assert {
                "UpdateAttr.Root/UpdateAttr.Root.csproj",
                "UpdateAttr.Middle/UpdateAttr.Middle.csproj",
                "UpdateAttr.Leaf/UpdateAttr.Leaf.csproj",
            } <= actions
            assert report["summary"]["update_projects"] == 11
            assert report["summary"]["blocked_projects"] == 0
        finally:
            Path("/app/Directory.Packages.props").write_text(original_props, encoding="utf-8")
            cleanup_dynamic()

    def test_waves_orders_projects_updated_only_by_runtime_profile_policy(self) -> None:
        """Runtime profile policy updates must be included in dependency waves."""
        cleanup_dynamic()
        policy = json.loads(json.dumps(BASE_POLICY))
        policy["runtime_profiles"] = {
            "edge": {
                "required_framework": "net9.0",
                "required_rids": ["linux-musl-x64"],
                "minimum_packages": {"Microsoft.Extensions.Hosting": "9.0.0"},
            }
        }
        policy["path_profile_overrides"] = {
            "ProfileWave.Middle/": "edge",
            "ProfileWave.Leaf/": "edge",
        }
        POLICY.write_text(json.dumps(policy), encoding="utf-8")
        try:
            fixtures = {
                "ProfileWave.Root": {
                    "profile": "<RuntimeProfile>edge</RuntimeProfile>",
                    "references": [],
                },
                "ProfileWave.Middle": {
                    "profile": "",
                    "references": ["ProfileWave.Root"],
                },
                "ProfileWave.Leaf": {
                    "profile": "",
                    "references": ["ProfileWave.Middle"],
                },
            }
            for name, config in fixtures.items():
                project_dir = Path("/app/src") / name
                project_dir.mkdir(parents=True, exist_ok=True)
                reference_xml = "\n".join(
                    f'    <ProjectReference Include="..\\{ref}\\{ref}.csproj" />'
                    for ref in config["references"]
                )
                project_dir.joinpath(f"{name}.csproj").write_text(
                    f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <RuntimeIdentifiers>linux-x64;win-x64</RuntimeIdentifiers>
    {config["profile"]}
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
{reference_xml}
  </ItemGroup>
</Project>
""",
                    encoding="utf-8",
                )

            report = run_waves(reset_dynamic=False)
            projects_by_wave = {
                project: row["wave"]
                for row in report["waves"]
                for project in row["projects"]
            }
            assert projects_by_wave["ProfileWave.Root/ProfileWave.Root.csproj"] < projects_by_wave[
                "ProfileWave.Middle/ProfileWave.Middle.csproj"
            ]
            assert projects_by_wave["ProfileWave.Middle/ProfileWave.Middle.csproj"] < projects_by_wave[
                "ProfileWave.Leaf/ProfileWave.Leaf.csproj"
            ]
            assert report["summary"]["update_projects"] == 9
            assert report["summary"]["blocked_projects"] == 0
            assert report["summary"]["wave_count"] == 3
        finally:
            cleanup_dynamic()
            reset_policy()
