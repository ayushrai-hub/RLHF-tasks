The QuestCapsule loader under /app is half-finished. It can open a capsule spec and its
cartridge, but it cannot yet read the header — the short base64 token that each spec under
/app/cartridges carries. At the moment running `php /app/bin/qcap.php decode <capsule>`
just writes an empty result.

Make it genuinely decode the header for every capsule in /app/cartridges and write the
result to /app/out/<capsule>.header.json. The exact JSON shape is pinned in
/app/docs/output-format.md. Nobody ever wrote the format down: the previous maintainer's
journal under /app/docs is the only account of how a header is laid out, how its fields
are encoded, and how its built-in consistency check works, so read it before you start.
The cartridge tables are described in /app/docs/cartridge-schema.md.

A correct decode recovers the entry room, the room count, the glyph set, the seed base,
and the check value, and reports whether the header's own check holds. Here <capsule> is a
spec filename stem such as verdant-hollow.
