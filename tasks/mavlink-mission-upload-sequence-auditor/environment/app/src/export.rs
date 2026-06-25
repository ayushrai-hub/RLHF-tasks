use std::f64::consts::PI;
use std::fs;
use std::path::Path;

use serde::Serialize;
use sha2::{Digest, Sha256};

use crate::domain::Waypoint;
use crate::profile::Profile;
use crate::store::Store;

#[derive(Serialize)]
struct ExportWaypoint {
    seq: u16,
    lat_deg: f64,
    lon_deg: f64,
    alt_meters: f64,
    frame: u8,
}

#[derive(Serialize)]
struct ExportDoc {
    vehicle_id: String,
    upload_id: String,
    waypoints: Vec<ExportWaypoint>,
    total_distance_m: f64,
    exported_at_unix: i64,
    upload_qc_pass: bool,
    audit_hash: String,
}

#[derive(Serialize)]
struct AuditHashPayload<'a> {
    vehicle_id: &'a str,
    upload_id: &'a str,
    waypoints: &'a [ExportWaypoint],
    total_distance_m: f64,
    exported_at_unix: i64,
}

pub struct Options<'a> {
    pub db_path: &'a Path,
    pub vehicle_id: &'a str,
    pub upload_id: &'a str,
    pub out_path: &'a Path,
    pub profile_path: &'a Path,
}

fn epoch_base() -> i64 {
    std::env::var("MISSION_EPOCH_BASE")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(1_704_067_200)
}

fn alt_meters(wp: &Waypoint, home_alt_m: f64) -> f64 {
    let raw = wp.alt_mm as f64 / 1000.0;
    if wp.frame == 3 {
        raw + home_alt_m
    } else {
        raw
    }
}

fn haversine_m(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let r = 6_371_000.0;
    let dlat = (lat2 - lat1) * PI / 180.0;
    let dlon = (lon2 - lon1) * PI / 180.0;
    let a = (dlat / 2.0).sin().powi(2)
        + lat1.to_radians().cos() * lat2.to_radians().cos() * (dlon / 2.0).sin().powi(2);
    let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());
    r * c
}

fn audit_hash(
    vehicle_id: &str,
    upload_id: &str,
    waypoints: &[ExportWaypoint],
    total_distance_m: f64,
    exported_at_unix: i64,
) -> Result<String, String> {
    let payload = AuditHashPayload {
        vehicle_id,
        upload_id,
        waypoints,
        total_distance_m,
        exported_at_unix,
    };
    let bytes = serde_json::to_string(&payload).map_err(|e| e.to_string())?;
    Ok(hex::encode(Sha256::digest(bytes.as_bytes())))
}

fn upload_qc_pass(
    waypoints: &[ExportWaypoint],
    total_distance_m: f64,
    profile: &Profile,
    vehicle_id: &str,
) -> Result<bool, String> {
    let max_rel = profile.max_rel_alt_m(vehicle_id)?;
    for wp in waypoints {
        if wp.frame == 3 && wp.alt_meters > max_rel {
            return Ok(false);
        }
    }
    let _ = total_distance_m;
    Ok(true)
}

pub fn run(opts: Options<'_>) -> Result<(), String> {
    let store = Store::open(opts.db_path)?;
    let profile = Profile::load(opts.profile_path)?;
    let home_alt = profile.home_alt_m(opts.vehicle_id)?;
    let waypoints = store.waypoints_for_upload(opts.vehicle_id, opts.upload_id)?;

    let export_wps: Vec<ExportWaypoint> = waypoints
        .iter()
        .filter(|wp| wp.flags & 0x04 == 0)
        .map(|wp| ExportWaypoint {
            seq: wp.seq,
            lat_deg: wp.lat_e7 as f64 / 1e7,
            lon_deg: wp.lon_e7 as f64 / 1e7,
            alt_meters: (alt_meters(wp, home_alt) * 1000.0).round() / 1000.0,
            frame: wp.frame,
        })
        .collect();

    let mut total = 0.0;
    for i in 1..export_wps.len() {
        if waypoints[i].flags & 0x02 != 0 {
            continue;
        }
        let lat1 = export_wps[i - 1].lat_deg;
        let lon1 = export_wps[i - 1].lon_deg;
        let lat2 = export_wps[i].lat_deg;
        let lon2 = export_wps[i].lon_deg;
        let leg = haversine_m(lat1, lon1, lat2, lon2);
        total += (leg * 1000.0).round() / 1000.0;
    }

    let max_seq: i64 = store
        .conn
        .query_row("SELECT COALESCE(MAX(seq), 0) FROM waypoints", [], |row| row.get(0))
        .map_err(|e| e.to_string())?;
    let total_distance_m = (total * 1000.0).round() / 1000.0;
    let exported_at_unix = epoch_base() + max_seq;
    let upload_qc_pass = upload_qc_pass(&export_wps, total_distance_m, &profile, opts.vehicle_id)?;
    let audit_hash = audit_hash(
        opts.vehicle_id,
        opts.upload_id,
        &export_wps,
        total_distance_m,
        exported_at_unix,
    )?;
    let doc = ExportDoc {
        vehicle_id: opts.vehicle_id.to_string(),
        upload_id: opts.upload_id.to_string(),
        waypoints: export_wps,
        total_distance_m,
        exported_at_unix,
        upload_qc_pass,
        audit_hash,
    };

    if let Some(parent) = opts.out_path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&doc).map_err(|e| e.to_string())?;
    fs::write(opts.out_path, json).map_err(|e| e.to_string())?;
    Ok(())
}
