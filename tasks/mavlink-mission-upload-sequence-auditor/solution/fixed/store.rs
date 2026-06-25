use std::path::Path;

use rusqlite::{params, Connection};

use crate::domain::Waypoint;

pub struct Store {
    pub conn: Connection,
}

impl Store {
    pub fn open(path: &Path) -> Result<Self, String> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        let conn = Connection::open(path).map_err(|e| e.to_string())?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS upload_commits (
                vehicle_id TEXT NOT NULL,
                upload_id TEXT NOT NULL,
                committed_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                PRIMARY KEY (vehicle_id, upload_id)
            );
            CREATE TABLE IF NOT EXISTS waypoints (
                vehicle_id TEXT NOT NULL,
                upload_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                lat_e7 INTEGER NOT NULL,
                lon_e7 INTEGER NOT NULL,
                alt_mm INTEGER NOT NULL,
                frame INTEGER NOT NULL,
                flags INTEGER NOT NULL,
                PRIMARY KEY (vehicle_id, upload_id, seq)
            );",
        )
        .map_err(|e| e.to_string())?;
        Ok(Self { conn })
    }

    pub fn upload_committed(&self, upload_id: &str, vehicle_id: &str) -> Result<bool, String> {
        let count: i64 = self
            .conn
            .query_row(
                "SELECT COUNT(*) FROM upload_commits WHERE upload_id = ?1 AND vehicle_id = ?2",
                params![upload_id, vehicle_id],
                |row| row.get(0),
            )
            .map_err(|e| e.to_string())?;
        Ok(count > 0)
    }

    pub fn insert_waypoint(&self, vehicle_id: &str, wp: &Waypoint) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT INTO waypoints (vehicle_id, upload_id, seq, lat_e7, lon_e7, alt_mm, frame, flags)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                params![
                    vehicle_id,
                    wp.upload_id,
                    wp.seq,
                    wp.lat_e7,
                    wp.lon_e7,
                    wp.alt_mm,
                    wp.frame,
                    wp.flags
                ],
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn mark_committed(&self, upload_id: &str, vehicle_id: &str) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT INTO upload_commits (vehicle_id, upload_id) VALUES (?1, ?2)",
                params![vehicle_id, upload_id],
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn waypoints_for_upload(
        &self,
        vehicle_id: &str,
        upload_id: &str,
    ) -> Result<Vec<Waypoint>, String> {
        let mut stmt = self
            .conn
            .prepare(
                "SELECT upload_id, seq, lat_e7, lon_e7, alt_mm, frame, flags
                 FROM waypoints WHERE vehicle_id = ?1 AND upload_id = ?2 ORDER BY seq ASC",
            )
            .map_err(|e| e.to_string())?;
        let rows = stmt
            .query_map(params![vehicle_id, upload_id], |row| {
                Ok(Waypoint {
                    upload_id: row.get(0)?,
                    seq: row.get(1)?,
                    lat_e7: row.get(2)?,
                    lon_e7: row.get(3)?,
                    alt_mm: row.get(4)?,
                    frame: row.get(5)?,
                    flags: row.get(6)?,
                })
            })
            .map_err(|e| e.to_string())?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row.map_err(|e| e.to_string())?);
        }
        Ok(out)
    }
}
