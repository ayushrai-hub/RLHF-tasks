<?php
namespace QuestCapsule;

// Orchestrates a capsule: loads its spec and cartridge, then runs decode / graph / solve
// and writes the results under the output directory in the documented format.
class Capsule
{
    private string $name;
    private string $appDir;
    private array $spec;
    private Cartridge $cart;

    public function __construct(string $name, string $appDir = '/app')
    {
        $this->name = $name;
        $this->appDir = rtrim($appDir, '/');
        $specPath = $this->appDir . '/cartridges/' . $name . '.qcap.json';
        if (!is_file($specPath)) {
            throw new \RuntimeException("spec not found: $specPath");
        }
        $spec = json_decode((string) file_get_contents($specPath), true);
        if (!is_array($spec) || !isset($spec['header'], $spec['cartridge'])) {
            throw new \RuntimeException("malformed spec: $specPath");
        }
        $this->spec = $spec;
        $this->cart = new Cartridge($this->appDir . '/cartridges/' . $spec['cartridge']);
    }

    private function outDir(): string
    {
        $dir = $this->appDir . '/out';
        if (!is_dir($dir)) {
            mkdir($dir, 0775, true);
        }
        return $dir;
    }

    private static function pretty(array $data): string
    {
        $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        // json_encode indents with 4 spaces per level; the contract uses 2.
        $json = preg_replace_callback('/^( +)/m', static function ($m) {
            return str_repeat(' ', intdiv(strlen($m[1]), 2));
        }, $json);
        return $json . "\n";
    }

    public function decode(): array
    {
        $h = Header::parse((string) $this->spec['header'], $this->cart);
        $out = [
            'capsule' => $this->name,
            'entry' => $h['entry'],
            'room_count' => $h['room_count'],
            'glyph_table' => $h['glyph_table'],
            'seed_base' => $h['seed_base'],
            'checksum' => $h['checksum'],
            'checksum_ok' => $h['checksum_ok'],
        ];
        file_put_contents($this->outDir() . '/' . $this->name . '.header.json', self::pretty($out));
        return $out;
    }

    private function glyphTable(): int
    {
        $h = Header::parse((string) $this->spec['header'], $this->cart);
        return (int) $h['glyph_table'];
    }

    public function graph(): array
    {
        $g = Graph::build($this->name, $this->cart, $this->glyphTable());
        $out = ['capsule' => $this->name, 'entry' => $g['entry'], 'rooms' => $g['rooms']];
        file_put_contents($this->outDir() . '/' . $this->name . '.graph.json', self::pretty($out));
        return $out;
    }

    public function solve(): array
    {
        $g = Graph::build($this->name, $this->cart, $this->glyphTable());
        $titleById = [];
        foreach ($g['rooms'] as $room) {
            $titleById[$room['id']] = $room['title'];
        }
        $written = [];
        foreach ($this->cart->seeds($this->name) as $seed) {
            $steps = Solver::solve($g, $seed['seed_value']);
            $lines = [];
            $entryTitle = $titleById[$g['entry']] ?? '';
            $lines[] = $entryTitle;
            foreach ($steps as $step) {
                $lines[] = $step['label'] . ' -> ' . ($titleById[$step['to']] ?? '');
            }
            $path = $this->outDir() . '/' . $this->name . '.' . $seed['seed_id'] . '.run';
            file_put_contents($path, implode("\n", $lines) . "\n");
            $written[] = $path;
        }
        return $written;
    }
}
