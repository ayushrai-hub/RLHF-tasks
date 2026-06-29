use crate::errors::AppError;
use crate::types::{MetricPoint, MetricsFile};
use std::collections::HashSet;
use std::path::Path;

pub fn read_metrics_file(path: &Path) -> Result<MetricsFile, AppError> {
    let content = std::fs::read_to_string(path)
        .map_err(|_e| AppError::IoError(format!("{}", path.display())))?;
    let mf: MetricsFile = serde_json::from_str(&content)
        .map_err(|e| AppError::ParseError(format!("Failed to parse {}: {}", path.display(), e)))?;
    Ok(mf)
}

#[allow(dead_code)]
pub fn deduplicate_points(files: &[MetricsFile]) -> Vec<MetricPoint> {
    let mut seen: HashSet<(String, String)> = HashSet::new();
    let mut combined = Vec::new();

    for mf in files {
        for point in &mf.metrics {
            let key = (point.metric.clone(), point.timestamp.clone());
            if !seen.contains(&key) {
                seen.insert(key);
                combined.push(point.clone());
            }
        }
    }

    combined
}

pub fn combine_all_points(files: &[MetricsFile]) -> Vec<MetricPoint> {
    let mut combined = Vec::new();
    for mf in files {
        combined.extend(mf.metrics.clone());
    }
    combined
}

pub fn parse_timestamp(ts: &str) -> Result<u64, AppError> {
    let cleaned = ts.trim_end_matches('Z');
    let parts: Vec<&str> = cleaned.split('.').collect();
    let base = parts[0];
    let epoch = chrono_parse(base)
        .ok_or_else(|| AppError::ParseError(format!("Cannot parse timestamp: {}", ts)))?;
    Ok(epoch)
}

fn chrono_parse(base: &str) -> Option<u64> {
    let parts: Vec<&str> = base.split('T').collect();
    if parts.len() != 2 {
        return None;
    }
    let date_parts: Vec<u64> = parts[0].split('-').filter_map(|s| s.parse().ok()).collect();
    let time_parts: Vec<u64> = parts[1].split(':').filter_map(|s| s.parse().ok()).collect();
    if date_parts.len() != 3 || time_parts.len() != 3 {
        return None;
    }
    Some(ymd_to_unix(
        date_parts[0],
        date_parts[1],
        date_parts[2],
        time_parts[0],
        time_parts[1],
        time_parts[2],
    ))
}

fn ymd_to_unix(year: u64, month: u64, day: u64, hour: u64, min: u64, sec: u64) -> u64 {
    let months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let leap = (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
    let mut days =
        (year - 1970) * 365 + (year - 1969) / 4 - (year - 1901) / 100 + (year - 1601) / 400;
    for m in 1..month {
        days += months[(m - 1) as usize] as u64;
        if m == 2 && leap {
            days += 1;
        }
    }
    days += day - 1;
    days * 86400 + hour * 3600 + min * 60 + sec
}
