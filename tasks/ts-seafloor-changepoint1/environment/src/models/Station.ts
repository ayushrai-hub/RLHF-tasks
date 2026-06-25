import { CalibrationParams } from '../types.js';

export class Station {
  readonly code: string;
  readonly fullName: string;
  readonly latitude: number;
  readonly longitude: number;
  readonly depthM: number;
  readonly deploymentDate: Date;
  calibration: CalibrationParams | null = null;

  constructor(opts: {
    code: string;
    full_name: string;
    latitude: number;
    longitude: number;
    depth_m: number;
    deployment_date: string;
  }) {
    this.code = opts.code;
    this.fullName = opts.full_name;
    this.latitude = opts.latitude;
    this.longitude = opts.longitude;
    this.depthM = opts.depth_m;
    this.deploymentDate = new Date(opts.deployment_date);
  }

  hasCalibration(): boolean {
    return this.calibration !== null;
  }

  toString(): string {
    return `Station(${this.code}, depth=${this.depthM}m)`;
  }
}
