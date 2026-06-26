<?php
// QuestCapsule loader CLI. Reads one capsule and runs a single stage of the pipeline.
require dirname(__DIR__) . '/lib/autoload.php';

use QuestCapsule\Capsule;

$args = array_slice($_SERVER['argv'], 1);
if (count($args) !== 2) {
    fwrite(STDERR, "usage: qcap.php <decode|graph|solve> <capsule>\n");
    exit(2);
}

[$command, $name] = $args;
$appDir = getenv('QCAP_APP_DIR') ?: '/app';

try {
    $capsule = new Capsule($name, $appDir);

    if ($command === 'decode') {
        $header = $capsule->decode();
        $check = $header['checksum_ok'] ? 'ok' : 'failed';
        echo "$name: header decoded, check $check\n";
    } elseif ($command === 'graph') {
        $graph = $capsule->graph();
        echo "$name: graph rebuilt with " . count($graph['rooms']) . " rooms\n";
    } elseif ($command === 'solve') {
        $runs = $capsule->solve();
        echo "$name: " . count($runs) . " save states played\n";
    } else {
        fwrite(STDERR, "unknown command: $command\n");
        exit(2);
    }
} catch (\Throwable $e) {
    fwrite(STDERR, 'error: ' . $e->getMessage() . "\n");
    exit(1);
}
