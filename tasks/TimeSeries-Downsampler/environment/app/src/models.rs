#[derive(Debug, Clone, PartialEq)]
pub struct Event {
    pub timestamp_ms: i64,
    pub event_id: String,
    pub name: String,
    pub value: f64,
    pub dependency_ids: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct WindowResult {
    pub window_start_ms: i64,
    pub window_end_ms: i64,
    pub name: String,
    pub count: usize,
    pub min: f64,
    pub max: f64,
    pub avg: f64,
    pub median: f64,
}
