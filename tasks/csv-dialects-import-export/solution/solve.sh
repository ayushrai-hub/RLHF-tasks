#!/usr/bin/env bash
set -uo pipefail
cd /app || exit 1
mkdir -p output

cat > /app/src/process.php << 'PHPEOF'
<?php
use League\Csv\Reader;
use League\Csv\Writer;
require '/app/vendor/autoload.php';

// ── Helpers ─────────────────────────────────────────────────────────

function loadFile(string $path): string {
    $raw = file_get_contents($path);
    if ($raw === false) throw new RuntimeException("Cannot read $path");
    if (substr($raw, 0, 2) === "\xFF\xFE") {
        $raw = mb_convert_encoding(substr($raw, 2), 'UTF-8', 'UTF-16LE');
    } elseif (substr($raw, 0, 3) === "\xEF\xBB\xBF") {
        $raw = substr($raw, 3);
    } elseif (!mb_check_encoding($raw, 'UTF-8')) {
        $raw = mb_convert_encoding($raw, 'UTF-8', 'ISO-8859-1');
        if (!mb_check_encoding($raw, 'UTF-8')) {
            $raw = mb_convert_encoding(file_get_contents($path), 'UTF-8', 'Windows-1252');
        }
    }
    return $raw;
}

function detectDelimiter(string $line): string {
    $best = ','; $bestCount = 0;
    foreach ([',', ';', "\t", '|', '^'] as $d) {
        $c = substr_count($line, $d);
        if ($c > $bestCount) { $bestCount = $c; $best = $d; }
    }
    return $best;
}

function normalizeDate(string $d): ?string {
    if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $d)) {
        $p = explode('-', $d);
        if (checkdate((int)$p[1], (int)$p[2], (int)$p[0])) return $d;
        return null;
    }
    if (preg_match('/^(\d{4})\/(\d{2})\/(\d{2})$/', $d, $m)) {
        if (checkdate((int)$m[2], (int)$m[3], (int)$m[1])) return "$m[1]-$m[2]-$m[3]";
        return null;
    }
    if (preg_match('/^(\d{2})\/(\d{2})\/(\d{4})$/', $d, $m)) {
        // Try DD/MM/YYYY first
        if (checkdate((int)$m[2], (int)$m[1], (int)$m[3])) return "$m[3]-$m[2]-$m[1]";
        // Try MM/DD/YYYY
        if (checkdate((int)$m[1], (int)$m[2], (int)$m[3])) return "$m[3]-$m[1]-$m[2]";
        return null;
    }
    if (preg_match('/^(\d{2})-(\d{2})-(\d{4})$/', $d, $m)) {
        if (checkdate((int)$m[2], (int)$m[1], (int)$m[3])) return "$m[3]-$m[2]-$m[1]";
        return null;
    }
    if (preg_match('/^(\d{2})-([A-Za-z]{3})-(\d{4})$/', $d, $m)) {
        $ts = strtotime("$m[1] $m[2] $m[3]");
        return $ts ? date('Y-m-d', $ts) : null;
    }
    return null;
}

function parseNumber(string $v): ?float {
    $v = trim($v);
    if ($v === '' || strtolower($v) === 'n/a') return null;
    if (str_contains($v, ',') && !str_contains($v, '.')) $v = str_replace(',', '.', $v);
    if (!is_numeric($v)) return null;
    return (float) $v;
}

function parseFixedWidth(string $line): array {
    return [
        'date'     => trim(substr($line, 0, 11)),
        'product'  => trim(substr($line, 11, 7)),
        'quantity' => trim(substr($line, 18, 5)),
        'price'    => trim(substr($line, 23, 8)),
    ];
}

// ── Load temporal exchange rates ────────────────────────────────────

function loadRates(string $path): array {
    $rates = [];
    $raw = file_get_contents($path);
    $reader = Reader::fromString($raw);
    $reader->setHeaderOffset(0);
    foreach ($reader->getRecords() as $r) {
        $rates[$r['Currency']] = (float) $r['RateToUSD'];
    }
    return $rates;
}

$ratesQ1 = loadRates('/app/data/exchange_rates_q1.csv');
$ratesQ2 = loadRates('/app/data/exchange_rates_q2.csv');
// Monthly rates (more granular — prefer over quarterly when available)
$ratesM01 = loadRates('/app/data/exchange_rates_2024-01.csv');
$ratesM02 = loadRates('/app/data/exchange_rates_2024-02.csv');
$ratesM03 = loadRates('/app/data/exchange_rates_2024-03.csv');

function getRate(string $currency, string $date): float {
    global $ratesQ1, $ratesQ2, $ratesM01, $ratesM02, $ratesM03;
    $month = (int)substr($date, 5, 2);
    // Prefer monthly rates for Q1; fall back to quarterly for missing currencies
    $monthly = match($month) {
        1 => $ratesM01,
        2 => $ratesM02,
        3 => $ratesM03,
        default => null,
    };
    if ($monthly !== null && isset($monthly[$currency])) {
        return $monthly[$currency];
    }
    $quarterly = ($month >= 1 && $month <= 3) ? $ratesQ1 : $ratesQ2;
    return $quarterly[$currency] ?? 1.0;
}

// ── Load product catalogs (v2 first) ────────────────────────────────

$products = [];
foreach (['/app/data/products_v2.tsv', '/app/data/products.tsv'] as $p) {
    if (!file_exists($p)) continue;
    $raw = loadFile($p);
    $reader = Reader::fromString($raw);
    $reader->setDelimiter("\t");
    $reader->setHeaderOffset(0);
    foreach ($reader->getRecords() as $r) {
        if (!isset($products[$r['ProductID']])) $products[$r['ProductID']] = $r['Name'];
    }
}
$validPids = array_keys($products);

// ── Process all sources ─────────────────────────────────────────────

$sources = [
    'EU'    => ['csv',  '/app/data/sales_eu.csv',    'EUR'],
    'US'    => ['csv',  '/app/data/sales_us.csv',    'USD'],
    'APAC'  => ['csv',  '/app/data/sales_apac.csv',  'JPY'],
    'UK'    => ['csv',  '/app/data/sales_uk.csv',    'GBP'],
    'LATAM' => ['csv',  '/app/data/sales_latam.csv', 'BRL'],
    'CAN'   => ['csv',  '/app/data/sales_can.csv',   'CAD'],
    'AFR'   => ['csv',  '/app/data/sales_afr.csv',   'ZAR'],
    'MEA'   => [
        ['csv',   '/app/data/sales_mea.csv',  'AED'],
        ['fixed', '/app/data/sales_mea.txt',  'USD'],
    ],
];

$allSales = [];
$regionalTotals = [];
$rejections = [];
$seenKeys = [];
$sourceOrder = array_keys($sources);
sort($sourceOrder); // alphabetical

foreach ($sourceOrder as $region) {
    $entries = $sources[$region];
    if (!is_array($entries[0])) {
        $entries = [$entries];
    }
    $regionCount = 0; $regionAmount = 0.0;
    foreach ($entries as [$fmt, $path, $currency]) {
        $content = loadFile($path);

        if ($fmt === 'fixed') {
            // Fixed-width: parse manually
            $lines = explode("\n", trim($content));
            $header = array_shift($lines); // skip header line
            $rowNum = 0;
            foreach ($lines as $line) {
                $rowNum++;
                if (trim($line) === '') continue;
                $row = parseFixedWidth($line);
                $result = processRow($row, $region, $rowNum, $currency, $regionCount, $regionAmount);
                if ($result) { $allSales[] = $result[0]; $regionCount = $result[1]; $regionAmount = $result[2]; }
            }
        } else {
            $firstLine = strtok($content, "\n");
            $delim = detectDelimiter($firstLine);
            $reader = Reader::fromString($content);
            $reader->setDelimiter($delim);
            $reader->setHeaderOffset(0);
            $rowNum = 0;
            foreach ($reader->getRecords() as $r) {
                $rowNum++;
                $cols = array_keys($r);
                $row = ['date' => '', 'product' => '', 'quantity' => '', 'price' => ''];
                foreach ($cols as $c) {
                    $lo = strtolower($c);
                    if (str_contains($lo, 'date')) $row['date'] = $r[$c];
                    elseif (str_contains($lo, 'product')) $row['product'] = $r[$c];
                    elseif (str_contains($lo, 'qty') || str_contains($lo, 'quantity')) $row['quantity'] = $r[$c];
                    elseif (str_contains($lo, 'price') || str_contains($lo, 'unit')) $row['price'] = $r[$c];
                }
                $result = processRow($row, $region, $rowNum, $currency, $regionCount, $regionAmount);
                if ($result) { $allSales[] = $result[0]; $regionCount = $result[1]; $regionAmount = $result[2]; }
            }
        }
    }
    $regionalTotals[$region] = ['transactions' => $regionCount, 'revenue' => round($regionAmount, 2)];
}

function processRow(array $row, string $region, int $rowNum, string $currency, int &$rc, float &$ra): ?array {
    global $rejections, $seenKeys, $validPids;

    if ($row['date'] === '' || $row['product'] === '' || $row['quantity'] === '' || $row['price'] === '') {
        $rejections[] = [$region, $rowNum, 'missing required fields'];
        return null;
    }

    $date = normalizeDate($row['date']);
    if ($date === null) { $rejections[] = [$region, $rowNum, 'invalid date']; return null; }

    if (!in_array($row['product'], $validPids)) {
        $rejections[] = [$region, $rowNum, 'unrecognized product']; return null;
    }

    $qtyVal = trim($row['quantity']);
    if (!is_numeric($qtyVal)) {
        $rejections[] = [$region, $rowNum, 'non-numeric quantity']; return null;
    }
    $quantity = (int)$qtyVal;
    if ($quantity < 0) { $rejections[] = [$region, $rowNum, 'negative quantity']; return null; }
    if ($quantity === 0) { $rejections[] = [$region, $rowNum, 'zero quantity']; return null; }

    $unitPriceSrc = parseNumber($row['price']);
    if ($unitPriceSrc === null) { $rejections[] = [$region, $rowNum, 'non-numeric price']; return null; }

    $dupKey = $date . '|' . $row['product'] . '|' . $quantity;
    if (isset($seenKeys[$dupKey])) { $rejections[] = [$region, $rowNum, 'duplicate transaction']; return null; }
    $seenKeys[$dupKey] = true;

    $rate = getRate($currency, $date);
    $upUsd = round($unitPriceSrc * $rate, 2);
    $amtUsd = round($quantity * $upUsd, 2);

    $rc++;
    $ra += $amtUsd;

    return [[
        'Date' => $date, 'ProductID' => $row['product'], 'Quantity' => $quantity,
        'UnitPrice' => sprintf('%.2f', $upUsd), 'AmountUSD' => sprintf('%.2f', $amtUsd),
        'SourceFile' => $region, 'SourceRow' => $rowNum,
    ], $rc, $ra];
}

// ── Anomaly detection ───────────────────────────────────────────────

$byProduct = [];
foreach ($allSales as $s) {
    $byProduct[$s['ProductID']][] = (float)$s['UnitPrice'];
}
$anomalies = [];
foreach ($allSales as $s) {
    $prices = $byProduct[$s['ProductID']] ?? [];
    if (count($prices) < 3) continue; // need at least 3 data points
    sort($prices);
    $n = count($prices);
    $median = ($n % 2) ? $prices[(int)($n/2)] : ($prices[$n/2 - 1] + $prices[$n/2]) / 2;
    if ($median == 0) continue;
    $up = (float)$s['UnitPrice'];
    $dev = abs($up - $median) / $median * 100;
    if ($dev > 30) {
        $anomalies[] = [
            'ProductID' => $s['ProductID'], 'SourceFile' => $s['SourceFile'],
            'RowNumber' => $s['SourceRow'], 'UnitPrice' => $s['UnitPrice'],
            'MedianPrice' => sprintf('%.2f', $median), 'DeviationPct' => sprintf('%.1f', $dev),
        ];
    }
}

// ── Write outputs ───────────────────────────────────────────────────

function writeCsv(string $path, array $header, array $rows): void {
    $w = Writer::fromString();
    $w->insertOne($header);
    $w->insertAll($rows);
    file_put_contents($path, $w->toString());
}

// consolidated_sales.csv
$csRows = array_map(fn($s) => [
    $s['Date'], $s['ProductID'], $s['Quantity'], $s['UnitPrice'], $s['AmountUSD']
], $allSales);
writeCsv('/app/output/consolidated_sales.csv', ['Date','ProductID','Quantity','UnitPrice','AmountUSD'], $csRows);

// product_summary.csv
$ps = [];
foreach ($allSales as $s) {
    $pid = $s['ProductID'];
    $ps[$pid] = ['qty' => ($ps[$pid]['qty']??0) + $s['Quantity'], 'amt' => ($ps[$pid]['amt']??0) + (float)$s['AmountUSD']];
}
foreach ($validPids as $pid) if (!isset($ps[$pid])) $ps[$pid] = ['qty' => 0, 'amt' => 0];
$psRows = [];
foreach ($ps as $pid => $d) {
    $psRows[] = [$pid, $products[$pid] ?? 'Unknown', (string)$d['qty'], sprintf('%.2f', round($d['amt'], 2))];
}
writeCsv('/app/output/product_summary.csv', ['ProductID','ProductName','TotalQty','TotalAmount'], $psRows);

// regional_summary.csv
$rsRows = [];
foreach ($regionalTotals as $region => $d) {
    $rsRows[] = [$region, (string)$d['transactions'], sprintf('%.2f', $d['revenue'])];
}
writeCsv('/app/output/regional_summary.csv', ['Region','TransactionCount','TotalRevenue'], $rsRows);

// validation_report.csv
$vrRows = array_map(fn($r) => [$r[0], (string)$r[1], $r[2]], $rejections);
writeCsv('/app/output/validation_report.csv', ['SourceFile','RowNumber','Reason'], $vrRows);

// anomaly_report.csv
$arRows = array_map(fn($a) => [$a['ProductID'], $a['SourceFile'], (string)$a['RowNumber'],
    $a['UnitPrice'], $a['MedianPrice'], $a['DeviationPct']], $anomalies);
writeCsv('/app/output/anomaly_report.csv', ['ProductID','SourceFile','RowNumber','UnitPrice','MedianPrice','DeviationPct'], $arRows);
PHPEOF
php /app/src/process.php
