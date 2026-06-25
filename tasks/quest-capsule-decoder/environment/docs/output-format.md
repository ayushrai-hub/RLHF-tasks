# Output format

The CLI writes its results under `/app/out/`. These are the exact shapes the loader's
consumers expect; they are contracts, so match them byte for byte.

## `decode <capsule>` → `/app/out/<capsule>.header.json`

A single JSON object, pretty-printed with 2-space indentation and a trailing newline, with
keys in this order:

    {
      "capsule": "<name>",
      "entry": <int>,
      "room_count": <int>,
      "glyph_table": <int>,
      "seed_base": <int>,
      "checksum": <int>,
      "checksum_ok": <bool>
    }

`checksum` is the value carried in the header. `checksum_ok` reports whether the header's
own consistency check holds.

## `graph <capsule>` → `/app/out/<capsule>.graph.json`

A JSON object, 2-space indentation, trailing newline:

    {
      "capsule": "<name>",
      "entry": <int>,
      "rooms": [
        {
          "id": <int>,
          "kind": "entry|normal|exit",
          "title": "<decoded title>",
          "body": "<decoded body>",
          "exits": [
            { "label": "<decoded label>", "to": <int>, "guard": "<decoded token>|null" }
          ]
        }
      ]
    }

`rooms` is ordered by `id` ascending. Within a room, `exits` is ordered by `label`
ascending, ties broken by `to` ascending. `guard` is `null` for an unguarded exit.

## `solve <capsule>` → `/app/out/<capsule>.<seed_id>.run`

One plain-text file per save state of the capsule. The first line is the entry room's
title. Each following line is the choice taken and the room it leads to, formatted exactly
as `<label> -> <title>`. The file ends with a single trailing newline. No blank lines, no
header, no seed echoed into the file.
