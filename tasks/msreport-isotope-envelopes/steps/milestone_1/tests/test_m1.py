"""Shared behavioral checks for the msreport milestone verifiers."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path


PROTON = 1.007276466812
NEUTRON = 1.003355


def build_cli() -> None:
    """Compile the public Java CLI before exercising it."""
    subprocess.run(["make", "-C", "/app", "clean", "all"], check=True, text=True, capture_output=True)


def run_cli(*args: str) -> None:
    """Run the public msreport executable with the provided arguments."""
    subprocess.run(["/app/bin/msreport", *args], check=True, text=True, capture_output=True)


def read_json(path: Path) -> dict:
    """Load a JSON object from a generated artifact."""
    return json.loads(path.read_text())


def public_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Copy public fixtures to an isolated directory for end-to-end verifier commands."""
    spectra = tmp_path / "runs"
    shutil.copytree("/app/data/runs", spectra)
    calibration = tmp_path / "calibration.tsv"
    policy = tmp_path / "isotope_policy.csv"
    replicates = tmp_path / "replicates.tsv"
    shutil.copy("/app/data/calibration.tsv", calibration)
    shutil.copy("/app/data/isotope_policy.csv", policy)
    shutil.copy("/app/data/replicates.tsv", replicates)
    return spectra, calibration, policy, replicates


def write_custom_fixture(base: Path) -> tuple[Path, Path, Path, Path]:
    """Create a verifier-owned fixture with non-public values and mixed status outcomes."""
    spectra = base / "runs"
    spectra.mkdir()
    (spectra / "zeta.tsv").write_text(
        "\n".join(
            [
                "run\tscan\tmz\tintensity\tquality",
                "zeta\t7\t520.1000\t1000\tOK",
                "zeta\t7\t520.6018\t600\tOK",
                "zeta\t7\t521.1034\t300\tOK",
                "zeta\t7\t521.6055\t120\tNOISE",
                "zeta\t9\t710.4000\t100\tOK",
            ]
        )
        + "\n"
    )
    (spectra / "eta.tsv").write_text(
        "\n".join(
            [
                "run\tscan\tmz\tintensity\tquality",
                "eta\t7\t520.1005\t1200\tOK",
                "eta\t7\t520.6020\t250\tOK",
                "eta\t7\t521.1037\t100\tOK",
                "eta\t9\t710.4040\t200\tOK",
            ]
        )
        + "\n"
    )
    (spectra / "theta.tsv").write_text(
        "\n".join(
            [
                "run\tscan\tmz\tintensity\tquality",
                "theta\t7\t520.1250\t900\tOK",
                "theta\t7\t520.6266\t500\tOK",
                "theta\t7\t521.1280\t250\tOK",
            ]
        )
        + "\n"
    )
    calibration = base / "calibration.tsv"
    calibration.write_text(
        "\n".join(
            [
                "run\tmz_offset\tintensity_scale",
                "zeta\t0.0030\t1.10",
                "eta\t-0.0020\t0.50",
                "theta\t0.0000\t1.00",
            ]
        )
        + "\n"
    )
    policy = base / "policy.csv"
    policy.write_text(
        "\n".join(
            [
                "family,run,scan,charge,min_peaks,mz_start,mz_end",
                "frag-x,zeta,7,2,3,520.00,521.20",
                "frag-x,eta,7,2,3,520.00,521.20",
                "frag-x,theta,7,2,3,520.00,521.20",
                "frag-y,zeta,9,1,2,710.0,711.7",
                "frag-y,eta,9,1,2,710.0,711.7",
            ]
        )
        + "\n"
    )
    replicates = base / "replicates.tsv"
    replicates.write_text("group\trun\ncohort-a\tzeta\ncohort-a\teta\ncohort-a\ttheta\n")
    return spectra, calibration, policy, replicates


def expected_centroids(spectra: Path, calibration: Path) -> dict:
    """Compute the expected centroid artifact from spectrum and calibration inputs."""
    cal = {}
    for line in calibration.read_text().splitlines()[1:]:
        run, offset, scale = line.split("\t")
        cal[run] = (float(offset), float(scale))
    runs: dict[str, dict[int, list[dict]]] = {}
    for file in sorted(spectra.glob("*.tsv"), key=lambda p: p.name):
        for line in file.read_text().splitlines()[1:]:
            run, scan, mz, intensity, quality = line.split("\t")
            if quality != "OK":
                continue
            offset, scale = cal.get(run, (0.0, 1.0))
            runs.setdefault(run, {}).setdefault(int(scan), []).append(
                {"mz": round(float(mz) + offset, 4), "intensity": int(round(float(intensity) * scale))}
            )
    result = {"runs": []}
    for run in sorted(runs):
        scans = []
        tic = 0
        for scan in sorted(runs[run]):
            peaks = sorted(runs[run][scan], key=lambda p: p["mz"])
            tic += sum(p["intensity"] for p in peaks)
            scans.append({"scan": scan, "peaks": peaks})
        result["runs"].append({"run": run, "scan_count": len(scans), "total_ion_current": tic, "scans": scans})
    return result


def expected_envelopes(centroids: dict, policy: Path) -> dict:
    """Compute isotope envelopes according to the public spacing and policy contract."""
    run_map = {
        run["run"]: {scan["scan"]: scan["peaks"] for scan in run["scans"]}
        for run in centroids["runs"]
    }
    envelopes = []
    for line in policy.read_text().splitlines()[1:]:
        family, run, scan_s, charge_s, min_s, start_s, end_s = line.split(",")
        scan = int(scan_s)
        charge = int(charge_s)
        min_peaks = int(min_s)
        start = float(start_s)
        end = float(end_s)
        peaks = [p for p in run_map.get(run, {}).get(scan, []) if start <= p["mz"] <= end]
        peaks.sort(key=lambda p: p["mz"])
        chain = best_chain(peaks, charge)
        if len(chain) < min_peaks:
            continue
        mono = round(chain[0]["mz"], 4)
        envelopes.append(
            {
                "family": family,
                "run": run,
                "scan": scan,
                "charge": charge,
                "peak_count": len(chain),
                "monoisotopic_mz": mono,
                "neutral_mass": round((mono - PROTON) * charge, 5),
                "intensity_sum": sum(p["intensity"] for p in chain),
                "peak_mz": [round(p["mz"], 4) for p in chain],
            }
        )
    envelopes.sort(key=lambda e: (e["family"], e["run"]))
    return {"envelopes": envelopes}


def best_chain(peaks: list[dict], charge: int) -> list[dict]:
    """Return the longest isotope chain, breaking ties by total intensity."""
    spacing = NEUTRON / charge
    best: list[dict] = []
    for index, peak in enumerate(peaks):
        chain = [peak]
        last = peak
        for candidate in peaks[index + 1 :]:
            if abs((candidate["mz"] - last["mz"]) - spacing) <= 0.015:
                chain.append(candidate)
                last = candidate
        if len(chain) > len(best) or (
            len(chain) == len(best)
            and sum(p["intensity"] for p in chain) > sum(p["intensity"] for p in best)
        ):
            best = chain
    return best


def expected_review(envelopes: dict, replicates: Path) -> dict:
    """Compute replicate-level review rows and status summary from envelope JSON."""
    groups: dict[str, list[str]] = {}
    for line in replicates.read_text().splitlines()[1:]:
        group, run = line.split("\t")
        groups.setdefault(group, []).append(run)
    families = sorted({e["family"] for e in envelopes["envelopes"]})
    rows = []
    counts = {"stable": 0, "drift": 0, "unstable_intensity": 0, "missing": 0}
    for group in sorted(groups):
        expected_runs = sorted(groups[group])
        for family in families:
            observed = sorted(
                [e for e in envelopes["envelopes"] if e["family"] == family and e["run"] in expected_runs],
                key=lambda e: e["run"],
            )
            observed_runs = [e["run"] for e in observed]
            missing = [run for run in expected_runs if run not in observed_runs]
            masses = [e["neutral_mass"] for e in observed]
            intensities = [e["intensity_sum"] for e in observed]
            mean_mass = round(sum(masses) / len(masses), 5) if masses else None
            ppm_span = round(((max(masses) - min(masses)) / mean_mass) * 1_000_000, 2) if masses else 0.0
            cv = None
            if intensities:
                mean_i = sum(intensities) / len(intensities)
                variance = sum((value - mean_i) ** 2 for value in intensities) / len(intensities)
                cv = round(math.sqrt(variance) / mean_i, 4) if mean_i else 0.0
            if missing:
                status = "missing"
            elif ppm_span > 12.0:
                status = "drift"
            elif cv is not None and cv > 0.35:
                status = "unstable_intensity"
            else:
                status = "stable"
            counts[status] += 1
            rows.append(
                {
                    "group": group,
                    "family": family,
                    "runs": expected_runs,
                    "observed_runs": observed_runs,
                    "missing_runs": missing,
                    "mean_neutral_mass": mean_mass,
                    "ppm_span": ppm_span,
                    "intensity_cv": cv,
                    "status": status,
                }
            )
    return {
        "groups": rows,
        "summary": {
            "group_count": len(groups),
            "family_review_count": len(rows),
            "stable_count": counts["stable"],
            "drift_count": counts["drift"],
            "unstable_intensity_count": counts["unstable_intensity"],
            "missing_count": counts["missing"],
        },
    }

def test_public_centroid_artifact_matches_calibrated_spectra(tmp_path: Path):
    """Verify the public centroid command calibrates, filters, sorts, and summarizes bundled spectra."""
    build_cli()
    spectra, calibration, _, _ = public_paths(tmp_path)
    output = tmp_path / "centroids.json"

    run_cli("centroid", "--spectra", str(spectra), "--calibration", str(calibration), "--output", str(output))

    assert read_json(output) == expected_centroids(spectra, calibration)


def test_centroid_uses_generated_fixture_not_public_answers(tmp_path: Path):
    """Verify centroid calculations on verifier-owned values with non-OK rows and scaling."""
    build_cli()
    spectra, calibration, _, _ = write_custom_fixture(tmp_path)
    output = tmp_path / "custom-centroids.json"

    run_cli("centroid", "--spectra", str(spectra), "--calibration", str(calibration), "--output", str(output))
    result = read_json(output)

    assert result == expected_centroids(spectra, calibration)
    zeta_scan = result["runs"][2]["scans"][0]
    assert all(peak["mz"] != 521.6085 for peak in zeta_scan["peaks"])
    assert zeta_scan["peaks"][0]["intensity"] == 1100
