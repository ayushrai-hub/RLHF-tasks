import { runFullMatrix } from "./engine.ts";

export async function main(argv: string[]): Promise<number> {
  let out = "/app/output/graph_report.json";
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--out" && argv[i + 1]) out = argv[i + 1];
  }
  if (!argv.includes("--matrix")) {
    console.error("usage: mgr_run --matrix --out <path>");
    return 2;
  }
  try {
    runFullMatrix(out);
    return 0;
  } catch (err) {
    console.error(String(err));
    return 1;
  }
}
