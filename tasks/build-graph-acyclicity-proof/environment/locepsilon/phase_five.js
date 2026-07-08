// Phase Five: Config Merger and Scenario Checkpoint
// Symbol: op_e (merge), op_f (checkpoint)
// Signature: function op_e(base, extra), function op_f(action, payload)

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const op_g = require('../loczeta/phase_six');

const CKPT_PATH = path.join(__dirname, '..', 'data', '.scenario_ckpt');

function stableDigest(config) {
  const payload = JSON.stringify(config, Object.keys(config).sort());
  return crypto.createHash('sha256').update(payload).digest('hex');
}

function op_e(base, extra) {
  if (!extra) {
    return JSON.parse(JSON.stringify(base));
  }

  const config = JSON.parse(JSON.stringify(base));

  if (extra.flags) {
    config.flags = Array.from(new Set([...(config.flags || []), ...extra.flags]));
  }

  if (extra.constraints) {
    config.constraints = extra.constraints;
  }

  if (extra.tasks) {
    const taskMap = new Map((config.tasks || []).map((t) => [t.id, t]));
    for (const t of extra.tasks) {
      taskMap.set(t.id, t);
    }
    config.tasks = Array.from(taskMap.values());
  }

  if (extra.parallel_groups) {
    config.parallel_groups = extra.parallel_groups;
  }

  return config;
}

function op_f(action, payload) {
  if (action === 'digest') {
    return stableDigest(payload);
  }

  if (action === 'read') {
    if (!fs.existsSync(CKPT_PATH)) {
      return { offset: 0, digest: null };
    }
    try {
      return JSON.parse(fs.readFileSync(CKPT_PATH, 'utf8'));
    } catch {
      return { offset: 0, digest: null };
    }
  }

  if (action === 'write') {
    fs.mkdirSync(path.dirname(CKPT_PATH), { recursive: true });
    fs.writeFileSync(CKPT_PATH, JSON.stringify(payload));
    return payload;
  }

  if (action === 'clear') {
    if (fs.existsSync(CKPT_PATH)) {
      fs.unlinkSync(CKPT_PATH);
    }
    return { cleared: true };
  }

  return null;
}

function enumerateScenarios(flagsList, constraints, evalConstraint) {
  return op_g(flagsList, constraints, evalConstraint);
}

module.exports = { op_e, op_f, enumerateScenarios };
