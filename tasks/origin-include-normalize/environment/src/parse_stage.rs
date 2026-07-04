use std::path::Path;

use crate::codec::{build_body, fold_label};
use crate::errors::Err;
use crate::model::{Edge, Row};

pub fn parse_lines(text: &str, anchor: &str, rel: &str) -> Result<Vec<Row>, Err> {
    let mut rows = Vec::new();
    let mut lane = 0u32;
    let mut cur_anchor = anchor.to_string();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with(';') {
            continue;
        }
        if let Some(rest) = line.strip_prefix("$ORIGIN") {
            cur_anchor = rest.trim().to_string();
            if !cur_anchor.ends_with('.') {
                cur_anchor.push('.');
            }
            continue;
        }
        if line.starts_with("$INCLUDE") {
            continue;
        }
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 4 {
            continue;
        }
        let mut idx = 0usize;
        let name = parts[idx].to_string();
        idx += 1;
        let mut ttl = 300u64;
        if parts[idx].chars().all(|c| c.is_ascii_digit()) {
            ttl = parts[idx].parse().unwrap_or(300);
            idx += 1;
        }
        if idx + 2 >= parts.len() {
            continue;
        }
        let klass = parts[idx].to_string();
        let rtype = parts[idx + 1].to_string();
        let mut rdata_parts: Vec<&str> = parts[idx + 2..].to_vec();
        let mut key = format!("auto{lane}");
        let mut mark = String::new();
        if let Some(pos) = rdata_parts.iter().position(|t| t.starts_with("@key=")) {
            if let Some(v) = rdata_parts[pos].strip_prefix("@key=") {
                key = v.to_string();
            }
            rdata_parts.remove(pos);
        }
        if let Some(pos) = rdata_parts.iter().position(|t| t.starts_with("@mark=")) {
            if let Some(v) = rdata_parts[pos].strip_prefix("@mark=") {
                mark = v.to_string();
            }
            rdata_parts.remove(pos);
        }
        let rdata = rdata_parts.join(" ");
        let holder = fold_label(&name, &cur_anchor);
        let body = build_body(&holder, &rtype, &klass, ttl, &rdata);
        rows.push(Row {
            key,
            mark,
            holder,
            rtype,
            klass,
            ttl,
            rdata,
            body,
            pkt: 0,
            byte: 0,
            lane,
            visit_ord: lane,
            anchor: cur_anchor.clone(),
            src_rel: rel.to_string(),
        });
        lane += 1;
    }
    let _ = rel;
    Ok(rows)
}
pub fn expand_includes(
    base: &Path,
    rel: &str,
    text: &str,
    anchor: &str,
) -> Result<(Vec<Row>, Vec<Edge>), Err> {
    let mut all_rows = Vec::new();
    let mut edges = Vec::new();
    let mut ord = 0u32;
    let mut cur_anchor = anchor.to_string();
    for line in text.lines() {
        let line = line.trim();
        if let Some(rest) = line.strip_prefix("$ORIGIN") {
            cur_anchor = rest.trim().to_string();
            if !cur_anchor.ends_with('.') {
                cur_anchor.push('.');
            }
            continue;
        }
        if let Some(rest) = line.strip_prefix("$INCLUDE") {
            let toks: Vec<&str> = rest.split_whitespace().collect();
            if toks.is_empty() {
                continue;
            }
            let child_rel = toks[0];
            let child_anchor = if toks.len() > 1 {
                let mut a = toks[1].to_string();
                if !a.ends_with('.') {
                    a.push('.');
                }
                a
            } else {
                cur_anchor.clone()
            };
            edges.push(Edge {
                from: rel.to_string(),
                to: child_rel.to_string(),
                ord,
            });
            ord += 1;
            let child = base.join(child_rel);
            let body = std::fs::read_to_string(&child).map_err(|e| Err::new(40, e.to_string()))?;
            let (sub_rows, sub_edges) =
                expand_includes(base, child_rel, &body, &child_anchor)?;
            edges.extend(sub_edges);
            all_rows.extend(sub_rows);
            continue;
        }
    }
    let local = parse_lines(text, &cur_anchor, rel)?;
    all_rows.extend(local);
    Ok((all_rows, edges))
}
