#!/usr/bin/env bash

set -euo pipefail

mkdir -p /tmp/mlflow/backend
mkdir -p /tmp/mlflow/artifacts
# /app/.venv is already activated through Dockerfile
nohup mlflow server \
  --host 127.0.0.1 \
  --port "${MLFLOW_PORT}" \
  --workers 1 \
  --backend-store-uri "sqlite:////tmp/mlflow/backend/mlflow.db" \
  --default-artifact-root "/tmp/mlflow/artifacts" \
  >/tmp/mlflow-server.log 2>&1 &

# Wait for the server to start.
for _ in $(seq 1 240); do
    if curl -fsS -o /dev/null -w '' http://127.0.0.1:${MLFLOW_PORT}/ >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done
if ! curl -fsS -o /dev/null -w '' http://127.0.0.1:${MLFLOW_PORT}/ >/dev/null 2>&1; then
    echo "Backend failed to start within expected time. Backend log:"
    cat /tmp/mlflow-server.log >&2 || true
    exit 1
fi
sleep 2  # Give the server a moment to finish accepting requests.

mkdir -p /app/src/plugins

cat <<'EOF' > /app/src/plugins/eval.plugin.ts
import { createHash } from 'node:crypto';
import { extname } from 'node:path';
import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { createAuthProvider } from '@mlflow/core/dist/auth';
import { MlflowClient } from '@mlflow/core';
import { InferenceSession, Tensor } from 'onnxruntime-node';

type MultipartPart = {
	contentType?: string;
	data: Buffer;
	filename?: string;
	headers: Record<string, string>;
	name?: string;
};

type CsvData = {
	evalValues: number[];
	featureRows: number[][];
};

type EvaluationResult = {
	datasetSize: number;
	score: number;
};

type MlflowRunData = {
	csvSha256: string;
	datasetSize: number;
	evalColumn: string;
	metric: string;
	modelSha256: string;
	score: number;
};

const SUPPORTED_METRICS = new Set(['accuracy', 'rmse', 'f1']);
const MAX_ONNX_FILE_BYTES = 100 * 1024 * 1024;
const MAX_CSV_FILE_BYTES = 25 * 1024 * 1024;
const MAX_MULTIPART_BODY_BYTES = 130 * 1024 * 1024;
const MAX_CSV_DATA_ROWS = 1000;
const MLFLOW_EXPERIMENT_NAME = 'model-evaluation';

function buildError(message: string, statusCode: number): Error {
	const error = new Error(message) as Error & { statusCode: number };
	error.statusCode = statusCode;
	return error;
}

function badRequest(message: string): Error {
	return buildError(message, 400);
}

function internalError(message: string): Error {
	return buildError(message, 500);
}

function validateFilename(filename: string): void {
	if (
		filename.includes('/') ||
		filename.includes('\\') ||
		filename.includes('..') ||
		/[\x00-\x1F\x7F]/.test(filename)
	) {
		throw badRequest('Uploaded filenames must not be path-like');
	}
}

function getBoundary(contentType: string | undefined): string {
	if (!contentType?.startsWith('multipart/form-data')) {
		throw badRequest('Request must be multipart/form-data');
	}

	const match = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i);
	const boundary = match?.[1] ?? match?.[2];

	if (!boundary) {
		throw badRequest('Missing multipart boundary');
	}

	return boundary;
}

async function readRequestBody(request: FastifyRequest): Promise<Buffer> {
	const chunks: Buffer[] = [];

	for await (const chunk of request.raw) {
		chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
	}

	return Buffer.concat(chunks);
}

function parseHeaders(rawHeaders: string): Record<string, string> {
	const headers: Record<string, string> = {};

	for (const line of rawHeaders.split('\r\n')) {
		const separatorIndex = line.indexOf(':');
		if (separatorIndex === -1) {
			continue;
		}

		const name = line.slice(0, separatorIndex).trim().toLowerCase();
		const value = line.slice(separatorIndex + 1).trim();
		headers[name] = value;
	}

	return headers;
}

function parseMultipart(body: Buffer, boundary: string): MultipartPart[] {
	const delimiter = Buffer.from(`--${boundary}`);
	const parts: MultipartPart[] = [];
	let cursor = 0;

	while (true) {
		const boundaryIndex = body.indexOf(delimiter, cursor);
		if (boundaryIndex === -1) {
			break;
		}

		let sectionStart = boundaryIndex + delimiter.length;
		const closingMarker = body
			.subarray(sectionStart, sectionStart + 2)
			.toString('utf8');

		if (closingMarker === '--') {
			break;
		}

		if (
			body.subarray(sectionStart, sectionStart + 2).toString('utf8') !==
			'\r\n'
		) {
			throw badRequest('Malformed multipart payload');
		}
		sectionStart += 2;

		const headerEnd = body.indexOf(Buffer.from('\r\n\r\n'), sectionStart);
		if (headerEnd === -1) {
			throw badRequest('Malformed multipart payload');
		}

		const headers = parseHeaders(
			body.toString('utf8', sectionStart, headerEnd),
		);
		const contentDisposition = headers['content-disposition'];
		if (!contentDisposition) {
			throw badRequest('Malformed multipart payload');
		}

		const nextBoundary = body.indexOf(
			Buffer.from(`\r\n--${boundary}`),
			headerEnd + 4,
		);
		if (nextBoundary === -1) {
			throw badRequest('Malformed multipart payload');
		}

		const nameMatch = contentDisposition.match(/name="([^"]+)"/i);
		const filenameMatch = contentDisposition.match(/filename="([^"]*)"/i);

		parts.push({
			contentType: headers['content-type'],
			data: body.subarray(headerEnd + 4, nextBoundary),
			filename: filenameMatch?.[1],
			headers,
			name: nameMatch?.[1],
		});

		cursor = nextBoundary + 2;
	}

	return parts;
}

function parseCsv(text: string): string[][] {
	const rows: string[][] = [];
	let currentField = '';
	let currentRow: string[] = [];
	let inQuotes = false;

	for (let index = 0; index < text.length; index += 1) {
		const char = text[index];

		if (inQuotes) {
			if (char === '"') {
				if (text[index + 1] === '"') {
					currentField += '"';
					index += 1;
				} else {
					inQuotes = false;
				}
			} else {
				currentField += char;
			}
			continue;
		}

		if (char === '"') {
			inQuotes = true;
			continue;
		}

		if (char === ',') {
			currentRow.push(currentField);
			currentField = '';
			continue;
		}

		if (char === '\r') {
			continue;
		}

		if (char === '\n') {
			currentRow.push(currentField);
			rows.push(currentRow);
			currentField = '';
			currentRow = [];
			continue;
		}

		currentField += char;
	}

	if (inQuotes) {
		throw badRequest('Malformed CSV');
	}

	if (currentField.length > 0 || currentRow.length > 0) {
		currentRow.push(currentField);
		rows.push(currentRow);
	}

	return rows.filter((row) => row.some((cell) => cell !== ''));
}

function parseFiniteNumber(rawValue: string): number {
	const numericValue = Number(rawValue);
	if (!Number.isFinite(numericValue)) {
		throw badRequest('CSV values must be finite numbers');
	}

	return numericValue;
}

function parseNumericCsv(csvBuffer: Buffer, evalColumn: string): CsvData {
	const csvText = csvBuffer.toString('utf8').replace(/^\uFEFF/, '');
	if (csvText.trim() === '') {
		throw badRequest('CSV file is empty');
	}

	const rows = parseCsv(csvText);
	const [header, ...dataRows] = rows;
	if (header.length === 0) {
		throw badRequest('CSV header is required');
	}
	if (dataRows.length < 2) {
		throw badRequest(
			'CSV must include a header and at least two data rows',
		);
	}
	if (dataRows.length > MAX_CSV_DATA_ROWS) {
		throw badRequest('CSV must not contain more than 1000 data rows');
	}

	const trimmedHeader = header.map((cell) => cell.trim());
	const evalIndex = trimmedHeader.indexOf(evalColumn);
	if (evalIndex === -1) {
		throw badRequest('eval_column must match a CSV column');
	}

	if (trimmedHeader.length < 2) {
		throw badRequest('CSV must include at least one feature column');
	}

	const featureRows: number[][] = [];
	const evalValues: number[] = [];

	for (const row of dataRows) {
		if (row.length !== trimmedHeader.length) {
			throw badRequest('CSV rows must have a value for every column');
		}

		const features: number[] = [];

		for (let index = 0; index < row.length; index += 1) {
			const rawValue = row[index]?.trim();
			if (!rawValue) {
				throw badRequest('CSV contains missing values');
			}

			const numericValue = parseFiniteNumber(rawValue);

			if (index === evalIndex) {
				evalValues.push(numericValue);
			} else {
				features.push(numericValue);
			}
		}

		if (features.length === 0) {
			throw badRequest('CSV must include at least one feature column');
		}

		featureRows.push(features);
	}

	return { evalValues, featureRows };
}

function validateInputShape(
	session: InferenceSession,
	inputName: string,
	featureCount: number,
): void {
	const metadata = session.inputMetadata as unknown as Record<
		string,
		{ dimensions?: Array<number | string | null | undefined> }
	>;
	const metadataEntry = metadata[inputName];
	const dimensions = metadataEntry?.dimensions ?? [];
	const trailingDimension = dimensions[dimensions.length - 1];

	if (
		typeof trailingDimension === 'number' &&
		trailingDimension > 0 &&
		trailingDimension !== featureCount
	) {
		throw badRequest('Model input shape does not match CSV columns');
	}
}

function flattenRows(rows: number[][]): Float32Array {
	const flattened = new Float32Array(rows.length * rows[0].length);
	let offset = 0;

	for (const row of rows) {
		for (const value of row) {
			flattened[offset] = value;
			offset += 1;
		}
	}

	return flattened;
}

function tensorDataToNumbers(data: Tensor['data']): number[] {
	if (Array.isArray(data)) {
		return data.map((value) => Number(value));
	}

	return Array.from(data as ArrayLike<number | bigint>, (value) =>
		Number(value),
	);
}

function argMaxByRow(
	values: number[],
	rowCount: number,
	columnCount: number,
): number[] {
	const predictions: number[] = [];

	for (let rowIndex = 0; rowIndex < rowCount; rowIndex += 1) {
		let bestIndex = 0;
		let bestValue = Number.NEGATIVE_INFINITY;

		for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
			const value = values[rowIndex * columnCount + columnIndex];
			if (value > bestValue) {
				bestValue = value;
				bestIndex = columnIndex;
			}
		}

		predictions.push(bestIndex);
	}

	return predictions;
}

function getPredictions(
	outputs: Record<string, Tensor>,
	rowCount: number,
): number[] {
	const entries = Object.entries(outputs);
	const scalarCandidates: { name: string; values: number[] }[] = [];
	const matrixCandidates: {
		name: string;
		values: number[];
		width: number;
	}[] = [];

	for (const [name, tensor] of entries) {
		const dimensions = tensor.dims;
		const values = tensorDataToNumbers(tensor.data);

		if (dimensions.length === 1 && dimensions[0] === rowCount) {
			scalarCandidates.push({ name, values });
			continue;
		}

		if (
			dimensions.length === 2 &&
			dimensions[0] === rowCount &&
			dimensions[1] === 1
		) {
			scalarCandidates.push({ name, values });
			continue;
		}

		if (
			dimensions.length === 2 &&
			dimensions[0] === rowCount &&
			typeof dimensions[1] === 'number' &&
			dimensions[1] > 1
		) {
			matrixCandidates.push({ name, values, width: dimensions[1] });
		}
	}

	const preferredScalar = scalarCandidates.find(({ name }) =>
		/(label|pred)/i.test(name),
	);
	if (preferredScalar) {
		return preferredScalar.values;
	}

	if (scalarCandidates.length > 0) {
		return scalarCandidates[0].values;
	}

	const preferredMatrix = matrixCandidates.find(({ name }) =>
		/(prob|score|logit)/i.test(name),
	);
	if (preferredMatrix) {
		return argMaxByRow(
			preferredMatrix.values,
			rowCount,
			preferredMatrix.width,
		);
	}

	if (matrixCandidates.length > 0) {
		return argMaxByRow(
			matrixCandidates[0].values,
			rowCount,
			matrixCandidates[0].width,
		);
	}

	throw badRequest('Model output format is unsupported');
}

function calculateAccuracy(actual: number[], predicted: number[]): number {
	let matches = 0;

	for (let index = 0; index < actual.length; index += 1) {
		const actualLabel = Math.round(actual[index]);
		const predictedLabel = Math.round(predicted[index]);
		if (actualLabel === predictedLabel) {
			matches += 1;
		}
	}

	return matches / actual.length;
}

function calculateRmse(actual: number[], predicted: number[]): number {
	let squaredError = 0;

	for (let index = 0; index < actual.length; index += 1) {
		const delta = actual[index] - predicted[index];
		squaredError += delta * delta;
	}

	return Math.sqrt(squaredError / actual.length);
}

function calculateF1(actual: number[], predicted: number[]): number {
	const normalizedActual = actual.map((value) => Math.round(value));
	const normalizedPredicted = predicted.map((value) => Math.round(value));
	const labels = Array.from(
		new Set([...normalizedActual, ...normalizedPredicted]),
	);
	let scoreSum = 0;

	for (const label of labels) {
		let truePositive = 0;
		let falsePositive = 0;
		let falseNegative = 0;

		for (let index = 0; index < normalizedActual.length; index += 1) {
			if (
				normalizedPredicted[index] === label &&
				normalizedActual[index] === label
			) {
				truePositive += 1;
			} else if (
				normalizedPredicted[index] === label &&
				normalizedActual[index] !== label
			) {
				falsePositive += 1;
			} else if (
				normalizedPredicted[index] !== label &&
				normalizedActual[index] === label
			) {
				falseNegative += 1;
			}
		}

		const precision =
			truePositive + falsePositive === 0
				? 0
				: truePositive / (truePositive + falsePositive);
		const recall =
			truePositive + falseNegative === 0
				? 0
				: truePositive / (truePositive + falseNegative);

		const labelScore =
			precision + recall === 0
				? 0
				: (2 * precision * recall) / (precision + recall);
		scoreSum += labelScore;
	}

	return scoreSum / labels.length;
}

function isBinaryLabels(values: number[]): boolean {
	return values.every((value) => value === 0 || value === 1);
}

function roundScore(score: number): number {
	return Number(score.toFixed(4));
}

async function evaluateModel(
	modelBuffer: Buffer,
	csvBuffer: Buffer,
	evalColumn: string,
	metric: string,
): Promise<EvaluationResult> {
	const { evalValues, featureRows } = parseNumericCsv(csvBuffer, evalColumn);
	const input = flattenRows(featureRows);

	let session: InferenceSession;
	try {
		session = await InferenceSession.create(new Uint8Array(modelBuffer));
	} catch {
		throw badRequest('Invalid ONNX model');
	}

	const inputName = session.inputNames[0];
	if (!inputName) {
		throw badRequest('Model must expose at least one input');
	}

	validateInputShape(session, inputName, featureRows[0].length);

	let outputs: Record<string, Tensor>;
	try {
		outputs = await session.run({
			[inputName]: new Tensor('float32', input, [
				featureRows.length,
				featureRows[0].length,
			]),
		});
	} catch {
		throw badRequest('Model inference failed');
	}

	const predictions = getPredictions(outputs, featureRows.length);
	if (predictions.length !== evalValues.length) {
		throw badRequest('Model output shape does not match CSV rows');
	}

	if (metric === 'accuracy') {
		return {
			datasetSize: featureRows.length,
			score: roundScore(calculateAccuracy(evalValues, predictions)),
		};
	}

	if (metric === 'rmse') {
		return {
			datasetSize: featureRows.length,
			score: roundScore(calculateRmse(evalValues, predictions)),
		};
	}

	if (!isBinaryLabels(evalValues) || !isBinaryLabels(predictions)) {
		throw badRequest(
			'Binary f1 is only supported for binary classification',
		);
	}

	return {
		datasetSize: featureRows.length,
		score: roundScore(calculateF1(evalValues, predictions)),
	};
}

function identifyFiles(parts: MultipartPart[]): {
	csvBuffer: Buffer;
	modelBuffer: Buffer;
} {
	const fileParts = parts.filter((part) => part.filename !== undefined);

	if (fileParts.length !== 2) {
		throw badRequest(
			'The "files" field must contain exactly one ONNX file and one CSV file',
		);
	}

	if (fileParts.some((part) => part.name !== 'files')) {
		throw badRequest('Files must be sent in the "files" field');
	}

	let modelBuffer: Buffer | undefined;
	let csvBuffer: Buffer | undefined;

	for (const part of fileParts) {
		const filename = part.filename ?? '';
		validateFilename(filename);
		const extension = extname(filename).toLowerCase();
		if (extension === '.onnx') {
			if (modelBuffer) {
				throw badRequest('Only one ONNX file is allowed');
			}
			if (part.data.length > MAX_ONNX_FILE_BYTES) {
				throw badRequest('ONNX file exceeds the 100MB size limit');
			}
			modelBuffer = part.data;
			continue;
		}

		if (extension === '.csv') {
			if (csvBuffer) {
				throw badRequest('Only one CSV file is allowed');
			}
			if (part.data.length > MAX_CSV_FILE_BYTES) {
				throw badRequest('CSV file exceeds the 25MB size limit');
			}
			csvBuffer = part.data;
			continue;
		}

		throw badRequest('Unsupported file type');
	}

	if (!modelBuffer || !csvBuffer) {
		throw badRequest(
			'The "files" field must contain exactly one ONNX file and one CSV file',
		);
	}

	return { csvBuffer, modelBuffer };
}

function getTextField(parts: MultipartPart[], fieldName: string): string {
	const matches = parts.filter(
		(part) => part.filename === undefined && part.name === fieldName,
	);

	if (matches.length > 1) {
		throw badRequest(`${fieldName} must appear exactly once`);
	}

	const value = matches[matches.length - 1]?.data.toString('utf8').trim();

	if (!value) {
		throw badRequest(`${fieldName} is required`);
	}

	return value;
}

function getMetric(parts: MultipartPart[]): string {
	const metric = getTextField(parts, 'metric').toLowerCase();
	if (!SUPPORTED_METRICS.has(metric)) {
		throw badRequest('Unsupported metric');
	}

	return metric;
}

function parseJsonResponse(text: string): Record<string, unknown> {
	if (!text) {
		return {};
	}

	try {
		return JSON.parse(text) as Record<string, unknown>;
	} catch {
		throw internalError('MLflow returned an invalid response');
	}
}

let mlflowClient: MlflowClient | undefined;
let mlflowExperimentId: string | undefined;

function getMlflowBaseUrl(): string {
	const port = process.env.MLFLOW_PORT?.trim();
	if (!port) {
		throw internalError('MLflow port is not configured');
	}

	return `http://127.0.0.1:${port}`;
}

function getMlflowClient(): MlflowClient {
	if (!mlflowClient) {
		const trackingUri = getMlflowBaseUrl();
		mlflowClient = new MlflowClient({
			trackingUri,
			authProvider: createAuthProvider({ trackingUri }),
		});
	}

	return mlflowClient;
}

async function mlflowPost(
	path: string,
	payload: Record<string, unknown>,
): Promise<Record<string, unknown>> {
	const response = await fetch(`${getMlflowBaseUrl()}${path}`, {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify(payload),
	});
	const data = parseJsonResponse(await response.text());

	if (!response.ok) {
		const message =
			typeof data.message === 'string'
				? data.message
				: 'MLflow request failed';
		throw internalError(message);
	}

	return data;
}

async function getMlflowExperimentByName(
	experimentName: string,
): Promise<string | undefined> {
	const url = new URL(
		'/api/2.0/mlflow/experiments/get-by-name',
		getMlflowBaseUrl(),
	);
	url.searchParams.set('experiment_name', experimentName);

	const response = await fetch(url);
	const data = parseJsonResponse(await response.text());

	if (response.status === 404) {
		return undefined;
	}

	if (!response.ok) {
		const message =
			typeof data.message === 'string'
				? data.message
				: 'MLflow request failed';
		throw internalError(message);
	}

	const experiment = data.experiment as
		| { experiment_id?: string | number }
		| undefined;
	const experimentId = experiment?.experiment_id;
	return experimentId === undefined ? undefined : String(experimentId);
}

async function ensureMlflowExperimentId(): Promise<string> {
	if (mlflowExperimentId) {
		return mlflowExperimentId;
	}

	try {
		const createdExperimentId = await getMlflowClient().createExperiment(
			MLFLOW_EXPERIMENT_NAME,
		);
		mlflowExperimentId = String(createdExperimentId);
		return mlflowExperimentId;
	} catch {
		const existingId = await getMlflowExperimentByName(
			MLFLOW_EXPERIMENT_NAME,
		);
		if (existingId) {
			mlflowExperimentId = existingId;
			return existingId;
		}
	}

	throw internalError('MLflow experiment could not be created');
}

async function createMlflowRun(
	experimentId: string,
	runName: string,
): Promise<string> {
	const created = await mlflowPost('/api/2.0/mlflow/runs/create', {
		experiment_id: experimentId,
		start_time: Date.now(),
		tags: [{ key: 'mlflow.runName', value: runName }],
	});
	const run = created.run as
		| { info?: { run_id?: string; run_uuid?: string } }
		| undefined;
	const runId = run?.info?.run_id ?? run?.info?.run_uuid;

	if (!runId) {
		throw internalError('MLflow run could not be created');
	}

	return runId;
}

async function finishMlflowRun(
	runId: string,
	status: 'FINISHED' | 'FAILED',
): Promise<void> {
	await mlflowPost('/api/2.0/mlflow/runs/update', {
		run_id: runId,
		end_time: Date.now(),
		status,
	});
}

async function logMlflowRun(data: MlflowRunData): Promise<void> {
	const experimentId = await ensureMlflowExperimentId();
	const timestampSeconds = Math.floor(Date.now() / 1000);
	const runName = `eval-${timestampSeconds}`;
	const runId = await createMlflowRun(experimentId, runName);

	try {
		await mlflowPost('/api/2.0/mlflow/runs/log-batch', {
			run_id: runId,
			params: [
				{ key: 'dataset_size', value: String(data.datasetSize) },
				{ key: 'eval_column', value: data.evalColumn },
				{ key: 'model_sha256', value: data.modelSha256 },
				{ key: 'csv_sha256', value: data.csvSha256 },
				{ key: 'metric', value: data.metric },
			],
			metrics: [
				{
					key: 'score',
					value: Number((data.score * 100).toFixed(4)),
					step: 0,
					timestamp: Date.now(),
				},
			],
		});
		await finishMlflowRun(runId, 'FINISHED');
	} catch (error) {
		try {
			await finishMlflowRun(runId, 'FAILED');
		} catch {
			// Preserve the original MLflow failure.
		}
		throw error;
	}
}

export default async function evalPlugin(
	fastify: FastifyInstance,
): Promise<void> {
	fastify.addContentTypeParser(
		/^multipart\/form-data(?:;.*)?$/i,
		{ parseAs: 'buffer' },
		(_request, payload, done) => {
			done(null, payload);
		},
	);

	fastify.get(
		'/health',
		async (_request: FastifyRequest, reply: FastifyReply) => {
			return reply.status(200).send({ status: 'ok' });
		},
	);

	fastify.post(
		'/eval',
		{ bodyLimit: MAX_MULTIPART_BODY_BYTES },
		async (request: FastifyRequest, reply: FastifyReply) => {
			try {
				const contentTypeHeader = request.headers['content-type'];
				const contentType =
					typeof contentTypeHeader === 'string'
						? contentTypeHeader
						: undefined;
				const boundary = getBoundary(contentType);
				const body = Buffer.isBuffer(request.body)
					? request.body
					: await readRequestBody(request);
				const parts = parseMultipart(body, boundary);
				const evalColumn = getTextField(parts, 'eval_column');
				const metric = getMetric(parts);
				const { csvBuffer, modelBuffer } = identifyFiles(parts);
				const csvSha256 = createHash('sha256')
					.update(csvBuffer)
					.digest('hex');
				const modelSha256 = createHash('sha256')
					.update(modelBuffer)
					.digest('hex');

				const evaluation = await evaluateModel(
					modelBuffer,
					csvBuffer,
					evalColumn,
					metric,
				);

				await logMlflowRun({
					csvSha256,
					datasetSize: evaluation.datasetSize,
					evalColumn,
					metric,
					modelSha256,
					score: evaluation.score,
				});

				request.log.debug({
					csvSha256,
					datasetSize: evaluation.datasetSize,
					evalColumn,
					metric,
					modelSha256,
					score: evaluation.score,
				});

				return reply.status(200).send({ score: evaluation.score });
			} catch (error) {
				request.log.error({ err: error });
				const statusCode =
					typeof error === 'object' &&
					error !== null &&
					'statusCode' in error &&
					typeof error.statusCode === 'number'
						? error.statusCode
						: 400;
				const message =
					error instanceof Error
						? error.message
						: 'Evaluation request failed';

				return reply.status(statusCode).send({
					error:
						statusCode >= 500
							? 'Internal Server Error'
							: 'Bad Request',
					message,
					statusCode,
				});
			}
		},
	);
}
EOF

echo "Done!"
