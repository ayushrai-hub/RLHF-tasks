#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { computeFrontier } from "../src/pruner.js";

const scenarioPath = process.argv[2];
if (!scenarioPath) {
  console.error("usage: transfer-pruner <scenario.json>");
  process.exit(2);
}

const scenario = JSON.parse(readFileSync(scenarioPath, "utf8"));
process.stdout.write(`${JSON.stringify(computeFrontier(scenario))}\n`);
