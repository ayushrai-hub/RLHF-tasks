"""Reference helpers for diffusion workbook verification."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

DB = Path("/app/workbook/data/workbook.sqlite")
FIXTURES = Path("/app/workbook/fixtures/sweeps")
KERNELS = Path("/app/workbook/kernels")
REPORT = Path("/app/workbook/reports/diffusion_report.md")
CHECKSUM = Path("/app/workbook/out/summary.checksum")
DEFAULT_FIT_LAG_MIN = 2
DEFAULT_FIT_LAG_MAX = 5


def parse_go_mod(content: str) -> dict:
    """Parse require and replace blocks from a go.mod file."""
    mod: dict = {"requires": [], "replace": []}
    section: str | None = None
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("module "):
            mod["path"] = line.removeprefix("module ").strip()
            continue
        if line == "require (":
            section = "require"
            continue
        if line == "replace (":
            section = "replace"
            continue
        if line == ")":
            section = None
            continue
        if line.startswith("require ") and not line.startswith("require ("):
            parts = line.removeprefix("require ").strip().split()
            mod["requires"].append({"path": parts[0], "version": parts[1] if len(parts) > 1 else ""})
            continue
        if "=>" in line and line.startswith("replace "):
            left, right = [part.strip().split() for part in line.removeprefix("replace ").split("=>", 1)]
            mod["replace"].append(
                {
                    "old_path": left[0],
                    "old_version": left[1] if len(left) > 1 else "",
                    "new_path": right[0],
                    "new_version": right[1] if len(right) > 1 else "",
                }
            )
            continue
        if section == "require":
            parts = line.split()
            mod["requires"].append({"path": parts[0], "version": parts[1] if len(parts) > 1 else ""})
            continue
        if section == "replace" and "=>" in line:
            left, right = [part.strip().split() for part in line.split("=>")]
            mod["replace"].append(
                {
                    "old_path": left[0],
                    "old_version": left[1] if len(left) > 1 else "",
                    "new_path": right[0],
                    "new_version": right[1] if len(right) > 1 else "",
                }
            )
    return mod


def module_dir(wrapper_module: str) -> Path:
    """Map a module import path to its directory under kernels/."""
    return KERNELS / wrapper_module.split("/")[-1]


def resolve_kernel_revision(wrapper_module: str) -> str:
    """Resolve effective kernel path@version after chained replace directives."""
    module_dir_path = module_dir(wrapper_module)
    mod = parse_go_mod((module_dir_path / "go.mod").read_text(encoding="utf-8"))
    kernel_req = next(row for row in mod["requires"] if row["path"] == "example.com/rd-kernel")
    target_path = kernel_req["path"]
    target_version = kernel_req["version"]
    while True:
        direct = next((row for row in mod["replace"] if row["old_path"] == target_path), None)
        if direct is None:
            break
        module_dir_path = (module_dir_path / direct["new_path"]).resolve()
        mod = parse_go_mod((module_dir_path / "go.mod").read_text(encoding="utf-8"))
        target_path = mod["path"]
        target_version = direct["new_version"]
    return f"{target_path}@{target_version}"


def load_fixture(path: Path) -> dict:
    """Load one nested sweep fixture."""
    return json.loads(path.read_text(encoding="utf-8"))


def expected_sweeps() -> list[dict]:
    """Return expected sweeps rows from fixtures."""
    rows: list[dict] = []
    for path in sorted(FIXTURES.glob("*.json")):
        payload = load_fixture(path)
        sweep_id = payload.get("meta", {}).get("run", {}).get("id")
        if not sweep_id:
            continue
        kernel = payload["meta"]["run"]["kernel"]
        params = payload["params"]
        rows.append(
            {
                "sweep_id": sweep_id,
                "kernel_revision": resolve_kernel_revision(kernel),
                "dt": float(params["dt"]),
                "dimension": int(params["dimension"]),
                "fit_lag_min": int(params.get("fit_lag_min", DEFAULT_FIT_LAG_MIN)),
                "fit_lag_max": int(params.get("fit_lag_max", DEFAULT_FIT_LAG_MAX)),
            }
        )
    return rows


def expected_msd_points(sweep_id: str) -> list[tuple[int, float]]:
    """Return lag and MSD pairs for a sweep fixture."""
    path = FIXTURES / f"{sweep_id}.json"
    payload = load_fixture(path)
    points = payload["series"]["msd"]
    return [(int(point["step"]), float(point["msd"])) for point in points]


def fit_diffusion(
    lags: list[int],
    msds: list[float],
    dimension: int,
    dt: float,
    fit_lag_min: int,
    fit_lag_max: int,
) -> tuple[float, float]:
    """Fit diffusion coefficient and RSS through the origin over a lag window."""
    fit_lags: list[int] = []
    fit_msds: list[float] = []
    for lag, msd in zip(lags, msds, strict=True):
        if fit_lag_min <= lag <= fit_lag_max:
            fit_lags.append(lag)
            fit_msds.append(msd)
    xs = [2 * dimension * lag * dt for lag in fit_lags]
    sum_xx = sum(x * x for x in xs)
    sum_xy = sum(x * y for x, y in zip(xs, fit_msds, strict=True))
    slope = sum_xy / sum_xx
    rss = 0.0
    for x, y in zip(xs, fit_msds, strict=True):
        residual = y - slope * x
        rss += residual * residual
    return round(slope, 6), round(rss, 6)


def expected_summary() -> list[dict]:
    """Return expected diffusion_summary rows."""
    rows: list[dict] = []
    for sweep in expected_sweeps():
        points = expected_msd_points(sweep["sweep_id"])
        lags = [lag for lag, _ in points]
        msds = [msd for _, msd in points]
        diffusion_coeff, rss = fit_diffusion(
            lags,
            msds,
            sweep["dimension"],
            sweep["dt"],
            sweep["fit_lag_min"],
            sweep["fit_lag_max"],
        )
        rows.append(
            {
                "sweep_id": sweep["sweep_id"],
                "kernel_revision": sweep["kernel_revision"],
                "diffusion_coeff": diffusion_coeff,
                "rss": rss,
            }
        )
    return sorted(rows, key=lambda row: row["sweep_id"])


def format_summary_row(row: dict) -> str:
    """Serialize one summary row for checksum canonicalization."""
    return (
        f'{{"sweep_id":"{row["sweep_id"]}","kernel_revision":"{row["kernel_revision"]}",'
        f'"diffusion_coeff":{row["diffusion_coeff"]:.6f},"rss":{row["rss"]:.6f}}}'
    )


def expected_checksum_body() -> str:
    """Return canonical checksum body bytes as UTF-8 text."""
    rows = expected_summary()
    return "\n".join(format_summary_row(row) for row in rows)


def expected_checksum() -> str:
    """Return sha256 hex digest for the canonical summary body."""
    return hashlib.sha256(expected_checksum_body().encode("utf-8")).hexdigest()


def report_checksum() -> str:
    """Parse checksum line from diffusion_report.md."""
    for line in REPORT.read_text(encoding="utf-8").splitlines():
        if line.startswith("checksum:"):
            return line.split(":", 1)[1].strip()
    raise ValueError("checksum line missing from report")


def connect() -> sqlite3.Connection:
    """Open workbook sqlite database."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn
