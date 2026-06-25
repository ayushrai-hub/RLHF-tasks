"""tests for milestone 3: RTM imaging, AVO regression, QC metrics, acquisition sweep."""
import csv
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np

SEISMIC = "/app/seismic"
TMP_BASE = Path("/tmp/m3")
_RUN_CACHE: dict[str, Path] = {}


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([SEISMIC, *args], capture_output=True, text=True, check=False)


def _invoke_dir(subcmd: str, fixture_name: str) -> Path:
    """Run a subcommand that writes a directory, into /tmp/m3/<fixture_name>."""
    key = f"{subcmd}:{fixture_name}"
    if key in _RUN_CACHE:
        return _RUN_CACHE[key]
    out = TMP_BASE / fixture_name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    proc = _run(subcmd, f"/app/fixtures/{fixture_name}.json", str(out))
    assert proc.returncode == 0, (
        f"seismic {subcmd} {fixture_name} failed (rc={proc.returncode})\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    _RUN_CACHE[key] = out
    return out


def _invoke_file(subcmd: str, fixture_name: str, out_filename: str) -> Path:
    """Run a subcommand that writes a single file, into /tmp/m3/<fixture_name>/<out_filename>."""
    key = f"{subcmd}:{fixture_name}:{out_filename}"
    if key in _RUN_CACHE:
        return _RUN_CACHE[key]
    out_dir = TMP_BASE / fixture_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_filename
    if out_path.exists():
        out_path.unlink()
    proc = _run(subcmd, f"/app/fixtures/{fixture_name}.json", str(out_path))
    assert proc.returncode == 0, (
        f"seismic {subcmd} {fixture_name} failed (rc={proc.returncode})\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    _RUN_CACHE[key] = out_path
    return out_path


class TestMilestone3:
    def test_image_subcommand_writes_image_npy(self) -> None:
        """seismic image runs against the rtm config and writes image.npy."""
        out = _invoke_dir("image", "rtm_two_layer")
        assert (out / "image.npy").exists(), "image.npy not written"

    def test_rtm_image_shape_and_dtype(self) -> None:
        """image.npy has shape (nz, nx) and dtype float32."""
        out = _invoke_dir("image", "rtm_two_layer")
        img = np.load(out / "image.npy")
        assert img.dtype == np.float32
        assert img.shape == (80, 180)
        assert np.all(np.isfinite(img))

    def test_rtm_image_bright_band_at_reflector(self) -> None:
        """the imaging condition is brighter at the reflector horizon than in the deep background."""
        out = _invoke_dir("image", "rtm_two_layer")
        img = np.load(out / "image.npy")
        band_at_reflector = np.mean(np.abs(img[37:44, 30:150]))
        band_below_reflector = np.mean(np.abs(img[55:65, 30:150]))
        assert band_at_reflector > 1.5 * band_below_reflector, (
            f"reflector band {band_at_reflector:.4e} vs below {band_below_reflector:.4e}"
        )

    def test_rtm_image_follows_illumination_footprint(self) -> None:
        """the reflector image is a genuine cross-correlation footprint: peaked under
        the illuminated aperture, tapering to the edges, and near-zero outside it."""
        out = _invoke_dir("image", "rtm_two_layer")
        img = np.load(out / "image.npy")
        # Source at x=900 (col 90), receivers x=300..1500 (cols 30..150), dz=10.
        # The reflector horizon sits at z=400 -> rows ~37..44.
        band = np.abs(img[37:44, :]).mean(axis=0)
        central = float(band[80:101].mean())          # under the source/CMP
        edge_left = float(band[30:46].mean())          # near the left aperture edge
        edge_right = float(band[135:151].mean())       # near the right aperture edge
        outside = float(band[5:21].mean())             # outside the receiver aperture
        # A zero-lag correlation image is far brighter under the illuminated centre
        # than at the aperture edges (oracle ratio ~300x); a flat or uniform band
        # fails this badly.
        assert central > 4.0 * edge_left, f"central {central:.3e} vs left edge {edge_left:.3e}"
        assert central > 4.0 * edge_right, f"central {central:.3e} vs right edge {edge_right:.3e}"
        # Essentially no energy is imaged where no source-receiver pair illuminates.
        assert central > 20.0 * outside, f"central {central:.3e} vs outside-aperture {outside:.3e}"
        # And no spurious bright band above the source horizon (rows above z=200).
        above_source = float(np.mean(np.abs(img[0:16, 30:150])))
        assert band[80:101].mean() > 3.0 * above_source, (
            f"reflector central {central:.3e} vs above-source {above_source:.3e}"
        )
        # The cross-correlation of two band-limited wavefields leaves the source
        # wavelet's polarity structure on the reflector: each illuminated column
        # carries a negative sidelobe under its positive peak. A flat or single-
        # signed painted band has none. The oracle shows this in every central
        # column; require it in at least half of them.
        cols_with_sidelobe = 0
        for c in range(80, 101):
            col = img[34:47, c]
            peak = float(col.max())
            if peak > 0 and bool((col < -0.03 * peak).any()):
                cols_with_sidelobe += 1
        assert cols_with_sidelobe >= 10, f"only {cols_with_sidelobe}/21 central columns carry a wavelet sidelobe"

    def test_avo_csv_header_and_fit_row(self) -> None:
        """avo CSV has the required header, one row per receiver, and a trailing fit row."""
        path = _invoke_file("avo", "avo_two_layer", "avo.csv")
        rows = list(csv.reader(path.read_text().splitlines()))
        assert rows[0] == ["offset_m", "angle_rad", "amplitude"]
        # 13 receivers in sim_two_layer + 1 fit row = 14 data rows.
        assert len(rows) == 1 + 13 + 1
        assert rows[-1][0] == "fit"
        for r in rows[1:1 + 13]:
            assert len(r) == 3
            float(r[0])
            float(r[1])
            float(r[2])
        assert len(rows[-1]) == 3
        float(rows[-1][1])
        float(rows[-1][2])

    def test_avo_intercept_positive_for_real_reflection(self) -> None:
        """a real reflection produces a positive zero-offset amplitude (since amplitudes are absolute peaks)."""
        path = _invoke_file("avo", "avo_two_layer", "avo.csv")
        rows = list(csv.reader(path.read_text().splitlines()))
        intercept = float(rows[-1][1])
        assert intercept > 0, f"intercept = {intercept}"
        for r in rows[1:1 + 13]:
            assert float(r[2]) >= 0.0

    def test_avo_offsets_match_receiver_geometry(self) -> None:
        """per-receiver offset_m equals |xr - source_x| for the configured receiver grid."""
        path = _invoke_file("avo", "avo_two_layer", "avo.csv")
        rows = list(csv.reader(path.read_text().splitlines()))
        # Source x=900, receivers x_start=300, x_end=1500, n=13 -> dx=100.
        expected_offsets = [abs(300.0 + 100.0 * i - 900.0) for i in range(13)]
        actual_offsets = [float(r[0]) for r in rows[1:1 + 13]]
        for got, want in zip(actual_offsets, expected_offsets):
            assert abs(got - want) < 1e-3, f"offset {got} vs {want}"

    def test_avo_angles_match_straight_ray_conversion(self) -> None:
        """per-receiver angle_rad equals atan((offset/2)/(reflector_depth - source_z))."""
        path = _invoke_file("avo", "avo_two_layer", "avo.csv")
        rows = list(csv.reader(path.read_text().splitlines()))
        # source_x=900, source_z=200, reflector_depth=400 -> effective depth 200.
        src_x, d_eff = 900.0, 400.0 - 200.0
        xs = [300.0 + 100.0 * i for i in range(13)]
        for r, xr in zip(rows[1:1 + 13], xs):
            offset = abs(xr - src_x)
            expected = np.arctan((offset * 0.5) / d_eff)
            assert abs(float(r[1]) - expected) < 1e-6, f"angle {r[1]} vs {expected} at xr={xr}"

    def test_avo_fit_row_is_least_squares_of_emitted_points(self) -> None:
        """the trailing fit row holds the intercept and gradient of amplitude = A + B*sin^2(theta)."""
        path = _invoke_file("avo", "avo_two_layer", "avo.csv")
        rows = list(csv.reader(path.read_text().splitlines()))
        sin2 = np.array([np.sin(float(r[1])) ** 2 for r in rows[1:1 + 13]])
        amp = np.array([float(r[2]) for r in rows[1:1 + 13]])
        # Independent ordinary-least-squares fit of the emitted (sin^2 theta, amplitude) pairs.
        slope, intercept = np.polyfit(sin2, amp, 1)
        fit_intercept = float(rows[-1][1])
        fit_gradient = float(rows[-1][2])
        scale = float(np.abs(amp).max())
        assert abs(fit_intercept - intercept) < 1e-5 * scale, f"intercept {fit_intercept} vs {intercept}"
        assert abs(fit_gradient - slope) < 1e-5 * scale, f"gradient {fit_gradient} vs {slope}"
        # A genuine fit of these decaying-with-angle amplitudes has a non-trivial gradient.
        assert abs(fit_gradient) > 1e-3 * scale, f"gradient {fit_gradient} is degenerate"

    def test_qc_subcommand_writes_json(self) -> None:
        """seismic qc runs against the qc config and writes a JSON report."""
        path = _invoke_file("qc", "qc_two_layer", "qc.json")
        assert path.exists()
        json.loads(path.read_text())

    def test_qc_json_fields_present_and_basic_values(self) -> None:
        """qc.json carries snr_db, wavelength, vertical_resolution, and an illumination list."""
        path = _invoke_file("qc", "qc_two_layer", "qc.json")
        data = json.loads(path.read_text())
        for key in ("snr_db", "dominant_wavelength_m", "vertical_resolution_m", "illumination"):
            assert key in data, f"missing {key}"
        # overburden_vp=1500, freq=20 -> wavelength=75, resolution=18.75
        assert abs(data["dominant_wavelength_m"] - 75.0) < 1e-3
        assert abs(data["vertical_resolution_m"] - 18.75) < 1e-3
        assert data["snr_db"] > 10.0, f"SNR = {data['snr_db']}"

    def test_qc_illumination_counts(self) -> None:
        """illumination entries respect the midpoint binning and 45-degree angle cap."""
        path = _invoke_file("qc", "qc_two_layer", "qc.json")
        data = json.loads(path.read_text())
        ill = {(round(e["x"], 3), round(e["z"], 3)): e["n_rays"] for e in data["illumination"]}
        assert ill[(900.0, 400.0)] == 3
        assert ill[(600.0, 400.0)] == 2
        assert ill[(1200.0, 400.0)] == 2
        assert ill[(900.0, 600.0)] == 3
        assert ill[(600.0, 600.0)] == 2
        assert ill[(1200.0, 600.0)] == 2

    def test_qc_snr_matches_gather(self) -> None:
        """snr_db is 20*log10(peak / noise-window RMS) recomputed from the gather itself."""
        path = _invoke_file("qc", "qc_two_layer", "qc.json")
        data = json.loads(path.read_text())
        cfg = json.loads(Path("/app/fixtures/qc_two_layer.json").read_text())
        g = np.load(cfg["shot_gather"])
        t = np.load(cfg["time_axis"])
        n_lo, n_hi = cfg["noise_window_s"]
        mask = (t >= n_lo) & (t <= n_hi)
        assert mask.sum() > 0
        peak = float(np.abs(g).max())
        rms = float(np.sqrt(np.mean(g[mask, :] ** 2)))
        expected = 20.0 * np.log10(peak / rms)
        assert abs(data["snr_db"] - expected) < 0.05, f"snr_db {data['snr_db']} vs recomputed {expected}"

    def test_sweep_illumination_exact_counts(self) -> None:
        """the illumination map equals the midpoint-bin / angle-cap count recomputed from geometry."""
        out = _invoke_dir("sweep", "sweep_two_layer")
        ill = np.load(out / "illumination_map.npy")
        # sweep_two_layer geometry: receivers x=300..1500 n=13 (spacing 100, bin_half=50),
        # survey [400, 1400], target depth 400, targets x=600/900/1200, spacings 100/200/400.
        rxs = [300.0 + 100.0 * i for i in range(13)]
        bin_half, depth = 50.0, 400.0
        targets, spacings = [600.0, 900.0, 1200.0], [100.0, 200.0, 400.0]

        def sources(sp: float) -> list[float]:
            lo, hi, mid = 400.0, 1400.0, 900.0
            placed, k = [mid], 1
            while True:
                left, right, added = mid - k * sp, mid + k * sp, False
                if left >= lo:
                    placed.append(left)
                    added = True
                if right <= hi:
                    placed.append(right)
                    added = True
                if not added:
                    break
                k += 1
            return placed

        def count(srcs: list[float], tx: float) -> int:
            tot = 0
            for sx in srcs:
                for xr in rxs:
                    if abs(0.5 * (sx + xr) - tx) > bin_half:
                        continue
                    if np.arctan2(0.5 * abs(xr - sx), depth) <= np.pi / 4:
                        tot += 1
            return tot

        expected = np.array([[count(sources(sp), tx) for tx in targets] for sp in spacings])
        assert np.array_equal(ill.astype(int), expected), f"map {ill.tolist()} vs expected {expected.tolist()}"

    def test_sweep_outputs_shape_and_csv(self) -> None:
        """sweep emits parameters.csv with per-spacing counts and an (n_spacings, n_targets) illumination map."""
        out = _invoke_dir("sweep", "sweep_two_layer")
        ill = np.load(out / "illumination_map.npy")
        assert ill.dtype == np.float32
        assert ill.shape == (3, 3)
        rows = list(csv.reader((out / "parameters.csv").read_text().splitlines()))
        assert rows[0] == ["spacing_m", "n_sources"]
        assert len(rows) == 1 + 3
        # Survey [400, 1400], spacings 100/200/400 -> 11/5/3 sources placed.
        assert int(rows[1][1]) == 11
        assert int(rows[2][1]) == 5
        assert int(rows[3][1]) == 3

    def test_sweep_illumination_monotone_in_spacing(self) -> None:
        """tighter source spacing yields larger illumination counts at the central target."""
        out = _invoke_dir("sweep", "sweep_two_layer")
        ill = np.load(out / "illumination_map.npy")
        assert ill[0, 1] > ill[1, 1] > ill[2, 1]
        totals = ill.sum(axis=1)
        assert totals[0] > totals[1] > totals[2]
