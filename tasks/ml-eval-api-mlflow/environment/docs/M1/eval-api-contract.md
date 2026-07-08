Evaluation API contract

The POST /eval endpoint evaluates ML models and returns response in JSON in exact format: {"score": <numeric_value>}. Example numeric value is 0.9312. If a request is successful, use status code 200. If it's a bad request, use 400, including multipart parser errors.

Request has a multipart form with field "files" containing exactly 2 files: one .onnx model and one .csv eval dataset, with no extra files, no duplicate model/dataset files, no files under other field names, no path-like filenames containing /, backslash, .., null bytes, or control characters, and size limits of 100MB for .onnx and 25MB for .csv. Reject requests which don't meet the criteria.

Model may be of any type like classification type or regression type, so handle those. Use onnxruntime-node to load and run the ONNX model. If onnx file is invalid, or if it looks like ONNX but cannot actually be used by ONNX runtime for this request, reject it before scoring. This also means rejecting a model that creates a session but fails when inference is run. If the model input shape does not match CSV columns, reject it, including the case where eval_column is the only CSV column.

In CSV, if any row has a missing value, reject the request. If CSV is empty, has <2 data rows, or has >1000 data rows, reject it. In the form, "eval_column" and "metric" are mentioned. Eval column is the column that the model predicts. Rest of the columns are inputs to the model. If no eval column is provided or eval column is not in the file, reject the request. Reject the request if eval_column or metric appears more than once.

All the values must be finite numeric values only, not strings. Reject NaN, Infinity, -Infinity, empty cells, and values that are not a standalone numeric literal, like 12abc or abc12.

Supported metrics are accuracy, rmse, and f1. f1 is binary f1 only for binary classification tasks, and reject it for regression tasks. Do not rely on ONNX metadata alone to decide task type. For f1, use the CSV values and model outputs themselves and reject unless both are already exactly 0 or 1. For accuracy and binary f1, treat numeric truth/prediction outputs as labels by rounding to the nearest integer before scoring. For f1, only allow requests when the raw truth and prediction values are already exactly 0 or 1. Values that merely round to 0 or 1 must still be rejected. If empty or other values are passed, reject it.
