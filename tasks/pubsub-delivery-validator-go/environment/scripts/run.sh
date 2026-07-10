#!/bin/bash
cd /app && ./bin/pubsub-validator --data /app/data/delivery_log.json --config /app/config/pubsub.toml --output /app/output
