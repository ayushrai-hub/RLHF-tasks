use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Waypoint {
    pub upload_id: String,
    pub seq: u16,
    pub lat_e7: i32,
    pub lon_e7: i32,
    pub alt_mm: i32,
    pub frame: u8,
    pub flags: u8,
}

#[derive(Debug, Clone)]
pub struct Footer {
    pub upload_id: String,
    pub expected_count: u16,
}
