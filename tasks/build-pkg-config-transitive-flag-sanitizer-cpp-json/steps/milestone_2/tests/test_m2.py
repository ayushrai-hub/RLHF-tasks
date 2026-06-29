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


class TestMilestone2:
    def test_resolve_separates_public_and_static_closures(self, tmp_path):
        """resolve keeps public link flags smaller than the static closure and records edge kinds."""
        tool = build_tool(tmp_path)
        out = tmp_path / "resolve.json"
        subprocess.run([
            str(tool),
            "resolve",
            "--pc-dir",
            str(APP / "input/pkgconfig"),
            "--manifest",
            str(APP / "input/manifests/release.json"),
            "--out",
            str(out),
        ], check=True)

        roots = {root["name"]: root for root in json.loads(out.read_text())["roots"]}
        appcore = roots["appcore"]
        assert appcore["public_libs"] == [
            "-L/opt/app/lib",
            "-lappcore",
            "-lsecret_static",
            "-L/usr/lib/x86_64-linux-gnu",
            "-lnet",
            "-L/usr/local/lib",
            "-ltls",
            "-L/usr/lib",
            "-lz",
        ]
        assert appcore["static_libs"] == [
            "-L/opt/app/lib",
            "-lappcore",
            "-lsecret_static",
            "-L/usr/lib/x86_64-linux-gnu",
            "-lnet",
            "-L/usr/local/lib",
            "-ltls",
            "-L/usr/lib",
            "-lz",
            "-Wl,--whole-archive",
            "-lcrypto",
            "-Wl,--no-whole-archive",
            "-L/opt/crypto/lib",
            "-pthread",
            "-ldl",
        ]
        assert appcore["dependency_edges"] == [
            {"from": "appcore", "to": "net", "kind": "public"},
            {"from": "net", "to": "tls", "kind": "public"},
            {"from": "appcore", "to": "zlib", "kind": "public"},
            {"from": "appcore", "to": "crypto", "kind": "private"},
            {"from": "tls", "to": "crypto", "kind": "private"},
        ]

    def test_resolve_uses_runtime_manifest_roots(self, tmp_path):
        """resolve honors root packages from a fresh manifest instead of hardcoding fixtures."""
        pc_dir = tmp_path / "pc"
        shutil.copytree(APP / "input/pkgconfig", pc_dir)
        manifest = tmp_path / "manifest.json"
        manifest.write_text('{"roots":["render"],"allowed_static_flags":[],"static_only_flags":[]}')
        tool = build_tool(tmp_path)
        out = tmp_path / "resolve.json"

        subprocess.run([str(tool), "resolve", "--pc-dir", str(pc_dir), "--manifest", str(manifest), "--out", str(out)], check=True)
        [render] = json.loads(out.read_text())["roots"]
        assert render["name"] == "render"
        assert render["public_libs"] == ["-L/opt/render/lib", "-lrender", "-L/usr/lib", "-lz"]
        assert render["static_libs"] == ["-L/opt/render/lib", "-lrender", "-L/usr/lib", "-lz", "/opt/render/lib/librender-fallback.a"]
        assert render["dependency_edges"] == [{"from": "render", "to": "zlib", "kind": "public"}]
