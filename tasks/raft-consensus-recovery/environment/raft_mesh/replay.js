import path from 'node:path';
import { loadBundle } from './parsers.js';
import { simulate } from './simulator.js';
import { classify } from './triage.js';
import {
  buildCommandTrace,
  buildSafetyCertificate,
  buildTermTimeline,
  linearizabilityDigest,
  snapshotMetrics,
} from './metrics.js';
import { writeOutputs, writeRejection } from './report.js';
import { simulationSeed } from './envmerge.js';

export function run(bundlePath, outputPath) {
  const bundle = loadBundle(bundlePath);
  const incidentId = path.basename(bundlePath);
  if (bundle.issue) {
    writeRejection(outputPath, incidentId, bundle.issue.code, bundle.issue.message);
    return 2;
  }

  const beforeSim = simulate(bundle, 'buggy');
  if (beforeSim.issue) {
    writeRejection(outputPath, incidentId, beforeSim.issue.code, beforeSim.issue.message);
    return 2;
  }
  const afterSim = simulate(bundle, 'safe');
  if (afterSim.issue) {
    writeRejection(outputPath, incidentId, afterSim.issue.code, afterSim.issue.message);
    return 2;
  }

  const seed = simulationSeed(bundle.envMap);
  const digest = linearizabilityDigest(bundle.commands, afterSim.applied);
  const classification = classify(beforeSim.metrics, afterSim.metrics);
  const parseSummary = {
    accepted_commands: bundle.commands.length,
    duplicate_commands: bundle.duplicateCommands,
    wal_frames: bundle.frameCount,
    env_files_merged: bundle.envFilesMerged,
    snapshot_rows: bundle.snapshotCount,
    rpc_rows: bundle.rpcTrace.length,
  };

  writeOutputs({
    outputPath,
    incidentId,
    digest,
    classification,
    before: snapshotMetrics(beforeSim.metrics),
    after: snapshotMetrics(afterSim.metrics),
    parseSummary,
    termTimeline: buildTermTimeline(beforeSim.timeline, afterSim.timeline),
    commandTrace: buildCommandTrace(bundle.commands, afterSim.applied),
    safetyCertificate: buildSafetyCertificate(afterSim.metrics, digest, seed),
    seed,
  });
  return 0;
}
