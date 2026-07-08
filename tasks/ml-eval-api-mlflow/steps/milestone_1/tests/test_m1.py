import csv
import io
import os
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import onnx
import onnx.helper as oh
import onnx.numpy_helper as onh
import onnxruntime as ort
import pytest
import requests
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error

_APP_DIR = Path("/app")
_SERVER_PORT = 3210
_BASE_URL = f"http://127.0.0.1:{_SERVER_PORT}"
_START_TIMEOUT_SECONDS = 90
_REQUEST_TIMEOUT_SECONDS = 30
_BOUNDARY = "---------------------------pytest-m1-boundary"
_MAX_ONNX_FILE_BYTES = 100 * 1024 * 1024
_MAX_CSV_FILE_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class _EvalArtifact:
    model_bytes: bytes
    csv_bytes: bytes
    eval_column: str
    expected_scores: dict[str, float]
    feature_count: int


def _write_eval_csv(rows: list[list[float]], eval_column: str = "target") -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    feature_headers = [f"feature_{index}" for index in range(len(rows[0]) - 1)]
    writer.writerow([*feature_headers, eval_column])
    writer.writerows(rows)
    return buffer.getvalue().encode()


def _serialize_model(model: onnx.ModelProto) -> bytes:
    onnx.checker.check_model(model)
    return model.SerializeToString()


def _build_regression_model_bytes(weights: np.ndarray, bias: float) -> bytes:
    feature_count = int(weights.shape[0])
    graph = oh.make_graph(
        nodes=[
            oh.make_node("MatMul", ["X", "weights"], ["matmul_out"]),
            oh.make_node("Add", ["matmul_out", "bias"], ["biased_out"]),
            oh.make_node("Squeeze", ["biased_out"], ["predictions"], axes=[1]),
        ],
        name="linear_regression_model",
        inputs=[
            oh.make_tensor_value_info(
                "X", onnx.TensorProto.FLOAT, [None, feature_count]
            )
        ],
        outputs=[
            oh.make_tensor_value_info("predictions", onnx.TensorProto.FLOAT, [None])
        ],
        initializer=[
            onh.from_array(
                weights.astype(np.float32).reshape(feature_count, 1), name="weights"
            ),
            onh.from_array(np.array([bias], dtype=np.float32), name="bias"),
        ],
    )
    model = oh.make_model(
        graph,
        producer_name="pytest-m1",
        opset_imports=[oh.make_operatorsetid("", 11)],
    )
    model.ir_version = 7
    return _serialize_model(model)


def _build_classification_model_bytes(weights: np.ndarray, bias: float) -> bytes:
    feature_count = int(weights.shape[0])
    graph = oh.make_graph(
        nodes=[
            oh.make_node("MatMul", ["X", "weights"], ["matmul_out"]),
            oh.make_node("Add", ["matmul_out", "bias"], ["biased_out"]),
            oh.make_node("Sigmoid", ["biased_out"], ["probability_out"]),
            oh.make_node("Greater", ["probability_out", "threshold"], ["label_bool"]),
            oh.make_node(
                "Cast", ["label_bool"], ["label_float"], to=onnx.TensorProto.FLOAT
            ),
            oh.make_node("Squeeze", ["label_float"], ["predictions"], axes=[1]),
        ],
        name="linear_classifier_model",
        inputs=[
            oh.make_tensor_value_info(
                "X", onnx.TensorProto.FLOAT, [None, feature_count]
            )
        ],
        outputs=[
            oh.make_tensor_value_info("predictions", onnx.TensorProto.FLOAT, [None])
        ],
        initializer=[
            onh.from_array(
                weights.astype(np.float32).reshape(feature_count, 1), name="weights"
            ),
            onh.from_array(np.array([bias], dtype=np.float32), name="bias"),
            onh.from_array(np.array([0.5], dtype=np.float32), name="threshold"),
        ],
    )
    model = oh.make_model(
        graph,
        producer_name="pytest-m1",
        opset_imports=[oh.make_operatorsetid("", 11)],
    )
    model.ir_version = 7
    return _serialize_model(model)


def _run_onnx_predictions(model_bytes: bytes, feature_matrix: np.ndarray) -> np.ndarray:
    session = ort.InferenceSession(model_bytes, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    predictions = session.run(None, {input_name: feature_matrix.astype(np.float32)})[0]
    return np.asarray(predictions, dtype=np.float64).reshape(-1)


def _compute_score(metric: str, truth: np.ndarray, predictions: np.ndarray) -> float:
    if metric in {"accuracy", "f1"}:
        # Sklearn classification metrics reject continuous predictions.
        # Mirror the API behavior by converting score-like outputs to binary labels.
        truth_labels = np.rint(truth).astype(int)
        prediction_labels = np.rint(predictions).astype(int)
        if metric == "accuracy":
            return float(accuracy_score(truth_labels, prediction_labels))
        return float(f1_score(truth_labels, prediction_labels))

    if metric == "accuracy":
        return float(accuracy_score(truth, predictions))
    if metric == "f1":
        return float(f1_score(truth, predictions))
    if metric == "rmse":
        return float(mean_squared_error(truth, predictions) ** 0.5)
    raise AssertionError(f"Unexpected metric {metric}")


def _build_classification_artifact(
    train_x: np.ndarray,
    train_y: np.ndarray,
    eval_x: np.ndarray,
    eval_y: np.ndarray,
) -> _EvalArtifact:
    model = LogisticRegression(random_state=0, solver="liblinear")
    model.fit(train_x, train_y)
    model_bytes = _build_classification_model_bytes(
        model.coef_[0], float(np.atleast_1d(model.intercept_)[0])
    )
    predictions = _run_onnx_predictions(model_bytes, eval_x)
    csv_rows = [
        [*feature_row.tolist(), float(target)]
        for feature_row, target in zip(
            eval_x.astype(float), eval_y.astype(float), strict=True
        )
    ]
    return _EvalArtifact(
        model_bytes=model_bytes,
        csv_bytes=_write_eval_csv(csv_rows),
        eval_column="target",
        expected_scores={
            metric: _compute_score(metric, eval_y.astype(float), predictions)
            for metric in ("accuracy", "f1", "rmse")
        },
        feature_count=int(eval_x.shape[1]),
    )


def _build_regression_artifact(
    train_x: np.ndarray,
    train_y: np.ndarray,
    eval_x: np.ndarray,
    eval_y: np.ndarray,
) -> _EvalArtifact:
    model = LinearRegression()
    model.fit(train_x, train_y)
    model_bytes = _build_regression_model_bytes(model.coef_, float(model.intercept_))
    predictions = _run_onnx_predictions(model_bytes, eval_x)
    csv_rows = [
        [*feature_row.tolist(), float(target)]
        for feature_row, target in zip(
            eval_x.astype(float), eval_y.astype(float), strict=True
        )
    ]
    return _EvalArtifact(
        model_bytes=model_bytes,
        csv_bytes=_write_eval_csv(csv_rows),
        eval_column="target",
        expected_scores={
            metric: _compute_score(metric, eval_y.astype(float), predictions)
            for metric in ("accuracy", "f1", "rmse")
        },
        feature_count=int(eval_x.shape[1]),
    )


def _build_runtime_failing_model_bytes() -> bytes:
    graph = oh.make_graph(
        nodes=[
            oh.make_node("Reshape", ["X", "bad_shape"], ["reshaped"]),
            oh.make_node("ReduceSum", ["reshaped"], ["reduced"], axes=[1], keepdims=0),
        ],
        name="runtime_failing_model",
        inputs=[oh.make_tensor_value_info("X", onnx.TensorProto.FLOAT, [None, 2])],
        outputs=[oh.make_tensor_value_info("reduced", onnx.TensorProto.FLOAT, [None])],
        initializer=[onh.from_array(np.array([3], dtype=np.int64), name="bad_shape")],
    )
    model = oh.make_model(
        graph,
        producer_name="pytest-m1",
        opset_imports=[oh.make_operatorsetid("", 11)],
    )
    model.ir_version = 7
    return _serialize_model(model)


def _encode_multipart(parts: list[dict[str, object]]) -> Tuple[bytes, str]:
    chunks: list[bytes] = []
    for part in parts:
        chunks.append(f"--{_BOUNDARY}\r\n".encode())
        disposition = f'Content-Disposition: form-data; name="{part["name"]}"'
        if "filename" in part:
            disposition += f'; filename="{part["filename"]}"'
        chunks.append(f"{disposition}\r\n".encode())
        if "content_type" in part:
            chunks.append(f'Content-Type: {part["content_type"]}\r\n'.encode())
        chunks.append(b"\r\n")
        body = part["body"]
        if isinstance(body, str):
            chunks.append(body.encode())
        else:
            assert isinstance(body, bytes)
            chunks.append(body)
        chunks.append(b"\r\n")
    chunks.append(f"--{_BOUNDARY}--\r\n".encode())
    return b"".join(chunks), _BOUNDARY


def _post_eval(parts: list[dict[str, object]]) -> requests.Response:
    body, boundary = _encode_multipart(parts)
    return requests.post(
        f"{_BASE_URL}/eval",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )


def _score_payload(response: requests.Response) -> dict[str, object]:
    payload = response.json()
    assert isinstance(payload, dict), "response must be a JSON object"
    assert set(payload) == {"score"}, "response must only contain score"
    assert isinstance(payload["score"], (int, float)) and not isinstance(
        payload["score"], bool
    ), "score must be numeric"
    return payload


def _assert_no_success_payload(response: requests.Response) -> None:
    try:
        payload = response.json()
    except ValueError:
        return
    assert not (
        isinstance(payload, dict)
        and set(payload) == {"score"}
        and isinstance(payload["score"], (int, float))
        and not isinstance(payload["score"], bool)
    ), "400 response must not look like a success payload"


def _wait_for_server(process: subprocess.Popen[str], log_path: Path) -> None:
    deadline = time.time() + _START_TIMEOUT_SECONDS
    last_error = None
    while time.time() < deadline:
        if process.poll() is not None:
            break
        try:
            with socket.create_connection(("127.0.0.1", _SERVER_PORT), timeout=1):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.5)
    log_output = log_path.read_text() if log_path.exists() else ""
    raise AssertionError(
        "npm start did not bring the server up\n"
        f"returncode={process.poll()} last_error={last_error}\n"
        f"logs:\n{log_output}"
    )


@pytest.fixture(scope="class")
def server():
    log_path = _APP_DIR / ".pytest-m1-server.log"
    log_handle = log_path.open("w")
    process = subprocess.Popen(
        ["npm", "start"],
        cwd=_APP_DIR,
        env=os.environ
        | {
            "SECRET_KEY_JWT": "test-secret",
            "DB_ENABLED": "false",
            "DB_PASSWORD": "postgres",
            "EMAIL_HOST": "localhost",
            "EMAIL_PORT": "1025",
            "EMAIL_AUTH_USER": "test",
            "EMAIL_AUTH_PASSWORD": "test",
            "EMAIL_FROM_NAME": "Test",
            "EMAIL_FROM_EMAIL": "test@example.com",
            "SWAGGER_USER": "test",
            "SWAGGER_PASSWORD": "test",
            "FASTIFY_PORT": str(_SERVER_PORT),
        },
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_server(process, log_path)
        yield {"process": process, "log_path": log_path}
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=15)
        log_handle.close()


@pytest.fixture(scope="class")
def artifacts() -> dict[str, _EvalArtifact]:
    classification_case_a = _build_classification_artifact(
        train_x=np.array(
            [
                [-3.0, -2.0],
                [-2.0, -1.0],
                [-1.0, -2.0],
                [1.0, 1.0],
                [2.0, 1.0],
                [1.5, 2.0],
            ],
            dtype=np.float32,
        ),
        train_y=np.array([0, 0, 0, 1, 1, 1], dtype=np.float32),
        eval_x=np.array(
            [
                [-1.5, -1.0],
                [1.2, 1.0],
                [2.1, 1.8],
                [-2.2, -1.5],
            ],
            dtype=np.float32,
        ),
        eval_y=np.array([0, 1, 1, 0], dtype=np.float32),
    )
    classification_case_b = _build_classification_artifact(
        train_x=np.array(
            [
                [-3.0, -2.0, -1.0],
                [-2.0, -1.0, -2.0],
                [-1.0, -2.0, -1.5],
                [1.0, 1.0, 2.0],
                [2.0, 1.0, 1.0],
                [1.5, 2.0, 1.0],
            ],
            dtype=np.float32,
        ),
        train_y=np.array([0, 0, 0, 1, 1, 1], dtype=np.float32),
        eval_x=np.array(
            [
                [-1.5, -1.0, -1.0],
                [1.2, 1.0, 1.0],
                [2.1, 1.8, 1.2],
                [-2.2, -1.5, -1.0],
            ],
            dtype=np.float32,
        ),
        eval_y=np.array([0, 1, 1, 0], dtype=np.float32),
    )
    classification_case_two_rows = _build_classification_artifact(
        train_x=np.array(
            [
                [-3.0, -2.0],
                [-2.0, -1.0],
                [-1.0, -2.0],
                [1.0, 1.0],
                [2.0, 1.0],
                [1.5, 2.0],
            ],
            dtype=np.float32,
        ),
        train_y=np.array([0, 0, 0, 1, 1, 1], dtype=np.float32),
        eval_x=np.array(
            [
                [-1.5, -1.0],
                [1.2, 1.0],
            ],
            dtype=np.float32,
        ),
        eval_y=np.array([0, 1], dtype=np.float32),
    )
    regression_case_a = _build_regression_artifact(
        train_x=np.array(
            [
                [0.0, 0.0],
                [0.0, 1.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.0, 2.0],
                [1.0, 2.0],
            ],
            dtype=np.float32,
        ),
        train_y=np.array([0, 0, 1, 1, 0, 1], dtype=np.float32),
        eval_x=np.array(
            [
                [0.0, 3.0],
                [1.0, 3.0],
                [0.0, 4.0],
                [1.0, 4.0],
            ],
            dtype=np.float32,
        ),
        eval_y=np.array([0, 1, 0, 1], dtype=np.float32),
    )
    regression_case_b = _build_regression_artifact(
        train_x=np.array(
            [
                [0.0, 0.0, 0.0],
                [0.0, 1.0, 1.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 1.0],
                [0.0, 2.0, 2.0],
                [1.0, 2.0, 2.0],
            ],
            dtype=np.float32,
        ),
        train_y=np.array([0, 0, 1, 1, 0, 1], dtype=np.float32),
        eval_x=np.array(
            [
                [0.0, 3.0, 3.0],
                [1.0, 3.0, 3.0],
                [0.0, 4.0, 4.0],
                [1.0, 4.0, 4.0],
            ],
            dtype=np.float32,
        ),
        eval_y=np.array([0, 1, 0, 1], dtype=np.float32),
    )
    return {
        "classification_case_a": classification_case_a,
        "classification_case_b": classification_case_b,
        "classification_case_two_rows": classification_case_two_rows,
        "regression_case_a": regression_case_a,
        "regression_case_b": regression_case_b,
    }


class TestMilestone1:
    def test_server_starts_with_npm_start(self, server):
        """Server starts with npm start."""
        assert server["process"].poll() is None, "npm start exited unexpectedly"

    def test_health_returns_200(self, server):
        """GET /health returns 200."""
        response = requests.get(f"{_BASE_URL}/health", timeout=_REQUEST_TIMEOUT_SECONDS)
        assert response.status_code == 200, "health must return 200"

    @pytest.mark.parametrize(
        ("artifact_name", "metric"),
        [
            # Classification case A against all supported metrics.
            ("classification_case_a", "accuracy"),
            ("classification_case_a", "f1"),
            ("classification_case_a", "rmse"),
            # Classification case B against all supported metrics.
            ("classification_case_b", "accuracy"),
            ("classification_case_b", "f1"),
            ("classification_case_b", "rmse"),
            # Exactly two data rows should still be accepted.
            ("classification_case_two_rows", "accuracy"),
            ("classification_case_two_rows", "f1"),
            ("classification_case_two_rows", "rmse"),
            # Regression case A against the supported non-F1 metrics.
            ("regression_case_a", "accuracy"),
            ("regression_case_a", "rmse"),
            # Regression case B against the supported non-F1 metrics.
            ("regression_case_b", "accuracy"),
            ("regression_case_b", "rmse"),
        ],
    )
    def test_eval_success_returns_expected_score(
        self, server, artifacts, artifact_name, metric
    ):
        """Successful eval returns the expected score payload."""
        artifact = artifacts[artifact_name]
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": artifact.model_bytes,
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": artifact.csv_bytes,
                },
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": metric},
            ]
        )
        assert response.status_code == 200, "successful eval must return 200"
        payload = _score_payload(response)
        assert payload["score"] == pytest.approx(
            artifact.expected_scores[metric], abs=1e-4
        ), "score must match local evaluation"

    def test_accuracy_rounds_continuous_numeric_outputs(self, server):
        """Accuracy rounds numeric truth and prediction values before scoring."""
        model_bytes = _build_regression_model_bytes(
            np.array([0.02], dtype=np.float32),
            0.47,
        )
        csv_bytes = _write_eval_csv(
            [
                [1.0, 0.0],  # Produces 0.49, which must round to label 0.
                [2.0, 1.0],  # Produces 0.51, which must round to label 1.
            ]
        )
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": model_bytes,
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": csv_bytes,
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ]
        )
        assert (
            response.status_code == 200
        ), "accuracy with continuous outputs must return 200"
        payload = _score_payload(response)
        assert payload["score"] == pytest.approx(1.0, abs=1e-4)

    @pytest.mark.parametrize(
        "artifact_name",
        [
            # Regression case A must reject binary F1.
            "regression_case_a",
            # Regression case B must reject binary F1.
            "regression_case_b",
        ],
    )
    def test_regression_rejects_f1_metric(self, server, artifacts, artifact_name):
        """Regression tasks reject the f1 metric."""
        artifact = artifacts[artifact_name]
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": artifact.model_bytes,
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": artifact.csv_bytes,
                },
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": "f1"},
            ]
        )
        assert response.status_code == 400, "regression f1 must return 400"
        _assert_no_success_payload(response)

    def test_f1_rejects_raw_predictions_outside_binary_labels(self, server):
        """F1 rejects raw predictions outside binary labels."""
        model_bytes = _build_regression_model_bytes(
            np.array([0.4], dtype=np.float32),
            -0.1,
        )
        csv_bytes = _write_eval_csv(
            [
                [1.0, 0.0],  # Produces a raw prediction of 0.3.
                [2.0, 1.0],  # Produces a raw prediction of 0.7.
            ]
        )
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": model_bytes,
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": csv_bytes,
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "f1"},
            ]
        )
        assert response.status_code == 400, "f1 must reject near-binary predictions"
        _assert_no_success_payload(response)

    def test_f1_rejects_non_binary_truth_labels(self, server):
        """F1 rejects truth labels that are not exactly binary."""
        model_bytes = _build_classification_model_bytes(
            np.array([0.0], dtype=np.float32),
            0.0,
        )
        csv_bytes = _write_eval_csv(
            [
                [1.0, 0.8],  # Near 1, but not exactly binary.
                [0.0, 0.2],  # Near 0, but not exactly binary.
                [1.0, 0.7],  # Another near-binary truth value.
                [0.0, 0.3],  # Another near-binary truth value.
            ]
        )
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": model_bytes,
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": csv_bytes,
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "f1"},
            ]
        )
        assert response.status_code == 400, "f1 must reject non-binary truth labels"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "parts",
        [
            # No multipart parts at all.
            [],
            # Multipart has metadata but omits the files field entirely.
            [
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ],
            # files field exists but uploaded file has no supported extension.
            [
                {
                    "name": "files",
                    "filename": "empty",
                    "content_type": "application/octet-stream",
                    "body": b"",
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ],
            # Wrong field name `file` instead of `files`.
            [
                {
                    "name": "file",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": b"not-used",
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ],
            # Wrong field name `model` for a CSV upload.
            [
                {
                    "name": "model",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": b"feature_0,target\n1,1\n",
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ],
            # Mixed wrong field names; still no valid `files` uploads.
            [
                {
                    "name": "model",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": b"not-used",
                },
                {
                    "name": "file",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": b"feature_0,target\n1,1\n",
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ],
        ],
    )
    def test_multipart_form_rejects_missing_or_wrong_file_fields(self, server, parts):
        """Multipart form rejects missing or wrong file fields."""
        response = _post_eval(parts)
        assert response.status_code == 400, "invalid multipart request must return 400"
        _assert_no_success_payload(response)

    def test_missing_multipart_form_returns_400(self, server):
        """Missing multipart form returns 400."""
        response = requests.post(
            f"{_BASE_URL}/eval",
            json={"eval_column": "target", "metric": "accuracy"},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        assert response.status_code == 400, "non-multipart request must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "filenames",
        [
            # Zero files in the multipart payload.
            [],
            # ONNX only; CSV missing.
            ["model.onnx"],
            # Two ONNX files; CSV missing.
            ["first.onnx", "second.onnx"],
            # CSV only; ONNX missing.
            ["dataset.csv"],
            # Two CSV files; ONNX missing.
            ["first.csv", "second.csv"],
            # More than two files in multipart payload with an unsupported extra file.
            ["model.onnx", "dataset.csv", "extra.txt"],
            # Three files with a duplicate model upload.
            ["first.onnx", "second.onnx", "dataset.csv"],
            # Three files with a duplicate CSV upload.
            ["model.onnx", "first.csv", "second.csv"],
            # Unsupported extra file type paired with ONNX.
            ["model.onnx", "notes.txt"],
            # Unsupported extra file type paired with CSV.
            ["dataset.csv", "notes.txt"],
        ],
    )
    def test_multipart_form_rejects_invalid_file_combinations(
        self, server, artifacts, filenames
    ):
        """Multipart form rejects invalid file combinations."""
        artifact = artifacts["classification_case_a"]
        file_payloads = []
        for filename in filenames:
            # Build each file body by extension so each invalid combination is explicit.
            if filename.endswith(".onnx"):
                body = artifact.model_bytes
                content_type = "application/octet-stream"
            elif filename.endswith(".csv"):
                body = artifact.csv_bytes
                content_type = "text/csv"
            else:
                body = b"unsupported"
                content_type = "text/plain"
            file_payloads.append(
                {
                    "name": "files",
                    "filename": filename,
                    "content_type": content_type,
                    "body": body,
                }
            )
        response = _post_eval(
            [
                *file_payloads,
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": "accuracy"},
            ]
        )
        assert response.status_code == 400, "invalid file combination must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        ("file_field_name", "include_extra_file"),
        [
            # Wrong multipart field name for the model file.
            ("model", False),
            # Wrong multipart field name for the dataset file.
            ("upload", False),
            # Valid files plus an unrelated extra file field.
            ("files", True),
        ],
    )
    def test_files_under_other_field_names_are_rejected(
        self, server, artifacts, file_field_name, include_extra_file
    ):
        """Files under non-files field names are rejected."""
        artifact = artifacts["classification_case_a"]
        parts = [
            {
                "name": "files" if include_extra_file else file_field_name,
                "filename": "model.onnx",
                "content_type": "application/octet-stream",
                "body": artifact.model_bytes,
            },
            {
                "name": "files",
                "filename": "dataset.csv",
                "content_type": "text/csv",
                "body": artifact.csv_bytes,
            },
        ]
        if include_extra_file:
            # Add a third file under a different field name to exercise the extra-field check.
            parts.append(
                {
                    "name": "extra",
                    "filename": "notes.txt",
                    "content_type": "text/plain",
                    "body": b"hi",
                }
            )
        response = _post_eval(
            [
                *parts,
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": "accuracy"},
            ]
        )
        assert (
            response.status_code == 400
        ), "invalid multipart file fields must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        ("model_filename", "csv_filename"),
        [
            # Forward slash path segment in the model filename.
            ("nested/model.onnx", "dataset.csv"),
            # Backslash path segment in the model filename.
            ("nested\\model.onnx", "dataset.csv"),
            # Parent directory traversal marker in the model filename.
            ("../model.onnx", "dataset.csv"),
            # Embedded null byte in the model filename.
            ("model\x00.onnx", "dataset.csv"),
            # Embedded control character in the model filename.
            ("model\tname.onnx", "dataset.csv"),
            # Forward slash path segment in the CSV filename while the model is valid.
            ("model.onnx", "nested/dataset.csv"),
            # Backslash path segment in the CSV filename while the model is valid.
            ("model.onnx", "nested\\dataset.csv"),
            # Parent directory traversal marker in the CSV filename while the model is valid.
            ("model.onnx", "../dataset.csv"),
            # Embedded null byte in the CSV filename while the model is valid.
            ("model.onnx", "dataset\x00.csv"),
            # Embedded control character in the CSV filename while the model is valid.
            ("model.onnx", "dataset\tname.csv"),
        ],
    )
    def test_path_like_filenames_are_rejected(
        self, server, artifacts, model_filename, csv_filename
    ):
        """Path-like filenames are rejected."""
        artifact = artifacts["classification_case_a"]
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": model_filename,
                    "content_type": "application/octet-stream",
                    "body": artifact.model_bytes,
                },
                {
                    "name": "files",
                    "filename": csv_filename,
                    "content_type": "text/csv",
                    "body": artifact.csv_bytes,
                },
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": "accuracy"},
            ]
        )
        assert response.status_code == 400, "path-like filename must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "parts",
        [
            [
                # ONNX payload just over the 100MB cap.
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": b"x" * (_MAX_ONNX_FILE_BYTES + 1),
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": b"feature_0,feature_1,target\n1,2,0\n2,3,1\n",
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ],
            [
                # CSV payload just over the 25MB cap.
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": b"onnx-placeholder",
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": b"x" * (_MAX_CSV_FILE_BYTES + 1),
                },
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ],
        ],
    )
    def test_oversize_files_are_rejected(self, server, parts):
        """Oversize uploads are rejected."""
        response = _post_eval(parts)
        assert response.status_code == 400, "oversize file must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "model_bytes_factory",
        [
            # .onnx extension with non-ONNX bytes.
            lambda artifacts: b"this is not an onnx model",
            # Truncated/corrupt ONNX bytes.
            lambda artifacts: artifacts["classification_case_a"].model_bytes[:20],
            # Valid-looking graph that fails at inference time.
            lambda artifacts: _build_runtime_failing_model_bytes(),
        ],
    )
    def test_onnx_validation_rejects_invalid_models(
        self, server, artifacts, model_bytes_factory
    ):
        """ONNX validation rejects invalid or unusable models."""
        artifact = artifacts["classification_case_a"]
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": model_bytes_factory(artifacts),
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": artifact.csv_bytes,
                },
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": "accuracy"},
            ]
        )
        assert response.status_code == 400, "invalid model must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "csv_bytes",
        [
            # Lower feature count than model input.
            b"feature_0,target\n0,0\n1,1\n",
            # Higher feature count than model input.
            b"feature_0,feature_1,feature_2,target\n0,0,0,0\n1,1,1,1\n",
        ],
    )
    def test_onnx_validation_rejects_feature_count_mismatches(
        self, server, artifacts, csv_bytes
    ):
        """ONNX validation rejects feature count mismatches."""
        artifact = artifacts["classification_case_a"]
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": artifact.model_bytes,
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": csv_bytes,
                },
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": "accuracy"},
            ]
        )
        assert response.status_code == 400, "feature count mismatch must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "csv_bytes",
        [
            # Empty CSV with no headers and no data rows.
            pytest.param(b"", id="empty_csv"),
            # Header only, which has zero data rows.
            pytest.param(
                b"feature_0,feature_1,target\n",
                id="header_only",
            ),
            # One data row, which is still fewer than two data rows.
            pytest.param(
                b"feature_0,feature_1,target\n1,2,0\n",
                id="single_data_row",
            ),
            # More than 1000 data rows.
            pytest.param(
                _write_eval_csv([[1, 2, index % 2] for index in range(1001)]),
                id="too_many_rows",
            ),
            # Missing feature value in one row.
            pytest.param(
                b"feature_0,feature_1,target\n1,,0\n2,3,1\n",
                id="missing_feature_value",
            ),
            # Missing eval value in one row.
            pytest.param(
                b"feature_0,feature_1,target\n1,2,\n2,3,1\n",
                id="missing_eval_value",
            ),
            # Non-numeric feature value.
            pytest.param(
                b"feature_0,feature_1,target\nabc,2,0\n2,3,1\n",
                id="non_numeric_feature",
            ),
            # Non-numeric eval value.
            pytest.param(
                b"feature_0,feature_1,target\n1,2,abc\n2,3,1\n",
                id="non_numeric_eval",
            ),
            # NaN feature value.
            pytest.param(
                b"feature_0,feature_1,target\nNaN,2,0\n2,3,1\n",
                id="nan_feature",
            ),
            # Positive infinity feature value.
            pytest.param(
                b"feature_0,feature_1,target\nInfinity,2,0\n2,3,1\n",
                id="positive_infinity_feature",
            ),
            # Negative infinity eval value.
            pytest.param(
                b"feature_0,feature_1,target\n1,2,-Infinity\n2,3,1\n",
                id="negative_infinity_eval",
            ),
            # Numeric text with surrounding junk.
            pytest.param(
                b"feature_0,feature_1,target\n12abc,2,0\n2,3,1\n",
                id="junk_numeric_text",
            ),
        ],
    )
    def test_csv_validation_rejects_empty_or_short_datasets(
        self, server, artifacts, csv_bytes
    ):
        """CSV validation rejects empty or short datasets."""
        artifact = artifacts["classification_case_a"]
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": artifact.model_bytes,
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": csv_bytes,
                },
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": "accuracy"},
            ]
        )
        assert response.status_code == 400, "invalid csv content must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "eval_column_part,csv_bytes",
        [
            # Missing eval_column field entirely.
            (None, b"feature_0,feature_1,target\n1,2,0\n2,3,1\n"),
            # Empty eval_column value.
            ("", b"feature_0,feature_1,target\n1,2,0\n2,3,1\n"),
            # eval_column does not exist in header.
            ("missing_target", b"feature_0,feature_1,target\n1,2,0\n2,3,1\n"),
            # eval_column is the only column (no feature columns).
            ("target", b"target\n0\n1\n"),
        ],
    )
    def test_eval_column_validation_rejects_invalid_values(
        self, server, artifacts, eval_column_part, csv_bytes
    ):
        """eval_column validation rejects invalid values."""
        artifact = artifacts["classification_case_a"]
        parts = [
            {
                "name": "files",
                "filename": "model.onnx",
                "content_type": "application/octet-stream",
                "body": artifact.model_bytes,
            },
            {
                "name": "files",
                "filename": "dataset.csv",
                "content_type": "text/csv",
                "body": csv_bytes,
            },
            {"name": "metric", "body": "accuracy"},
        ]
        if eval_column_part is not None:
            parts.append({"name": "eval_column", "body": eval_column_part})
        response = _post_eval(parts)
        assert response.status_code == 400, "invalid eval_column must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "metric_part",
        [
            None,  # Missing metric field entirely.
            "",  # Empty metric value.
            "mae",  # Unsupported metric value.
        ],
    )
    def test_metric_validation_rejects_invalid_values(
        self, server, artifacts, metric_part
    ):
        """Metric validation rejects invalid values."""
        artifact = artifacts["classification_case_a"]
        # Build a valid base multipart payload first (model + dataset + eval column).
        parts = [
            {
                "name": "files",
                "filename": "model.onnx",
                "content_type": "application/octet-stream",
                "body": artifact.model_bytes,
            },
            {
                "name": "files",
                "filename": "dataset.csv",
                "content_type": "text/csv",
                "body": artifact.csv_bytes,
            },
            {"name": "eval_column", "body": artifact.eval_column},
        ]
        # Add metric only when provided so the `None` case verifies missing metric handling.
        if metric_part is not None:
            parts.append({"name": "metric", "body": metric_part})
        # Submit the multipart form and confirm invalid metric variants are rejected.
        response = _post_eval(parts)
        assert response.status_code == 400, "invalid metric must return 400"
        _assert_no_success_payload(response)

    @pytest.mark.parametrize(
        "duplicate_field,field_values",
        [
            # Duplicate eval_column parts must be rejected.
            ("eval_column", ["target", "target"]),
            # Duplicate metric parts must be rejected.
            ("metric", ["accuracy", "accuracy"]),
        ],
    )
    def test_duplicate_text_fields_are_rejected(
        self, server, artifacts, duplicate_field, field_values
    ):
        """Duplicate eval form fields are rejected."""
        artifact = artifacts["classification_case_a"]
        parts = [
            {
                "name": "files",
                "filename": "model.onnx",
                "content_type": "application/octet-stream",
                "body": artifact.model_bytes,
            },
            {
                "name": "files",
                "filename": "dataset.csv",
                "content_type": "text/csv",
                "body": artifact.csv_bytes,
            },
        ]

        if duplicate_field == "eval_column":
            parts.extend(
                [
                    {"name": "metric", "body": "accuracy"},
                    # First eval_column part.
                    {"name": "eval_column", "body": field_values[0]},
                    # Second eval_column part.
                    {"name": "eval_column", "body": field_values[1]},
                ]
            )
        else:
            parts.extend(
                [
                    {"name": "eval_column", "body": artifact.eval_column},
                    # First metric part.
                    {"name": "metric", "body": field_values[0]},
                    # Second metric part.
                    {"name": "metric", "body": field_values[1]},
                ]
            )

        response = _post_eval(parts)
        assert response.status_code == 400, "duplicate field must return 400"
        _assert_no_success_payload(response)

    def test_more_than_two_files_rejects_even_when_extensions_look_valid(
        self, server, artifacts
    ):
        """More than two files rejects even with valid-looking files."""
        artifact = artifacts["classification_case_a"]
        response = _post_eval(
            [
                {
                    "name": "files",
                    "filename": "model.onnx",
                    "content_type": "application/octet-stream",
                    "body": artifact.model_bytes,
                },
                {
                    "name": "files",
                    "filename": "dataset.csv",
                    "content_type": "text/csv",
                    "body": artifact.csv_bytes,
                },
                {
                    "name": "files",
                    "filename": "extra.csv",
                    "content_type": "text/csv",
                    "body": artifact.csv_bytes,
                },
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": "accuracy"},
            ]
        )
        assert (
            response.status_code == 400
        ), "more than two uploaded files must return 400"
        _assert_no_success_payload(response)
