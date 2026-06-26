from __future__ import annotations

import json
import os
from pathlib import Path

from scheduler import schedule_messages

APP_DIR = Path(os.environ.get('APP_DIR', '/app'))
DATA_DIR = APP_DIR / 'data'
OUTPUT_DIR = APP_DIR / 'output'


def main() -> None:
    polls = json.loads((DATA_DIR / 'polls.json').read_text(encoding='utf-8'))
    candidates = json.loads((DATA_DIR / 'candidates.json').read_text(encoding='utf-8'))
    messages = json.loads((DATA_DIR / 'messages.json').read_text(encoding='utf-8'))
    config = json.loads((DATA_DIR / 'config.json').read_text(encoding='utf-8'))
    report = schedule_messages(polls, candidates, messages, config)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
