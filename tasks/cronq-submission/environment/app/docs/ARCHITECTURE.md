# Architecture

`cronq` is a small command-line tool that parses a five-field cron expression
and prints the next N times it would fire from a given starting point. It has
no external dependencies -- just the JDK and `java.time`.

## Module layout

```
/app
├── cronq.jar                          executable (built from src/)
├── build.sh                           compile + package into cronq.jar
├── src/com/cronq/
│   ├── Cli.java                        argument parsing + main()
│   ├── model/
│   │   ├── CronExpr.java               the five parsed fields
│   │   └── Field.java                  one field's allowed value set
│   ├── parse/
│   │   ├── CronParser.java             splits the line into five fields
│   │   ├── FieldParser.java            one field string -> value set
│   │   ├── NameTable.java              month / day-of-week name maps
│   │   └── ParseException.java         parse failure -> exit 2
│   ├── match/
│   │   └── Matcher.java                does a given minute match the expr?
│   ├── calc/
│   │   └── NextCalculator.java         walk forward, collect next N matches
│   └── io/
│       └── JsonWriter.java             emit the result object
├── data/
│   ├── manifest.json                   reference outputs for some cases
│   └── cases/                          bundled (expr, from, count) cases
├── docs/                               this directory
└── tools/
    └── gen_manifest.py                 regenerates the manifest (dev only)
```

## Flow

```
   cronq next --expr <e> --from <t> --count <n>
       │
       ▼
   CronExpr expr = CronParser.parse(e)
       │   (each of the five fields goes through FieldParser, with the
       │    right bounds and -- for month / day-of-week -- a name table)
       │
       ▼
   NextCalculator.next(expr, from, n)
       │   starts just after `from`, steps minute by minute, and asks
       │   Matcher.matches(expr, minute) at each step until it has n hits
       │
       ▼
   JsonWriter.success(...) -> stdout
```

## Notes on the pieces

### `parse/`

`CronParser` only knows about field *order* and *bounds*; the actual
grammar (lists, ranges, steps, names) lives in `FieldParser`, which turns one
field string into the concrete set of integers it permits. `Field` remembers
whether it was restricted (written as anything other than a leading `*`),
which the day rule in section 2 depends on.

### `match/`

`Matcher` checks minute, hour and month independently, then applies the
day-of-month / day-of-week rule from `PROTOCOL.md` section 2. The day rule is the
only place where two fields interact.

### `calc/`

`NextCalculator` is deliberately simple: it scans forward a minute at a time
in UTC rather than trying to be clever about jumping ahead. There's a hard
cap on how far it will look so an impossible expression terminates instead of
spinning forever.
