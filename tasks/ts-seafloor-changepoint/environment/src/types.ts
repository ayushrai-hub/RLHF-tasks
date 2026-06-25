export interface StationInfo {
  code: string;
  full_name: string;
  latitude: number;
  longitude: number;
  depth_m: number;
  deployment_date: string;
  status: string;
}

export interface RawReading {
  id: number;
  station_id: string;
  sensor_type: string;
  timestamp: string;
  raw_value: number;
  unit: string;
}

export interface CalibrationParams {
  station_id: string;
  pressure_gain: number;
  pressure_offset: number;
  z_score_threshold: number;
  min_duration_hours: number;
  maintenance_windows: MaintenanceWindow[];
}

export interface MaintenanceWindow {
  start: Date;
  end: Date;
  reason: string;
}

export interface CalibratedSeries {
  station_id: string;
  sensor_type: string;
  timestamps: Date[];
  values: number[];
}

export interface DetectedEvent {
  station_id: string;
  sensor_type: string;
  start_time: string;
  duration_hours: number;
  displacement_estimate: number;
  confidence_score: number;
  excluded: boolean;
  exclusion_reason: string | null;
}

export interface EventCatalog {
  generated_at: string;
  total_events: number;
  excluded_events: number;
  events: DetectedEvent[];
}
