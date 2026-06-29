"""Behavioral verifier for fits-wcs-sky-atlas-generator.

Independent Python WCS reference drives subprocess CLI checks.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

BIN = Path("/app/bin/wcs-atlas")
ATLAS = Path("/app/output/wcs-atlas.json")
SNAPSHOT = Path("/app/var/wcs-keyword-snapshot.json")
STAMP = Path("/app/var/wcs-ingest-stamp.txt")
TAN = Path("/app/fixtures/fits/tan_basic.fits")
SIN = Path("/app/fixtures/fits/sin_basic.fits")
PC = Path("/app/fixtures/fits/pc_skew.fits")
HEADER_ONLY = Path("/app/fixtures/fits/header_only.fits")
HIDDEN_CONTINUE = Path("/opt/verifier-fixtures/fits/continue_crval.fits")
HIDDEN_HIERARCH = Path("/opt/verifier-fixtures/fits/hierarch_obs.fits")
HIDDEN_PC_SIN = Path("/opt/verifier-fixtures/fits/pc_sin_hidden.fits")


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [str(BIN), *args],
        capture_output=True,
        text=True,
        env=merged,
        check=False,
    )


def reset_outputs() -> None:
    ATLAS.unlink(missing_ok=True)
    SNAPSHOT.unlink(missing_ok=True)
    STAMP.unlink(missing_ok=True)


def read_fits_cards(path: Path) -> list[dict[str, str]]:
    data = path.read_bytes()
    cards: list[dict[str, str]] = []
    block = 2880
    card_len = 80
    for off in range(0, len(data), block):
        chunk = data[off : off + block]
        if len(chunk) < block:
            break
        for i in range(block // card_len):
            line = chunk[i * card_len : (i + 1) * card_len].decode("ascii", errors="replace")
            if line.startswith("HIERARCH"):
                eq = line.find("=")
                if eq > 8:
                    kw = line[8:eq].strip()
                    rest = line[eq + 1 :].split("/")[0].strip() if eq + 1 < len(line) else ""
                    comment = line.split("/", 1)[1].strip() if "/" in line[eq + 1 :] else ""
                    cards.append({"keyword": kw, "value": rest, "comment": comment})
                    continue
            kw = line[:8].strip()
            if not kw:
                continue
            rest = line[10:].split("/")[0].strip() if len(line) > 10 else ""
            if kw == "CONTINUE":
                if cards:
                    cards[-1]["value"] += rest.strip()
                continue
            if kw == "END":
                return cards
            comment = ""
            if "/" in line[10:]:
                comment = line.split("/", 1)[1].strip()
            cards.append({"keyword": kw, "value": rest, "comment": comment})
    return cards


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    return v


def keywords_from_cards(cards: list[dict[str, str]]) -> dict[str, Any]:
    kw: dict[str, Any] = {
        "naxis": 0,
        "naxis1": 1,
        "naxis2": 1,
        "ctype1": "",
        "ctype2": "",
        "crpix1": 1.0,
        "crpix2": 1.0,
        "crval1": 0.0,
        "crval2": 0.0,
        "cdelt1": 1.0,
        "cdelt2": 1.0,
        "has_cd": False,
        "cd11": 1.0,
        "cd12": 0.0,
        "cd21": 0.0,
        "cd22": 1.0,
        "has_pc": False,
        "pc11": 1.0,
        "pc12": 0.0,
        "pc21": 0.0,
        "pc22": 1.0,
    }
    for c in cards:
        k = c["keyword"]
        v = _strip_quotes(c["value"])
        if k == "NAXIS":
            kw["naxis"] = int(float(v))
        elif k == "NAXIS1":
            kw["naxis1"] = int(float(v))
        elif k == "NAXIS2":
            kw["naxis2"] = int(float(v))
        elif k == "CTYPE1":
            kw["ctype1"] = v
        elif k == "CTYPE2":
            kw["ctype2"] = v
        elif k == "CRPIX1":
            kw["crpix1"] = float(v)
        elif k == "CRPIX2":
            kw["crpix2"] = float(v)
        elif k == "CRVAL1":
            kw["crval1"] = float(v)
        elif k == "CRVAL2":
            kw["crval2"] = float(v)
        elif k == "CDELT1":
            kw["cdelt1"] = float(v)
        elif k == "CDELT2":
            kw["cdelt2"] = float(v)
        elif k == "CD1_1":
            kw["has_cd"] = True
            kw["cd11"] = float(v)
        elif k == "CD1_2":
            kw["has_cd"] = True
            kw["cd12"] = float(v)
        elif k == "CD2_1":
            kw["has_cd"] = True
            kw["cd21"] = float(v)
        elif k == "CD2_2":
            kw["has_cd"] = True
            kw["cd22"] = float(v)
        elif k == "PC1_1":
            kw["has_pc"] = True
            kw["pc11"] = float(v)
        elif k == "PC1_2":
            kw["has_pc"] = True
            kw["pc12"] = float(v)
        elif k == "PC2_1":
            kw["has_pc"] = True
            kw["pc21"] = float(v)
        elif k == "PC2_2":
            kw["has_pc"] = True
            kw["pc22"] = float(v)
    if kw["naxis"] == 0:
        kw["naxis1"] = 1
        kw["naxis2"] = 1
    return kw


def projection_from_ctype(ctype1: str) -> str:
    return "SIN" if "SIN" in ctype1[5:] else "TAN"


def linear_transform(x: float, y: float, kw: dict[str, Any]) -> tuple[float, float]:
    dx = x - kw["crpix1"]
    dy = y - kw["crpix2"]
    if kw["has_cd"]:
        xi = kw["cd11"] * dx + kw["cd12"] * dy
        eta = kw["cd21"] * dx + kw["cd22"] * dy
        return xi, eta
    m11 = kw["pc11"] * kw["cdelt1"] if kw["has_pc"] else kw["cdelt1"]
    m12 = kw["pc12"] * kw["cdelt2"] if kw["has_pc"] else 0.0
    m21 = kw["pc21"] * kw["cdelt1"] if kw["has_pc"] else 0.0
    m22 = kw["pc22"] * kw["cdelt2"] if kw["has_pc"] else kw["cdelt2"]
    xi = m11 * dx + m12 * dy
    eta = m21 * dx + m22 * dy
    return xi, eta


def project_tan(xi_deg: float, eta_deg: float, kw: dict[str, Any]) -> tuple[float, float]:
    ra0 = math.radians(kw["crval1"])
    dec0 = math.radians(kw["crval2"])
    xi_r = math.radians(xi_deg)
    eta_r = math.radians(eta_deg)
    denom = math.cos(dec0) - eta_r * math.sin(dec0)
    ra = ra0 + math.atan2(xi_r, denom)
    dec = math.atan2(math.sin(dec0) + eta_r * math.cos(dec0), math.sqrt(xi_r * xi_r + denom * denom))
    ra_deg = math.degrees(ra) % 360.0
    return ra_deg, math.degrees(dec)


def project_sin(xi_deg: float, eta_deg: float, kw: dict[str, Any]) -> tuple[float, float]:
    ra0 = math.radians(kw["crval1"])
    dec0 = math.radians(kw["crval2"])
    xi_r = math.radians(xi_deg)
    eta_r = math.radians(eta_deg)
    rho = math.hypot(xi_r, eta_r)
    if rho < 1e-15:
        return kw["crval1"] % 360.0, kw["crval2"]
    cos_r = math.cos(rho)
    sin_r = math.sin(rho)
    dec = math.asin(math.sin(dec0) * cos_r + (eta_r / rho) * math.cos(dec0) * sin_r)
    ra = ra0 + math.atan2(
        xi_r * sin_r, rho * math.cos(dec0) * cos_r - eta_r * math.sin(dec0) * sin_r
    )
    return math.degrees(ra) % 360.0, math.degrees(dec)


def pixel_to_sky(x: float, y: float, kw: dict[str, Any]) -> tuple[float, float]:
    xi, eta = linear_transform(x, y, kw)
    if projection_from_ctype(kw["ctype1"]) == "SIN":
        return project_sin(xi, eta, kw)
    return project_tan(xi, eta, kw)


def reference_corners(path: Path) -> list[dict[str, float]]:
    cards = read_fits_cards(path)
    kw = keywords_from_cards(cards)
    n1, n2 = kw["naxis1"], kw["naxis2"]
    pixels = [(1.0, 1.0), (float(n1), 1.0), (1.0, float(n2)), (float(n1), float(n2))]
    out: list[dict[str, float]] = []
    for px, py in pixels:
        ra, dec = pixel_to_sky(px, py, kw)
        out.append({"pixel_x": px, "pixel_y": py, "ra_deg": ra, "dec_deg": dec})
    out.sort(key=lambda c: (c["ra_deg"], c["dec_deg"]))
    return out


def close(a: float, b: float, tol: float = 1e-5) -> bool:
    return abs(a - b) <= tol


class TestWcsAtlas:
    def test_build_tan_basic_success(self) -> None:
        """Build on bundled TAN FITS exits zero."""
        reset_outputs()
        proc = run_cli("build", str(TAN))
        assert proc.returncode == 0, proc.stderr + proc.stdout

    def test_atlas_schema_fields(self) -> None:
        """Atlas JSON includes required schema fields."""
        reset_outputs()
        run_cli("build", str(TAN))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        for key in (
            "version",
            "fits_path",
            "naxis1",
            "naxis2",
            "projection",
            "corners",
            "axis_midpoints",
            "fingerprint",
        ):
            assert key in data

    def test_tan_corners_match_reference(self) -> None:
        """TAN corner RA Dec match independent Python WCS reference."""
        reset_outputs()
        run_cli("build", str(TAN))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        expect = reference_corners(TAN)
        assert len(data["corners"]) == 4
        for got, exp in zip(data["corners"], expect, strict=True):
            assert close(got["ra_deg"], exp["ra_deg"], 1e-4)
            assert close(got["dec_deg"], exp["dec_deg"], 1e-4)

    def test_corners_sorted_by_ra_dec(self) -> None:
        """Corner list is sorted by ra_deg then dec_deg ascending."""
        reset_outputs()
        run_cli("build", str(TAN))
        corners = json.loads(ATLAS.read_text(encoding="utf-8"))["corners"]
        keys = [(c["ra_deg"], c["dec_deg"]) for c in corners]
        assert keys == sorted(keys)

    def test_sin_projection_family(self) -> None:
        """SIN FITS reports projection SIN and matches reference corners."""
        reset_outputs()
        run_cli("build", str(SIN))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        assert data["projection"] == "SIN"
        expect = reference_corners(SIN)
        for got, exp in zip(data["corners"], expect, strict=True):
            assert close(got["ra_deg"], exp["ra_deg"], 1e-4)
            assert close(got["dec_deg"], exp["dec_deg"], 1e-4)

    def test_pc_skew_matrix_corners(self) -> None:
        """PC skew FITS corner coordinates match reference linear composition."""
        reset_outputs()
        run_cli("build", str(PC))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        expect = reference_corners(PC)
        for got, exp in zip(data["corners"], expect, strict=True):
            assert close(got["ra_deg"], exp["ra_deg"], 1e-4)

    def test_keyword_snapshot_written(self) -> None:
        """Build writes keyword snapshot JSON before atlas export."""
        reset_outputs()
        run_cli("build", str(TAN))
        assert SNAPSHOT.is_file()
        snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        assert snap["version"] == 1
        assert len(snap["cards"]) >= 5
        assert "canonical" in snap

    def test_snapshot_canonical_contains_crval(self) -> None:
        """Keyword snapshot canonical string includes CRVAL keywords."""
        reset_outputs()
        run_cli("build", str(TAN))
        snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        assert "CRVAL1=" in snap["canonical"]

    def test_build_idempotent_bytes(self) -> None:
        """Repeated build yields byte-identical atlas and snapshot."""
        reset_outputs()
        run_cli("build", str(TAN))
        a1 = ATLAS.read_bytes()
        s1 = SNAPSHOT.read_bytes()
        run_cli("build", str(TAN))
        assert ATLAS.read_bytes() == a1
        assert SNAPSHOT.read_bytes() == s1

    def test_header_only_naxis_zero(self) -> None:
        """Header-only FITS with NAXIS 0 still produces four corners."""
        reset_outputs()
        run_cli("build", str(HEADER_ONLY))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        assert data["naxis1"] == 1
        assert len(data["corners"]) == 4

    def test_pixel_scale_positive(self) -> None:
        """Atlas reports positive pixel_scale_arcsec for TAN basic."""
        reset_outputs()
        run_cli("build", str(TAN))
        scale = json.loads(ATLAS.read_text(encoding="utf-8"))["pixel_scale_arcsec"]
        assert scale > 0

    def test_axis_midpoints_count(self) -> None:
        """Atlas includes four axis midpoint entries."""
        reset_outputs()
        run_cli("build", str(TAN))
        mids = json.loads(ATLAS.read_text(encoding="utf-8"))["axis_midpoints"]
        assert len(mids) == 4

    def test_center_pixel_near_crval(self) -> None:
        """Sky coordinate at CRPIX is near CRVAL for TAN basic."""
        reset_outputs()
        run_cli("build", str(TAN))
        cards = read_fits_cards(TAN)
        kw = keywords_from_cards(cards)
        ra, dec = pixel_to_sky(kw["crpix1"], kw["crpix2"], kw)
        assert close(ra, kw["crval1"], 0.01)
        assert close(dec, kw["crval2"], 0.01)

    def test_hidden_continue_crval_tb3(self) -> None:
        """TB3_FITS_PATH hidden CONTINUE fixture drives build ingest."""
        reset_outputs()
        hidden = str(HIDDEN_CONTINUE)
        env = {"TB3_FITS_PATH": hidden}
        proc = run_cli("build", str(TAN), env=env)
        assert proc.returncode == 0, proc.stderr
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        assert hidden in data["fits_path"] or data["fits_path"] == hidden
        expect = reference_corners(HIDDEN_CONTINUE)
        for got, exp in zip(data["corners"], expect, strict=True):
            assert close(got["ra_deg"], exp["ra_deg"], 1e-4)

    def test_hidden_continue_crval_value(self) -> None:
        """Hidden CONTINUE fixture CRVAL1 parses as 45.125."""
        reset_outputs()
        run_cli("build", str(HIDDEN_CONTINUE))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        assert close(data["crval1"], 45.125, 1e-6)

    def test_hidden_pc_sin_projection(self) -> None:
        """Hidden PC SIN fixture corners match reference."""
        reset_outputs()
        run_cli("build", str(HIDDEN_PC_SIN))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        assert data["projection"] == "SIN"
        expect = reference_corners(HIDDEN_PC_SIN)
        for got, exp in zip(data["corners"], expect, strict=True):
            assert close(got["ra_deg"], exp["ra_deg"], 1e-4)
            assert close(got["dec_deg"], exp["dec_deg"], 1e-4)

    def test_hidden_hierarch_snapshot_keyword(self) -> None:
        """Hidden HIERARCH fixture keyword appears in snapshot cards and canonical."""
        reset_outputs()
        run_cli("build", str(HIDDEN_HIERARCH))
        snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        keys = {c["keyword"] for c in snap["cards"]}
        assert "ESO DPR CATG" in keys
        assert "ESO DPR CATG=CALIB" in snap["canonical"]

    def test_ingest_stamp_written(self) -> None:
        """Build writes resolved FITS path to ingest stamp file."""
        reset_outputs()
        run_cli("build", str(TAN))
        assert STAMP.is_file()
        assert STAMP.read_text(encoding="utf-8").strip() == str(TAN)

    def test_tb3_overrides_positional_path(self) -> None:
        """TB3_FITS_PATH overrides positional FITS argument."""
        reset_outputs()
        env = {"TB3_FITS_PATH": str(SIN)}
        proc = run_cli("build", str(TAN), env=env)
        assert proc.returncode == 0, proc.stderr
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        assert data["projection"] == "SIN"

    def test_atlas_writes_output_path(self) -> None:
        """Build creates /app/output/wcs-atlas.json."""
        reset_outputs()
        run_cli("build", str(TAN))
        assert ATLAS.is_file()

    def test_crpix_preserved_in_atlas(self) -> None:
        """Atlas echoes CRPIX values from header."""
        reset_outputs()
        run_cli("build", str(TAN))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        assert close(data["crpix1"], 100.5, 1e-6)
        assert close(data["crpix2"], 50.5, 1e-6)

    def test_ctype_echo(self) -> None:
        """Atlas echoes CTYPE strings from FITS header."""
        reset_outputs()
        run_cli("build", str(TAN))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        assert "TAN" in data["ctype1"]

    def test_sin_differs_from_tan_same_pixels(self) -> None:
        """SIN and TAN projections yield different corner RA for sin_basic."""
        cards = read_fits_cards(SIN)
        kw = keywords_from_cards(cards)
        ra_tan, _ = project_tan(*linear_transform(1.0, 1.0, kw), kw)
        ra_sin, _ = project_sin(*linear_transform(1.0, 1.0, kw), kw)
        assert abs(ra_tan - ra_sin) > 1e-3

    def test_snapshot_cards_include_naxis(self) -> None:
        """Keyword snapshot lists NAXIS card from header."""
        reset_outputs()
        run_cli("build", str(TAN))
        snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        keys = {c["keyword"] for c in snap["cards"]}
        assert "NAXIS" in keys

    def test_build_missing_file_fails(self) -> None:
        """Build on missing FITS path returns non-zero exit."""
        reset_outputs()
        proc = run_cli("build", "/app/output/no-such-file.fits")
        assert proc.returncode != 0

    def test_corner_pixel_coordinates_exact(self) -> None:
        """Corner pixel_x and pixel_y match FITS dimension corners."""
        reset_outputs()
        run_cli("build", str(TAN))
        corners = json.loads(ATLAS.read_text(encoding="utf-8"))["corners"]
        pixels = {(c["pixel_x"], c["pixel_y"]) for c in corners}
        assert pixels == {(1.0, 1.0), (200.0, 1.0), (1.0, 100.0), (200.0, 100.0)}

    def test_fingerprint_stable_and_non_empty(self) -> None:
        """Fingerprint is non-empty hex and stable across repeated builds."""
        reset_outputs()
        run_cli("build", str(TAN))
        data = json.loads(ATLAS.read_text(encoding="utf-8"))
        fp1 = data["fingerprint"]
        assert isinstance(fp1, str) and len(fp1) == 16 and all(c in "0123456789abcdef" for c in fp1)
        run_cli("build", str(SIN))
        fp2 = json.loads(ATLAS.read_text(encoding="utf-8"))["fingerprint"]
        assert fp1 != fp2
        run_cli("build", str(TAN))
        fp3 = json.loads(ATLAS.read_text(encoding="utf-8"))["fingerprint"]
        assert fp3 == fp1

    def test_subprocess_cli_deterministic(self) -> None:
        """Two subprocess CLI builds yield identical corner coordinates."""
        reset_outputs()
        proc1 = run_cli("build", str(PC))
        assert proc1.returncode == 0, proc1.stderr
        corners1 = json.loads(ATLAS.read_text(encoding="utf-8"))["corners"]
        reset_outputs()
        proc2 = run_cli("build", str(PC))
        assert proc2.returncode == 0, proc2.stderr
        corners2 = json.loads(ATLAS.read_text(encoding="utf-8"))["corners"]
        for a, b in zip(corners1, corners2, strict=True):
            assert close(a["ra_deg"], b["ra_deg"], 1e-9)
            assert close(a["dec_deg"], b["dec_deg"], 1e-9)
        expect = reference_corners(PC)
        assert close(corners1[0]["ra_deg"], expect[0]["ra_deg"], 1e-4)
