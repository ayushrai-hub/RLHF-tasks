#!/bin/bash
echo "Validating configuration..."
if [ ! -f /app/config/settings.json ]; then echo "ERROR"; exit 1; fi
echo "Valid."
