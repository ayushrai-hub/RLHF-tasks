import { main } from "./bin.ts";

main(process.argv.slice(2)).then((code) => process.exit(code));
