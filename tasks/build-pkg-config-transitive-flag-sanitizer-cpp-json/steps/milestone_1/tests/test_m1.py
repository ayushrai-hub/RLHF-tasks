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


class TestMilestone1:
    def test_parse_expands_variables_and_requirement_constraints(self, tmp_path):
        """parse writes sorted package metadata with expanded variables and cleaned requirement names."""
        tool = build_tool(tmp_path)
        out = tmp_path / "parse.json"
        subprocess.run([
            str(tool),
            "parse",
            "--pc-dir",
            str(APP / "input/pkgconfig"),
            "--manifest",
            str(APP / "input/manifests/release.json"),
            "--out",
            str(out),
        ], check=True)

        data = json.loads(out.read_text())
        assert list(data) == ["packages", "errors"]
        assert data["errors"] == []
        names = [pkg["name"] for pkg in data["packages"]]
        assert names == sorted(names)

        appcore = next(pkg for pkg in data["packages"] if pkg["name"] == "appcore")
        assert appcore["requires"] == ["net", "zlib"]
        assert appcore["requires_private"] == ["crypto"]
        assert appcore["libs"] == ["-L/opt/app/lib", "-lappcore", "-lsecret_static"]
        assert appcore["libs_private"] == ["-Wl,--whole-archive", "-lcrypto", "-Wl,--no-whole-archive"]
        assert appcore["cflags"] == ["-I/opt/app/include/appcore"]

    def test_parse_handles_runtime_created_pc_files(self, tmp_path):
        """parse handles fresh .pc files with nested variables and empty optional fields."""
        pc_dir = tmp_path / "pc"
        shutil.copytree(APP / "input/pkgconfig", pc_dir)
        (pc_dir / "widget.pc").write_text(
            "prefix=/tmp/widget\n"
            "exec_prefix=${prefix}\n"
            "libdir=${exec_prefix}/lib64\n"
            "Name: widget\n"
            "Description: Runtime widget\n"
            "Version: 7.0\n"
            "Requires: json >= 4.0, zlib\n"
            "Libs: -L${libdir} -lwidget\n"
            "Cflags:\n"
        )
        manifest = tmp_path / "manifest.json"
        manifest.write_text('{"roots":["widget"],"allowed_static_flags":[],"static_only_flags":[]}')
        tool = build_tool(tmp_path)
        out = tmp_path / "parse.json"

        subprocess.run([str(tool), "parse", "--pc-dir", str(pc_dir), "--manifest", str(manifest), "--out", str(out)], check=True)
        widget = next(pkg for pkg in json.loads(out.read_text())["packages"] if pkg["name"] == "widget")
        assert widget["requires"] == ["json", "zlib"]
        assert widget["requires_private"] == []
        assert widget["libs"] == ["-L/tmp/widget/lib64", "-lwidget"]
        assert widget["cflags"] == []
