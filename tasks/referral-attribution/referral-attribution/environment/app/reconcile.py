from __future__ import annotations

import json
import os
from pathlib import Path

from referral_processor import build_report

APP_DIR = Path(os.environ.get('APP_DIR', '/app'))
DATA_DIR = APP_DIR / 'data'
OUTPUT_DIR = APP_DIR / 'output'


def main() -> None:
    referrers = json.loads((DATA_DIR / 'referrers.json').read_text(encoding='utf-8'))
    events = json.loads((DATA_DIR / 'events.json').read_text(encoding='utf-8'))
    report = build_report(referrers, events)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
