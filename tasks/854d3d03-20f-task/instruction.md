There's a Go tool under `/app` called `depmap` that reconstructs the build order for container images from declarative fixtures, without running one. Only `import` is trustworthy. The `plan` and `graph` steps were stubbed during a prototype: they look only at the packages named directly on each spec, pick the first release, and emit no edges. Make them correct.

Keep the three subcommands and their flags exactly as they are:

- `depmap import --specs /app/data/specs --locks /app/data/locks/packages.lock.json --toolchains /app/data/toolchains.json --db /app/out/build.db`
- `depmap plan --db /app/out/build.db --out /app/out/build-plan.json`
- `depmap graph --db /app/out/build.db --out /app/out/depgraph.dot`

`import` already loads the fixtures into SQLite and its schema lives in the code. depmap's constraint grammar, version rules, conflicts, conditional markers, virtual packages, extras, and spec ordering are written up in `/app/README.md`. Read it alongside the fixtures for the exact meanings. Both `plan` and `graph` must work entirely off the database, never by re-reading the JSON.

Pick one release per package so every constraint holds at once, then order the result. Build the full transitive closure from the specs over package deps and toolchain requirements, including toolchain-to-toolchain ones, and drop anything no spec needs. When the highest independent picks are jointly unsatisfiable, back off to lower releases until consistent. Prefer higher versions, comparing package by package in ascending name order.

Node ids are `spec:<name>`, `pkg:<name>@<version>`, and `tc:<name>@<version>`. An edge from A to B means B builds before A. Order nodes so every dependency comes before what needs it, breaking ties by the id that sorts first, so the same fixtures always produce the same plan.

Write `/app/out/build-plan.json` as an object with `build_order`, `node_count`, and `edge_count`. `build_order` is the ordered array of nodes, each `{"id", "type", "name", "version", "depends_on"}`, where `type` is `spec`, `package`, or `toolchain`, `version` is empty for specs, and `depends_on` is the direct dependency ids sorted ascending, always a JSON array (`[]` not `null`). Write `/app/out/depgraph.dot` as a Graphviz digraph named `depmap`: one node line per node as `"<id>" [type="<type>"];` in ascending id order, then edges as `"<A>" -> "<B>";` sorted by source then target. Both outputs must be deterministic.
