MLflow tracking contract

In /app/, you have implemented the "/eval" path in the API server. There, implement tracking using MLflow server in port MLFLOW_PORT. MLflow experiment name must be "model-evaluation". Note that if I start a new MLflow server, I may pass a different MLFLOW_PORT before starting the API server, so read MLFLOW_PORT value.

For every successful, not failed, POST /eval request, create exactly one MLflow run. Log only these MLFlow Params: dataset_size, eval_column, model_sha256, csv_sha256, metric. Log only this MLFlow Metric: score, which is the API score multiplied by 100 and stored as a percentage number. Note that dataset_size is the number of rows in the dataset, eval_column is the name of the column used for evaluation, model_sha256 is the sha256 hash of the model file, csv_sha256 is the sha256 hash of the csv file, and metric is the name of the metric used for evaluation. Run name must be "eval-<timestamp>", where timestamp is the Unix timestamp in seconds at the time the request is handled. Each MLflow run must be ended with FINISHED status after logging is complete.

"onnxruntime-node" and "@mlflow/core" packages are installed.
