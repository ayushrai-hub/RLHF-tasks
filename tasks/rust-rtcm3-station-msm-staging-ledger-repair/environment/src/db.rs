use rusqlite::Connection;
use std::fs;
use std::path::Path;

pub fn open(db_path: &str) -> Result<Connection, String> {
    Connection::open(db_path).map_err(|e| e.to_string())
}

pub fn init(db_path: &str) -> Result<(), String> {
    if let Some(parent) = Path::new(db_path).parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
    }
    let schema = include_str!("../docs/schema.sql");
    let conn = open(db_path)?;
    conn.execute_batch(schema).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn new_id(prefix: &str) -> String {
    format!("{prefix}-{}", uuid::Uuid::new_v4())
}
