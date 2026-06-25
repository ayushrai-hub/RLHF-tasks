# cronq schedule protocol

Version: 1.0

This is the contract for how `cronq` parses a five-field cron expression and
computes upcoming fire times. The CLI and the bundled case fixtures rely on
the rules below being implemented exactly.

## 1. Expression format

An expression is five whitespace-separated fields, in this order:

```
minute  hour  day-of-month  month  day-of-week
```

Field bounds:

| field        | range  | names           |
|--------------|--------|-----------------|
| minute       | 0-59   | -               |
| hour         | 0-23   | -               |
| day-of-month | 1-31   | -               |
| month        | 1-12   | JAN .. DEC      |
| day-of-week  | 0-6    | SUN .. SAT      |

Day-of-week is Sunday-based: SUN is 0, SAT is 6. Names are matched
case-insensitively and may be used anywhere a number is allowed in those two
fields.

Each field is a comma-separated list of terms. A term is one of:

| term       | meaning                                                       |
|------------|---------------------------------------------------------------|
| `*`        | every value in the field's range                              |
| `*/k`      | a stepped series across the field's range                     |
| `v`        | the single value `v`                                          |
| `v/k`      | a stepped series anchored on `v`                              |
| `a-b`      | every value in the inclusive range `a` to `b`                 |
| `a-b/k`    | a stepped series over the range `a` to `b`                    |

Steps follow the usual cron convention; a term whose step would produce no
values, or whose values fall outside the field range, is an error.

## 2. The day-of-month / day-of-week rule

This is the part of cron people most often get wrong, so it's spelled out
here. A field is *restricted* when it is written as anything other than a
leading `*` -- so `*` and `*/k` are both unrestricted, while `5`, `1-5`,
`MON`, and `1,15` are restricted.

* If neither day-of-month nor day-of-week is restricted, every day matches.
* If exactly one of them is restricted, only that field decides the day.
* If **both** are restricted, a day matches when it satisfies day-of-month
  **or** day-of-week -- not both. `0 0 13 * FRI` fires on the 13th of every
  month and on every Friday.

## 3. Computing the next fire times

`cronq next` takes a starting timestamp (`--from`) and a count, and returns
the next `count` timestamps that the expression matches.

* All timestamps are UTC. Input is ISO-8601 with a trailing `Z`
  (`YYYY-MM-DDTHH:MM:SSZ`); output is the same shape with seconds always
  `00`.
* Cron fires at second `:00` of a matching minute.
* "Next" means **strictly after** `--from`. If `--from` lands exactly on a
  matching minute, that minute is *not* returned -- the first result is the
  following match.
* Results are in ascending order and the search rolls over day, month, and
  year boundaries as needed.

## 4. Output

On success `cronq next` prints one JSON object to stdout:

```jsonc
{
  "ok":      true,
  "expr":    "<the expression, whitespace-normalised>",
  "from":    "<the --from value, unchanged>",
  "matches": ["YYYY-MM-DDTHH:MM:00Z", ...]   // exactly `count` entries
}
```

On failure it prints `{"ok": false, "error": "<message>"}`.

## 5. Exit codes

| code | meaning                                                       |
|------|---------------------------------------------------------------|
| 0    | success                                                       |
| 2    | usage error, or the expression / `--from` value didn't parse  |
| 3    | parsed fine but no matches were found within the search bound |
