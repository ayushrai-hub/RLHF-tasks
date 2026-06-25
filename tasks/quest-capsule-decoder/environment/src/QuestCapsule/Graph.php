<?php
namespace QuestCapsule;

// Reconstructs the playable room graph for a capsule from the cartridge rows.
class Graph
{
    /**
     * Build the decoded room graph.
     *
     * Returns ['entry' => int, 'rooms' => array<...>] where each room has id, kind, title,
     * body, and an ordered list of exits (label, to, guard).
     *
     * Not implemented yet: returns an empty graph. The decoding and ordering rules are in
     * docs/operator-log.md and docs/output-format.md.
     */
    public static function build(string $capsule, Cartridge $cart, int $glyphTable): array
    {
        return ['entry' => null, 'rooms' => []];
    }
}
