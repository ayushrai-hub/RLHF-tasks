"""Unit tests for milestone 3. Validates TriageWorker."""

import json
import math
import shutil
import subprocess
import struct
import zlib
from pathlib import Path

DECISIONS_PATH = Path("/app/output/protocol-decisions.json")
SUMMARY_PATH = Path("/app/output/run_summary.json")
PREDICTIONS_DIR = Path("/app/output/predictions")
WORKER_SRC = Path("/app/src/TriageWorker.kt")
INCOMING_DIR = Path("/app/incoming_frames")
MODEL_PATH = Path("/app/models/classifier.bin")
OUTPUTS_PATH = Path("/app/terraform/outputs.json")
CLASS_NAMES = ["no_aurora", "weak_aurora", "strong_aurora"]


def paeth_predictor(left: int, up: int, upper_left: int) -> int:
    """Return the PNG Paeth predictor for one channel."""
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def read_png_average_green(path: Path) -> float:
    """Compute normalized average green intensity from a non-interlaced RGB/RGBA PNG."""
    raw = path.read_bytes()
    assert raw.startswith(b"\x89PNG\r\n\x1a\n"), f"{path} is not a PNG file"

    offset = 8
    width = height = bit_depth = color_type = None
    compressed = bytearray()
    while offset < len(raw):
        length = struct.unpack(">I", raw[offset : offset + 4])[0]
        chunk_type = raw[offset + 4 : offset + 8]
        chunk_data = raw[offset + 8 : offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            assert bit_depth == 8, f"{path} must use 8-bit channels"
            assert color_type in {2, 6}, f"{path} must be RGB or RGBA"
            assert interlace == 0, f"{path} must be non-interlaced"
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    assert width is not None and height is not None
    channels = 3 if color_type == 2 else 4
    stride = width * channels
    decoded = zlib.decompress(bytes(compressed))
    previous = bytearray(stride)
    green_total = 0

    pos = 0
    for _ in range(height):
        filter_type = decoded[pos]
        pos += 1
        row = bytearray(decoded[pos : pos + stride])
        pos += stride

        for i, value in enumerate(row):
            left = row[i - channels] if i >= channels else 0
            up = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if filter_type == 1:
                row[i] = (value + left) & 0xFF
            elif filter_type == 2:
                row[i] = (value + up) & 0xFF
            elif filter_type == 3:
                row[i] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                row[i] = (value + paeth_predictor(left, up, upper_left)) & 0xFF
            else:
                assert filter_type == 0, f"{path} uses unsupported PNG filter {filter_type}"

        for pixel in range(width):
            green_total += row[pixel * channels + 1]
        previous = row

    return green_total / (width * height * 255.0)


def load_model_weights(path: Path) -> list[tuple[float, float]]:
    """Load the three model weight/bias rows from classifier.bin."""
    weights = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            parts = line.strip().split(",")
            assert len(parts) == 2, f"Expected 2 parameters per class weight line, got {len(parts)}"
            weights.append((float(parts[0]), float(parts[1])))
    assert len(weights) == 3, f"Expected 3 classes of weights, got {len(weights)}"
    return weights


def classify_frame(image_path: Path, weights: list[tuple[float, float]]) -> tuple[str, float, list[float]]:
    """Classify one frame with independently parsed model weights and PNG pixels."""
    green_intensity = read_png_average_green(image_path)
    logits = [weight * green_intensity + bias for weight, bias in weights]
    max_logit = max(logits)
    exps = [math.exp(logit - max_logit) for logit in logits]
    exp_sum = sum(exps)
    probs = [value / exp_sum for value in exps]
    prediction = max(range(len(probs)), key=probs.__getitem__)
    return CLASS_NAMES[prediction], probs[prediction], probs


class TestMilestone3:
    """Tests for Milestone 3: Run Background Triage Worker."""

    def test_milestone_3_files_exist(self) -> None:
        """Verify the triage worker source file exists."""
        assert WORKER_SRC.is_file(), f"Source file {WORKER_SRC} does not exist"

    def test_milestone_3_execution(self) -> None:
        """Run the triage program and verify predictions and summary outputs."""
        if SUMMARY_PATH.exists():
            SUMMARY_PATH.unlink()
        for f in PREDICTIONS_DIR.glob("*_result.json"):
            f.unlink()

        # Compile and execute
        compile_res = subprocess.run([
            "kotlinc", "-cp", "/usr/share/java/gson.jar",
            str(WORKER_SRC), "-include-runtime", "-d", "/tmp/TriageWorker.jar"
        ], capture_output=True, text=True)
        assert compile_res.returncode == 0, f"Compilation failed: {compile_res.stderr}"

        run_res = subprocess.run([
            "java", "-cp", "/usr/share/java/gson.jar:/tmp/TriageWorker.jar", "TriageWorkerKt"
        ], capture_output=True, text=True)
        assert run_res.returncode == 0, f"Execution failed: {run_res.stderr}"

        # Assert outputs exist
        assert SUMMARY_PATH.exists(), f"Summary JSON {SUMMARY_PATH} was not created"
        
        # Load decisions rules
        with open(DECISIONS_PATH, "r", encoding="utf-8") as f:
            decisions = json.load(f)
        strong_threshold = decisions["strong_aurora_threshold"]
        temp_threshold = decisions["quarantine_temp_threshold"]
        untrusted_sensor = decisions["untrusted_sensor_id"]
        weights = load_model_weights(MODEL_PATH)

        # Parse and validate individual predictions
        png_files = list(INCOMING_DIR.glob("*.png"))
        assert len(png_files) > 0, "No incoming png frames found"

        local_counts = {"total": 0, "escalate": 0, "quarantine": 0, "archive": 0}

        for png_file in png_files:
            frame_id = png_file.stem
            result_file = PREDICTIONS_DIR / f"{frame_id}_result.json"
            meta_file = INCOMING_DIR / f"{frame_id}.json"
            
            assert result_file.exists(), f"Result file {result_file} was not created for {frame_id}"
            assert meta_file.exists(), f"Metadata file {meta_file} not found for {frame_id}"

            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            sensor_id = meta["sensor_id"]
            temperature = meta["temperature"]

            with open(result_file, "r", encoding="utf-8") as f:
                res = json.load(f)

            # Verify schema
            assert res["frame_id"] == frame_id
            assert res["aurora_class"] in ["no_aurora", "weak_aurora", "strong_aurora"]
            assert isinstance(res["probability"], (int, float))
            assert res["action"] in ["archive", "quarantine", "escalate"]
            assert isinstance(res["flagged"], bool)

            expected_class, expected_probability, probabilities = classify_frame(png_file, weights)
            assert res["aurora_class"] == expected_class
            assert math.isclose(
                res["probability"], expected_probability, rel_tol=1e-7, abs_tol=1e-7
            )

            # Check rule logic against independently computed model probabilities.
            expected_action = "archive"
            expected_flagged = False

            if sensor_id == untrusted_sensor:
                expected_action = "quarantine"
                expected_flagged = True
            else:
                if probabilities[2] >= strong_threshold:
                    expected_action = "escalate"
                    expected_flagged = True
                elif expected_class == "weak_aurora" and temperature < temp_threshold:
                    expected_action = "quarantine"
                    expected_flagged = True

            assert res["action"] == expected_action, (
                f"Mismatched action for {frame_id}: got {res['action']}, "
                f"expected {expected_action}"
            )
            assert res["flagged"] == expected_flagged, (
                f"Mismatched flagged status for {frame_id}: got {res['flagged']}, "
                f"expected {expected_flagged}"
            )

            local_counts["total"] += 1
            local_counts[res["action"]] += 1

        # Verify summary file counts
        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            summary = json.load(f)

        assert summary["total_processed"] == local_counts["total"]
        assert summary["escalated_count"] == local_counts["escalate"]
        assert summary["quarantined_count"] == local_counts["quarantine"]
        assert summary["archived_count"] == local_counts["archive"]

    def test_milestone_3_mutated_execution(self) -> None:
        """Verify the triage worker behaves dynamically under mutated protocol decisions."""
        # Backup original decisions
        backup_path = Path("/tmp/protocol-decisions.json.bak")
        DECISIONS_PATH.rename(backup_path)

        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                decisions = json.load(f)

            # Mutate: set quarantine temperature threshold to a very low value
            decisions["quarantine_temp_threshold"] = -50.0
            # Mutate: set strong threshold to a high value
            decisions["strong_aurora_threshold"] = 0.99
            
            with open(DECISIONS_PATH, "w", encoding="utf-8") as f:
                json.dump(decisions, f)
            weights = load_model_weights(MODEL_PATH)

            # Re-run the worker
            run_res = subprocess.run([
                "java", "-cp", "/usr/share/java/gson.jar:/tmp/TriageWorker.jar", "TriageWorkerKt"
            ], capture_output=True, text=True)
            assert run_res.returncode == 0, f"Execution failed on mutated decisions: {run_res.stderr}"

            # Read mutated outputs and verify
            png_files = list(INCOMING_DIR.glob("*.png"))
            for png_file in png_files:
                frame_id = png_file.stem
                result_file = PREDICTIONS_DIR / f"{frame_id}_result.json"
                meta_file = INCOMING_DIR / f"{frame_id}.json"

                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                sensor_id = meta["sensor_id"]
                temperature = meta["temperature"]

                with open(result_file, "r", encoding="utf-8") as f:
                    res = json.load(f)

                expected_class, expected_probability, probabilities = classify_frame(png_file, weights)
                assert res["aurora_class"] == expected_class
                assert math.isclose(
                    res["probability"], expected_probability, rel_tol=1e-7, abs_tol=1e-7
                )

                # Under -50.0C threshold, a weak_aurora with e.g. -28.4C temperature
                # should NOT be quarantined anymore (it should be archived).
                # Similarly, a strong_aurora with probability < 0.99 should not escalate.
                if sensor_id == decisions["untrusted_sensor_id"]:
                    assert res["action"] == "quarantine"
                    assert res["flagged"] is True
                else:
                    if expected_class == "weak_aurora" and temperature >= -50.0:
                        assert res["action"] == "archive"
                        assert res["flagged"] is False
                    if probabilities[2] < 0.99:
                        assert res["action"] == "archive"
                        assert res["flagged"] is False

        finally:
            # Restore original decisions
            if DECISIONS_PATH.exists():
                DECISIONS_PATH.unlink()
            backup_path.rename(DECISIONS_PATH)

    def test_milestone_3_relocated_paths_and_fresh_snapshot(self) -> None:
        """Verify relocated directories and stale prediction cleanup on rerun."""
        alternate_incoming = Path("/tmp/aurora-relocated-incoming")
        alternate_predictions = Path("/tmp/aurora-relocated-predictions")
        original_outputs = OUTPUTS_PATH.read_text(encoding="utf-8")

        for directory in (alternate_incoming, alternate_predictions):
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir(parents=True)

        try:
            for frame_id in ("frame_001", "frame_002"):
                shutil.copy2(INCOMING_DIR / f"{frame_id}.png", alternate_incoming / f"{frame_id}.png")
                shutil.copy2(INCOMING_DIR / f"{frame_id}.json", alternate_incoming / f"{frame_id}.json")

            stale_file = alternate_predictions / "frame_999_result.json"
            stale_file.write_text('{"frame_id":"frame_999","action":"escalate"}', encoding="utf-8")

            outputs = json.loads(original_outputs)
            outputs["incoming_directory"]["value"] = str(alternate_incoming)
            outputs["predictions_directory"]["value"] = str(alternate_predictions)
            OUTPUTS_PATH.write_text(json.dumps(outputs), encoding="utf-8")

            run_res = subprocess.run([
                "java", "-cp", "/usr/share/java/gson.jar:/tmp/TriageWorker.jar", "TriageWorkerKt"
            ], capture_output=True, text=True)
            assert run_res.returncode == 0, f"Execution failed with relocated paths: {run_res.stderr}"
            assert not stale_file.exists(), "Stale prediction files must be removed before each run"

            result_files = sorted(alternate_predictions.glob("*_result.json"))
            assert [path.name for path in result_files] == [
                "frame_001_result.json",
                "frame_002_result.json",
            ]

            with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
                summary = json.load(f)
            assert summary["total_processed"] == 2
            assert (
                summary["escalated_count"]
                + summary["quarantined_count"]
                + summary["archived_count"]
            ) == 2
        finally:
            OUTPUTS_PATH.write_text(original_outputs, encoding="utf-8")
            for directory in (alternate_incoming, alternate_predictions):
                if directory.exists():
                    shutil.rmtree(directory)
