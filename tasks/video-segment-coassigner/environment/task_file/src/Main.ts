// TODO: replace this placeholder with the video-segment co-assigner.
// Compile: npx tsc   (from src/)  Run: node Main.js <input_dir> <output_dir>
import * as fs from "fs";
import * as path from "path";
const argv = process.argv.slice(2);
const outDir = argv.length >= 2 ? argv[1] : "output_data";
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "assignment.jsonl"), "");
