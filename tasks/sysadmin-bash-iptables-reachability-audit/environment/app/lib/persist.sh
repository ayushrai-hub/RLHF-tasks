persist_normalized() {
    require_cmd sqlite3 || return 1
    require_cmd jq || return 1

    db_init
    log_info "persisting $NORMALIZED_PATH -> $DB_PATH (scaffold only)"

    # Scaffold-only: log a warning so it is clear the audit tables are
    # not yet populated. The agent's job is to replace this body.
    log_warn "persist_normalized is incomplete — no rows inserted into chains/rules/chain_graph/rule_audit"
}
