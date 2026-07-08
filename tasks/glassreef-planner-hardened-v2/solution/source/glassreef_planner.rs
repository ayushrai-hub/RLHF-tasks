use glassreef_planner::core::csv::read_csv;
use glassreef_planner::core::digest::fnv1a64_hex;
use glassreef_planner::core::json::{esc, string_array};
use glassreef_planner::core::reachability::reachable;
use glassreef_planner::core::time::hour_index;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::process::Command;

#[derive(Clone)]
struct Station { id: String, kind: String, priority: i64 }
#[derive(Clone)]
struct Span { id: String, from: String, to: String, region: String, depth_m: i64, status: String, splice_family: String, priority_base: i64, corridor: String, length_nm: f64 }
#[derive(Clone)]
struct Ship { id: String, available: String, kits: Vec<String>, depth_rating: i64, max_sea: i64, crew: String }
#[derive(Clone)]
struct Window { id: String, region: String, start: String, end: String, max_sea: i64, current_limit: f64 }
#[derive(Clone)]
struct Current { corridor: String, window: String, mean: f64, bearing: f64 }
#[derive(Clone)]
struct Blackout { ship_id: String, start: String, end: String }
#[derive(Clone)]
struct Mission { cooldown_hours: i64, blackouts: Vec<Blackout> }
#[derive(Clone)]
struct Repair { span_id: String, ship_id: String, start: String, end: String, family: String, score: i64, restored: Vec<String>, reason: String }
#[derive(Clone)]
struct Reject { span_id: String, reason: String }

fn arg_value(args: &[String], name: &str, default: &str) -> String {
    let mut i = 1;
    while i + 1 < args.len() {
        if args[i] == name { return args[i + 1].clone(); }
        i += 1;
    }
    default.to_string()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mission_id = arg_value(&args, "--mission-id", "glassreef-primary");
    let output = arg_value(&args, "--output", "/app/output/repair_plan.json");

    let mission = load_mission("/app/data/missions/glassreef_primary.json");
    let stations = apply_station_profiles(load_stations("/app/data/network/stations.csv"), "/app/data/network/station_profiles");
    let spans = load_spans("/app/data/network/spans.csv");
    let ships = load_ships("/app/data/vessels/ships.csv");
    let windows = load_windows("/app/data/weather/windows.csv");
    let currents = load_currents("/app/data/currents/corridors.csv");
    let rules = load_rules("/app/build/splice_rules.csv");
    let hazard_penalty = load_hazard_penalties("/app/data/reference/hazards");

    let station_map: HashMap<String, Station> = stations.iter().map(|s| (s.id.clone(), s.clone())).collect();
    let mut shores: Vec<String> = stations.iter().filter(|s| s.kind.as_str() == "shore").map(|s| s.id.clone()).collect();
    shores.sort();
    let ok_edges: Vec<(String, String)> = spans.iter().filter(|s| s.status.as_str() == "OK").map(|s| (s.from.clone(), s.to.clone())).collect();
    let base_reach = reachable(&shores, &ok_edges);

    let mut candidate_bundles: Vec<(Span, Vec<Repair>, String)> = Vec::new();
    let mut broken: Vec<Span> = spans.iter().filter(|s| s.status.as_str() == "BROKEN").cloned().collect();
    broken.sort_by(|a, b| a.id.cmp(&b.id));

    for span in broken {
        let restored = restored_stations(&span, &ok_edges, &base_reach, &shores, &station_map);
        let restored_priority: i64 = restored.iter().filter_map(|id| station_map.get(id)).map(|s| s.priority).sum();
        let duration = duration_hours(span.length_nm);
        let mut candidates = Vec::new();
        let mut compatible_seen = false;
        let mut weather_seen = false;
        let mut current_seen = false;
        let mut duration_seen = false;
        let mut blackout_free_seen = false;
        for ship in &ships {
            if ship.depth_rating < span.depth_m { continue; }
            let best_bonus = best_compatibility_bonus(&rules, &span.splice_family, &ship.kits);
            let best_bonus = match best_bonus { Some(v) => v, None => continue };
            compatible_seen = true;
            for window in &windows {
                if window.region.as_str() != span.region.as_str() { continue; }
                if ship.available.as_str() > window.start.as_str() { continue; }
                if ship.max_sea < window.max_sea { continue; }
                weather_seen = true;
                let cur = currents.iter().find(|c| c.corridor.as_str() == span.corridor.as_str() && c.window.as_str() == window.id.as_str());
                let cur = match cur { Some(c) => c, None => continue };
                if cur.mean > window.current_limit { continue; }
                current_seen = true;
                let end = add_hours(&window.start, duration);
                if hour_index(&end) > hour_index(&window.end) { continue; }
                duration_seen = true;
                if overlaps_blackout(&ship.id, &window.start, &end, &mission.blackouts) { continue; }
                blackout_free_seen = true;
                let drift = drift_penalty(cur.mean, cur.bearing, span.depth_m);
                let score = total_score(span.priority_base, restored_priority, best_bonus, drift, span.depth_m, &ship.crew, *hazard_penalty.get(&span.region).unwrap_or(&0));
                candidates.push(Repair { span_id: span.id.clone(), ship_id: ship.id.clone(), start: window.start.clone(), end, family: span.splice_family.clone(), score, restored: restored.clone(), reason: "scheduled".to_string() });
            }
        }
        candidates.sort_by(|a, b| b.score.cmp(&a.score).then(a.start.cmp(&b.start)).then(a.ship_id.cmp(&b.ship_id)).then(a.span_id.cmp(&b.span_id)));
        let fallback = if !compatible_seen { "no-compatible-ship" } else if !weather_seen { "no-weather-window" } else if !current_seen { "no-current-window" } else if !duration_seen { "no-duration-window" } else if !blackout_free_seen { "ship-blackout" } else { "ship-window-conflict" };
        candidate_bundles.push((span, candidates, fallback.to_string()));
    }

    candidate_bundles.sort_by(|a, b| {
        let ascore = a.1.get(0).map(|r| r.score).unwrap_or(-999999);
        let bscore = b.1.get(0).map(|r| r.score).unwrap_or(-999999);
        let astart = a.1.get(0).map(|r| r.start.as_str()).unwrap_or("9999");
        let bstart = b.1.get(0).map(|r| r.start.as_str()).unwrap_or("9999");
        bscore.cmp(&ascore).then(astart.cmp(bstart)).then(a.0.id.cmp(&b.0.id))
    });

    let mut repairs = Vec::new();
    let mut rejects = Vec::new();
    let mut ship_busy: HashMap<String, Vec<(String, String)>> = HashMap::new();
    for (span, candidates, fallback) in candidate_bundles {
        let mut chosen: Option<Repair> = None;
        for cand in candidates {
            let busy = ship_busy.entry(cand.ship_id.clone()).or_default();
            if can_schedule(&cand, busy, mission.cooldown_hours) {
                busy.push((cand.start.clone(), cand.end.clone()));
                chosen = Some(cand);
                break;
            }
        }
        if let Some(r) = chosen { repairs.push(r); }
        else { rejects.push(Reject { span_id: span.id, reason: fallback }); }
    }

    repairs.sort_by(|a, b| b.score.cmp(&a.score).then(a.start.cmp(&b.start)).then(a.span_id.cmp(&b.span_id)));
    rejects.sort_by(|a, b| a.span_id.cmp(&b.span_id));

    let mut final_edges = ok_edges.clone();
    let repaired: HashSet<String> = repairs.iter().map(|r| r.span_id.clone()).collect();
    for span in &spans {
        if repaired.contains(&span.id) { final_edges.push((span.from.clone(), span.to.clone())); }
    }
    let final_reach = reachable(&shores, &final_edges);
    let mut unreachable: Vec<String> = stations.iter().filter(|s| s.kind.as_str() != "shore" && !final_reach.contains(&s.id)).map(|s| s.id.clone()).collect();
    unreachable.sort();

    let digest = plan_digest(&repairs, &rejects, &unreachable);
    let json = render_json(&mission_id, &repairs, &rejects, &unreachable, &digest);
    if let Some(parent) = Path::new(&output).parent() { let _ = fs::create_dir_all(parent); }
    fs::write(output, json).expect("write repair plan");
}

fn csv_last_wins(path: &str, keys: &[&str]) -> Vec<HashMap<String, String>> {
    let rows = read_csv(path);
    let mut order: Vec<String> = Vec::new();
    let mut seen: HashMap<String, HashMap<String, String>> = HashMap::new();
    for row in rows {
        let key = keys.iter().map(|k| row.get(*k).cloned().unwrap_or_default()).collect::<Vec<_>>().join("\u{1f}");
        if !seen.contains_key(&key) { order.push(key.clone()); }
        seen.insert(key, row);
    }
    order.into_iter().filter_map(|key| seen.remove(&key)).collect()
}

fn load_stations(path: &str) -> Vec<Station> {
    csv_last_wins(path, &["station_id"]).into_iter().map(|r| Station { id: val(&r, "station_id"), kind: val(&r, "kind"), priority: parse_i(&r, "priority") }).collect()
}
fn apply_station_profiles(mut stations: Vec<Station>, dir: &str) -> Vec<Station> {
    let mut paths: Vec<_> = match fs::read_dir(dir) { Ok(entries) => entries.flatten().map(|e| e.path()).collect(), Err(_) => Vec::new() };
    paths.sort();
    for path in paths {
        if path.extension().and_then(|s| s.to_str()) != Some("json") { continue; }
        let text = match fs::read_to_string(path) { Ok(t) => t, Err(_) => continue };
        let id = match json_string_field(&text, "station_id") { Some(v) => v, None => continue };
        if let Some(station) = stations.iter_mut().find(|s| s.id == id) {
            if let Some(kind) = json_string_field(&text, "kind") { station.kind = kind; }
            if let Some(priority) = json_int_field(&text, "priority") { station.priority = priority; }
        }
    }
    stations
}
fn load_spans(path: &str) -> Vec<Span> {
    csv_last_wins(path, &["span_id"]).into_iter().map(|r| Span { id: val(&r, "span_id"), from: val(&r, "from"), to: val(&r, "to"), region: val(&r, "region"), depth_m: parse_i(&r, "depth_m"), status: val(&r, "status"), splice_family: val(&r, "splice_family"), priority_base: parse_i(&r, "priority_base"), corridor: val(&r, "current_corridor"), length_nm: parse_f(&r, "length_nm") }).collect()
}
fn load_ships(path: &str) -> Vec<Ship> {
    csv_last_wins(path, &["ship_id"]).into_iter().map(|r| Ship { id: val(&r, "ship_id"), available: val(&r, "available_from_utc"), kits: val(&r, "splice_kits").split('|').map(|s| s.to_string()).collect(), depth_rating: parse_i(&r, "depth_rating_m"), max_sea: parse_i(&r, "max_sea_state"), crew: val(&r, "crew_grade") }).collect()
}
fn load_windows(path: &str) -> Vec<Window> {
    csv_last_wins(path, &["window_id"]).into_iter().map(|r| Window { id: val(&r, "window_id"), region: val(&r, "region"), start: val(&r, "start_utc"), end: val(&r, "end_utc"), max_sea: parse_i(&r, "max_sea_state"), current_limit: parse_f(&r, "current_limit_mps") }).collect()
}
fn load_currents(path: &str) -> Vec<Current> {
    csv_last_wins(path, &["corridor_id", "window_id"]).into_iter().map(|r| Current { corridor: val(&r, "corridor_id"), window: val(&r, "window_id"), mean: parse_f(&r, "mean_mps"), bearing: parse_f(&r, "bearing_deg") }).collect()
}
fn load_rules(path: &str) -> HashMap<String, Vec<(String, i64)>> {
    let mut map: HashMap<String, Vec<(String, i64)>> = HashMap::new();
    for r in csv_last_wins(path, &["family", "kit"]) {
        map.entry(val(&r, "family")).or_default().push((val(&r, "kit"), parse_i(&r, "bonus")));
    }
    map
}
fn load_mission(path: &str) -> Mission {
    let text = fs::read_to_string(path).unwrap_or_default();
    let cooldown_hours = json_int_field(&text, "ship_cooldown_hours").unwrap_or(0);
    let mut blackouts = Vec::new();
    for obj in json_array_objects(&text, "ship_blackouts") {
        let ship_id = json_string_field(&obj, "ship_id").unwrap_or_default();
        let start = json_string_field(&obj, "start_utc").unwrap_or_default();
        let end = json_string_field(&obj, "end_utc").unwrap_or_default();
        if !ship_id.is_empty() && !start.is_empty() && !end.is_empty() { blackouts.push(Blackout { ship_id, start, end }); }
    }
    Mission { cooldown_hours, blackouts }
}
fn val(row: &HashMap<String, String>, key: &str) -> String { row.get(key).cloned().unwrap_or_default() }
fn parse_i(row: &HashMap<String, String>, key: &str) -> i64 { val(row, key).parse().unwrap_or(0) }
fn parse_f(row: &HashMap<String, String>, key: &str) -> f64 { val(row, key).parse().unwrap_or(0.0) }

fn load_hazard_penalties(dir: &str) -> HashMap<String, i64> {
    let mut totals: HashMap<String, i64> = HashMap::new();
    let entries = match fs::read_dir(dir) { Ok(e) => e, Err(_) => return totals };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) != Some("json") { continue; }
        let text = match fs::read_to_string(path) { Ok(t) => t, Err(_) => continue };
        let region = match json_string_field(&text, "region") { Some(v) => v, None => continue };
        let severity = match json_int_field(&text, "severity") { Some(v) => v, None => continue };
        *totals.entry(region).or_insert(0) += severity;
    }
    totals.into_iter().map(|(region, severity)| (region, severity / 100)).collect()
}
fn json_string_field(text: &str, key: &str) -> Option<String> {
    let marker = format!("\"{}\"", key);
    let pos = text.find(&marker)?;
    let after = &text[pos + marker.len()..];
    let colon = after.find(':')?;
    let rest = &after[colon + 1..];
    let start = rest.find('"')?;
    let rest2 = &rest[start + 1..];
    let end = rest2.find('"')?;
    Some(rest2[..end].to_string())
}
fn json_int_field(text: &str, key: &str) -> Option<i64> {
    let marker = format!("\"{}\"", key);
    let pos = text.find(&marker)?;
    let after = &text[pos + marker.len()..];
    let colon = after.find(':')?;
    let rest = after[colon + 1..].trim_start();
    let mut end = 0;
    for (i, ch) in rest.char_indices() {
        if i == 0 && ch == '-' { end = 1; continue; }
        if ch.is_ascii_digit() { end = i + ch.len_utf8(); } else { break; }
    }
    if end == 0 { return None; }
    rest[..end].parse().ok()
}
fn json_array_objects(text: &str, key: &str) -> Vec<String> {
    let marker = format!("\"{}\"", key);
    let pos = match text.find(&marker) { Some(v) => v, None => return Vec::new() };
    let after = &text[pos + marker.len()..];
    let array_start_rel = match after.find('[') { Some(v) => v, None => return Vec::new() };
    let array_text = &after[array_start_rel + 1..];
    let mut out = Vec::new();
    let mut depth = 0_i32;
    let mut obj_start: Option<usize> = None;
    for (i, ch) in array_text.char_indices() {
        match ch {
            '{' => {
                if depth == 0 { obj_start = Some(i); }
                depth += 1;
            }
            '}' => {
                depth -= 1;
                if depth == 0 {
                    if let Some(start) = obj_start.take() { out.push(array_text[start..=i].to_string()); }
                }
            }
            ']' if depth == 0 => break,
            _ => {}
        }
    }
    out
}

fn best_compatibility_bonus(rules: &HashMap<String, Vec<(String, i64)>>, family: &str, kits: &[String]) -> Option<i64> {
    let mut best: Option<i64> = None;
    if let Some(entries) = rules.get(family) {
        for (kit, bonus) in entries {
            if kits.iter().any(|k| k == kit) {
                best = Some(best.map(|b| b.max(*bonus)).unwrap_or(*bonus));
            }
        }
    }
    best
}
fn restored_stations(span: &Span, ok_edges: &[(String, String)], base: &HashSet<String>, shores: &[String], stations: &HashMap<String, Station>) -> Vec<String> {
    let mut edges = ok_edges.to_vec();
    edges.push((span.from.clone(), span.to.clone()));
    let after = reachable(shores, &edges);
    let mut out: Vec<String> = after.into_iter().filter(|id| !base.contains(id)).filter(|id| stations.get(id).map(|s| s.kind.as_str() != "shore").unwrap_or(false)).collect();
    out.sort();
    out
}
fn drift_penalty(mean: f64, bearing: f64, depth: i64) -> i64 {
    let out = Command::new("/app/build/current_adjust").arg(format!("{:.3}", mean)).arg(format!("{:.1}", bearing)).arg(depth.to_string()).output();
    if let Ok(o) = out {
        let txt = String::from_utf8_lossy(&o.stdout);
        return txt.trim().parse().unwrap_or(0);
    }
    0
}
fn duration_hours(length_nm: f64) -> i64 {
    let out = Command::new("/app/build/repair_duration").arg(format!("{:.3}", length_nm)).output();
    if let Ok(o) = out {
        let txt = String::from_utf8_lossy(&o.stdout);
        return txt.trim().parse().unwrap_or(1).max(1);
    }
    1
}
fn add_hours(ts: &str, hours: i64) -> String {
    let total = hour_index(ts) + hours;
    let mut day_index = total.div_euclid(24);
    let hour = total.rem_euclid(24);
    let month_days = [31_i64, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let mut month = 1_i64;
    for days in month_days {
        if day_index < days { break; }
        day_index -= days;
        month += 1;
    }
    format!("2026-{:02}-{:02}T{:02}:00Z", month, day_index + 1, hour)
}
fn overlaps_hours(a_start: &str, a_end: &str, b_start: &str, b_end: &str) -> bool {
    hour_index(a_start) < hour_index(b_end) && hour_index(b_start) < hour_index(a_end)
}
fn overlaps_blackout(ship_id: &str, start: &str, end: &str, blackouts: &[Blackout]) -> bool {
    blackouts.iter().any(|b| b.ship_id == ship_id && overlaps_hours(start, end, &b.start, &b.end))
}
fn can_schedule(cand: &Repair, busy: &[(String, String)], cooldown: i64) -> bool {
    let start = hour_index(&cand.start);
    let end = hour_index(&cand.end);
    for (old_start, old_end) in busy {
        let os = hour_index(old_start);
        let oe = hour_index(old_end);
        if start < oe && os < end { return false; }
        if end <= os && end + cooldown > os { return false; }
        if oe <= start && oe + cooldown > start { return false; }
    }
    true
}
fn total_score(priority_base: i64, restored_priority: i64, compatibility_bonus: i64, drift_penalty: i64, depth_m: i64, crew: &str, hazard_penalty: i64) -> i64 {
    let crew_bonus = match crew { "A" => 8, "B" => 4, "C" => 1, _ => 0 };
    let depth_penalty = if depth_m <= 3000 { 0 } else { (depth_m - 3000) / 700 };
    priority_base * 10 + restored_priority + compatibility_bonus + crew_bonus - drift_penalty - depth_penalty - hazard_penalty
}
fn plan_digest(repairs: &[Repair], rejects: &[Reject], unreachable: &[String]) -> String {
    let mut lines = Vec::new();
    for r in repairs {
        lines.push(format!("{}|{}|{}|{}|{}|{}", r.span_id, r.ship_id, r.start, r.end, r.score, r.restored.join(";")));
    }
    for r in rejects { lines.push(format!("reject|{}|{}", r.span_id, r.reason)); }
    for u in unreachable { lines.push(format!("unreachable|{}", u)); }
    fnv1a64_hex(&lines.join("\n"))
}
fn render_json(mission_id: &str, repairs: &[Repair], rejects: &[Reject], unreachable: &[String], digest: &str) -> String {
    let mut out = String::new();
    out.push_str("{\n");
    out.push_str("  \"generated_by\": \"glassreef-planner\",\n");
    out.push_str(&format!("  \"mission_id\": \"{}\",\n", esc(mission_id)));
    out.push_str("  \"repair_windows\": [\n");
    for (idx, r) in repairs.iter().enumerate() {
        if idx > 0 { out.push_str(",\n"); }
        out.push_str(&format!("    {{\"span_id\":\"{}\",\"ship_id\":\"{}\",\"start_utc\":\"{}\",\"end_utc\":\"{}\",\"splice_family\":\"{}\",\"score\":{},\"restored_stations\":{},\"reason\":\"{}\"}}", esc(&r.span_id), esc(&r.ship_id), esc(&r.start), esc(&r.end), esc(&r.family), r.score, string_array(&r.restored), esc(&r.reason)));
    }
    out.push_str("\n  ],\n");
    out.push_str(&format!("  \"unreachable_stations\": {},\n", string_array(unreachable)));
    out.push_str("  \"rejected_repairs\": [\n");
    for (idx, r) in rejects.iter().enumerate() {
        if idx > 0 { out.push_str(",\n"); }
        out.push_str(&format!("    {{\"span_id\":\"{}\",\"reason\":\"{}\"}}", esc(&r.span_id), esc(&r.reason)));
    }
    out.push_str("\n  ],\n");
    out.push_str(&format!("  \"plan_digest\": \"{}\"\n", digest));
    out.push_str("}\n");
    out
}
