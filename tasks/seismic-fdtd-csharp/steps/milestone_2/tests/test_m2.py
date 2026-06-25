"""tests for milestone 2: 2D elastic FDTD with absorbing zone and SLS attenuation."""
import shutil
import subprocess
from pathlib import Path

import numpy as np

SEISMIC = "/app/seismic"
TMP_BASE = Path("/tmp/m2")
_SIM_CACHE: dict[str, Path] = {}


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([SEISMIC, *args], capture_output=True, text=True, check=False)


def _simulate(fixture_name: str) -> Path:
    """Run /app/seismic simulate on the named fixture and return its output dir.

    The fixture's `model_dir` and `source.path` point inside /app/output, populated by
    the agent's milestone solve. The output dir is /tmp/m2/<fixture_name>, freshly
    created on first call and memoised across tests.
    """
    if fixture_name in _SIM_CACHE:
        return _SIM_CACHE[fixture_name]
    out = TMP_BASE / fixture_name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    fixture_path = f"/app/fixtures/{fixture_name}.json"
    proc = _run("simulate", fixture_path, str(out))
    assert proc.returncode == 0, (
        f"seismic simulate {fixture_name} failed (rc={proc.returncode})\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    _SIM_CACHE[fixture_name] = out
    return out


def _load_gather(p: Path) -> tuple[np.ndarray, np.ndarray]:
    g = np.load(p / "shot_gather.npy")
    t = np.load(p / "time.npy")
    return g, t


class TestMilestone2:
    def test_simulate_subcommand_writes_required_outputs(self) -> None:
        """seismic simulate produces shot_gather.npy and time.npy in the chosen output dir."""
        out = _simulate("sim_homo_on")
        assert (out / "shot_gather.npy").exists(), "shot_gather.npy not written"
        assert (out / "time.npy").exists(), "time.npy not written"

    def test_shot_gather_shape_and_dtype(self) -> None:
        """shot_gather.npy has shape (n_steps, n_receivers) and dtype float32."""
        out = _simulate("sim_homo_on")
        g, _ = _load_gather(out)
        assert g.dtype == np.float32
        assert g.shape == (600, 9)

    def test_time_axis_correctness(self) -> None:
        """time.npy starts at 0 and steps by dt = 0.001 s for n_steps samples."""
        out = _simulate("sim_homo_on")
        _, t = _load_gather(out)
        assert t.shape == (600,)
        assert abs(float(t[0])) < 1e-7
        assert abs(float(t[1] - t[0]) - 0.001) < 1e-6
        assert abs(float(t[-1]) - 0.599) < 1e-4

    def test_no_nan_or_blowup_in_gather(self) -> None:
        """the simulator stays numerically bounded."""
        out = _simulate("sim_homo_on")
        g, _ = _load_gather(out)
        assert np.all(np.isfinite(g))
        assert float(np.abs(g).max()) < 1e6

    def test_direct_arrival_travel_time(self) -> None:
        """direct P-wave arrival lines up with distance/Vp at a measured receiver."""
        out = _simulate("sim_homo_on")
        g, _ = _load_gather(out)
        # Receiver index 4 -> x=600, z=600. Source at (600, 150). Vertical distance 450 m.
        # Vp=2000 m/s, source delay=0.04 s. Analytical arrival ~ 0.265 s -> step 265.
        # A 2nd-order spatial stencil at ~8 points-per-wavelength delays the peak by
        # roughly one wavelength worth of steps, so allow the peak anywhere in the
        # window that brackets both ideal and dispersive implementations.
        trace = g[:, 4]
        win_lo, win_hi = 240, 320
        seg = trace[win_lo:win_hi]
        peak_idx = int(win_lo + np.argmax(np.abs(seg)))
        peak_amp = float(np.abs(seg).max())
        assert win_lo < peak_idx < win_hi - 1, f"direct arrival peak at step {peak_idx} sits on window edge"
        noise = float(np.sqrt(np.mean(trace[:20] ** 2)) + 1e-30)
        assert peak_amp > 5.0 * noise, f"direct arrival amplitude {peak_amp} vs noise {noise}"

    def test_pml_reduces_interior_energy_after_boundary_interaction(self) -> None:
        """with PML, interior vz^2 after the wave hits boundaries is smaller and the
        boundary zone itself is strongly damped rather than reflecting."""
        out_off = _simulate("sim_homo_off")
        out_on = _simulate("sim_homo_on")
        snap_off = np.load(out_off / "snapshots" / "snap_000500.npy")
        snap_on = np.load(out_on / "snapshots" / "snap_000500.npy")
        interior_off = snap_off[12:-12, 12:-12]
        interior_on = snap_on[12:-12, 12:-12]
        e_off = float(np.sum(interior_off ** 2))
        e_on = float(np.sum(interior_on ** 2))
        assert e_off > 0
        assert e_on > 0
        # The reflected energy that stays in the interior without PML is roughly
        # 2.1x the absorbed-boundary case; a working absorber must clear this gap.
        assert e_off / e_on > 1.9, f"PML interior ratio {e_off / e_on:.2f} (off/on); expected > 1.9"
        # The boundary zone (the 12-cell ring that the PML damps) must hold far
        # less energy with the absorber on, since the wave is attenuated there
        # instead of reflecting back. The oracle ratio is ~30x.
        mask = np.ones(snap_off.shape, dtype=bool)
        mask[12:-12, 12:-12] = False
        ring_off = float(np.sum(snap_off[mask] ** 2))
        ring_on = float(np.sum(snap_on[mask] ** 2))
        assert ring_on > 0
        assert ring_off / ring_on > 5.0, f"PML boundary-zone ratio {ring_off / ring_on:.2f}; expected > 5"

    def test_attenuation_amplitude_decay(self) -> None:
        """enabling Q-based attenuation reduces direct-arrival amplitude versus the elastic case."""
        out_on = _simulate("sim_homo_on")
        out_attn = _simulate("sim_homo_attn")
        g_on, _ = _load_gather(out_on)
        g_attn, _ = _load_gather(out_attn)
        win_lo, win_hi = 240, 320
        peak_on = float(np.abs(g_on[win_lo:win_hi, 4]).max())
        peak_attn = float(np.abs(g_attn[win_lo:win_hi, 4]).max())
        assert peak_on > 0
        ratio = peak_attn / peak_on
        # The per-step SLS factor exp(-pi * f_ref * dt / Q) is applied to the
        # stress fields only, so the recorded vz peak decays less than a naive
        # bulk estimate; the discretised oracle lands at ~0.82. The band excludes
        # both the no-attenuation case (1.0) and an over-damped solver.
        assert 0.74 < ratio < 0.90, f"attn/no-attn amplitude ratio = {ratio:.3f}"

    def test_vz_injection_direct_arrival(self) -> None:
        """a vertical-velocity source injects into vz and produces the direct arrival."""
        out = _simulate("sim_homo_vz")
        g, _ = _load_gather(out)
        assert g.shape == (600, 9)
        assert np.all(np.isfinite(g))
        # Same geometry as sim_homo_on: receiver 4 -> x=600, z=600, source (600, 150).
        # Vertical distance 450 m at Vp=2000 plus the 0.04 s delay -> arrival ~step 265,
        # dispersively delayed but well inside the window.
        trace = g[:, 4]
        win_lo, win_hi = 240, 320
        seg = trace[win_lo:win_hi]
        peak_idx = int(win_lo + np.argmax(np.abs(seg)))
        peak_amp = float(np.abs(seg).max())
        assert win_lo < peak_idx < win_hi - 1, f"vz direct arrival peak at step {peak_idx} sits on window edge"
        noise = float(np.sqrt(np.mean(trace[:20] ** 2)) + 1e-30)
        assert peak_amp > 5.0 * noise, f"vz direct arrival amplitude {peak_amp} vs noise {noise}"

    def test_elastic_shear_arrival(self) -> None:
        """a non-zero vs medium radiates a shear arrival that the acoustic medium cannot."""
        out_el = _simulate("sim_homo_swave")   # vp=2000, vs=1150 elastic
        out_ac = _simulate("sim_homo_vz")       # vp=2000, vs=0 acoustic, identical geometry
        g_el, _ = _load_gather(out_el)
        g_ac, _ = _load_gather(out_ac)
        # Receivers x=200..1000 step 100, z=600; vertical-force source at (600, 150).
        # In the late window (after the P arrival) the elastic run carries an SV
        # arrival; the acoustic run is quiet there. SV radiation peaks at oblique
        # take-off, so the offset receivers (x=300 and x=900) show it strongly.
        late = slice(400, 590)

        def late_energy(g, ri):
            return float(np.sum(g[late, ri] ** 2))

        for ri in (1, 7):  # x=300 and x=900, ~300 m offset
            r_el = late_energy(g_el, ri)
            r_ac = late_energy(g_ac, ri)
            assert r_ac > 0
            assert r_el / r_ac > 3.0, f"recv {ri} elastic/acoustic late energy {r_el / r_ac:.2f}; expected > 3"
        # Directly beneath the source (x=600) a vertical force radiates almost no
        # SV, so the elastic and acoustic late energies stay comparable there.
        r_el0 = late_energy(g_el, 4)
        r_ac0 = late_energy(g_ac, 4)
        assert r_el0 / r_ac0 < 1.8, f"on-axis elastic/acoustic late energy {r_el0 / r_ac0:.2f}; expected < 1.8"

    def test_snapshots_present_at_correct_steps(self) -> None:
        """snapshots are emitted every snapshot_interval and carry the model's grid shape."""
        out = _simulate("sim_two_layer")
        snap_dir = out / "snapshots"
        # snapshot_interval=100, n_steps=600 -> steps 0, 100, 200, 300, 400, 500.
        for step in (0, 100, 200, 300, 400, 500):
            p = snap_dir / f"snap_{step:06d}.npy"
            assert p.exists(), f"missing {p}"
            arr = np.load(p)
            assert arr.shape == (80, 180), f"{p} shape {arr.shape}"
            assert arr.dtype == np.float32
        assert not (snap_dir / "snap_000600.npy").exists()

    def test_two_layer_reflection_arrival(self) -> None:
        """a clear secondary arrival appears at the predicted reflection time at a near-source receiver."""
        out = _simulate("sim_two_layer")
        g, _ = _load_gather(out)
        # Receivers x = 300..1500 step 100 -> indices 0..12. Source at x=900, z=200.
        # Receiver index 7 -> x=1000, offset 100 m. Reflector at z=400.
        # Image source at (900, 600); path = sqrt(100^2 + 400^2) ~ 412.3 m at Vp1=1500.
        # Analytical arrival ~ 0.315 s -> step 315.
        trace = g[:, 7]
        win_lo, win_hi = 285, 395
        seg = trace[win_lo:win_hi]
        peak_idx = int(win_lo + np.argmax(np.abs(seg)))
        peak_amp = float(np.abs(seg).max())
        assert win_lo < peak_idx < win_hi - 1, f"reflection peak at step {peak_idx} sits on window edge"
        early_rms = float(np.sqrt(np.mean(trace[:30] ** 2)) + 1e-30)
        assert peak_amp > 5.0 * early_rms, f"reflection peak {peak_amp} vs early rms {early_rms}"
