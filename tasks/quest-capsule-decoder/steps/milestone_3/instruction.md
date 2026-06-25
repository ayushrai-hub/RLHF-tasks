The last piece is making the loader actually play. Each capsule keeps a handful of save
states in the cartridge, and from any one of them there is a route that reaches the
capsule's exit room. Implement `php /app/bin/qcap.php solve <capsule>` so it walks every
save state of every capsule in /app/cartridges to completion and writes each winning route
to /app/out/<capsule>.<seed_id>.run.

The transcript layout — the first line, each step, and the exact separator between a choice
and the room it leads to — is fixed in /app/docs/output-format.md, and the routes have to
come out identical on every run. How the walk picks its way through the rooms, how a save
state steers which way it goes, and how the gated exits are opened are all described in the
previous maintainer's notes under /app/docs.

Some routes only work if the right things are picked up along the way, so a walk that
ignores them will dead-end before it reaches the exit.
