import csv
import difflib
import hashlib
import io
import json
import os
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypedDict, cast

import mlflow
import numpy as np
import onnx
import onnx.helper as oh
import onnx.numpy_helper as onh
import onnxruntime as ort
import pytest
import requests
from mlflow.entities import ViewType
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error

_APP_DIR = Path("/app")
_DEFAULT_MLFLOW_PORT = 5000
_REQUEST_TIMEOUT_SECONDS = 30
_START_TIMEOUT_SECONDS = 120
_BOUNDARY = "---------------------------pytest-m2-boundary"
_MODEL_FILENAME = "model.onnx"
_CSV_FILENAME = "dataset.csv"
_EXPERIMENT_NAME = "model-evaluation"
_EXPECTED_PARAM_KEYS = {
    "dataset_size",
    "eval_column",
    "model_sha256",
    "csv_sha256",
    "metric",
}
_EXPECTED_METRIC_KEYS = {"score"}


class _ExperimentSnapshot(TypedDict):
    name: str
    run_ids: set[str]


@dataclass(frozen=True)
class _EvalArtifact:
    csv_bytes: bytes
    dataset_size: int
    eval_column: str
    expected_scores: dict[str, float]
    feature_count: int
    model_bytes: bytes


@dataclass(frozen=True)
class _StartedServer:
    api_base_url: str
    fastify_port: int
    log_path: Path
    mlflow_port: int
    process: subprocess.Popen[str]
    tracking_uri: str


@dataclass(frozen=True)
class _ReferenceServer:
    api_base_url: str
    log_handle: io.TextIOWrapper
    mlflow_process: subprocess.Popen[str]
    mlflow_port: int
    server: ThreadingHTTPServer
    thread: threading.Thread
    tracking_uri: str


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http(
    url: str,
    process: subprocess.Popen[str],
    log_path: Path,
    expected_statuses: set[int] | None = None,
) -> None:
    deadline = time.time() + _START_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.time() < deadline:
        if process.poll() is not None:
            break
        try:
            response = requests.get(url, timeout=2, allow_redirects=False)
            if expected_statuses is None or response.status_code in expected_statuses:
                return
            last_error = AssertionError(
                f"unexpected status {response.status_code} for {url}"
            )
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(0.5)
    logs = log_path.read_text() if log_path.exists() else ""
    raise AssertionError(
        f"service did not become ready: {url}\n"
        f"returncode={process.poll()} last_error={last_error}\n"
        f"logs:\n{logs}"
    )


def _parse_multipart_bytes(
    body: bytes, boundary: str
) -> dict[str, list[tuple[dict[str, str], bytes]]]:
    parts: dict[str, list[tuple[dict[str, str], bytes]]] = {}
    delimiter = f"--{boundary}".encode()
    for raw_part in body.split(delimiter):
        if raw_part.startswith(b"\r\n"):
            raw_part = raw_part[2:]
        if raw_part.endswith(b"--\r\n"):
            raw_part = raw_part[:-4]
        elif raw_part.endswith(b"\r\n"):
            raw_part = raw_part[:-2]
        if not raw_part or raw_part == b"--":
            continue
        header_blob, separator, content = raw_part.partition(b"\r\n\r\n")
        if not separator:
            continue
        headers: dict[str, str] = {}
        for line in header_blob.decode("utf-8").split("\r\n"):
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
        disposition = headers.get("content-disposition", "")
        name = ""
        filename = ""
        for item in disposition.split(";"):
            item = item.strip()
            if item.startswith("name="):
                name = item[5:].strip('"')
            elif item.startswith("filename="):
                filename = item[9:].strip('"')
        if not name:
            continue
        headers["filename"] = filename
        if content.endswith(b"\r\n"):
            content = content[:-2]
        parts.setdefault(name, []).append((headers, content))
    return parts


def _terminate_process(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=20)


def _start_app_server(
    tmp_dir: Path,
    fastify_port: int,
    mlflow_port: int | None = None,
) -> _StartedServer:
    log_path = tmp_dir / f"npm-start-{fastify_port}.log"
    log_handle = log_path.open("w")
    env = os.environ | {
        "FASTIFY_PORT": str(fastify_port),
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
    }
    if mlflow_port is not None:
        env["MLFLOW_PORT"] = str(mlflow_port)
    process = subprocess.Popen(
        ["npm", "start"],
        cwd=_APP_DIR,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_http(
            f"http://127.0.0.1:{fastify_port}/health",
            process,
            log_path,
            expected_statuses={200},
        )
        resolved_mlflow_port = int(env.get("MLFLOW_PORT", os.environ["MLFLOW_PORT"]))
        _wait_for_http(
            f"http://127.0.0.1:{resolved_mlflow_port}/",
            process,
            log_path,
            expected_statuses={200, 301, 302, 303, 307, 308},
        )
        return _StartedServer(
            api_base_url=f"http://127.0.0.1:{fastify_port}",
            fastify_port=fastify_port,
            log_path=log_path,
            mlflow_port=resolved_mlflow_port,
            process=process,
            tracking_uri=f"http://127.0.0.1:{resolved_mlflow_port}",
        )
    except Exception:
        _terminate_process(process)
        log_handle.close()
        raise


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
        producer_name="pytest-m2",
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
        producer_name="pytest-m2",
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
    if metric == "accuracy":
        return float(accuracy_score(np.rint(truth).astype(int), np.rint(predictions)))
    if metric == "f1":
        return float(
            f1_score(np.rint(truth).astype(int), np.rint(predictions).astype(int))
        )
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
        csv_bytes=_write_eval_csv(csv_rows),
        dataset_size=int(eval_x.shape[0]),
        eval_column="target",
        expected_scores={
            metric: _compute_score(metric, eval_y.astype(float), predictions)
            for metric in ("accuracy", "f1", "rmse")
        },
        feature_count=int(eval_x.shape[1]),
        model_bytes=model_bytes,
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
        csv_bytes=_write_eval_csv(csv_rows),
        dataset_size=int(eval_x.shape[0]),
        eval_column="target",
        expected_scores={
            metric: _compute_score(metric, eval_y.astype(float), predictions)
            for metric in ("accuracy", "f1", "rmse")
        },
        feature_count=int(eval_x.shape[1]),
        model_bytes=model_bytes,
    )


def _encode_multipart(parts: list[dict[str, object]]) -> tuple[bytes, str]:
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
            assert isinstance(body, bytes), "multipart bytes must be bytes"
            chunks.append(body)
        chunks.append(b"\r\n")
    chunks.append(f"--{_BOUNDARY}--\r\n".encode())
    return b"".join(chunks), _BOUNDARY


def _post_eval(
    base_url: str,
    parts: list[dict[str, object]],
) -> requests.Response:
    body, boundary = _encode_multipart(parts)
    return requests.post(
        f"{base_url}/eval",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )


def _score_payload(response: requests.Response) -> dict[str, object]:
    payload = response.json()
    assert isinstance(payload, dict), "response must be a JSON object"
    assert set(payload) == {"score"}, "response must only contain score"
    assert isinstance(payload["score"], (int, float)), "score must be numeric"
    assert not isinstance(payload["score"], bool), "score must not be boolean"
    return payload


def _mlflow_root_response(base_url: str) -> requests.Response:
    return requests.get(
        f"{base_url}/",
        timeout=_REQUEST_TIMEOUT_SECONDS,
        allow_redirects=True,
    )


def _snapshot_runs(client: mlflow.MlflowClient) -> dict[str, _ExperimentSnapshot]:
    snapshot: dict[str, _ExperimentSnapshot] = {}
    for experiment in client.search_experiments(view_type=ViewType.ALL):
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=5000,
        )
        snapshot[experiment.experiment_id] = {
            "name": experiment.name,
            "run_ids": {run.info.run_id for run in runs},
        }
    return snapshot


def _new_runs(
    before: dict[str, _ExperimentSnapshot],
    after: dict[str, _ExperimentSnapshot],
) -> dict[str, _ExperimentSnapshot]:
    delta: dict[str, _ExperimentSnapshot] = {}
    for experiment_id, after_data in after.items():
        before_data = before.get(experiment_id)
        before_ids = (
            set() if before_data is None else cast(set[str], before_data["run_ids"])
        )
        current_ids = cast(set[str], after_data["run_ids"])
        new_run_ids = current_ids - before_ids
        if new_run_ids:
            delta[experiment_id] = {
                "name": cast(str, after_data["name"]),
                "run_ids": new_run_ids,
            }
    return delta


def _standalone_mlflow_command(port: int, store_dir: Path) -> list[str]:
    return [
        "/app/.venv/bin/mlflow",
        "server",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--workers",
        "1",
        "--backend-store-uri",
        f"sqlite:///{store_dir / 'backend' / 'mlflow.db'}",
        "--default-artifact-root",
        str(store_dir / "artifacts"),
    ]


def _start_mlflow_process(
    port: int, store_dir: Path, log_handle: io.TextIOWrapper, log_path: Path
) -> subprocess.Popen[str]:
    (store_dir / "backend").mkdir(parents=True, exist_ok=True)
    (store_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        _standalone_mlflow_command(port, store_dir),
        cwd=_APP_DIR,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.time() + _START_TIMEOUT_SECONDS
    while time.time() < deadline:
        if process.poll() is not None:
            break
        try:
            response = requests.get(
                f"http://127.0.0.1:{port}/",
                timeout=2,
                allow_redirects=True,
            )
            if response.status_code == 200:
                return process
        except requests.RequestException:
            pass
        time.sleep(0.5)
    logs = log_path.read_text() if log_path.exists() else ""
    process.poll()
    raise AssertionError(
        f"service did not become ready: http://127.0.0.1:{port}/\n"
        f"returncode={process.returncode}\n"
        f"logs:\n{logs}"
    )


def _assert_eval_run_name_in_window(
    run_name: str | None,
    request_started_at: int,
    request_finished_at: int,
) -> None:
    assert run_name is not None, "run name tag must exist"
    prefix, separator, timestamp_text = run_name.partition("-")
    assert prefix == "eval" and separator == "-", "run name must start with eval-"
    assert timestamp_text.isdigit(), "run timestamp must be unix seconds"
    timestamp = int(timestamp_text)
    assert (
        request_started_at <= timestamp <= request_finished_at
    ), "run timestamp must fall within the eval request window"


def _log_reference_mlflow_run(
    tracking_uri: str,
    artifact: _EvalArtifact,
    metric: str,
) -> None:
    previous_tracking_uri = mlflow.get_tracking_uri()
    try:
        mlflow.set_tracking_uri(tracking_uri)
        experiment_id = mlflow.set_experiment(_EXPERIMENT_NAME).experiment_id
        with mlflow.start_run(
            experiment_id=experiment_id,
            run_name=f"eval-{int(time.time())}",
        ):
            mlflow.log_params(
                {
                    "dataset_size": str(artifact.dataset_size),
                    "eval_column": artifact.eval_column,
                    "model_sha256": hashlib.sha256(artifact.model_bytes).hexdigest(),
                    "csv_sha256": hashlib.sha256(artifact.csv_bytes).hexdigest(),
                    "metric": metric,
                }
            )
            mlflow.log_metric(
                "score",
                round(float(artifact.expected_scores[metric]) * 100, 4),
            )
    finally:
        mlflow.set_tracking_uri(previous_tracking_uri)


def _start_reference_server(
    tmp_dir: Path,
    artifacts: dict[str, _EvalArtifact],
) -> _ReferenceServer:
    mlflow_port = _pick_free_port()
    log_path = tmp_dir / "reference-mlflow.log"
    log_handle = log_path.open("w")
    try:
        mlflow_process = _start_mlflow_process(
            mlflow_port, tmp_dir / "reference-store", log_handle, log_path
        )
        tracking_uri = f"http://127.0.0.1:{mlflow_port}"

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health":
                    body = b'{"status":"ok"}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/eval":
                    self.send_response(404)
                    self.end_headers()
                    return

                try:
                    content_type = self.headers.get("Content-Type", "")
                    boundary = ""
                    for part in content_type.split(";"):
                        part = part.strip()
                        if part.startswith("boundary="):
                            boundary = part.split("=", 1)[1].strip('"')
                            break
                    if not boundary:
                        self._send_json(
                            400,
                            {
                                "error": "Bad Request",
                                "message": "Missing multipart boundary",
                                "statusCode": 400,
                            },
                        )
                        return

                    content_length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(content_length)
                    parts = _parse_multipart_bytes(body, boundary)
                    metric_parts = parts.get("metric", [])
                    eval_column_parts = parts.get("eval_column", [])
                    files = parts.get("files", [])
                    metric = metric_parts[0][1].decode("utf-8") if metric_parts else ""
                    eval_column = (
                        eval_column_parts[0][1].decode("utf-8")
                        if eval_column_parts
                        else ""
                    )

                    model_bytes = b""
                    csv_bytes = b""
                    for headers, item_bytes in files:
                        filename = headers.get("filename", "")
                        if filename.endswith(".onnx"):
                            model_bytes = item_bytes
                        if filename.endswith(".csv"):
                            csv_bytes = item_bytes

                    if (
                        not model_bytes
                        or not csv_bytes
                        or not metric
                        or not eval_column
                    ):
                        self._send_json(
                            400,
                            {
                                "error": "Bad Request",
                                "message": "Missing eval inputs",
                                "statusCode": 400,
                            },
                        )
                        return

                    artifact = next(
                        (
                            current
                            for current in artifacts.values()
                            if current.model_bytes == model_bytes
                            and current.csv_bytes == csv_bytes
                            and current.eval_column == eval_column
                        ),
                        None,
                    )
                    if artifact is None or metric not in artifact.expected_scores:
                        self._send_json(
                            400,
                            {
                                "error": "Bad Request",
                                "message": "Unsupported eval payload",
                                "statusCode": 400,
                            },
                        )
                        return

                    _log_reference_mlflow_run(tracking_uri, artifact, metric)
                    self._send_json(200, {"score": artifact.expected_scores[metric]})
                except Exception as exc:
                    self._send_json(
                        500,
                        {
                            "error": "Internal Server Error",
                            "message": str(exc),
                            "statusCode": 500,
                        },
                    )

            def log_message(self, format: str, *args: object) -> None:
                return

            def _send_json(self, status_code: int, payload: dict[str, object]) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        port = _pick_free_port()
        server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return _ReferenceServer(
            api_base_url=f"http://127.0.0.1:{port}",
            log_handle=log_handle,
            mlflow_process=mlflow_process,
            mlflow_port=mlflow_port,
            server=server,
            thread=thread,
            tracking_uri=tracking_uri,
        )
    except Exception:
        log_handle.close()
        raise


@pytest.fixture(scope="class")
def artifacts() -> dict[str, _EvalArtifact]:
    classification = _build_classification_artifact(
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
    regression = _build_regression_artifact(
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
    return {"classification": classification, "regression": regression}


@pytest.fixture(scope="class")
def reference_server(
    tmp_path_factory: pytest.TempPathFactory,
    artifacts: dict[str, _EvalArtifact],
):
    tmp_dir = tmp_path_factory.mktemp("m2-reference-server")
    started = _start_reference_server(tmp_dir, artifacts)
    try:
        yield started
    finally:
        started.server.shutdown()
        started.server.server_close()
        _terminate_process(started.mlflow_process)
        started.log_handle.close()


@pytest.fixture(scope="class")
def server(tmp_path_factory: pytest.TempPathFactory):
    tmp_dir = tmp_path_factory.mktemp("m2-default-server")
    started = _start_app_server(tmp_dir, fastify_port=_pick_free_port())
    try:
        yield started
    finally:
        _terminate_process(started.process)


@pytest.fixture()
def custom_mlflow_server(tmp_path: Path):
    port = _pick_free_port()
    log_path = tmp_path / "custom-mlflow.log"
    log_handle = log_path.open("w")
    process: subprocess.Popen[str] | None = None
    try:
        process = _start_mlflow_process(port, tmp_path, log_handle, log_path)
        yield {
            "log_path": log_path,
            "port": port,
            "process": process,
            "tracking_uri": f"http://127.0.0.1:{port}",
        }
    finally:
        if process is not None:
            _terminate_process(process)
        log_handle.close()


class TestMilestone2:
    def test_mlflow_get_root_content_matches(self, custom_mlflow_server):
        """MLflow's GET / of agents' server matches a custom server started here."""
        assert os.environ.get("MLFLOW_PORT") == str(
            _DEFAULT_MLFLOW_PORT
        ), f"MLFLOW_PORT must stay {_DEFAULT_MLFLOW_PORT}"

        # This tests that MLFlow instance survived beyond the closure of agent's terminal session.
        submitted_root = _mlflow_root_response(
            f"http://127.0.0.1:{_DEFAULT_MLFLOW_PORT}"
        )
        reference_root = _mlflow_root_response(custom_mlflow_server["tracking_uri"])
        similarity = difflib.SequenceMatcher(
            None, submitted_root.text, reference_root.text
        ).ratio()

        assert submitted_root.status_code == 200, "submitted MLflow root must work"
        assert reference_root.status_code == 200, "reference MLflow root must work"
        assert (
            similarity >= 0.95
        ), "MLflow root content must match the standalone server closely"

    def test_server_starts_with_npm_start(self, server):
        """npm start keeps API and MLflow reachable."""
        assert server.process.poll() is None, "npm start exited unexpectedly"

        api_response = requests.get(
            f"{server.api_base_url}/health", timeout=_REQUEST_TIMEOUT_SECONDS
        )
        assert api_response.status_code == 200, "health must return 200"

    @pytest.mark.parametrize(
        ("artifact_name", "metric"),
        [
            # Classification coverage for accuracy.
            ("classification", "accuracy"),
            # Classification coverage for F1.
            ("classification", "f1"),
            # Regression coverage for RMSE.
            ("regression", "rmse"),
        ],
    )
    def test_successful_eval_logs_expected_mlflow_run(
        self, server, artifacts, artifact_name, metric
    ):
        """Successful eval on the submitted server logs one matching MLflow run."""
        artifact = artifacts[artifact_name]
        client = mlflow.MlflowClient(tracking_uri=server.tracking_uri)
        before = _snapshot_runs(client)
        request_started_at = int(time.time())

        response = _post_eval(
            server.api_base_url,
            [
                {
                    "name": "files",
                    "filename": _MODEL_FILENAME,
                    "content_type": "application/octet-stream",
                    "body": artifact.model_bytes,
                },
                {
                    "name": "files",
                    "filename": _CSV_FILENAME,
                    "content_type": "text/csv",
                    "body": artifact.csv_bytes,
                },
                {"name": "eval_column", "body": artifact.eval_column},
                {"name": "metric", "body": metric},
            ],
        )
        request_finished_at = int(time.time())
        payload = _score_payload(response)
        assert response.status_code == 200, "eval must succeed"
        assert payload["score"] == pytest.approx(
            artifact.expected_scores[metric], abs=1e-4
        ), "API score must match local evaluation"

        experiment = client.get_experiment_by_name(_EXPERIMENT_NAME)
        assert experiment is not None, "model-evaluation experiment must exist"

        after = _snapshot_runs(client)
        new_runs = _new_runs(before, after)
        other_experiment_new_runs = sum(
            len(cast(set[str], data["run_ids"]))
            for data in new_runs.values()
            if cast(str, data["name"]) != _EXPERIMENT_NAME
        )
        assert other_experiment_new_runs == 0, "other experiments must stay unchanged"

        experiment_delta = new_runs.get(experiment.experiment_id)
        assert experiment_delta is not None, "model-evaluation must receive the new run"
        assert (
            len(cast(set[str], experiment_delta["run_ids"])) == 1
        ), "exactly one run must be created"

        run_id = next(iter(cast(set[str], experiment_delta["run_ids"])))
        run = client.get_run(run_id)
        assert (
            run.info.experiment_id == experiment.experiment_id
        ), "run must belong to model-evaluation"
        assert run.info.status == "FINISHED", "run must end with FINISHED status"

        _assert_eval_run_name_in_window(
            run.data.tags.get("mlflow.runName"),
            request_started_at,
            request_finished_at,
        )

        params = run.data.params
        assert (
            set(params) == _EXPECTED_PARAM_KEYS
        ), "only expected params must be logged"
        assert params["dataset_size"] == str(
            artifact.dataset_size
        ), "dataset_size must match request CSV"
        assert (
            params["eval_column"] == artifact.eval_column
        ), "eval_column must match request"
        assert params["metric"] == metric, "metric must match request"
        assert (
            params["model_sha256"] == hashlib.sha256(artifact.model_bytes).hexdigest()
        ), "model_sha256 must match request model"
        assert (
            params["csv_sha256"] == hashlib.sha256(artifact.csv_bytes).hexdigest()
        ), "csv_sha256 must match request csv"

        metrics = run.data.metrics
        assert set(metrics) == _EXPECTED_METRIC_KEYS, "only score metric must be logged"
        assert metrics["score"] == pytest.approx(
            float(cast(float, payload["score"])) * 100,
            abs=1e-2,
        ), "MLflow score must be the API score percentage"

    # Edge cases aligned with the milestone requirements.

    def test_invalid_request_does_not_create_mlflow_run(self, server):
        """Invalid eval must not create an MLflow run."""
        client = mlflow.MlflowClient(tracking_uri=server.tracking_uri)
        before = _snapshot_runs(client)

        response = _post_eval(
            server.api_base_url,
            [
                {"name": "eval_column", "body": "target"},
                {"name": "metric", "body": "accuracy"},
            ],
        )

        assert response.status_code == 400, "invalid request must return 400"
        after = _snapshot_runs(client)
        assert _new_runs(before, after) == {}, "failed request must not create runs"

    def test_submitted_server_matches_reference_response(
        self, server, reference_server, artifacts
    ):
        """Submitted server must match the reference eval response."""
        artifact = artifacts["classification"]
        parts = [
            {
                "name": "files",
                "filename": _MODEL_FILENAME,
                "content_type": "application/octet-stream",
                "body": artifact.model_bytes,
            },
            {
                "name": "files",
                "filename": _CSV_FILENAME,
                "content_type": "text/csv",
                "body": artifact.csv_bytes,
            },
            {"name": "eval_column", "body": artifact.eval_column},
            {"name": "metric", "body": "accuracy"},
        ]
        submitted_response = _post_eval(server.api_base_url, parts)
        reference_response = _post_eval(reference_server.api_base_url, parts)

        assert submitted_response.status_code == 200, "submitted eval must succeed"
        assert reference_response.status_code == 200, "reference eval must succeed"
        assert _score_payload(submitted_response)["score"] == pytest.approx(
            _score_payload(reference_response)["score"],
            abs=1e-4,
        ), "submitted score must match reference"

    def test_temporary_mlflow_port_override_is_used(
        self, tmp_path: Path, artifacts, custom_mlflow_server
    ):
        """Temporary MLFLOW_PORT override must redirect logging."""
        fastify_port = _pick_free_port()
        original_port = os.environ.get("MLFLOW_PORT")
        server = _start_app_server(
            tmp_path,
            fastify_port=fastify_port,
            mlflow_port=custom_mlflow_server["port"],
        )
        default_client = mlflow.MlflowClient(
            tracking_uri=f"http://127.0.0.1:{_DEFAULT_MLFLOW_PORT}"
        )
        custom_client = mlflow.MlflowClient(
            tracking_uri=custom_mlflow_server["tracking_uri"]
        )
        default_before = _snapshot_runs(default_client)
        custom_before = _snapshot_runs(custom_client)

        artifact = artifacts["classification"]
        try:
            request_started_at = int(time.time())
            response = _post_eval(
                server.api_base_url,
                [
                    {
                        "name": "files",
                        "filename": _MODEL_FILENAME,
                        "content_type": "application/octet-stream",
                        "body": artifact.model_bytes,
                    },
                    {
                        "name": "files",
                        "filename": _CSV_FILENAME,
                        "content_type": "text/csv",
                        "body": artifact.csv_bytes,
                    },
                    {"name": "eval_column", "body": artifact.eval_column},
                    {"name": "metric", "body": "accuracy"},
                ],
            )
            request_finished_at = int(time.time())
            assert response.status_code == 200, "eval must succeed with custom port"
            payload = _score_payload(response)
            assert payload["score"] == pytest.approx(
                artifact.expected_scores["accuracy"], abs=1e-4
            ), "API score must match local evaluation"

            default_after = _snapshot_runs(default_client)
            custom_after = _snapshot_runs(custom_client)
            assert (
                _new_runs(default_before, default_after) == {}
            ), "default MLflow server must stay unchanged"

            custom_delta = _new_runs(custom_before, custom_after)
            custom_experiment = custom_client.get_experiment_by_name(_EXPERIMENT_NAME)
            assert (
                custom_experiment is not None
            ), "custom MLflow must get the experiment"
            assert (
                custom_experiment.experiment_id in custom_delta
            ), "custom MLflow must receive the new run"
            assert (
                len(
                    cast(
                        set[str],
                        custom_delta[custom_experiment.experiment_id]["run_ids"],
                    )
                )
                == 1
            ), "custom MLflow must receive exactly one new run"

            run_id = next(
                iter(
                    cast(
                        set[str],
                        custom_delta[custom_experiment.experiment_id]["run_ids"],
                    )
                )
            )
            run = custom_client.get_run(run_id)
            assert (
                run.info.experiment_id == custom_experiment.experiment_id
            ), "run must belong to the custom experiment"
            assert run.info.status == "FINISHED", "run must end with FINISHED status"

            _assert_eval_run_name_in_window(
                run.data.tags.get("mlflow.runName"),
                request_started_at,
                request_finished_at,
            )

            params = run.data.params
            assert (
                set(params) == _EXPECTED_PARAM_KEYS
            ), "only expected params must be logged"
            assert params["dataset_size"] == str(
                artifact.dataset_size
            ), "dataset_size must match request CSV"
            assert (
                params["eval_column"] == artifact.eval_column
            ), "eval_column must match request"
            assert params["metric"] == "accuracy", "metric must match request"
            assert (
                params["model_sha256"]
                == hashlib.sha256(artifact.model_bytes).hexdigest()
            ), "model_sha256 must match request model"
            assert (
                params["csv_sha256"] == hashlib.sha256(artifact.csv_bytes).hexdigest()
            ), "csv_sha256 must match request csv"

            metrics = run.data.metrics
            assert (
                set(metrics) == _EXPECTED_METRIC_KEYS
            ), "only score metric must be logged"
            assert metrics["score"] == pytest.approx(
                float(cast(float, payload["score"])) * 100,
                abs=1e-2,
            ), "MLflow score must be the API score percentage"
        finally:
            _terminate_process(server.process)
            assert (
                os.environ.get("MLFLOW_PORT") == original_port
            ), "parent MLFLOW_PORT must stay unchanged"
