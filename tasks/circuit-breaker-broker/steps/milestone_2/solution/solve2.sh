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
use serde::Serialize;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::Arc;

#[derive(Clone, Serialize)]
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

#[derive(Clone, Serialize)]
struct AuditRow {
    id: u64,
    now_us: u64,
    breaker_ids: Vec<String>,
    allowed: bool,
    denied_by: Option<String>,
}

struct AppState {
    now_us: Mutex<u64>,
    breakers: Mutex<HashMap<String, Breaker>>,
    audit: Mutex<Vec<AuditRow>>,
    audit_id_counter: Mutex<u64>,
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

    Json(breaker_to_json(b)).into_response()
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
                    return err(StatusCode::BAD_REQUEST, "breaker_ids invalid or contains duplicates");
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

    // Evaluate route checks
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
    
    // Log to audit
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

#[tokio::main]
async fn main() {
    let state = Arc::new(AppState {
        now_us: Mutex::new(0),
        breakers: Mutex::new(HashMap::new()),
        audit: Mutex::new(Vec::new()),
        audit_id_counter: Mutex::new(0),
    });
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
