<?php
// Minimal PSR-4-ish autoloader for the QuestCapsule namespace. No Composer, no network.
spl_autoload_register(function (string $class): void {
    $prefix = 'QuestCapsule\\';
    if (strncmp($class, $prefix, strlen($prefix)) !== 0) {
        return;
    }
    $rel = substr($class, strlen($prefix));
    $path = dirname(__DIR__) . '/src/QuestCapsule/' . str_replace('\\', '/', $rel) . '.php';
    if (is_file($path)) {
        require $path;
    }
});
