from __future__ import annotations

import json
import os
from pathlib import Path

from on_boarding_service import build_report

APP_DIR = Path(os.environ.get('APP_DIR', '/app'))
DATA_DIR = APP_DIR / 'data'
OUTPUT_DIR = APP_DIR / 'output'


def main() -> None:
    config = json.loads((DATA_DIR / 'config.json').read_text(encoding='utf-8'))
    rows = json.loads((DATA_DIR / 'onboarding.json').read_text(encoding='utf-8'))
    report = build_report(config, rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
