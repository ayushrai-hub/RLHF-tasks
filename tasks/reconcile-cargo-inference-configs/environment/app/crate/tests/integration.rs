//! Integration tests for the crate config loader. These exercise serving.toml
//! parsing; they do not concern the release-plan reconciliation.

use sentiment_infer::config::CrateConfig;

#[test]
fn loads_serving_ceilings() {
    let text = r#"
[serving]
max_batch_size = 16
max_concurrency = 16
request_timeout_ms = 2000
"#;
    let cfg = CrateConfig::from_toml(text).unwrap();
    assert_eq!(cfg.max_batch_size, 16);
    assert_eq!(cfg.max_concurrency, 16);
    assert_eq!(cfg.request_timeout_ms, 2000);
}

#[test]
fn falls_back_when_missing() {
    let text = "[serving]\nmax_batch_size = 8\n";
    let cfg = CrateConfig::from_toml(text).unwrap();
    assert_eq!(cfg.max_batch_size, 8);
    // concurrency falls back to the compile-time default
    assert_eq!(cfg.max_concurrency, 4);
}
