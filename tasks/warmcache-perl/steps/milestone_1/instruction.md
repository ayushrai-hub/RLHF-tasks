Our edge-CDN warm-cache planner reconstructs its warm-up plan from a framed descriptor file at `/app/warmcache.dat`, but the only surviving specification of that file is a long migration chronicle at `/app/docs/chronicle.md`. The chronicle records five revisions of the descriptor format; only the current revision describes the file you actually have, and the older revisions appear throughout as superseded, conflicting examples, so you must read it and synthesize the current rules rather than grep for a single block.

Write a deterministic command-line tool in Perl at `/app/plan.pl`, run as `perl /app/plan.pl <stage>`, that carries the planner through three stages across this and the following milestones. Each stage reads `/app/warmcache.dat` and writes one JSON file under `/app/out/`. There are worked input/output pairs under `/app/examples/`. Where the chronicle says the format delegates normalization to command-line utilities, match the behavior of POSIX `cksum`, `base64`, `sort`, `join`, and `cut` exactly; you may call those utilities or reimplement them, but a casual reimplementation that does not match them will fail. Do not delegate the work to another language interpreter.

Milestone 1 is the `decode` stage. Read `/app/warmcache.dat`, validate and decode its frames according to the current revision, and write `/app/out/decode.json`. It must be a JSON object with exactly three keys:

- `objs`: a list of `[key, [prereq, ...]]` for the canonical OBJ records, sorted ascending by key.
- `hits`: a list of `[key, weight]` for the canonical HIT records, sorted ascending by key.
- `invalid`: a list of `[sequence, code]` for every frame that fails validation, sorted ascending.

The error codes and the exact framing, encoding, checksum, and record rules are defined by the current revision in `/app/docs/chronicle.md`; the older revisions' rules will give a plausible but wrong decoder. Run `perl /app/plan.pl decode` and check `/app/out/decode.json` before declaring the milestone complete.
