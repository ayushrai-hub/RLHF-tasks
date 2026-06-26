#!/bin/bash
set -euo pipefail

mkdir -p /opt/change-freeze/vendor/freezeengine
cp /opt/change-freeze/vendor_templates/freezeengine/*.go /opt/change-freeze/vendor/freezeengine/
