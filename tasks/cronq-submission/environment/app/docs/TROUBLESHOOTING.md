# Troubleshooting

## "expected 5 fields, got N"

The expression didn't split into exactly five whitespace-separated fields.
Leading/trailing spaces are fine; what isn't fine is a missing field or an
extra one. Seconds are not a field here -- the layout is minute, hour,
day-of-month, month, day-of-week.

## "value out of range" / "not a number or known name"

A term referenced a value outside its field's bounds (see `PROTOCOL.md` section 1)
or a name that isn't one of the recognised three-letter month / day-of-week
abbreviations. Day-of-week is 0-6 with Sunday at 0; there's no `7`.

## Times are correct but the search seems slow or returns an error

`NextCalculator` scans minute by minute and gives up after a bounded number
of minutes. Very sparse expressions (say, a specific day that only occurs in
leap years) are still well within the bound, but a genuinely impossible
expression will exit 3 rather than run forever.

## Comparing against the manifest

`data/manifest.json` holds reference outputs for a subset of the bundled
cases in `data/cases/`. If the CLI's `matches` array for a case disagrees
with the manifest, the manifest is right -- it was computed from the protocol,
not from the current code.
