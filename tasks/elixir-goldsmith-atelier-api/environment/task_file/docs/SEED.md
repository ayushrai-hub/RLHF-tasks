# Seed data notes

The `seed/seed.sql` file is loaded on first start. Use
`bash scripts/reset_db.sh` inside `/app` when you need to recreate
`/app/data/atelier.db` from the seed.

This is just a map of the fixture topology. Treat `seed/seed.sql` as the source
of truth for exact row values.

## Goldsmith Mentor Tree

```
1 albrecht   mentor=null
2 beatrix    mentor=1
3 cassius    mentor=1
4 delphine   mentor=2
5 ewald      mentor=null
6 frieda     mentor=5
7 gerold     mentor=null
8 hilde      mentor=null
```

## Piece Assignments and State

```
1  AA-0001  released       smith=1
2  AA-0002  released       smith=2
3  AA-0003  hallmarked     smith=1
4  AA-0004  released       smith=1
5  AA-0005  cast_complete  smith=3
6  AA-0006  chased         smith=4
7  AA-0007  hallmarked     smith=1
8  AA-0008  hallmarked     smith=5
9  AA-0009  released       smith=5  parent=8
10 AA-0010  cast_complete  smith=6  parent=9
11 AA-0011  ingot_selected smith=null
12 AA-0012  assayed        smith=2
13 AA-0013  chased         smith=1
14 AA-0014  chased         smith=1
15 AA-0015  chased         smith=1
16 AA-0016  chased         smith=1
17 AA-0017  ingot_selected smith=2  parent=18
18 AA-0018  ingot_selected smith=2  parent=17
19 AA-0019  cast_active    smith=3
20 AA-0020  released       smith=7
```

Pieces 17 and 18 intentionally form a parent cycle for cycle-safe lineage
walks. Pieces 8, 9, and 10 form a simple parent chain. A few pieces also have
component rows in the seed; those are separate from `parent_id`.

## Audit Chain Starting State

The seed loads zero `audit_entries` rows. Every appending endpoint starts the
chain from genesis with `prev_hash = "0" * 64`.
