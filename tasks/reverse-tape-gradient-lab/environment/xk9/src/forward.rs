use crate::ops::{broadcast_shapes, broadcast_to, data_of, num, reduce_sum, shape_of, size};
use serde_json::{json, Map, Value};
use std::collections::HashMap;

pub fn run_forward(input: &Value) -> Value {
    let graph = input.get("graph").unwrap_or(input);
    let mut values: Map<String, Value> = Map::new();
    let mut shapes: HashMap<String, Vec<usize>> = HashMap::new();

    if let Some(vars) = graph.get("vars").and_then(|v| v.as_object()) {
        for (name, spec) in vars {
            let shape = shape_of(spec);
            let data = data_of(spec);
            values.insert(name.clone(), json!(data));
            shapes.insert(name.clone(), shape);
        }
    }

    let mut trace = Vec::new();
    if let Some(nodes) = graph.get("nodes").and_then(|v| v.as_array()) {
        for node in nodes {
            let id = node.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let op = node.get("op").and_then(|v| v.as_str()).unwrap_or("");
            let inputs: Vec<String> = node
                .get("inputs")
                .and_then(|v| v.as_array())
                .map(|a| a.iter().filter_map(|x| x.as_str().map(str::to_string)).collect())
                .unwrap_or_default();
            let (data, shape) = match op {
                "add" | "mul" => {
                    let a = values.get(&inputs[0]).cloned().unwrap_or(json!([]));
                    let b = values.get(&inputs[1]).cloned().unwrap_or(json!([]));
                    let sa = shapes.get(&inputs[0]).cloned().unwrap_or_default();
                    let sb = shapes.get(&inputs[1]).cloned().unwrap_or_default();
                    let out_shape = match broadcast_shapes(&sa, &sb) {
                        Some(s) => s,
                        None => {
                            return json!({"ok": false, "error": "broadcast"});
                        }
                    };
                    let da = a.as_array().unwrap();
                    let db = b.as_array().unwrap();
                    let fa: Vec<f64> = da.iter().map(num).collect();
                    let fb: Vec<f64> = db.iter().map(num).collect();
                    let ba = broadcast_to(&fa, &sa, &out_shape);
                    let bb = broadcast_to(&fb, &sb, &out_shape);
                    let out: Vec<f64> = ba
                        .iter()
                        .zip(bb.iter())
                        .map(|(x, y)| if op == "add" { x + y } else { x * y })
                        .collect();
                    (out, out_shape)
                }
                "matmul" => {
                    let a = values.get(&inputs[0]).cloned().unwrap_or(json!([]));
                    let b = values.get(&inputs[1]).cloned().unwrap_or(json!([]));
                    let sa = shapes.get(&inputs[0]).cloned().unwrap_or_default();
                    let sb = shapes.get(&inputs[1]).cloned().unwrap_or_default();
                    if sa.len() < 2 || sb.len() < 2 {
                        return json!({"ok": false, "error": "matmul rank"});
                    }
                    let m = sa[sa.len() - 2];
                    let k = sa[sa.len() - 1];
                    let k2 = sb[sb.len() - 2];
                    let n = sb[sb.len() - 1];
                    if k != k2 {
                        return json!({"ok": false, "error": "matmul inner"});
                    }
                    let batch: Vec<usize> = sa[..sa.len() - 2].to_vec();
                    let batch_size = batch.iter().product::<usize>().max(1);
                    let fa: Vec<f64> = a.as_array().unwrap().iter().map(num).collect();
                    let fb: Vec<f64> = b.as_array().unwrap().iter().map(num).collect();
                    let mut out_shape = batch.clone();
                    out_shape.push(m);
                    out_shape.push(n);
                    let mut out = vec![0.0; size(&out_shape)];
                    for bidx in 0..batch_size {
                        for i in 0..m {
                            for j in 0..n {
                                let mut sum = 0.0;
                                for t in 0..k {
                                    let a_idx = bidx * m * k + i * k + t;
                                    let b_idx = bidx * k * n + t * n + j;
                                    sum += fa[a_idx] * fb[b_idx];
                                }
                                out[bidx * m * n + i * n + j] = sum;
                            }
                        }
                    }
                    (out, out_shape)
                }
                "reduce_sum" => {
                    let a = values.get(&inputs[0]).cloned().unwrap_or(json!([]));
                    let sa = shapes.get(&inputs[0]).cloned().unwrap_or_default();
                    let fa: Vec<f64> = a.as_array().unwrap().iter().map(num).collect();
                    let axes: Vec<i64> = node
                        .get("axes")
                        .and_then(|v| v.as_array())
                        .map(|arr| arr.iter().filter_map(|x| x.as_i64()).collect())
                        .unwrap_or_default();
                    let (out, out_shape) = reduce_sum(&fa, &sa, &axes);
                    (out, out_shape)
                }
                _ => (vec![0.0], vec![1]),
            };
            values.insert(id.clone(), json!(data));
            shapes.insert(id.clone(), shape.clone());
            trace.push(json!({"node_id": id, "op": op, "forward": data}));
        }
    }

    let loss_id = graph.get("loss").and_then(|v| v.as_str()).unwrap_or("out");
    let loss = values
        .get(loss_id)
        .and_then(|v| v.as_array())
        .and_then(|a| a.first())
        .map(num)
        .unwrap_or(0.0);

    let mut shapes_json = Map::new();
    for (k, v) in &shapes {
        shapes_json.insert(k.clone(), json!(v));
    }

    json!({"ok": true, "values": values, "shapes": shapes_json, "trace": trace, "loss": loss})
}
