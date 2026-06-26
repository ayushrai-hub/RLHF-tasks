<?php
namespace QuestCapsule;

// Read-only access to the SQLite cartridge. This layer is complete; it only fetches the
// raw rows. Interpreting the encoded payloads is the job of the other classes.
class Cartridge
{
    private \SQLite3 $db;

    public function __construct(string $path)
    {
        if (!is_file($path)) {
            throw new \RuntimeException("cartridge not found: $path");
        }
        $this->db = new \SQLite3($path, SQLITE3_OPEN_READONLY);
        $this->db->busyTimeout(2000);
    }

    /** Load glyph set $tableId as a Glyphs instance. */
    public function glyphSet(int $tableId): Glyphs
    {
        $map = [];
        $stmt = $this->db->prepare('SELECT code, plain FROM glyphs WHERE table_id = :t');
        $stmt->bindValue(':t', $tableId, SQLITE3_INTEGER);
        $res = $stmt->execute();
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $map[$row['code']] = $row['plain'];
        }
        return new Glyphs($map);
    }

    /** @return array<int,array{room_id:int,kind:string,title_glyph:string,body_glyph:string}> */
    public function rooms(string $capsule): array
    {
        $out = [];
        $stmt = $this->db->prepare(
            'SELECT room_id, kind, title_glyph, body_glyph FROM rooms WHERE capsule = :c ORDER BY room_id'
        );
        $stmt->bindValue(':c', $capsule, SQLITE3_TEXT);
        $res = $stmt->execute();
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $row['room_id'] = (int) $row['room_id'];
            $out[] = $row;
        }
        return $out;
    }

    /** @return array<int,array{from_room:int,label_glyph:string,to_room:int,guard_glyph:?string}> */
    public function edges(string $capsule): array
    {
        $out = [];
        $stmt = $this->db->prepare(
            'SELECT from_room, label_glyph, to_room, guard_glyph FROM edges WHERE capsule = :c'
        );
        $stmt->bindValue(':c', $capsule, SQLITE3_TEXT);
        $res = $stmt->execute();
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $row['from_room'] = (int) $row['from_room'];
            $row['to_room'] = (int) $row['to_room'];
            $row['guard_glyph'] = $row['guard_glyph'] !== null ? (string) $row['guard_glyph'] : null;
            $out[] = $row;
        }
        return $out;
    }

    /** @return array<int,array{seed_id:int,seed_value:int}> */
    public function seeds(string $capsule): array
    {
        $out = [];
        $stmt = $this->db->prepare(
            'SELECT seed_id, seed_value FROM seeds WHERE capsule = :c ORDER BY seed_id'
        );
        $stmt->bindValue(':c', $capsule, SQLITE3_TEXT);
        $res = $stmt->execute();
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $out[] = ['seed_id' => (int) $row['seed_id'], 'seed_value' => (int) $row['seed_value']];
        }
        return $out;
    }
}
