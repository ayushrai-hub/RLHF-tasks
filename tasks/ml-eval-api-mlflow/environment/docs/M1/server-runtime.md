Server runtime notes

GET /health must return 200.

"onnxruntime-node" package is installed. Do not attempt to install anything else, as there is no internet access. Don't get terminal stuck in any process or starting servers.

The server will be started from /app using "npm start" as usual. The usual backend environment variables are assumed to be supplied by the caller. The server must bind to the port specified by the FASTIFY_PORT environment variable, so just read FASTIFY_PORT at startup and don't hard-code another API port. Do not assume a fixed API port instead of the existing environment value.
