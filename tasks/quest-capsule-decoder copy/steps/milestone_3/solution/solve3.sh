#!/bin/bash
# Milestone 3 oracle: play every save state to completion and emit its winning transcript.
set -euo pipefail

cd /app

echo "== save states for one capsule =="
sqlite3 /app/cartridges/quests.cartridge.db \
    "SELECT seed_id, seed_value FROM seeds WHERE capsule = 'verdant-hollow' ORDER BY seed_id;"

cat > /app/src/QuestCapsule/Solver.php <<'PHPEOF'
<?php
namespace QuestCapsule;

// Plays a capsule's save state to completion and returns the walked path.
class Solver
{
    /** @return array<int,array{label:string,to:int}> the steps from entry to the exit room */
    public static function solve(array $graph, int $seedValue): array
    {
        $rooms = [];
        $exitId = null;
        foreach ($graph['rooms'] as $r) {
            $rooms[$r['id']] = $r;
            if ($r['kind'] === 'exit') {
                $exitId = $r['id'];
            }
        }
        $grants = static function (string $body): array {
            $toks = [];
            foreach (explode('.', $body) as $clause) {
                $clause = trim($clause);
                if (strncmp($clause, 'grant ', 6) === 0) {
                    $toks[] = trim(substr($clause, 6));
                }
            }
            return $toks;
        };

        $dfs = static function (int $room, array $visited, array $inv)
            use (&$dfs, $rooms, $exitId, $grants, $seedValue) {
            $inv2 = array_values(array_unique(array_merge($inv, $grants($rooms[$room]['body']))));
            if ($room === $exitId) {
                return [];
            }
            $cand = [];
            foreach ($rooms[$room]['exits'] as $e) {
                if (in_array($e['to'], $visited, true)) {
                    continue;
                }
                if ($e['guard'] !== null && !in_array($e['guard'], $inv2, true)) {
                    continue;
                }
                $cand[] = $e;
            }
            usort($cand, static function ($a, $b) {
                return [$a['label'], $a['to']] <=> [$b['label'], $b['to']];
            });
            $k = count($cand);
            if ($k === 0) {
                return null;
            }
            $start = $seedValue % $k;
            $order = array_merge(array_slice($cand, $start), array_slice($cand, 0, $start));
            foreach ($order as $e) {
                $res = $dfs($e['to'], array_merge($visited, [$e['to']]), $inv2);
                if ($res !== null) {
                    return array_merge([['label' => $e['label'], 'to' => $e['to']]], $res);
                }
            }
            return null;
        };

        $res = $dfs($graph['entry'], [$graph['entry']], []);
        return $res === null ? [] : $res;
    }
}
PHPEOF

for spec in /app/cartridges/*.qcap.json; do
    name="$(basename "$spec" .qcap.json)"
    php /app/bin/qcap.php solve "$name"
done

echo "== a winning transcript =="
cat /app/out/verdant-hollow.1.run
