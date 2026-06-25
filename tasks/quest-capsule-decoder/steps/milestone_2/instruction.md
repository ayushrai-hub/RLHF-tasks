With the header decoding now in place, the loader needs to turn a capsule into something
playable. Build the room graph for every capsule in /app/cartridges so that
`php /app/bin/qcap.php graph <capsule>` writes /app/out/<capsule>.graph.json.

Each room stores an encoded title and description in the cartridge, plus a set of exits
that point at other rooms — and some of those exits are gated. Decode all of it and lay
the graph out exactly as /app/docs/output-format.md specifies, including the order in which
rooms and their exits must appear. The encoding itself, and what a gate on an exit means,
are covered in the previous maintainer's notes under /app/docs; the table shapes are in
/app/docs/cartridge-schema.md.

The finished graph should name the entry room and, for every room, give its decoded title,
its decoded description, and its list of exits with their decoded labels, their targets,
and any gate token attached to them.
