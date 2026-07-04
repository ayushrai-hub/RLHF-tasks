#!/usr/bin/env node
import path from 'node:path';
import { run } from '../raft_mesh/replay.js';

function parseArgs(argv) {
  const args = { bundle: '/app/scenarios/partition', output: '/app/output' };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--bundle') {
      args.bundle = argv[i + 1];
      i += 1;
    } else if (argv[i] === '--output') {
      args.output = argv[i + 1];
      i += 1;
    }
  }
  return args;
}

const args = parseArgs(process.argv);
process.exit(run(path.resolve(args.bundle), path.resolve(args.output)));
