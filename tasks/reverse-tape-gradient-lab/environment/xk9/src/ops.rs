
use serde_json::Value;

pub fn num(v: &Value) -> f64 {
    v.as_f64().unwrap_or(0.0)
}

pub fn shape_of(v: &Value) -> Vec<usize> {
    if let Some(s) = v.get("shape").and_then(|s| s.as_array()) {
        return s
            .iter()
            .filter_map(|x| x.as_u64().map(|n| n as usize))
            .collect();
    }
    if let Some(s) = v.as_array() {
        return s
            .iter()
            .filter_map(|x| x.as_u64().map(|n| n as usize))
            .collect();
    }
    vec![]
}

pub fn data_of(v: &Value) -> Vec<f64> {
    v.get("data")
        .and_then(|d| d.as_array())
        .map(|a| a.iter().map(num).collect())
        .unwrap_or_default()
}

pub fn size(shape: &[usize]) -> usize {
    shape.iter().product::<usize>().max(1)
}

pub fn broadcast_shapes(a: &[usize], b: &[usize]) -> Option<Vec<usize>> {
    let ra: Vec<usize> = a.iter().rev().copied().collect();
    let rb: Vec<usize> = b.iter().rev().copied().collect();
    let n = ra.len().max(rb.len());
    let mut out_rev = Vec::new();
    for i in 0..n {
        let da = if i < ra.len() { ra[i] } else { 1 };
        let db = if i < rb.len() { rb[i] } else { 1 };
        if da == db || da == 1 || db == 1 {
            out_rev.push(da.max(db));
        } else {
            return None;
        }
    }
    let mut out: Vec<usize> = out_rev.into_iter().rev().collect();
    if out.is_empty() {
        out.push(1);
    }
    Some(out)
}

pub fn broadcast_to(data: &[f64], from: &[usize], to: &[usize]) -> Vec<f64> {
    let to_size = size(to);
    let mut out = vec![0.0; to_size];
    let from_rank = from.len();
    let to_rank = to.len();
    let offset = to_rank.saturating_sub(from_rank);
    for flat in 0..to_size {
        let mut rem = flat;
        let mut coords = vec![0usize; to_rank];
        for i in (0..to_rank).rev() {
            coords[i] = rem % to[i];
            rem /= to[i];
        }
        let mut src_flat = 0usize;
        let mut stride = 1usize;
        for i in (0..from_rank).rev() {
            let to_axis = offset + i;
            let c = if from[i] == 1 {
                0
            } else {
                coords[to_axis]
            };
            src_flat += c * stride;
            stride *= from[i];
        }
        out[flat] = data[src_flat.min(data.len().saturating_sub(1))];
    }
    out
}

pub fn reduce_sum(data: &[f64], shape: &[usize], axes: &[i64]) -> (Vec<f64>, Vec<usize>) {
    let rank = shape.len();
    let mut norm: Vec<usize> = axes
        .iter()
        .map(|&a| {
            let ai = a as i64;
            if ai < 0 { (rank as i64 + ai) as usize } else { ai as usize }
        })
        .collect();
    norm.sort_unstable();
    norm.dedup();
    let out_shape: Vec<usize> = shape
        .iter()
        .enumerate()
        .filter_map(|(i, &d)| if norm.contains(&i) { None } else { Some(d) })
        .collect();
    let out_shape = if out_shape.is_empty() { vec![1] } else { out_shape };
    let mut out = vec![0.0; size(&out_shape)];
    let in_size = size(shape);
    for flat in 0..in_size {
        let mut idx = flat;
        let mut coords = vec![0usize; rank];
        for i in (0..rank).rev() {
            coords[i] = idx % shape[i];
            idx /= shape[i];
        }
        let mut oidx = 0usize;
        let mut stride = 1usize;
        for (i, &d) in out_shape.iter().enumerate().rev() {
            let src_axis = shape
                .iter()
                .enumerate()
                .filter(|(j, _)| !norm.contains(j))
                .map(|(j, _)| j)
                .nth(out_shape.len() - 1 - i)
                .unwrap_or(0);
            oidx += coords[src_axis] * stride;
            stride *= d;
        }
        let val = data[flat];
        let idx = oidx.min(out.len().saturating_sub(1));
        out[idx] += val;
    }
    if out_shape == vec![1] && shape.is_empty() {
        out = vec![data[0]];
    }
    (out, out_shape)
}
