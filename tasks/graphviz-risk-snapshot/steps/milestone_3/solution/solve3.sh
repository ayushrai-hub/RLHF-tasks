#!/bin/bash
set -euo pipefail
mkdir -p /app

cat > /app/solve3.js <<'JS'
const express = require('express');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

const JWT_SECRET = 'ringo-hope';
const JWT_ISSUER = 'graphviz-risk-snapshot';
const JWT_AUDIENCE = 'worker';
const SNAPSHOT_SECRET = 'snapshot-secret-test';

let vulnerabilities = [];

const app = express();
app.use(express.json());

app.get('/api/graphviz', (req, res) => {
    const edges = [];
    for (const vuln of vulnerabilities) {
        edges.push([`${vuln.name}@${vuln.version}`, vuln.advisoryId]);
        edges.push([vuln.advisoryId, vuln.severity]);
    }

    const snapshot = {
        generatedAt: new Date().toISOString(),
        findings: vulnerabilities,
        edges,
    };

    const payload = JSON.stringify(snapshot);
    const signature = crypto.createHmac('sha256', SNAPSHOT_SECRET).update(payload).digest('hex');

    res.json({ ...snapshot, sign: signature });
});

app.get('/api/jwt-token', (req, res) => {
    const token = jwt.sign({ user: 'worker' }, JWT_SECRET, {
        algorithm: 'HS256',
        issuer: JWT_ISSUER,
        audience: JWT_AUDIENCE,
        expiresIn: '1d',
    });
    res.json({ token });
});

app.use((req, res, next) => {
    const authHeader = req.headers['authorization'] || req.headers['Authorization'];
    const token = typeof authHeader === 'string' ? authHeader.replace(/^Bearer\s+/i, '').trim() : null;

    if (req.method === 'GET' && (req.path === '/api/graphviz' || req.path === '/api/jwt-token')) {
        return next();
    }

    if (!token) {
        return res.status(401).json({ error: 'Missing JWT' });
    }

    try {
        jwt.verify(token, JWT_SECRET, {
            algorithms: ['HS256'],
            issuer: JWT_ISSUER,
            audience: JWT_AUDIENCE,
        });
        next();
    } catch (e) {
        res.status(401).json({ error: 'Invalid JWT' });
    }
});

app.get('/api/advisory', (req, res) => {
    res.json(vulnerabilities);
});

app.post('/api/advisory', (req, res) => {
    vulnerabilities = Array.isArray(req.body?.advisory) ? req.body.advisory : [];
    res.json({ success: true });
});

async function startServer() {
    const PORT = process.env.PORT || 8080;
    await new Promise(resolve => {
        app.listen(PORT, () => {
            console.log(`Server is running at port ${PORT}`);
            resolve('Started');
        });
    });
}

startServer();
JS

cat > /app/worker.js <<'JS'
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const csv2json = require('csvtojson');

const REPO_ROOT = process.cwd();
const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8080';
const TASK_INTERVAL = 1000;

function getCsvPath() {
    const candidates = [
        process.env.CSV_PATH,
        '/app/dependencies.csv',
        path.join(REPO_ROOT, 'environment', 'dependencies.csv'),
    ].filter(Boolean);

    for (const candidate of candidates) {
        try {
            if (fs.existsSync(candidate)) {
                return candidate;
            }
        } catch (error) {
            // ignore
        }
    }

    return candidates[0] || path.join(REPO_ROOT, 'environment', 'dependencies.csv');
}

function getDataFilePath(dependencyName) {
    const candidates = [
        path.join('/app', 'data', `${dependencyName}.json`),
        path.join(REPO_ROOT, 'environment', 'data', `${dependencyName}.json`),
    ];

    for (const candidate of candidates) {
        try {
            if (fs.existsSync(candidate)) {
                return candidate;
            }
        } catch (error) {
            // ignore
        }
    }

    return candidates[0];
}

function normalizeSeverity(vulnerability) {
    if (typeof vulnerability?.severity === 'string' && vulnerability.severity) {
        return vulnerability.severity;
    }

    if (Array.isArray(vulnerability?.severity)) {
        const severity = vulnerability.severity.find((item) => typeof item?.score === 'string' && item.score);
        if (severity) {
            return severity.score;
        }
    }

    if (typeof vulnerability?.database_specific?.severity === 'string' && vulnerability.database_specific.severity) {
        return vulnerability.database_specific.severity;
    }

    if (typeof vulnerability?.severityScore === 'string' && vulnerability.severityScore) {
        return vulnerability.severityScore;
    }

    return 'unknown';
}

async function getToken() {
    const { data } = await axios.get(`${API_BASE_URL}/api/jwt-token`, { timeout: 5000 });
    return data.token;
}

async function runWorker() {
    const dependencies = await csv2json().fromFile(getCsvPath());
    let token = null;

    const runTask = async () => {
        try {
            if (!token) {
                token = await getToken();
            }

            const advisories = [];
            for (const dependency of dependencies) {
                let data = [];
                try {
                    const response = JSON.parse(fs.readFileSync(getDataFilePath(dependency.name), 'utf8'));
                    data = Array.isArray(response?.vulns) ? response.vulns : [];
                } catch (error) {
                    data = [];
                }

                for (const vulnerability of data) {
                    advisories.push({
                        advisoryId: vulnerability.id || vulnerability.advisoryId || 'unknown',
                        name: dependency.name,
                        age: vulnerability.published || vulnerability.modified || new Date().toISOString(),
                        severity: normalizeSeverity(vulnerability),
                        package: dependency.name,
                        version: dependency.version,
                    });
                }
            }

            await axios.post(`${API_BASE_URL}/api/advisory`, { advisory: advisories }, {
                headers: { Authorization: token },
                timeout: 5000,
            });
        } catch (error) {
            console.error(error.message);
        } finally {
            setTimeout(() => runTask(), TASK_INTERVAL);
        }
    };

    runTask();
}

runWorker();
JS