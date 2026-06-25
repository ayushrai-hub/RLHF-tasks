<?php
namespace QuestCapsule;

// Plays a capsule's save state to completion and returns the walked path.
class Solver
{
    /**
     * Solve one run.
     *
     * $graph is the structure returned by Graph::build. Returns an ordered list of steps,
     * each ['label' => string, 'to' => int], describing the rooms walked from the entry to
     * the exit room. Returns an empty list when no walk is produced.
     *
     * Not implemented yet. The walk rule (guards, grants, and how the seed selects the
     * route) is described in docs/operator-log.md.
     */
    public static function solve(array $graph, int $seedValue): array
    {
        return [];
    }
}
