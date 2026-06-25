"""tests for milestone 1: model parsing, source generation, NPY output."""
import shutil
import subprocess
from pathlib import Path

import numpy as np

SEISMIC = "/app/seismic"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([SEISMIC, *args], capture_output=True, text=True, check=False)


def _fresh_dir(name: str) -> Path:
    p = Path("/tmp/m1") / name
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)
    return p


def _build_model(fixture: str, out_name: str) -> Path:
    out = _fresh_dir(out_name)
    proc = _run("model", f"/app/fixtures/{fixture}", str(out))
    assert proc.returncode == 0, f"model failed: stdout={proc.stdout} stderr={proc.stderr}"
    return out


def _build_source(fixture: str, out_name: str) -> Path:
    out_dir = _fresh_dir(out_name)
    out_path = out_dir / "wavelet.npy"
    proc = _run("source", f"/app/fixtures/{fixture}", str(out_path))
    assert proc.returncode == 0, f"source failed: stdout={proc.stdout} stderr={proc.stderr}"
    return out_path


class TestMilestone1:
    def test_model_arrays_present_and_shape(self) -> None:
        """seismic model writes five float32 (nz, nx) arrays for vp, vs, rho, qp, qs."""
        out = _build_model("layered_simple.json", "layered_simple")
        expected = (100, 200)
        for name in ("vp", "vs", "rho", "qp", "qs"):
            p = out / f"{name}.npy"
            assert p.exists(), f"missing {p}"
            arr = np.load(p)
            assert arr.dtype == np.float32, f"{name} dtype = {arr.dtype}"
            assert arr.shape == expected, f"{name} shape = {arr.shape}"

    def test_layer_assignment_by_depth(self) -> None:
        """layers are assigned by cell-centre depth (water/middle/bottom)."""
        out = _build_model("layered_simple.json", "layered_simple")
        vp = np.load(out / "vp.npy")
        rho = np.load(out / "rho.npy")
        # iz=10 → z=50 (water layer: vp=1500, rho=1000)
        assert abs(vp[10, 100] - 1500.0) < 1e-3
        assert abs(rho[10, 100] - 1000.0) < 1e-3
        # iz=40 → z=200 (middle layer: vp=2500, rho=2100)
        assert abs(vp[40, 100] - 2500.0) < 1e-3
        assert abs(rho[40, 100] - 2100.0) < 1e-3
        # iz=80 → z=400 (bottom layer: vp=3500, rho=2400)
        assert abs(vp[80, 100] - 3500.0) < 1e-3
        assert abs(rho[80, 100] - 2400.0) < 1e-3

    def test_water_layer_has_zero_vs(self) -> None:
        """the water layer carries vs=0 through to the vs.npy grid."""
        out = _build_model("layered_simple.json", "layered_simple")
        vs = np.load(out / "vs.npy")
        assert vs[10, 100] == 0.0
        assert vs[10, 50] == 0.0
        assert vs[19, 80] == 0.0  # last row still inside water (iz=19 → z=95)

    def test_q_factors_propagated(self) -> None:
        """qp.npy and qs.npy reflect the per-layer Q values."""
        out = _build_model("layered_simple.json", "layered_simple")
        qp = np.load(out / "qp.npy")
        qs = np.load(out / "qs.npy")
        # water layer (iz=10 → z=50): qp = qs = 1e6
        assert qp[10, 100] > 1e5
        assert qs[10, 100] > 1e5
        # middle layer (iz=40 → z=200): qp=80, qs=50
        assert abs(qp[40, 100] - 80.0) < 1e-3
        assert abs(qs[40, 100] - 50.0) < 1e-3

    def test_salt_polygon_overrides_layer(self) -> None:
        """a cell whose centre lies inside a salt polygon takes the salt properties."""
        out = _build_model("layered_with_salt.json", "layered_with_salt")
        vp = np.load(out / "vp.npy")
        rho = np.load(out / "rho.npy")
        # (x=500, z=300) → ix=100, iz=60. Inside polygon → salt vp=4500, rho=2200.
        assert abs(vp[60, 100] - 4500.0) < 1e-3, f"got vp={vp[60, 100]}"
        assert abs(rho[60, 100] - 2200.0) < 1e-3

    def test_outside_salt_polygon_uses_layer(self) -> None:
        """cells outside every salt polygon still use the layered background."""
        out = _build_model("layered_with_salt.json", "layered_with_salt")
        vp = np.load(out / "vp.npy")
        # (x=100, z=300) → ix=20, iz=60. Outside polygon → layer 3 vp=3000.
        assert abs(vp[60, 20] - 3000.0) < 1e-3

    def test_fault_hanging_wall_vs_footwall(self) -> None:
        """the hanging wall (right of the directed fault line) is downthrown by throw."""
        out = _build_model("layered_with_fault.json", "layered_with_fault")
        vp = np.load(out / "vp.npy")
        # Fault is vertical at x=500 from z=50 to z=500, throw=60.
        # Footwall cell: (x=400, z=300) → ix=80, iz=60. Lookup at z=300 → layer 3 vp=3000.
        assert abs(vp[60, 80] - 3000.0) < 1e-3, f"footwall got vp={vp[60, 80]}"
        # Hanging-wall cell: (x=600, z=300) → ix=120, iz=60. Lookup at z=240 → layer 2 vp=2200.
        assert abs(vp[60, 120] - 2200.0) < 1e-3, f"hangingwall got vp={vp[60, 120]}"

    def test_fault_then_salt_precedence(self) -> None:
        """salt overrides faulted cells, while faulted cells outside salt keep the throw-shifted layer."""
        out = _build_model("layered_fault_salt.json", "layered_fault_salt")
        vp = np.load(out / "vp.npy")
        rho = np.load(out / "rho.npy")
        # Vertical fault at x=500 (hanging wall x>500), throw=120. Salt box x in [600,800], z in [250,400].
        # Salt cell: (x=700, z=300) -> ix=140, iz=60. Inside salt and on the hanging wall -> salt wins.
        assert abs(vp[60, 140] - 4500.0) < 1e-3, f"salt cell vp={vp[60, 140]}"
        assert abs(rho[60, 140] - 2200.0) < 1e-3, f"salt cell rho={rho[60, 140]}"
        # Hanging-wall cell outside salt: (x=560, z=300) -> ix=112, iz=60. Lookup at z=180 -> layer 2 vp=2200.
        assert abs(vp[60, 112] - 2200.0) < 1e-3, f"hanging-wall non-salt vp={vp[60, 112]}"
        # Footwall cell: (x=200, z=300) -> ix=40, iz=60. Lookup at z=300 -> layer 3 vp=3000.
        assert abs(vp[60, 40] - 3000.0) < 1e-3, f"footwall vp={vp[60, 40]}"

    def test_multiple_faults_stack_additively(self) -> None:
        """a cell on the hanging-wall side of two faults is shifted by the sum of both throws."""
        out = _build_model("layered_multi_fault.json", "layered_multi_fault")
        vp = np.load(out / "vp.npy")
        # Faults at x=400 and x=800, each throw=120 (hanging wall to the right). Row z=300 -> iz=60.
        # Outside both faults: (x=200) -> ix=40. Lookup at z=300 -> layer 3 vp=3000.
        assert abs(vp[60, 40] - 3000.0) < 1e-3, f"no-fault vp={vp[60, 40]}"
        # Right of one fault: (x=600) -> ix=120. Lookup at z=180 -> layer 2 vp=2200.
        assert abs(vp[60, 120] - 2200.0) < 1e-3, f"single-fault vp={vp[60, 120]}"
        # Right of both faults: (x=900) -> ix=180. Lookup at z=60 (300-240) -> layer 1 vp=1500.
        assert abs(vp[60, 180] - 1500.0) < 1e-3, f"double-fault vp={vp[60, 180]}"

    def test_source_ricker_peak_frequency(self) -> None:
        """ricker spectrum peaks at the documented dominant frequency."""
        path = _build_source("source_ricker.json", "ricker")
        w = np.load(path)
        sr = 2000.0
        n = w.size
        assert n == int(round(0.4 * sr))
        spec = np.abs(np.fft.rfft(w))
        freqs = np.fft.rfftfreq(n, d=1.0 / sr)
        peak_f = freqs[int(np.argmax(spec))]
        assert abs(peak_f - 25.0) <= 2.5, f"peak f={peak_f}, expected ~25"

    def test_source_explosive_zero_mean_and_peak(self) -> None:
        """explosive (gaussian derivative) integrates to ~0 and peaks near the dominant frequency."""
        path = _build_source("source_explosive.json", "explosive")
        w = np.load(path)
        # DC ≈ 0 for an odd function around its centre
        assert abs(w.sum()) < 0.5 * float(np.abs(w).max()) * w.size ** 0.0  # i.e. < 0.5
        assert abs(w.sum()) < 0.5
        # Spectral peak should match the configured dominant frequency (30 Hz) with alpha=2(pi f)^2.
        sr = 2000.0
        n = w.size
        spec = np.abs(np.fft.rfft(w))
        freqs = np.fft.rfftfreq(n, d=1.0 / sr)
        peak_f = freqs[int(np.argmax(spec))]
        assert abs(peak_f - 30.0) <= 4.0, f"peak f={peak_f}, expected ~30"

    def test_source_vibroseis_instantaneous_frequency(self) -> None:
        """vibroseis instantaneous frequency rises linearly from f_start to f_end."""
        from scipy.signal import hilbert
        path = _build_source("source_vibroseis.json", "vibroseis")
        w = np.load(path)
        sr = 1000.0
        T = 4.0
        n = w.size
        assert n == int(round(T * sr))
        analytic = hilbert(w)
        phase = np.unwrap(np.angle(analytic))
        inst_f = np.diff(phase) * sr / (2.0 * np.pi)
        # Sample IF inside the central, fully-tapered region (avoid the cosine ramps)
        i_quarter = n // 4
        i_three_quarter = 3 * n // 4
        f_q = inst_f[i_quarter]
        f_tq = inst_f[i_three_quarter]
        # Theoretical: f0=8, f1=60, k=(60-8)/4=13. IF at t=1s = 21; IF at t=3s = 47.
        assert abs(f_q - 21.0) < 3.0, f"IF at t=1s = {f_q}"
        assert abs(f_tq - 47.0) < 3.0, f"IF at t=3s = {f_tq}"

    def test_all_sources_normalized_to_unit_max(self) -> None:
        """every wavelet is normalised so the maximum absolute sample equals exactly 1."""
        for fixture, name in (
            ("source_ricker.json", "ricker_norm"),
            ("source_explosive.json", "explosive_norm"),
            ("source_vibroseis.json", "vibroseis_norm"),
        ):
            path = _build_source(fixture, name)
            w = np.load(path)
            assert abs(float(np.abs(w).max()) - 1.0) < 1e-5, f"{fixture}: max|w|={np.abs(w).max()}"

    def test_missing_args_exit_nonzero(self) -> None:
        """seismic exits non-zero when a required argument is missing."""
        no_sub = _run()
        assert no_sub.returncode != 0, "no subcommand should fail"
        partial_model = _run("model", "/app/fixtures/layered_simple.json")
        assert partial_model.returncode != 0, "model with no output dir should fail"
        partial_source = _run("source", "/app/fixtures/source_ricker.json")
        assert partial_source.returncode != 0, "source with no output path should fail"

    def test_nonexistent_input_exit_nonzero(self) -> None:
        """a missing input file produces a non-zero exit and no truncated output."""
        out_dir = _fresh_dir("nonexistent_model")
        proc = _run("model", "/app/fixtures/__does_not_exist__.json", str(out_dir))
        assert proc.returncode != 0, f"expected non-zero, got {proc.returncode}"
        # No output arrays should have been written if the input is unreadable.
        for name in ("vp", "vs", "rho", "qp", "qs"):
            assert not (out_dir / f"{name}.npy").exists(), f"{name}.npy written despite missing input"

    def test_malformed_json_exit_nonzero(self) -> None:
        """malformed source JSON produces a non-zero exit."""
        bad = Path("/tmp/m1/bad_source.json")
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("{this is not valid json,,,")
        out_dir = _fresh_dir("malformed_source_out")
        proc = _run("source", str(bad), str(out_dir / "w.npy"))
        assert proc.returncode != 0, f"expected non-zero, got {proc.returncode}"

    def test_unknown_source_type_exit_nonzero(self) -> None:
        """a wavelet type outside ricker/explosive/vibroseis produces a non-zero exit."""
        bad = Path("/tmp/m1/unknown_type.json")
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text(
            '{"type": "rectangular", "sample_rate_hz": 1000, "duration_s": 0.2, '
            '"dominant_frequency_hz": 25, "delay_s": 0.05}'
        )
        out_dir = _fresh_dir("unknown_type_out")
        proc = _run("source", str(bad), str(out_dir / "w.npy"))
        assert proc.returncode != 0, f"expected non-zero, got {proc.returncode}"
