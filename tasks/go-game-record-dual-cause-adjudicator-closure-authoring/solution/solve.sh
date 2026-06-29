#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > r/dragon-cup-17.ggr <<'RECORD'
record_id: dragon-cup-17
ruleset: tournament-area-2026
board_size: 5
komi: 6.5
main:
1 B A1
2 W B1
3 B A2
4 W B2
variation ko-threat-read from 4:
5 B E5
6 W D5
endvariation
6 W C1
7 B C2
8 W D1
9 B E1
10 W pass
11 B pass
score black_area=15 white_area=7
result B+1.5
RECORD

cat > j/policy.json <<'JSON'
{
  "policy_id": "local-independent-adjudicator-v1",
  "ruleset": "tournament-area-2026",
  "closing_passes_required": 2,
  "score_source": "area_score",
  "allow_legacy_score_token": true,
  "komi": 6.5,
  "require_branch_leakage_zero": true,
  "expected_records": {
    "dragon-cup-17": {
      "winner": "B",
      "margin": 1.5,
      "terminal_pass_move_numbers": [10, 11],
      "required_variation": "ko-threat-read",
      "required_branch_only_moves": ["B:E5", "W:D5"],
      "allow_legacy_score_token": false
    },
    "sansei-legacy-1999": {
      "winner": "B",
      "margin": 2.5,
      "terminal_pass_move_numbers": [4, 5],
      "required_variation": "",
      "required_branch_only_moves": [],
      "allow_legacy_score_token": true
    }
  }
}
JSON

./tools/run_public_workflow.sh
