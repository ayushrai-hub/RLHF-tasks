use serde_json::{json, Value};

pub fn run_backward(_input: &Value) -> Value {
    json!({
        "ok": false,
        "error": "backward_not_implemented",
        "var_grads": {},
        "trace": []
    })
}
