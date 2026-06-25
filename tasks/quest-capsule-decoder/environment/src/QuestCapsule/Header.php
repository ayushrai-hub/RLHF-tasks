<?php
namespace QuestCapsule;

// Parses the opaque header carried in a capsule spec.
class Header
{
    /**
     * Decode the spec's base64 header into the capsule's parameters.
     *
     * Returns an associative array with keys: entry, room_count, glyph_table, seed_base,
     * checksum, checksum_ok.
     *
     * Not implemented yet: returns nulls so the CLI runs end to end. The header layout and
     * its consistency check are described in docs/operator-log.md.
     */
    public static function parse(string $base64, Cartridge $cart): array
    {
        return [
            'entry' => null,
            'room_count' => null,
            'glyph_table' => null,
            'seed_base' => null,
            'checksum' => null,
            'checksum_ok' => false,
        ];
    }
}
