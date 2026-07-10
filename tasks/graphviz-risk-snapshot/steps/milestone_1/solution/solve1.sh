#!/bin/bash
set -euo pipefail

# Create solve1.js
cat > /app/solve1.js << EOF
const express = require('express');
const jwt = require('jsonwebtoken');

// Constants
const JWT_SECRET = 'ringo-hope';
const JWT_ISSUER = 'graphviz-risk-snapshot';
const JWT_AUDIENCE = 'worker';

let vulnerabilities = [];

// Initialize an Express app
const app = express();

// Middleware to parse JSON
app.use(express.json());

app.use((req, res, next) => {
    const authHeader = req.headers['authorization'] || req.headers['Authorization'];
    const token = typeof authHeader === 'string'
        ? authHeader.replace(/^Bearer\\s+/i, '').trim()
        : null;

    if (!token) {
        return res.status(401).json({ error: 'Missing JWT' });
    }

    try {
        const payload = jwt.verify(token, JWT_SECRET, {
            algorithms: ['HS256'],
            issuer: JWT_ISSUER,
            audience: JWT_AUDIENCE,
        });
        req.user = payload;
        next();
    } catch (e) {
        res.status(401).json({ error: 'Invalid JWT' });
    }
});

app.post('/api/advisory', (req, res) => {
    vulnerabilities = Array.isArray(req.body?.advisory) ? req.body.advisory : [];
    res.json({ success: true });
});

/**
 * Bind the express server at a specific port.
 */
async function startServer() {
    const PORT = process.env.PORT || 8080;

    await new Promise(resolve => {
        app.listen(PORT, () => {
            console.log(\`Server is running at port \${PORT}\`);
            resolve('Started');
        });
    });
}

startServer();
EOF
