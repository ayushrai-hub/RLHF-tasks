import json
import shutil
import subprocess
from pathlib import Path


APP = Path("/app")


def build_tool(tmp_path: Path) -> Path:
    build_dir = tmp_path / "build"
    subprocess.run(["cmake", "-S", str(APP), "-B", str(build_dir)], check=True)
    subprocess.run(["cmake", "--build", str(build_dir)], check=True)
    return build_dir / "pc-sanitize"


class TestMilestone3:
    def test_audit_reports_static_leaks_missing_edges_and_summary(self, tmp_path):
        """audit reports leaked public static flags, missing dependency edges, and deterministic summary fields."""
        tool = build_tool(tmp_path)
        out = tmp_path / "audit.json"
        subprocess.run([
            str(tool),
            "audit",
            "--pc-dir",
            str(APP / "input/pkgconfig"),
            "--manifest",
            str(APP / "input/manifests/release.json"),
            "--out",
            str(out),
        ], check=True)

        data = json.loads(out.read_text())
        assert list(data) == ["findings", "summary"]
        assert data["findings"] == [
            {"kind": "missing_dependency_edge", "package": "analytics", "detail": "-ljson should be declared as dependency json"},
            {"kind": "leaked_static_flag", "package": "appcore", "detail": "-lsecret_static"},
        ]
        assert data["summary"] == {
            "total": 2,
            "by_kind": {"leaked_static_flag": 1, "missing_dependency_edge": 1},
            "affected_packages": ["analytics", "appcore"],
        }

    def test_audit_classifies_runtime_archive_and_allowed_flags(self, tmp_path):
        """audit detects runtime-created archive leaks while respecting allowed static flags."""
        pc_dir = tmp_path / "pc"
        shutil.copytree(APP / "input/pkgconfig", pc_dir)
        (pc_dir / "plugin.pc").write_text(
            "prefix=/tmp/plugin\n"
            "libdir=${prefix}/lib\n"
            "Name: plugin\n"
            "Description: Plugin\n"
            "Version: 1\n"
            "Requires: json\n"
            "Libs: -L${libdir} -lplugin ${libdir}/libplugin-extra.a -pthread\n"
            "Libs.private:\n"
            "Cflags:\n"
        )
        manifest = tmp_path / "manifest.json"
        manifest.write_text('{"roots":["plugin"],"allowed_static_flags":["-pthread"],"static_only_flags":[]}')
        tool = build_tool(tmp_path)
        out = tmp_path / "audit.json"

        subprocess.run([str(tool), "audit", "--pc-dir", str(pc_dir), "--manifest", str(manifest), "--out", str(out)], check=True)
        findings = json.loads(out.read_text())["findings"]
        assert {"kind": "leaked_static_flag", "package": "plugin", "detail": "/tmp/plugin/lib/libplugin-extra.a"} in findings
        assert all(item["detail"] != "-pthread" for item in findings)
        assert all(not (item["package"] == "plugin" and item["kind"] == "missing_dependency_edge") for item in findings)
