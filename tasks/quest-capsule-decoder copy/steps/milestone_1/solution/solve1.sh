#!/bin/bash
# Milestone 1 oracle: implement glyph decoding and header parsing, then decode every header.
set -euo pipefail

cd /app

echo "== a capsule spec =="
cat /app/cartridges/verdant-hollow.qcap.json
echo "== glyph set 7 size =="
sqlite3 /app/cartridges/quests.cartridge.db "SELECT count(*) FROM glyphs WHERE table_id = 7;"
echo "== a decoded header record (base64) =="
php -r '$s=json_decode(file_get_contents("/app/cartridges/verdant-hollow.qcap.json"),true);echo base64_decode($s["header"]),"\n";'

cat > /app/src/QuestCapsule/Glyphs.php <<'PHPEOF'
<?php
namespace QuestCapsule;

// A glyph set: a substitution between cartridge symbols and plain characters.
class Glyphs
{
    /** @var array<string,string> code => plain */
    private array $map;

    /** @param array<string,string> $map */
    public function __construct(array $map)
    {
        $this->map = $map;
    }

    public function size(): int
    {
        return count($this->map);
    }

    /** Decode an encoded payload (fixed-width 2-char codes) into plain text. */
    public function decode(string $payload): string
    {
        $len = strlen($payload);
        if ($len % 2 !== 0) {
            throw new \RuntimeException("odd-length glyph payload: $payload");
        }
        $out = '';
        for ($i = 0; $i < $len; $i += 2) {
            $code = substr($payload, $i, 2);
            if (!isset($this->map[$code])) {
                throw new \RuntimeException("unknown glyph code: $code");
            }
            $out .= $this->map[$code];
        }
        return $out;
    }
}
PHPEOF

cat > /app/src/QuestCapsule/Header.php <<'PHPEOF'
<?php
namespace QuestCapsule;

// Parses the opaque header carried in a capsule spec.
class Header
{
    public const CHECK_MOD = 9973;

    /**
     * Decode the spec's base64 header. Every numeric field is glyph-encoded except the
     * glyph-set id `g`, which is plain. The check is (entry + room_count + seed_base) mod 9973.
     */
    public static function parse(string $base64, Cartridge $cart): array
    {
        $rec = base64_decode($base64, true);
        if ($rec === false) {
            throw new \RuntimeException('header is not valid base64');
        }
        $fields = [];
        foreach (explode(';', $rec) as $part) {
            $eq = strpos($part, '=');
            if ($eq !== false) {
                $fields[substr($part, 0, $eq)] = substr($part, $eq + 1);
            }
        }
        $g = (int) $fields['g'];
        $glyphs = $cart->glyphSet($g);
        $entry = (int) $glyphs->decode($fields['e']);
        $roomCount = (int) $glyphs->decode($fields['n']);
        $seedBase = (int) $glyphs->decode($fields['s']);
        $checksum = (int) $glyphs->decode($fields['k']);
        $computed = ($entry + $roomCount + $seedBase) % self::CHECK_MOD;
        return [
            'entry' => $entry,
            'room_count' => $roomCount,
            'glyph_table' => $g,
            'seed_base' => $seedBase,
            'checksum' => $checksum,
            'checksum_ok' => $checksum === $computed,
        ];
    }
}
PHPEOF

for spec in /app/cartridges/*.qcap.json; do
    name="$(basename "$spec" .qcap.json)"
    php /app/bin/qcap.php decode "$name"
done

echo "== a decoded header artifact =="
cat /app/out/verdant-hollow.header.json
