"""Unit tests for milestone 2. Validates ClassifierTrainer."""

import json
import math
import shutil
import struct
import zlib
import subprocess
from pathlib import Path

DATASET_PATH = Path("/app/dataset")
METRICS_PATH = Path("/app/output/training-metrics.json")
MODEL_PATH = Path("/app/models/classifier.bin")
OUTPUTS_PATH = Path("/app/terraform/outputs.json")
TRAINER_SRC = Path("/app/src/ClassifierTrainer.kt")
TRAINER_JAR = Path("/tmp/ClassifierTrainer.jar")

CLASS_NAMES = ["no_aurora", "weak_aurora", "strong_aurora"]


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
                predictor = paeth_predictor(left, up, upper_left)
                row[i] = (value + predictor) & 0xFF
            else:
                assert filter_type == 0, f"{path} uses unsupported PNG filter {filter_type}"

        for pixel in range(width):
            green_total += row[pixel * channels + 1]
        previous = row

    return green_total / (width * height * 255.0)


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


def evaluate_model(weights: list[tuple[float, float]], dataset_dir: Path) -> tuple[float, float]:
    """Evaluate saved weights independently against the labeled PNG training data."""
    correct = 0
    total = 0
    loss_sum = 0.0

    for label, class_name in enumerate(CLASS_NAMES):
        for image_path in sorted((dataset_dir / class_name).glob("*.png")):
            green_intensity = read_png_average_green(image_path)
            logits = [weight * green_intensity + bias for weight, bias in weights]
            max_logit = max(logits)
            exps = [math.exp(logit - max_logit) for logit in logits]
            exp_sum = sum(exps)
            probs = [value / exp_sum for value in exps]
            prediction = max(range(len(probs)), key=probs.__getitem__)
            correct += int(prediction == label)
            total += 1
            loss_sum += -math.log(max(probs[label], 1e-15))

    assert total > 0, f"No training PNGs found under {dataset_dir}"
    return correct / total, loss_sum / total


def compile_trainer() -> None:
    """Compile the Kotlin trainer into a reusable jar for this test run."""
    compile_res = subprocess.run([
        "kotlinc", "-cp", "/usr/share/java/gson.jar",
        str(TRAINER_SRC), "-include-runtime", "-d", str(TRAINER_JAR)
    ], capture_output=True, text=True)
    assert compile_res.returncode == 0, f"Compilation failed: {compile_res.stderr}"


class TestMilestone2:
    """Tests for Milestone 2: Train Frame Classifier."""

    def test_milestone_2_files_exist(self) -> None:
        """Verify the trainer source file exists."""
        assert TRAINER_SRC.is_file(), f"Source file {TRAINER_SRC} does not exist"

    def test_milestone_2_execution(self) -> None:
        """Run training and independently verify metrics against the image dataset."""
        if METRICS_PATH.exists():
            METRICS_PATH.unlink()
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()

        compile_trainer()

        run_res = subprocess.run([
            "java", "-cp", f"/usr/share/java/gson.jar:{TRAINER_JAR}", "ClassifierTrainerKt"
        ], capture_output=True, text=True)
        assert run_res.returncode == 0, f"Execution failed: {run_res.stderr}"
        assert MODEL_PATH.exists(), f"Model parameters {MODEL_PATH} were not created"
        assert METRICS_PATH.exists(), f"Metrics JSON {METRICS_PATH} was not created"

        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        assert metrics["epochs"] == 50, f"Expected 50 epochs, got {metrics['epochs']}"
        assert metrics["final_accuracy"] > 0.95, f"Expected final accuracy > 0.95, got {metrics['final_accuracy']}"
        assert metrics["final_loss"] < 0.2, f"Expected final loss < 0.2, got {metrics['final_loss']}"

        weights = load_model_weights(MODEL_PATH)
        actual_accuracy, actual_loss = evaluate_model(weights, DATASET_PATH)
        assert actual_accuracy > 0.95, f"Independent eval: acc={actual_accuracy}"
        assert actual_loss < 0.2, f"Independent eval: loss={actual_loss}"
        assert abs(actual_accuracy - metrics["final_accuracy"]) < 0.05
        assert abs(actual_loss - metrics["final_loss"]) < 0.05

    def test_milestone_2_reads_dataset_path_from_outputs(self) -> None:
        """Verify the trainer uses the dataset path from Terraform outputs."""
        alternate_dataset = Path("/tmp/aurora-training-dataset")
        hidden_dataset = Path("/tmp/original-app-dataset")
        original_outputs = OUTPUTS_PATH.read_text(encoding="utf-8")
        if alternate_dataset.exists():
            shutil.rmtree(alternate_dataset)
        if hidden_dataset.exists():
            shutil.rmtree(hidden_dataset)

        shutil.copytree(DATASET_PATH, alternate_dataset)
        shutil.copytree(DATASET_PATH, hidden_dataset)
        shutil.rmtree(DATASET_PATH)
        try:
            compile_trainer()
            outputs = json.loads(original_outputs)
            outputs["dataset_directory"]["value"] = str(alternate_dataset)
            OUTPUTS_PATH.write_text(json.dumps(outputs), encoding="utf-8")
            if METRICS_PATH.exists():
                METRICS_PATH.unlink()
            if MODEL_PATH.exists():
                MODEL_PATH.unlink()

            run_res = subprocess.run([
                "java", "-cp", f"/usr/share/java/gson.jar:{TRAINER_JAR}", "ClassifierTrainerKt"
            ], capture_output=True, text=True)
            assert run_res.returncode == 0, f"Execution failed with relocated dataset: {run_res.stderr}"

            weights = load_model_weights(MODEL_PATH)
            actual_accuracy, actual_loss = evaluate_model(weights, alternate_dataset)
            assert actual_accuracy > 0.95, f"Independent relocated eval: acc={actual_accuracy}"
            assert actual_loss < 0.2, f"Independent relocated eval: loss={actual_loss}"
        finally:
            OUTPUTS_PATH.write_text(original_outputs, encoding="utf-8")
            if DATASET_PATH.exists():
                shutil.rmtree(DATASET_PATH)
            shutil.move(str(hidden_dataset), str(DATASET_PATH))
            if alternate_dataset.exists():
                shutil.rmtree(alternate_dataset)
