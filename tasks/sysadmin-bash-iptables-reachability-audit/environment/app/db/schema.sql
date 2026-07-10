-- iptables reachability audit store. Authoritative — do not modify.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS chains (
    table_name                 TEXT NOT NULL,
    name                       TEXT NOT NULL,
    chain_kind                 TEXT NOT NULL,
    default_policy             TEXT NOT NULL,
    packet_count               INTEGER NOT NULL,
    byte_count                 INTEGER NOT NULL,
    effective_default_policy   TEXT NOT NULL,
    is_dead_chain              INTEGER NOT NULL,
    is_effectively_dead_chain  INTEGER NOT NULL,
    PRIMARY KEY (table_name, name)
);

CREATE TABLE IF NOT EXISTS rules (
    rule_id                    TEXT PRIMARY KEY,
    table_name                 TEXT NOT NULL,
    chain                      TEXT NOT NULL,
    position                   INTEGER NOT NULL,
    target                     TEXT NOT NULL,
    target_args                TEXT NOT NULL,
    target_type                TEXT NOT NULL,
    matcher_csv                TEXT NOT NULL,
    is_unconditional           INTEGER NOT NULL,
    packet_count               INTEGER NOT NULL,
    byte_count                 INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rules_chain_position ON rules(table_name, chain, position);

CREATE TABLE IF NOT EXISTS chain_graph (
    from_table_name            TEXT NOT NULL,
    from_chain                 TEXT NOT NULL,
    to_table_name              TEXT NOT NULL,
    to_chain                   TEXT NOT NULL,
    via_rule_id                TEXT NOT NULL,
    PRIMARY KEY (from_table_name, from_chain, to_table_name, to_chain, via_rule_id)
);

CREATE TABLE IF NOT EXISTS rule_audit (
    rule_id                    TEXT PRIMARY KEY,
    is_reachable               INTEGER NOT NULL,
    blocked_by_rule_id         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS packet_traces (
    probe_id        TEXT PRIMARY KEY,
    entry_table     TEXT NOT NULL,
    entry_chain     TEXT NOT NULL,
    final_verdict   TEXT NOT NULL,
    decided_by      TEXT NOT NULL,
    hop_count       INTEGER NOT NULL,
    path            TEXT NOT NULL
);
