import { DetectedEvent } from '../types.js';

export class EventCandidate {
  stationId: string;
  sensorType: string;
  startTime: Date;
  endTime: Date;
  durationHours: number;
  peakZScore: number;
  meanAmplitude: number;
  displacementEstimate: number;
  confidenceScore: number;
  excluded: boolean;
  exclusionReason: string | null;

  constructor(opts: {
    stationId: string;
    sensorType: string;
    startTime: Date;
    endTime: Date;
    peakZScore: number;
    meanAmplitude: number;
    displacementEstimate: number;
  }) {
    this.stationId = opts.stationId;
    this.sensorType = opts.sensorType;
    this.startTime = opts.startTime;
    this.endTime = opts.endTime;
    this.durationHours =
      (opts.endTime.getTime() - opts.startTime.getTime()) / (1000 * 3600);
    this.peakZScore = opts.peakZScore;
    this.meanAmplitude = opts.meanAmplitude;
    this.displacementEstimate = opts.displacementEstimate;
    this.confidenceScore = 0;
    this.excluded = false;
    this.exclusionReason = null;
  }

  toJSON(): DetectedEvent {
    return {
      station_id: this.stationId,
      sensor_type: this.sensorType,
      start_time: this.startTime.toISOString(),
      duration_hours: Math.round(this.durationHours * 100) / 100,
      displacement_estimate: Math.round(this.displacementEstimate * 10000) / 10000,
      confidence_score: Math.round(this.confidenceScore * 10000) / 10000,
      excluded: this.excluded,
      exclusion_reason: this.exclusionReason,
    };
  }
}
