import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { goldenPolicyPath } from './envmerge.js';

function stableJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

export function configSha256() {
  const policy = fs.readFileSync(goldenPolicyPath());
  return crypto.createHash('sha256').update(policy).digest('hex');
}

export function writeRejection(outputPath, incidentId, code, message) {
  fs.mkdirSync(outputPath, { recursive: true });
  const report = {
    schema_version: 4,
    status: 'rejected',
    incident_id: incidentId,
    error: { code, message },
  };
  fs.writeFileSync(path.join(outputPath, 'consensus_report.json'), stableJson(report));
}

export function writeOutputs({
  outputPath,
  incidentId,
  digest,
  classification,
  before,
  after,
  parseSummary,
  termTimeline,
  commandTrace,
  safetyCertificate,
  seed,
}) {
  fs.mkdirSync(outputPath, { recursive: true });
  const report = {
    schema_version: 4,
    status: 'accepted',
    incident_id: incidentId,
    linearizability_digest: digest,
    classification: classification.classification,
    root_cause: classification.root_cause,
    primary_node: classification.primary_node,
    secondary_symptoms: classification.secondary_symptoms,
    rejected_causes: classification.rejected_causes,
    repair_plan: classification.repair_plan,
    before,
    after,
    parse_summary: parseSummary,
  };
  fs.writeFileSync(path.join(outputPath, 'consensus_report.json'), stableJson(report));

  const csvLines = ['phase,node_id,term,start_tick,end_tick,role,votes_received'];
  for (const row of termTimeline) {
    csvLines.push(
      `${row.phase},${row.node_id},${row.term},${row.start_tick},${row.end_tick},${row.role},${row.votes_received}`,
    );
  }
  fs.writeFileSync(path.join(outputPath, 'term_timeline.csv'), `${csvLines.join('\n')}\n`);

  fs.writeFileSync(
    path.join(outputPath, 'command_trace.json'),
    `${JSON.stringify({ schema_version: 4, commands: commandTrace }, null, 2)}\n`,
  );

  fs.writeFileSync(
    path.join(outputPath, 'safety_certificate.json'),
    stableJson(safetyCertificate),
  );

  const manifest = [
    `cluster_policy_changed=false`,
    `config_sha256=${configSha256()}`,
    `linearizability_digest=${digest}`,
    `simulation_seed=${seed}`,
  ].sort();
  fs.writeFileSync(path.join(outputPath, 'wal_digest.txt'), `${manifest.join('\n')}\n`);
}
