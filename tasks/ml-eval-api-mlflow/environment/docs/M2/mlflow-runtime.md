MLflow runtime notes

MLflow is installed in /app/.venv/, which is activated. Start the MLflow server in the port in env variable MLFLOW_PORT in the background, and it should work even after terminal is closed.

Don't try to install anything as there is not internet. Beware of limited memory and don't start multiple workers in MLflow.

The Docker environment already has MLFLOW_PORT set, and a caller may also pass a different MLFLOW_PORT before starting the API server. Read the current MLFLOW_PORT value at API startup. The API server is still started from /app with "npm start" and must also keep using FASTIFY_PORT for its own HTTP port. Do not assume fixed MLFLOW_PORT or FASTIFY_PORT values instead of the existing environment values.
