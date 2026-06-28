Add migration-wave planning to /app/tools/msbuild_audit.py:

python3 /app/tools/msbuild_audit.py waves /app/src /app/Directory.Packages.props /app/policy/runtime-policy.json /app/out/msbuild-migration-waves.json

Use the current policy classification plus ProjectReference dependency ordering and write waves, blocked, retire, and summary. Parse ProjectReference entries in plain or namespaced MSBuild XML, resolve them relative to the referencing project, expand $(MSBuildThisFileDirectory), normalize discovered in-tree references to /app/src-relative paths, and ignore external or undiscovered references. Put each non-blocked update project in one 1-based wave after any referenced update projects; keep projects do not delay waves. References to retired projects and dependency cycles among update projects block the affected update projects.

Each wave row has exactly wave and alphabetically sorted projects. Each blocked row has exactly path, name, and reasons, sorted by path; retired-dependency reasons must use the exact string format retired dependency: <path>, and cycle reasons include dependency cycle. retire is an alphabetically sorted list of retired project paths. summary has wave_count, update_projects, blocked_projects, and retire_projects, where update_projects counts every update-classified project including blocked ones.
