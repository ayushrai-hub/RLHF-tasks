import Database from 'better-sqlite3';
import { RawReading, StationInfo } from '../types.js';

export function getStations(db: Database.Database): StationInfo[] {
  return db.prepare('SELECT * FROM stations ORDER BY code').all() as StationInfo[];
}

export function getStationIds(db: Database.Database): string[] {
  const rows = db.prepare('SELECT DISTINCT station_id FROM readings ORDER BY station_id').all() as { station_id: string }[];
  return rows.map(r => r.station_id);
}

export function getSensorTypes(db: Database.Database, stationId: string): string[] {
  const rows = db
    .prepare('SELECT DISTINCT sensor_type FROM readings WHERE station_id = ? ORDER BY sensor_type')
    .all(stationId) as { sensor_type: string }[];
  return rows.map(r => r.sensor_type);
}

export function getReadings(
  db: Database.Database,
  stationId: string,
  sensorType: string,
): RawReading[] {
  return db
    .prepare(
      'SELECT * FROM readings WHERE station_id = ? AND sensor_type = ? ORDER BY timestamp ASC',
    )
    .all(stationId, sensorType) as RawReading[];
}

export function getReadingCount(
  db: Database.Database,
  stationId: string,
  sensorType: string,
): number {
  const row = db
    .prepare('SELECT COUNT(*) as cnt FROM readings WHERE station_id = ? AND sensor_type = ?')
    .get(stationId, sensorType) as { cnt: number };
  return row.cnt;
}
