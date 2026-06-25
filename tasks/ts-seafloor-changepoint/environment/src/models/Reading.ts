import { RawReading } from '../types.js';

export class Reading {
  readonly id: number;
  readonly stationId: string;
  readonly sensorType: string;
  readonly timestamp: Date;
  readonly rawValue: number;
  readonly unit: string;

  constructor(row: RawReading) {
    this.id = row.id;
    this.stationId = row.station_id;
    this.sensorType = row.sensor_type;
    this.timestamp = new Date(row.timestamp);
    this.rawValue = row.raw_value;
    this.unit = row.unit;
  }

  /**
   * Apply linear calibration: calibrated = raw * gain + offset.
   * gain and offset come from the station calibration parameters in the dossier.
   */
  calibrate(gain: number, offset: number): number {
    return this.rawValue * gain + offset;
  }
}
