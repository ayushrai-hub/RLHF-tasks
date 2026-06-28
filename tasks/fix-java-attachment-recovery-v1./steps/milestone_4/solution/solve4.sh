#!/bin/bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${SCRIPT_DIR}/apply_milestone_1.sh"
bash "${SCRIPT_DIR}/apply_milestone_2.sh"
bash "${SCRIPT_DIR}/apply_milestone_3.sh"
bash "${SCRIPT_DIR}/apply_milestone_4.sh"
mvn -q -B -o test
