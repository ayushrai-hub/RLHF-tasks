#!/bin/bash
# Milestone 2 oracle: reconstruct the decoded room graph for every capsule.
set -euo pipefail

cd /app

echo "== rooms and edges for one capsule =="
sqlite3 /app/cartridges/quests.cartridge.db \
    "SELECT room_id, kind FROM rooms WHERE capsule = 'verdant-hollow' ORDER BY room_id;"
sqlite3 /app/cartridges/quests.cartridge.db \
    "SELECT from_room, to_room, guard_glyph IS NOT NULL AS guarded FROM edges WHERE capsule = 'verdant-hollow';"

cat > /app/src/QuestCapsule/Graph.php <<'PHPEOF'
<?php
namespace QuestCapsule;

// Reconstructs the playable room graph for a capsule from the cartridge rows.
class Graph
{
    /** Build the decoded room graph: rooms ordered by id; exits ordered by label then to. */
    public static function build(string $capsule, Cartridge $cart, int $glyphTable): array
    {
        $glyphs = $cart->glyphSet($glyphTable);
        $edgesByRoom = [];
        foreach ($cart->edges($capsule) as $e) {
            $edgesByRoom[$e['from_room']][] = $e;
        }
        $rooms = [];
        $entry = null;
        foreach ($cart->rooms($capsule) as $r) {
            if ($r['kind'] === 'entry') {
                $entry = $r['room_id'];
            }
            $exits = [];
            foreach ($edgesByRoom[$r['room_id']] ?? [] as $e) {
                $guard = $e['guard_glyph'] !== null ? $glyphs->decode($e['guard_glyph']) : null;
                $exits[] = ['label' => $glyphs->decode($e['label_glyph']), 'to' => $e['to_room'], 'guard' => $guard];
            }
            usort($exits, static function ($a, $b) {
                return [$a['label'], $a['to']] <=> [$b['label'], $b['to']];
            });
            $rooms[] = [
                'id' => $r['room_id'],
                'kind' => $r['kind'],
                'title' => $glyphs->decode($r['title_glyph']),
                'body' => $glyphs->decode($r['body_glyph']),
                'exits' => $exits,
            ];
        }
        return ['entry' => $entry, 'rooms' => $rooms];
    }
}
PHPEOF

for spec in /app/cartridges/*.qcap.json; do
    name="$(basename "$spec" .qcap.json)"
    php /app/bin/qcap.php graph "$name"
done

echo "== a reconstructed graph artifact =="
head -n 30 /app/out/verdant-hollow.graph.json
