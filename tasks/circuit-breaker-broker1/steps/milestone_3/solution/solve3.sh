#!/usr/bin/env bash
set -euo pipefail

cd /app

if [ -f /app/server.pid ]; then
    kill -9 "$(cat /app/server.pid)" 2>/dev/null || true
    rm -f /app/server.pid
fi
pkill -9 -f '/app/target/release/server' 2>/dev/null || true
sleep 0.3

mkdir -p /app/src /app/state

cat > /app/Cargo.toml <<'TOML_EOF'
[package]
name = "server"
version = "0.0.1"
edition = "2021"

[[bin]]
name = "server"
path = "src/main.rs"

[dependencies]
axum = "=0.7.9"
tokio = { version = "=1.44.2", features = ["rt-multi-thread", "macros", "net"] }
serde = { version = "=1.0.219", features = ["derive"] }
serde_json = { version = "=1.0.140", features = ["preserve_order"] }
parking_lot = "=0.12.3"
sha2 = "=0.10.8"
hex = "=0.4.3"
TOML_EOF

cat > /app/src/main.rs <<'RUST_EOF'
use axum::{
    body::Bytes,
    extract::{Path, Query, State},
    http::StatusCode,
    response::{Html, IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use parking_lot::Mutex;
use serde::{Serialize, Deserialize};
use serde_json::{json, Value};
use sha2::{Sha256, Digest};
use std::collections::HashMap;
use std::sync::Arc;

#[derive(Clone, Serialize, Deserialize)]
struct Breaker {
    id: String,
    policy: String,
    failure_threshold: u64,
    recovery_timeout_us: Option<u64>,
    window_us: Option<u64>,
    state: String, // "CLOSED", "OPEN", "HALF-OPEN"
    failure_count: u64,
    last_state_change_us: u64,
    failures: Vec<u64>,
}

#[derive(Clone, Serialize, Deserialize)]
struct AuditRow {
    id: u64,
    now_us: u64,
    breaker_ids: Vec<String>,
    allowed: bool,
    denied_by: Option<String>,
}

#[derive(Clone, Serialize, Deserialize)]
struct AlertThreshold {
    max_denial_count: u64,
    window_us: u64,
}

#[derive(Clone, Serialize, Deserialize)]
struct Alert {
    id: u64,
    now_us: u64,
    breaker_id: String,
    denial_count: u64,
    threshold: u64,
    severity: String,
}

struct AppState {
    now_us: Mutex<u64>,
    breakers: Mutex<HashMap<String, Breaker>>,
    audit: Mutex<Vec<AuditRow>>,
    audit_id_counter: Mutex<u64>,
    alert_thresholds: Mutex<HashMap<String, AlertThreshold>>,
    alerts: Mutex<Vec<Alert>>,
    alert_id_counter: Mutex<u64>,
    last_alert_at_us: Mutex<HashMap<String, u64>>,
}

fn breaker_to_json(b: &Breaker) -> Value {
    json!({
        "id": b.id,
        "policy": b.policy,
        "failure_threshold": b.failure_threshold,
        "recovery_timeout_us": b.recovery_timeout_us.map(|x| Value::Number(x.into())).unwrap_or(Value::Null),
        "window_us": b.window_us.map(|x| Value::Number(x.into())).unwrap_or(Value::Null),
        "state": b.state,
        "failure_count": b.failure_count,
        "last_state_change_us": b.last_state_change_us,
    })
}

fn err(code: StatusCode, msg: &str) -> Response {
    (code, Json(json!({"error": msg}))).into_response()
}

fn parse_json(body: &Bytes) -> Result<Value, Response> {
    if body.is_empty() {
        return Ok(json!({}));
    }
    serde_json::from_slice::<Value>(body).map_err(|_| err(StatusCode::BAD_REQUEST, "invalid json"))
}

fn id_valid(id: &str) -> bool {
    if id.is_empty() || id.len() > 64 {
        return false;
    }
    id.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
}

fn write_state(s: &AppState) {
    let now_val = *s.now_us.lock();
    let breakers = s.breakers.lock().clone();
    let audit = s.audit.lock().clone();
    let audit_id_counter = *s.audit_id_counter.lock();
    let alert_thresholds = s.alert_thresholds.lock().clone();
    let alerts = s.alerts.lock().clone();
    let alert_id_counter = *s.alert_id_counter.lock();
    let last_alert_at_us = s.last_alert_at_us.lock().clone();
    
    let sorted_breakers: std::collections::BTreeMap<String, Breaker> = breakers.into_iter().collect();
    let sorted_thresholds: std::collections::BTreeMap<String, AlertThreshold> = alert_thresholds.into_iter().collect();
    let sorted_last_alert: std::collections::BTreeMap<String, u64> = last_alert_at_us.into_iter().collect();

    let snapshot = json!({
        "schema_version": 1,
        "now_us": now_val,
        "breakers": sorted_breakers,
        "audit": audit,
        "audit_id_counter": audit_id_counter,
        "alert_thresholds": sorted_thresholds,
        "alerts": alerts,
        "alert_id_counter": alert_id_counter,
        "last_alert_at_us": sorted_last_alert,
    });
    
    let data = serde_json::to_string(&snapshot).unwrap();
    let tmp_path = "/app/state/state.json.tmp";
    let path = "/app/state/state.json";
    std::fs::write(tmp_path, data).unwrap();
    std::fs::rename(tmp_path, path).unwrap();
}

async fn index() -> impl IntoResponse {
    Html(
        r#"<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Circuit Breaker Broker</title>
<script src="chart.js"></script></head>
<body>
<h1>Circuit Breaker Broker</h1>
<canvas id="closedChart"></canvas>
<canvas id="openChart"></canvas>
<canvas id="breakersChart"></canvas>
</body></html>"#,
    )
}

async fn health() -> impl IntoResponse {
    Json(json!({"status": "ok"}))
}

async fn now(State(s): State<Arc<AppState>>) -> impl IntoResponse {
    let n = *s.now_us.lock();
    Json(json!({"now_us": n}))
}

async fn advance(State(s): State<Arc<AppState>>, body: Bytes) -> Response {
    let v = match parse_json(&body) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let micros = match v.get("micros") {
        Some(Value::Number(n)) => match n.as_i64() {
            Some(i) if i >= 0 => i as u64,
            _ => return err(StatusCode::BAD_REQUEST, "micros must be a non-negative integer"),
        },
        _ => return err(StatusCode::BAD_REQUEST, "micros required (non-negative integer)"),
    };
    let mut g = s.now_us.lock();
    *g = g.saturating_add(micros);
    let n = *g;
    drop(g);
    write_state(&s);
    Json(json!({"now_us": n})).into_response()
}

async fn create_breaker(State(s): State<Arc<AppState>>, body: Bytes) -> Response {
    let v = match parse_json(&body) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let id = match v.get("id").and_then(|x| x.as_str()) {
        Some(s) if id_valid(s) => s.to_string(),
        _ => return err(StatusCode::BAD_REQUEST, "id must be 1..=64 chars of [A-Za-z0-9_-]"),
    };
    let policy = match v.get("policy").and_then(|x| x.as_str()) {
        Some("simple") => "simple".to_string(),
        Some("sliding") => "sliding".to_string(),
        _ => return err(StatusCode::BAD_REQUEST, "policy must be 'simple' or 'sliding'"),
    };
    let failure_threshold = match v.get("failure_threshold").and_then(|x| x.as_i64()) {
        Some(i) if i >= 1 => i as u64,
        _ => return err(StatusCode::BAD_REQUEST, "failure_threshold must be integer >= 1"),
    };
    
    let recovery_timeout_us = match v.get("recovery_timeout_us") {
        None => None,
        Some(Value::Number(n)) => match n.as_i64() {
            Some(i) if i >= 1 => Some(i as u64),
            _ => return err(StatusCode::BAD_REQUEST, "recovery_timeout_us must be integer >= 1"),
        },
        _ => return err(StatusCode::BAD_REQUEST, "recovery_timeout_us must be integer >= 1"),
    };

    let window_us = match v.get("window_us") {
        None => None,
        Some(Value::Number(n)) => match n.as_i64() {
            Some(i) if i >= 1 => Some(i as u64),
            _ => return err(StatusCode::BAD_REQUEST, "window_us must be integer >= 1"),
        },
        _ => return err(StatusCode::BAD_REQUEST, "window_us must be integer >= 1"),
    };

    if policy == "simple" {
        if recovery_timeout_us.is_none() {
            return err(StatusCode::BAD_REQUEST, "recovery_timeout_us required for simple policy");
        }
        if window_us.is_some() {
            return err(StatusCode::BAD_REQUEST, "window_us not allowed for simple policy");
        }
    } else { // sliding
        if window_us.is_none() {
            return err(StatusCode::BAD_REQUEST, "window_us required for sliding policy");
        }
        if recovery_timeout_us.is_some() {
            return err(StatusCode::BAD_REQUEST, "recovery_timeout_us not allowed for sliding policy");
        }
    }

    let now_val = *s.now_us.lock();
    let mut bm = s.breakers.lock();
    if bm.contains_key(&id) {
        return err(StatusCode::CONFLICT, "breaker id already exists");
    }
    
    let b = Breaker {
        id: id.clone(),
        policy,
        failure_threshold,
        recovery_timeout_us,
        window_us,
        state: "CLOSED".to_string(),
        failure_count: 0,
        last_state_change_us: now_val,
        failures: Vec::new(),
    };
    let body = breaker_to_json(&b);
    bm.insert(id, b);
    drop(bm);
    write_state(&s);
    (StatusCode::CREATED, Json(body)).into_response()
}

async fn get_breaker(State(s): State<Arc<AppState>>, Path(id): Path<String>) -> Response {
    let bm = s.breakers.lock();
    match bm.get(&id) {
        Some(b) => Json(breaker_to_json(b)).into_response(),
        None => err(StatusCode::NOT_FOUND, "breaker not found"),
    }
}

async fn report(State(s): State<Arc<AppState>>, body: Bytes) -> Response {
    let v = match parse_json(&body) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let id = match v.get("id").and_then(|x| x.as_str()) {
        Some(s) if id_valid(s) => s.to_string(),
        _ => return err(StatusCode::BAD_REQUEST, "id invalid"),
    };
    let success = match v.get("success").and_then(|x| x.as_bool()) {
        Some(b) => b,
        _ => return err(StatusCode::BAD_REQUEST, "success required (boolean)"),
    };
    let now_val = *s.now_us.lock();
    let mut bm = s.breakers.lock();
    let b = match bm.get_mut(&id) {
        Some(b) => b,
        None => return err(StatusCode::NOT_FOUND, "breaker not found"),
    };

    let timeout = b.recovery_timeout_us.unwrap_or_else(|| b.window_us.unwrap_or(0));

    if b.state == "OPEN" {
        let retry_after = (b.last_state_change_us.saturating_add(timeout)).saturating_sub(now_val);
        return (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({
                "error": "circuit open",
                "state": "OPEN",
                "retry_after_us": retry_after
            }))
        ).into_response();
    }

    if b.policy == "simple" {
        if b.state == "CLOSED" {
            if !success {
                b.failure_count += 1;
                if b.failure_count >= b.failure_threshold {
                    b.state = "OPEN".to_string();
                    b.last_state_change_us = now_val;
                }
            } else {
                b.failure_count = 0;
            }
        } else if b.state == "HALF-OPEN" {
            if success {
                b.state = "CLOSED".to_string();
                b.failure_count = 0;
                b.last_state_change_us = now_val;
            } else {
                b.state = "OPEN".to_string();
                b.last_state_change_us = now_val;
            }
        }
    } else { // sliding
        if b.state == "CLOSED" {
            if !success {
                b.failures.push(now_val);
            }
            let win = b.window_us.unwrap_or(0);
            let start = now_val.saturating_sub(win);
            b.failures.retain(|&t| t >= start && t <= now_val);
            
            if b.failures.len() as u64 >= b.failure_threshold {
                b.state = "OPEN".to_string();
                b.last_state_change_us = now_val;
            }
        } else if b.state == "HALF-OPEN" {
            if success {
                b.state = "CLOSED".to_string();
                b.failures.clear();
                b.last_state_change_us = now_val;
            } else {
                b.state = "OPEN".to_string();
                b.failures.push(now_val);
                b.last_state_change_us = now_val;
            }
        }
    }

    drop(bm);
    write_state(&s);
    Json(json!({
        "id": id,
        "success": success
    })).into_response()
}

fn check_alerts(s: &Arc<AppState>, breaker_id: &str, now_val: u64) {
    let threshold = {
        let tm = s.alert_thresholds.lock();
        tm.get(breaker_id).cloned()
    };
    
    if let Some(t) = threshold {
        let cooldown_active = {
            let cooldowns = s.last_alert_at_us.lock();
            if let Some(&last_us) = cooldowns.get(breaker_id) {
                now_val < last_us + 60_000_000
            } else {
                false
            }
        };
        if cooldown_active {
            return;
        }
        
        let window_start = now_val.saturating_sub(t.window_us);
        let audit_log = s.audit.lock();
        let matching: Vec<AuditRow> = audit_log.iter()
            .filter(|r| r.breaker_ids.contains(&breaker_id.to_string()) && r.now_us >= window_start && r.now_us <= now_val)
            .cloned()
            .collect();
        drop(audit_log);
        
        if matching.len() >= 30 {
            let denial_count = matching.iter().filter(|r| !r.allowed).count() as u64;
            
            if denial_count > t.max_denial_count {
                let threshold_val = t.max_denial_count;
                let margin = (denial_count.saturating_sub(threshold_val)) as f64 / threshold_val.max(1) as f64;
                let severity = if margin < 0.25 {
                    "low"
                } else if margin < 0.50 {
                    "medium"
                } else if margin < 1.0 {
                    "high"
                } else {
                    "critical"
                };
                
                let mut alert_counter = s.alert_id_counter.lock();
                *alert_counter += 1;
                let alert = Alert {
                    id: *alert_counter,
                    now_us: now_val,
                    breaker_id: breaker_id.to_string(),
                    denial_count,
                    threshold: threshold_val,
                    severity: severity.to_string(),
                };
                
                s.alerts.lock().push(alert);
                s.last_alert_at_us.lock().insert(breaker_id.to_string(), now_val);
            }
        }
    }
}

async fn check(State(s): State<Arc<AppState>>, body: Bytes) -> Response {
    let v = match parse_json(&body) {
        Ok(v) => v,
        Err(r) => return r,
    };
    
    let mut ids = Vec::new();
    let is_composite = if let Some(arr) = v.get("breaker_ids").and_then(|x| x.as_array()) {
        for val in arr {
            if let Some(id) = val.as_str() {
                if id_valid(id) && !ids.contains(&id.to_string()) {
                    ids.push(id.to_string());
                } else {
                    return err(StatusCode::BAD_REQUEST, "breaker_ids invalid");
                }
            } else {
                return err(StatusCode::BAD_REQUEST, "breaker_ids elements must be strings");
            }
        }
        true
    } else {
        let breaker_id = match v.get("breaker_id").and_then(|x| x.as_str()) {
            Some(s) if id_valid(s) => s.to_string(),
            _ => return err(StatusCode::BAD_REQUEST, "breaker_id invalid"),
        };
        ids.push(breaker_id);
        false
    };

    if ids.is_empty() || ids.len() > 8 {
        return err(StatusCode::BAD_REQUEST, "breaker_ids length must be 1..=8");
    }

    let now_val = *s.now_us.lock();
    let mut bm = s.breakers.lock();
    
    // Auto half-open check for all queried breakers
    for id in &ids {
        if let Some(b) = bm.get_mut(id) {
            let timeout = b.recovery_timeout_us.unwrap_or_else(|| b.window_us.unwrap_or(0));
            if b.state == "OPEN" && now_val.saturating_sub(b.last_state_change_us) >= timeout {
                b.state = "HALF-OPEN".to_string();
                b.last_state_change_us = now_val;
            }
        } else {
            return err(StatusCode::NOT_FOUND, &format!("breaker {} not found", id));
        }
    }

    let mut denied_by = None;
    let mut max_retry = 0;
    let mut state_map = HashMap::new();

    for id in &ids {
        if let Some(b) = bm.get(id) {
            state_map.insert(id.clone(), b.state.clone());
            if b.state == "OPEN" {
                if denied_by.is_none() {
                    denied_by = Some(id.clone());
                }
                let timeout = b.recovery_timeout_us.unwrap_or_else(|| b.window_us.unwrap_or(0));
                let retry = (b.last_state_change_us.saturating_add(timeout)).saturating_sub(now_val);
                if retry > max_retry {
                    max_retry = retry;
                }
            }
        }
    }

    let allowed = denied_by.is_none();
    
    let mut a_counter = s.audit_id_counter.lock();
    *a_counter += 1;
    let row = AuditRow {
        id: *a_counter,
        now_us: now_val,
        breaker_ids: ids.clone(),
        allowed,
        denied_by: denied_by.clone(),
    };
    
    let mut audit_log = s.audit.lock();
    audit_log.push(row);
    if audit_log.len() > 1000 {
        audit_log.remove(0);
    }
    drop(audit_log);
    drop(a_counter);
    drop(bm);

    // Alert check
    for id in &ids {
        check_alerts(&s, id, now_val);
    }

    write_state(&s);

    if is_composite {
        if allowed {
            Json(json!({
                "allowed": true,
                "state_map": state_map
            })).into_response()
        } else {
            Json(json!({
                "allowed": false,
                "denied_by": denied_by.unwrap(),
                "retry_after_us": max_retry
            })).into_response()
        }
    } else {
        let single_id = &ids[0];
        let state = state_map.get(single_id).unwrap();
        if allowed {
            Json(json!({
                "allowed": true,
                "state": state
            })).into_response()
        } else {
            Json(json!({
                "allowed": false,
                "state": "OPEN",
                "retry_after_us": max_retry
            })).into_response()
        }
    }
}

async fn get_audit(State(s): State<Arc<AppState>>, Query(params): Query<HashMap<String, String>>) -> Response {
    let limit = match params.get("limit") {
        None => 100,
        Some(val) => match val.parse::<i64>() {
            Ok(i) if i >= 1 && i <= 1000 => i as usize,
            _ => return err(StatusCode::BAD_REQUEST, "invalid limit"),
        }
    };
    
    let breaker_id = params.get("breaker_id").cloned();
    let since_id = match params.get("since_id") {
        None => 0,
        Some(val) => match val.parse::<u64>() {
            Ok(i) => i,
            _ => return err(StatusCode::BAD_REQUEST, "invalid since_id"),
        }
    };

    let audit_log = s.audit.lock();
    let mut filtered: Vec<AuditRow> = audit_log.iter()
        .filter(|row| {
            if let Some(ref b_id) = breaker_id {
                row.breaker_ids.contains(b_id) && row.id > since_id
            } else {
                row.id > since_id
            }
        })
        .cloned()
        .collect();

    filtered.sort_by_key(|r| r.id);
    let len = filtered.len();
    let start = len.saturating_sub(limit);
    let slice = &filtered[start..];
    
    Json(json!({
        "audit": slice,
        "count": slice.len(),
    })).into_response()
}

async fn get_integrity(State(s): State<Arc<AppState>>) -> Response {
    let path = "/app/state/state.json";
    let exists = std::path::Path::new(path).exists();
    let (sha, snapshot) = if exists {
        let bytes = std::fs::read(path).unwrap();
        let mut hasher = Sha256::new();
        hasher.update(&bytes);
        let hash_hex = hex::encode(hasher.finalize());
        let val: Value = serde_json::from_slice(&bytes).unwrap();
        
        let count_breakers = val.get("breakers").and_then(|x| x.as_object()).map(|x| x.len()).unwrap_or(0);
        let count_audit = val.get("audit").and_then(|x| x.as_array()).map(|x| x.len()).unwrap_or(0);
        let count_alerts = val.get("alerts").and_then(|x| x.as_array()).map(|x| x.len()).unwrap_or(0);
        let audit_counter = val.get("audit_id_counter").and_then(|x| x.as_u64()).unwrap_or(0);
        let alert_counter = val.get("alert_id_counter").and_then(|x| x.as_u64()).unwrap_or(0);
        let now_us = val.get("now_us").and_then(|x| x.as_u64()).unwrap_or(0);
        
        (hash_hex, json!({
            "breakers": count_breakers,
            "audit": count_audit,
            "alerts": count_alerts,
            "audit_id_counter": audit_counter,
            "alert_id_counter": alert_counter,
            "now_us": now_us,
        }))
    } else {
        ("".to_string(), json!({
            "breakers": 0,
            "audit": 0,
            "alerts": 0,
            "audit_id_counter": 0,
            "alert_id_counter": 0,
            "now_us": 0,
        }))
    };

    Json(json!({
        "state_file_exists": exists,
        "sha256": sha,
        "snapshot": snapshot,
    })).into_response()
}

async fn reload_state(State(s): State<Arc<AppState>>) -> Response {
    let path = "/app/state/state.json";
    if !std::path::Path::new(path).exists() {
        *s.now_us.lock() = 0;
        s.breakers.lock().clear();
        s.audit.lock().clear();
        *s.audit_id_counter.lock() = 0;
        s.alert_thresholds.lock().clear();
        s.alerts.lock().clear();
        *s.alert_id_counter.lock() = 0;
        s.last_alert_at_us.lock().clear();
    } else {
        if let Ok(bytes) = std::fs::read(path) {
            if let Ok(val) = serde_json::from_slice::<Value>(&bytes) {
                *s.now_us.lock() = val.get("now_us").and_then(|x| x.as_u64()).unwrap_or(0);
                
                let mut bm = s.breakers.lock();
                bm.clear();
                if let Some(breakers_obj) = val.get("breakers").and_then(|x| x.as_object()) {
                    for (k, v) in breakers_obj {
                        if let Ok(b) = serde_json::from_value::<Breaker>(v.clone()) {
                            bm.insert(k.clone(), b);
                        }
                    }
                }
                
                let mut audit_log = s.audit.lock();
                audit_log.clear();
                if let Some(audit_arr) = val.get("audit").and_then(|x| x.as_array()) {
                    for v in audit_arr {
                        if let Ok(row) = serde_json::from_value::<AuditRow>(v.clone()) {
                            audit_log.push(row);
                        }
                    }
                }
                
                *s.audit_id_counter.lock() = val.get("audit_id_counter").and_then(|x| x.as_u64()).unwrap_or(0);
                
                let mut thresholds = s.alert_thresholds.lock();
                thresholds.clear();
                if let Some(t_obj) = val.get("alert_thresholds").and_then(|x| x.as_object()) {
                    for (k, v) in t_obj {
                        if let Ok(t) = serde_json::from_value::<AlertThreshold>(v.clone()) {
                            thresholds.insert(k.clone(), t);
                        }
                    }
                }
                
                let mut alerts_log = s.alerts.lock();
                alerts_log.clear();
                if let Some(alerts_arr) = val.get("alerts").and_then(|x| x.as_array()) {
                    for v in alerts_arr {
                        if let Ok(a) = serde_json::from_value::<Alert>(v.clone()) {
                            alerts_log.push(a);
                        }
                    }
                }
                
                *s.alert_id_counter.lock() = val.get("alert_id_counter").and_then(|x| x.as_u64()).unwrap_or(0);
                
                let mut last_alert = s.last_alert_at_us.lock();
                last_alert.clear();
                if let Some(la_obj) = val.get("last_alert_at_us").and_then(|x| x.as_object()) {
                    for (k, v) in la_obj {
                        if let Some(u) = v.as_u64() {
                            last_alert.insert(k.clone(), u);
                        }
                    }
                }
            }
        }
    }

    let exists = std::path::Path::new(path).exists();
    let (sha, snapshot) = if exists {
        let bytes = std::fs::read(path).unwrap();
        let mut hasher = Sha256::new();
        hasher.update(&bytes);
        let hash_hex = hex::encode(hasher.finalize());
        let val: Value = serde_json::from_slice(&bytes).unwrap();
        
        let count_breakers = val.get("breakers").and_then(|x| x.as_object()).map(|x| x.len()).unwrap_or(0);
        let count_audit = val.get("audit").and_then(|x| x.as_array()).map(|x| x.len()).unwrap_or(0);
        let count_alerts = val.get("alerts").and_then(|x| x.as_array()).map(|x| x.len()).unwrap_or(0);
        let audit_counter = val.get("audit_id_counter").and_then(|x| x.as_u64()).unwrap_or(0);
        let alert_counter = val.get("alert_id_counter").and_then(|x| x.as_u64()).unwrap_or(0);
        let now_us = val.get("now_us").and_then(|x| x.as_u64()).unwrap_or(0);
        
        (hash_hex, json!({
            "breakers": count_breakers,
            "audit": count_audit,
            "alerts": count_alerts,
            "audit_id_counter": audit_counter,
            "alert_id_counter": alert_counter,
            "now_us": now_us,
        }))
    } else {
        ("".to_string(), json!({
            "breakers": 0,
            "audit": 0,
            "alerts": 0,
            "audit_id_counter": 0,
            "alert_id_counter": 0,
            "now_us": 0,
        }))
    };

    Json(json!({
        "reloaded": true,
        "integrity": {
            "state_file_exists": exists,
            "sha256": sha,
            "snapshot": snapshot,
        }
    })).into_response()
}

async fn get_thresholds(State(s): State<Arc<AppState>>) -> Response {
    let tm = s.alert_thresholds.lock();
    let map: HashMap<String, AlertThreshold> = tm.clone();
    Json(map).into_response()
}

async fn post_thresholds(State(s): State<Arc<AppState>>, body: Bytes) -> Response {
    let v = match parse_json(&body) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let breaker_id = match v.get("breaker_id").and_then(|x| x.as_str()) {
        Some(s) if id_valid(s) => s.to_string(),
        _ => return err(StatusCode::BAD_REQUEST, "breaker_id invalid"),
    };
    
    {
        let bm = s.breakers.lock();
        if !bm.contains_key(&breaker_id) {
            return err(StatusCode::NOT_FOUND, "breaker not found");
        }
    }

    let max_denial = v.get("max_denial_count");
    let window_us = match v.get("window_us").and_then(|x| x.as_i64()) {
        Some(i) if i >= 1 => i as u64,
        _ => return err(StatusCode::BAD_REQUEST, "window_us invalid"),
    };

    let mut tm = s.alert_thresholds.lock();
    if max_denial.is_none() || max_denial.unwrap().is_null() {
        tm.remove(&breaker_id);
        drop(tm);
        write_state(&s);
        Json(json!({
            "breaker_id": breaker_id,
            "max_denial_count": Value::Null,
            "window_us": window_us
        })).into_response()
    } else {
        let count = match max_denial.unwrap().as_i64() {
            Some(i) if i >= 0 => i as u64,
            _ => return err(StatusCode::BAD_REQUEST, "max_denial_count must be integer >= 0"),
        };
        let t = AlertThreshold {
            max_denial_count: count,
            window_us,
        };
        tm.insert(breaker_id.clone(), t);
        drop(tm);
        write_state(&s);
        Json(json!({
            "breaker_id": breaker_id,
            "max_denial_count": count,
            "window_us": window_us
        })).into_response()
    }
}

async fn get_alerts(State(s): State<Arc<AppState>>, Query(params): Query<HashMap<String, String>>) -> Response {
    let limit = match params.get("limit") {
        None => 100,
        Some(val) => match val.parse::<i64>() {
            Ok(i) if i >= 1 && i <= 1000 => i as usize,
            _ => return err(StatusCode::BAD_REQUEST, "invalid limit"),
        }
    };
    
    let breaker_id = params.get("breaker_id").cloned();
    let since_id = match params.get("since_id") {
        None => 0,
        Some(val) => match val.parse::<u64>() {
            Ok(i) => i,
            _ => return err(StatusCode::BAD_REQUEST, "invalid since_id"),
        }
    };

    let alerts_log = s.alerts.lock();
    let mut filtered: Vec<Alert> = alerts_log.iter()
        .filter(|row| {
            if let Some(ref b_id) = breaker_id {
                row.breaker_id == *b_id && row.id > since_id
            } else {
                row.id > since_id
            }
        })
        .cloned()
        .collect();

    filtered.sort_by_key(|r| r.id);
    let len = filtered.len();
    let start = len.saturating_sub(limit);
    let slice = &filtered[start..];
    
    Json(json!({
        "alerts": slice,
        "count": slice.len(),
    })).into_response()
}

async fn clear_alerts(State(s): State<Arc<AppState>>) -> Response {
    s.alerts.lock().clear();
    *s.alert_id_counter.lock() = 0;
    s.last_alert_at_us.lock().clear();
    write_state(&s);
    Json(json!({"cleared": true})).into_response()
}

#[tokio::main]
async fn main() {
    let state = Arc::new(AppState {
        now_us: Mutex::new(0),
        breakers: Mutex::new(HashMap::new()),
        audit: Mutex::new(Vec::new()),
        audit_id_counter: Mutex::new(0),
        alert_thresholds: Mutex::new(HashMap::new()),
        alerts: Mutex::new(Vec::new()),
        alert_id_counter: Mutex::new(0),
        last_alert_at_us: Mutex::new(HashMap::new()),
    });
    
    // Auto load state
    {
        let path = "/app/state/state.json";
        if std::path::Path::new(path).exists() {
            if let Ok(bytes) = std::fs::read(path) {
                if let Ok(val) = serde_json::from_slice::<Value>(&bytes) {
                    *state.now_us.lock() = val.get("now_us").and_then(|x| x.as_u64()).unwrap_or(0);
                    let mut bm = state.breakers.lock();
                    if let Some(breakers_obj) = val.get("breakers").and_then(|x| x.as_object()) {
                        for (k, v) in breakers_obj {
                            if let Ok(b) = serde_json::from_value::<Breaker>(v.clone()) {
                                bm.insert(k.clone(), b);
                            }
                        }
                    }
                    let mut audit_log = state.audit.lock();
                    if let Some(audit_arr) = val.get("audit").and_then(|x| x.as_array()) {
                        for v in audit_arr {
                            if let Ok(row) = serde_json::from_value::<AuditRow>(v.clone()) {
                                audit_log.push(row);
                            }
                        }
                    }
                    *state.audit_id_counter.lock() = val.get("audit_id_counter").and_then(|x| x.as_u64()).unwrap_or(0);
                    let mut thresholds = state.alert_thresholds.lock();
                    if let Some(t_obj) = val.get("alert_thresholds").and_then(|x| x.as_object()) {
                        for (k, v) in t_obj {
                            if let Ok(t) = serde_json::from_value::<AlertThreshold>(v.clone()) {
                                thresholds.insert(k.clone(), t);
                            }
                        }
                    }
                    let mut alerts_log = state.alerts.lock();
                    if let Some(alerts_arr) = val.get("alerts").and_then(|x| x.as_array()) {
                        for v in alerts_arr {
                            if let Ok(a) = serde_json::from_value::<Alert>(v.clone()) {
                                alerts_log.push(a);
                            }
                        }
                    }
                    *state.alert_id_counter.lock() = val.get("alert_id_counter").and_then(|x| x.as_u64()).unwrap_or(0);
                    let mut last_alert = state.last_alert_at_us.lock();
                    if let Some(la_obj) = val.get("last_alert_at_us").and_then(|x| x.as_object()) {
                        for (k, v) in la_obj {
                            if let Some(u) = v.as_u64() {
                                last_alert.insert(k.clone(), u);
                            }
                        }
                    }
                }
            }
        }
    }

    let app = Router::new()
        .route("/", get(index))
        .route("/api/health", get(health))
        .route("/api/now", get(now))
        .route("/api/admin/advance", post(advance))
        .route("/api/breakers", post(create_breaker))
        .route("/api/breakers/:id", get(get_breaker))
        .route("/api/breakers/report", post(report))
        .route("/api/check", post(check))
        .route("/api/audit", get(get_audit))
        .route("/api/state/integrity", get(get_integrity))
        .route("/api/admin/reload-state", post(reload_state))
        .route("/api/alerts/thresholds", get(get_thresholds).post(post_thresholds))
        .route("/api/alerts", get(get_alerts))
        .route("/api/alerts/clear", post(clear_alerts))
        .with_state(state);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
RUST_EOF

cd /app
export CARGO_NET_OFFLINE=true
cargo build --release --offline 2>&1 | tail -5

for _ in $(seq 1 20); do
    if ! ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE '(:|\.)8080$'; then
        break
    fi
    sleep 0.2
done

nohup /app/target/release/server >/app/server.log 2>&1 &
echo $! > /app/server.pid
disown || true

for _ in $(seq 1 100); do
    if curl -fsS -m 2 http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
        echo "broker up (pid=$(cat /app/server.pid))"
        exit 0
    fi
    sleep 0.2
done

echo "broker failed to come up" >&2
cat /app/server.log >&2 || true
exit 1
