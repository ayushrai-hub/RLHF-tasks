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

    /**
     * Decode an encoded payload into plain text.
     *
     * Not implemented yet: returns the payload untouched so the rest of the pipeline can be
     * exercised. The real decoding rule lives in docs/operator-log.md.
     */
    public function decode(string $payload): string
    {
        return $payload;
    }
}
