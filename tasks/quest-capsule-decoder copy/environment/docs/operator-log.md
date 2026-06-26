# Loader Field Notes — QuestCapsule maintenance journal

Maintainer: M. Okonkwo. This is my working journal for keeping the old QuestCapsule
loader alive. The original author (T.R.) left no spec — only the runtime and a pile
of `.qcap.json` files plus the cartridge database. Everything below is what I pieced
together by feeding capsules to the loader, reading the rejections, and poking at the
cartridge with sqlite. If you are taking over the loader, read this front to back; the
format is not hard once you see it, but nothing about it is written down anywhere else.

The shipped pieces are: a small JSON file per capsule (the *spec*), and a single
SQLite *cartridge* that holds the room fragments, the glyph tables, the edges, and the
save-state seeds. The spec is tiny. The cartridge is where the game actually lives. The
spec's only real content is an opaque `header` string; the rest is a pointer at the
cartridge file.

## The shape of a spec

Every spec is three keys: `magic`, `cartridge`, `header`. `magic` has been `QC2` on
everything I have seen (older `QC1` capsules are gone — see the changelog further down).
`cartridge` names the SQLite file to open. `header` is one long token of base64. That is
the whole spec. Do not look for room data in the JSON; it is not there.

## Cracking the header — worked end to end on a throwaway capsule

I will not use a real capsule for the arithmetic because then you would just copy my
numbers instead of learning the move. Here is a demo capsule I built by hand with a
*different* glyph set (set 3, six symbols) so you can follow every step.

Demo header (base64): `ZT1hZjtuPWhiO2c9MztzPWRkYmhkYztrPWRkYmhmaA==`

Base64-decode it and you get a flat ASCII record:

    e=af;n=hb;g=3;s=ddbhdc;k=ddbhfh

So the decoded header is a `;`-separated list of `key=value` pairs. The keys I have ever
seen are `e`, `n`, `g`, `s`, `k`. Their meaning took me a week of rejected loads to nail
down:

- `e` — the entry room id (where a run starts)
- `n` — the number of rooms in the capsule
- `g` — the glyph-set id to decode this capsule with
- `s` — the seed base
- `k` — a check value

Here is the part that tripped me up for days: **only `g` is written in plain digits.**
`e`, `n`, `s`, `k` are all written in *glyphs*, not in ordinary numbers. In the demo
above `g=3` is literally the digit 3, but `e`, `n`, `s`, `k` are strings of letter-pairs.
You decode those letter-pairs with the glyph set whose id is `g`.

## How a glyph value decodes

A glyph value is just text written two characters at a time. You cut the string into
2-character chunks and look each chunk up in the glyph set. Nothing is delimited; the
width is always exactly two. If a value has an odd length, something upstream is wrong
and the loader will refuse it.

In demo set 3 the digit symbols are: `af`=0, `dd`=1, `dc`=2, `hb`=3, `bh`=4, `fh`=5, `ed`=6, `fg`=7, `gd`=8, `ee`=9.

So `s=ddbhdc` cuts into `dd` + `bh` + `dc`, which maps back to 142 — i.e. the seed base is 142. The same chunk
rule decodes `e`, `n` and `k`. There is nothing special about numbers here: the loader
treats a "number" field as text and only parses it as an integer *after* the glyphs are
resolved. That is why `n` for a seven-room capsule is six characters of glyphs, not the
single character `7`.

## The check field

`k` is not random. After I decode `e`, `n` and `s` to integers, `k` is exactly
`(e + n + s) mod 9973`. The loader recomputes that sum and compares it to the decoded
`k`; if they differ it prints `header check mismatch` and stops. In the demo:
`e=0`, `n=3`, `s=142`, so `(0 + 3 + 142) mod 9973 = 145`, and sure enough the decoded
`k` is 145. 9973 is the modulus on every capsule I have checked — it is the largest prime
under ten thousand, which is probably why T.R. picked it. When you write a decoder, carry
both the decoded `k` and a boolean for whether the recomputed sum agrees; a capsule with
a bad check is still readable, the loader just won't *run* it.

## The cartridge tables

Open the cartridge with sqlite and you find four tables. `glyphs(table_id, code, plain)`
is the substitution itself — one row per symbol, e.g. all the rows with `table_id = 7`
make up glyph set 7. `rooms(capsule, room_id, kind, title_glyph, body_glyph)` holds the
fragments; `kind` is `entry`, `exit`, or `normal`, and the `entry` room's id always
equals the header `e`. `edges(capsule, from_room, label_glyph, to_room, guard_glyph)`
holds the transitions. `seeds(capsule, seed_id, seed_value)` holds the save states.

Everything ending in `_glyph` decodes with the same 2-char rule as the header values,
using the capsule's glyph set. `to_room` is a plain integer (it is a row id, not text).
`guard_glyph` is either null or a glyph value that decodes to a token name.

## Rooms, exits, and the grant trick

A room's `title_glyph` decodes to its title and `body_glyph` to its description. Most
bodies are flavour text, but some bodies carry an instruction to the runtime: if a body,
split on periods, has a clause of the form `grant <token>`, then entering that room hands
the player that token for the rest of the run. I missed this for ages because the grant
clause reads like ordinary prose once decoded.

Each row in `edges` is one exit out of `from_room`: a decoded `label` (the word the
player "says"), a `to_room`, and maybe a `guard`. A guarded edge cannot be taken unless
the player is already holding the guard's token. Tokens come from `grant` clauses in
rooms visited earlier on the same path. So a guarded door late in a capsule usually means
there is a room somewhere upstream whose body grants the matching token, and a winning
route has to pass through it first.

## How a run is solved (the part T.R. clearly enjoyed)

A run starts in the entry room and ends when it reaches the single `exit` room. The
loader walks the graph deterministically, and the seed decides the walk. Here is the rule
I reconstructed by replaying save states until the traces matched:

At the current room, first collect any grant the room gives. Then gather the exits you
could legally take right now — the target has not already been visited on this path, and
the exit is either unguarded or its guard token is in hand. Sort those candidate exits by
label (ascending), breaking ties by `to_room`. Now the seed comes in: start scanning the
sorted list at position `seed_value mod (number of candidates)` and wrap around the end.
Walk that order and take the first exit from which the run can still reach the exit room;
if a branch dead-ends, back out and try the next. A room you back out of is free to be
visited again on a different branch, and a token you picked up only counts while you are
on the path that found it.

The emitted transcript is just the rooms you actually end up walking, in order. The first
line is the entry room's title. Each later line is the label you took and the room it led
to, written `label -> title`. That transcript is what has to come out byte-for-byte; the
exact text layout is in output-format.md.

## Session log

What follows is the dated journal — the order I actually figured things out, with the dead ends left in on purpose.

### 2031-01-05

Quiet afternoon, good time to dig. Working salt-myre today; the transcript came out one room too short.

Decoded the room rows for salt-myre out of the cartridge directly. Room 4 carries `title_glyph` = `FYWKVJZFALJQXNZFUEWKUZ` — that is 11 chunks (FY WK VJ ZF AL JQ XN ZF UE WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 55 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on salt-myre. Seed 2008 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

If a future capsule breaks this, start by re-reading the header rules at the top.

### 2031-01-08

Short session, just wanted to confirm a hunch. Working verdant-hollow today; a guarded door never opened.

Replayed the save states on verdant-hollow. Seed 4120 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 3 carries `title_glyph` = `PDJQQVFYUEALJMXNWKWKMNZF` — that is 12 chunks (PD JQ QV FY UE AL JM XN WK WK MN ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 38 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-01-13

Picking this up again after the weekend. Working salt-myre today; the transcript came out one room too short.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9NztzPVh...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=8, s=134, so the check is `(0 + 8 + 134) mod 9973 = 142`. Writing s=134 in set-3 glyphs gives the chunks `dd` `hb` `bh`; feed those back through the set and you recover 134, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-01-22

Came back to an old TODO. Working verdant-hollow today; the loader printed `header check mismatch` and quit.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 5 carries `title_glyph` = `JRAEPDJRALPPJRXNTFKSMNWK` — that is 12 chunks (JR AE PD JR AL PP JR XN TF KS MN WK), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVNEU...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=7, s=320, so the check is `(2 + 7 + 320) mod 9973 = 329`. Writing s=320 in set-3 glyphs gives the chunks `hb` `dc` `af`; feed those back through the set and you recover 320, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-02-03

Notes before I forget the thread. Working amber-transit today; the entry room didn't match what the spec claimed.

Replayed the save states on amber-transit. Seed 2834 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6914 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 0 to 2 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-02-12

Slow day on the loader. Working salt-myre today; the entry room didn't match what the spec claimed.

Decoded the room rows for salt-myre out of the cartridge directly. Room 2 carries `title_glyph` = `UEFYZFALVJKSPDMNWKHWXNUEVJWKUZ` — that is 15 chunks (UE FY ZF AL VJ KS PD MN WK HW XN UE VJ WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on salt-myre. Seed 2008 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8897 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-02-21

Long one today. Working verdant-hollow today; two exits tied and the walk went the wrong way.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on verdant-hollow. Seed 7448 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 4120 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-02-27

Another rejection to chase down. Working salt-myre today; a run hung instead of finishing.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=5, s=233, so the check is `(1 + 5 + 233) mod 9973 = 239`. Writing s=233 in set-3 glyphs gives the chunks `dc` `hb` `hb`; feed those back through the set and you recover 233, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-03-01

Notes before I forget the thread. Working amber-transit today; two exits tied and the walk went the wrong way.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9Nzt...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=6, s=368, so the check is `(2 + 6 + 368) mod 9973 = 376`. Writing s=368 in set-3 glyphs gives the chunks `hb` `ed` `gd`; feed those back through the set and you recover 368, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Decoded the room rows for amber-transit out of the cartridge directly. Room 5 carries `title_glyph` = `HWMNWKYJXNZFUEALJRVJQVQVVJJM` — that is 14 chunks (HW MN WK YJ XN ZF UE AL JR VJ QV QV VJ JM), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-03-07

Notes before I forget the thread. Working salt-myre today; the loader said the glyph value had odd length.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9NztzPVhHWV...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=7, s=630, so the check is `(1 + 7 + 630) mod 9973 = 638`. Writing s=630 in set-3 glyphs gives the chunks `ed` `hb` `af`; feed those back through the set and you recover 630, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-03-09

Another rejection to chase down. Working verdant-hollow today; the loader said the glyph value had odd length.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 2 carries `title_glyph` = `PDUEFYQVQVALJMMNQVQV` — that is 10 chunks (PD UE FY QV QV AL JM MN QV QV), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 58 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVNEU0...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=8, s=412, so the check is `(1 + 8 + 412) mod 9973 = 421`. Writing s=412 in set-3 glyphs gives the chunks `bh` `dd` `dc`; feed those back through the set and you recover 412, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-03-13

Short session, just wanted to confirm a hunch. Working salt-myre today; the transcript came out one room too short.

Decoded the room rows for salt-myre out of the cartridge directly. Room 1 carries `title_glyph` = `QVVJJMALKSWKFYYJQPMN` — that is 10 chunks (QV VJ JM AL KS WK FY YJ QP MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 70 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9NztzPVhH...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=6, s=490, so the check is `(1 + 6 + 490) mod 9973 = 497`. Writing s=490 in set-3 glyphs gives the chunks `bh` `ee` `af`; feed those back through the set and you recover 490, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-03-17

Quiet afternoon, good time to dig. Working salt-myre today; a body looked like flavour but changed the run.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9Nz...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=4, s=947, so the check is `(1 + 4 + 947) mod 9973 = 952`. Writing s=947 in set-3 glyphs gives the chunks `ee` `bh` `fg`; feed those back through the set and you recover 947, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2008 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-03-19

Quiet afternoon, good time to dig. Working salt-myre today; a guarded door never opened.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Decoded the room rows for salt-myre out of the cartridge directly. Room 3 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 54 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-03-27

Short session, just wanted to confirm a hunch. Working salt-myre today; the entry room didn't match what the spec claimed.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on salt-myre. Seed 2008 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8897 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Cross-checked against two other capsules before believing it.

### 2031-04-05

Back on the capsule queue. Working verdant-hollow today; a guarded door never opened.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 3 carries `title_glyph` = `PDJQQVFYUEALJMXNWKWKMNZF` — that is 12 chunks (PD JQ QV FY UE AL JM XN WK WK MN ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 38 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVNEU...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=5, s=125, so the check is `(0 + 5 + 125) mod 9973 = 130`. Writing s=125 in set-3 glyphs gives the chunks `dd` `dc` `fh`; feed those back through the set and you recover 125, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-04-07

Came back to an old TODO. Working amber-transit today; the loader said the glyph value had odd length.

Decoded the room rows for amber-transit out of the cartridge directly. Room 5 carries `title_glyph` = `HWMNWKYJXNZFUEALJRVJQVQVVJJM` — that is 14 chunks (HW MN WK YJ XN ZF UE AL JR VJ QV QV VJ JM), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9N...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=3, s=858, so the check is `(0 + 3 + 858) mod 9973 = 861`. Writing s=858 in set-3 glyphs gives the chunks `gd` `fh` `gd`; feed those back through the set and you recover 858, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Cross-checked against two other capsules before believing it.

### 2031-04-09

Another rejection to chase down. Working tin-observatory today; a guarded door never opened.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPUxC...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=6, s=132, so the check is `(2 + 6 + 132) mod 9973 = 140`. Writing s=132 in set-3 glyphs gives the chunks `dd` `hb` `dc`; feed those back through the set and you recover 132, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Replayed the save states on tin-observatory. Seed 8138 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 877 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-04-17

Came back to an old TODO. Working salt-myre today; the entry room didn't match what the spec claimed.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Decoded the room rows for salt-myre out of the cartridge directly. Room 6 carries `title_glyph` = `PDXNQVUEALTFXNWKPDJR` — that is 10 chunks (PD XN QV UE AL TF XN WK PD JR), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-04-23

Picking this up again after the weekend. Working amber-transit today; the loader printed `header check mismatch` and quit.

Decoded the room rows for amber-transit out of the cartridge directly. Room 3 carries `title_glyph` = `PPVJJQJQMNWKALSGFYQVZF` — that is 11 chunks (PP VJ JQ JQ MN WK AL SG FY QV ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPU...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=3, s=208, so the check is `(2 + 3 + 208) mod 9973 = 213`. Writing s=208 in set-3 glyphs gives the chunks `dc` `af` `gd`; feed those back through the set and you recover 208, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-04-26

Got pulled into this by a support ticket. Working salt-myre today; a run hung instead of finishing.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9Nzt...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=7, s=886, so the check is `(1 + 7 + 886) mod 9973 = 894`. Writing s=886 in set-3 glyphs gives the chunks `gd` `gd` `ed`; feed those back through the set and you recover 886, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-05-07

Notes before I forget the thread. Working verdant-hollow today; the loader said the glyph value had odd length.

Replayed the save states on verdant-hollow. Seed 3933 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 4120 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVNE...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=8, s=774, so the check is `(2 + 8 + 774) mod 9973 = 784`. Writing s=774 in set-3 glyphs gives the chunks `fg` `fg` `bh`; feed those back through the set and you recover 774, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-05-13

Long one today. Working tin-observatory today; the transcript came out one room too short.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on tin-observatory. Seed 877 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8138 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-05-16

Came back to an old TODO. Working verdant-hollow today; the seed seemed to have no effect at all.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 4 carries `title_glyph` = `JQXNQVMNALVJWKPPJRXNWKYJ` — that is 12 chunks (JQ XN QV MN AL VJ WK PP JR XN WK YJ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 52 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9N...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=6, s=964, so the check is `(0 + 6 + 964) mod 9973 = 970`. Writing s=964 in set-3 glyphs gives the chunks `ee` `ed` `bh`; feed those back through the set and you recover 964, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-05-25

Picking this up again after the weekend. Working verdant-hollow today; the seed seemed to have no effect at all.

Replayed the save states on verdant-hollow. Seed 7448 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 2 carries `title_glyph` = `PDUEFYQVQVALJMMNQVQV` — that is 10 chunks (PD UE FY QV QV AL JM MN QV QV), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 58 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-05-28

Another rejection to chase down. Working tin-observatory today; the loader printed `header check mismatch` and quit.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPUx...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=4, s=978, so the check is `(1 + 4 + 978) mod 9973 = 983`. Writing s=978 in set-3 glyphs gives the chunks `ee` `fg` `gd`; feed those back through the set and you recover 978, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-06-05

Long one today. Working salt-myre today; the transcript came out one room too short.

Decoded the room rows for salt-myre out of the cartridge directly. Room 4 carries `title_glyph` = `FYWKVJZFALJQXNZFUEWKUZ` — that is 11 chunks (FY WK VJ ZF AL JQ XN ZF UE WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 55 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9NztzPVhH...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=5, s=422, so the check is `(0 + 5 + 422) mod 9973 = 427`. Writing s=422 in set-3 glyphs gives the chunks `bh` `dc` `dc`; feed those back through the set and you recover 422, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-06-12

Notes before I forget the thread. Working salt-myre today; the seed seemed to have no effect at all.

Decoded the room rows for salt-myre out of the cartridge directly. Room 3 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 54 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on salt-myre. Seed 6705 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2008 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-06-21

Long one today. Working amber-transit today; a body looked like flavour but changed the run.

Decoded the room rows for amber-transit out of the cartridge directly. Room 5 carries `title_glyph` = `HWMNWKYJXNZFUEALJRVJQVQVVJJM` — that is 14 chunks (HW MN WK YJ XN ZF UE AL JR VJ QV QV VJ JM), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on amber-transit. Seed 6914 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6340 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-07-01

Short session, just wanted to confirm a hunch. Working amber-transit today; the entry room didn't match what the spec claimed.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPUdDTE...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=5, s=270, so the check is `(1 + 5 + 270) mod 9973 = 276`. Writing s=270 in set-3 glyphs gives the chunks `dc` `fg` `af`; feed those back through the set and you recover 270, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Decoded the room rows for amber-transit out of the cartridge directly. Room 2 carries `title_glyph` = `FYWKVJZFALJQXNZFUEWKUZ` — that is 11 chunks (FY WK VJ ZF AL JQ XN ZF UE WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-07-06

Long one today. Working salt-myre today; two exits tied and the walk went the wrong way.

Decoded the room rows for salt-myre out of the cartridge directly. Room 2 carries `title_glyph` = `UEFYZFALVJKSPDMNWKHWXNUEVJWKUZ` — that is 15 chunks (UE FY ZF AL VJ KS PD MN WK HW XN UE VJ WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-07-15

Notes before I forget the thread. Working salt-myre today; the seed seemed to have no effect at all.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2008 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-07-20

Came back to an old TODO. Working amber-transit today; a run hung instead of finishing.

Decoded the room rows for amber-transit out of the cartridge directly. Room 2 carries `title_glyph` = `FYWKVJZFALJQXNZFUEWKUZ` — that is 11 chunks (FY WK VJ ZF AL JQ XN ZF UE WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9Nz...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=9, s=397, so the check is `(2 + 9 + 397) mod 9973 = 408`. Writing s=397 in set-3 glyphs gives the chunks `hb` `ee` `fg`; feed those back through the set and you recover 397, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-07-27

Got pulled into this by a support ticket. Working salt-myre today; the decoded title came out as garbage.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for salt-myre out of the cartridge directly. Room 4 carries `title_glyph` = `FYWKVJZFALJQXNZFUEWKUZ` — that is 11 chunks (FY WK VJ ZF AL JQ XN ZF UE WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 55 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-08-05

Quiet afternoon, good time to dig. Working tin-observatory today; a run hung instead of finishing.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 5 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9Nzt...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=6, s=880, so the check is `(1 + 6 + 880) mod 9973 = 887`. Writing s=880 in set-3 glyphs gives the chunks `gd` `gd` `af`; feed those back through the set and you recover 880, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-08-10

Another rejection to chase down. Working salt-myre today; the seed seemed to have no effect at all.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9Nztz...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=9, s=814, so the check is `(2 + 9 + 814) mod 9973 = 825`. Writing s=814 in set-3 glyphs gives the chunks `gd` `dd` `bh`; feed those back through the set and you recover 814, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-08-17

Notes before I forget the thread. Working salt-myre today; the loader said the glyph value had odd length.

Replayed the save states on salt-myre. Seed 2008 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9N...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=8, s=296, so the check is `(1 + 8 + 296) mod 9973 = 305`. Writing s=296 in set-3 glyphs gives the chunks `dc` `ee` `ed`; feed those back through the set and you recover 296, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-08-23

Back on the capsule queue. Working salt-myre today; the entry room didn't match what the spec claimed.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9N...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=6, s=115, so the check is `(2 + 6 + 115) mod 9973 = 123`. Writing s=115 in set-3 glyphs gives the chunks `dd` `dd` `fh`; feed those back through the set and you recover 115, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-09-01

Picking this up again after the weekend. Working verdant-hollow today; a body looked like flavour but changed the run.

Replayed the save states on verdant-hollow. Seed 3933 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 7448 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPV...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=9, s=684, so the check is `(0 + 9 + 684) mod 9973 = 693`. Writing s=684 in set-3 glyphs gives the chunks `ed` `gd` `bh`; feed those back through the set and you recover 684, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-09-05

Short session, just wanted to confirm a hunch. Working tin-observatory today; two exits tied and the walk went the wrong way.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPUxC...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=6, s=538, so the check is `(1 + 6 + 538) mod 9973 = 545`. Writing s=538 in set-3 glyphs gives the chunks `fh` `hb` `gd`; feed those back through the set and you recover 538, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 3 carries `title_glyph` = `WKAEPDUEMNYJALQPXNUEMN` — that is 11 chunks (WK AE PD UE MN YJ AL QP XN UE MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 54 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Adding this to the running list of things the loader never bothered to document.

### 2031-09-12

Notes before I forget the thread. Working salt-myre today; a run hung instead of finishing.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=3, s=567, so the check is `(1 + 3 + 567) mod 9973 = 571`. Writing s=567 in set-3 glyphs gives the chunks `fh` `ed` `fg`; feed those back through the set and you recover 567, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2008 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-09-15

Quiet afternoon, good time to dig. Working tin-observatory today; the entry room didn't match what the spec claimed.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=3, s=549, so the check is `(0 + 3 + 549) mod 9973 = 552`. Writing s=549 in set-3 glyphs gives the chunks `fh` `bh` `ee`; feed those back through the set and you recover 549, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-09-19

Long one today. Working salt-myre today; a guarded door never opened.

Decoded the room rows for salt-myre out of the cartridge directly. Room 6 carries `title_glyph` = `PDXNQVUEALTFXNWKPDJR` — that is 10 chunks (PD XN QV UE AL TF XN WK PD JR), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-09-21

Quiet afternoon, good time to dig. Working salt-myre today; a guarded door never opened.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for salt-myre out of the cartridge directly. Room 4 carries `title_glyph` = `FYWKVJZFALJQXNZFUEWKUZ` — that is 11 chunks (FY WK VJ ZF AL JQ XN ZF UE WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 55 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Adding this to the running list of things the loader never bothered to document.

### 2031-09-27

Came back to an old TODO. Working amber-transit today; the seed seemed to have no effect at all.

Replayed the save states on amber-transit. Seed 6914 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2834 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 3 to 4 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-10-03

Got pulled into this by a support ticket. Working amber-transit today; a guarded door never opened.

Decoded the room rows for amber-transit out of the cartridge directly. Room 5 carries `title_glyph` = `HWMNWKYJXNZFUEALJRVJQVQVVJJM` — that is 14 chunks (HW MN WK YJ XN ZF UE AL JR VJ QV QV VJ JM), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 2 to 1 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-10-09

Long one today. Working tin-observatory today; two exits tied and the walk went the wrong way.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=9, s=975, so the check is `(0 + 9 + 975) mod 9973 = 984`. Writing s=975 in set-3 glyphs gives the chunks `ee` `fg` `fh`; feed those back through the set and you recover 975, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-10-11

Slow day on the loader. Working amber-transit today; the transcript came out one room too short.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 3 to 4 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=6, s=258, so the check is `(1 + 6 + 258) mod 9973 = 265`. Writing s=258 in set-3 glyphs gives the chunks `dc` `fh` `gd`; feed those back through the set and you recover 258, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-10-17

Short session, just wanted to confirm a hunch. Working salt-myre today; the seed seemed to have no effect at all.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-10-21

Got pulled into this by a support ticket. Working salt-myre today; a body looked like flavour but changed the run.

Decoded the room rows for salt-myre out of the cartridge directly. Room 3 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 54 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on salt-myre. Seed 2008 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-11-01

Quiet afternoon, good time to dig. Working amber-transit today; a guarded door never opened.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 3 to 4 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPUdDT...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=5, s=395, so the check is `(1 + 5 + 395) mod 9973 = 401`. Writing s=395 in set-3 glyphs gives the chunks `hb` `ee` `fh`; feed those back through the set and you recover 395, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Cross-checked against two other capsules before believing it.

### 2031-11-07

Notes before I forget the thread. Working tin-observatory today; a run hung instead of finishing.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 5 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Adding this to the running list of things the loader never bothered to document.

### 2031-11-11

Short session, just wanted to confirm a hunch. Working verdant-hollow today; the loader printed `header check mismatch` and quit.

Replayed the save states on verdant-hollow. Seed 4120 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 5 carries `title_glyph` = `JRAEPDJRALPPJRXNTFKSMNWK` — that is 12 chunks (JR AE PD JR AL PP JR XN TF KS MN WK), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-11-19

Picking this up again after the weekend. Working salt-myre today; two exits tied and the walk went the wrong way.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9Nzt...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=7, s=160, so the check is `(1 + 7 + 160) mod 9973 = 168`. Writing s=160 in set-3 glyphs gives the chunks `dd` `ed` `af`; feed those back through the set and you recover 160, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-11-24

Back on the capsule queue. Working amber-transit today; two exits tied and the walk went the wrong way.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPUd...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=9, s=258, so the check is `(0 + 9 + 258) mod 9973 = 267`. Writing s=258 in set-3 glyphs gives the chunks `dc` `fh` `gd`; feed those back through the set and you recover 258, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 3 to 4 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-11-26

Another rejection to chase down. Working tin-observatory today; the loader said the glyph value had odd length.

Replayed the save states on tin-observatory. Seed 8138 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2803 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 5 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-12-07

Long one today. Working tin-observatory today; a run hung instead of finishing.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPUxCW...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=7, s=304, so the check is `(2 + 7 + 304) mod 9973 = 313`. Writing s=304 in set-3 glyphs gives the chunks `hb` `af` `bh`; feed those back through the set and you recover 304, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Cross-checked against two other capsules before believing it.

### 2031-12-12

Quiet afternoon, good time to dig. Working verdant-hollow today; two exits tied and the walk went the wrong way.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVNEU...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=7, s=957, so the check is `(0 + 7 + 957) mod 9973 = 964`. Writing s=957 in set-3 glyphs gives the chunks `ee` `fh` `fg`; feed those back through the set and you recover 957, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 3 carries `title_glyph` = `PDJQQVFYUEALJMXNWKWKMNZF` — that is 12 chunks (PD JQ QV FY UE AL JM XN WK WK MN ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 38 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-12-16

Picking this up again after the weekend. Working amber-transit today; two exits tied and the walk went the wrong way.

Replayed the save states on amber-transit. Seed 2834 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6340 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9N...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=5, s=576, so the check is `(0 + 5 + 576) mod 9973 = 581`. Writing s=576 in set-3 glyphs gives the chunks `fh` `fg` `ed`; feed those back through the set and you recover 576, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-12-25

Short session, just wanted to confirm a hunch. Working tin-observatory today; the loader printed `header check mismatch` and quit.

Replayed the save states on tin-observatory. Seed 8138 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2803 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 6 carries `title_glyph` = `YJWKVJJMZFMNYJALXNWKPPJRFYHWMN` — that is 15 chunks (YJ WK VJ JM ZF MN YJ AL XN WK PP JR FY HW MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Cross-checked against two other capsules before believing it.

### 2032-01-04

Picking this up again after the weekend. Working amber-transit today; two exits tied and the walk went the wrong way.

Decoded the room rows for amber-transit out of the cartridge directly. Room 1 carries `title_glyph` = `UEFYZFALVJKSPDMNWKHWXNUEVJWKUZ` — that is 15 chunks (UE FY ZF AL VJ KS PD MN WK HW XN UE VJ WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 2 to 1 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Cross-checked against two other capsules before believing it.

### 2032-01-08

Another rejection to chase down. Working verdant-hollow today; the entry room didn't match what the spec claimed.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=8, s=865, so the check is `(1 + 8 + 865) mod 9973 = 874`. Writing s=865 in set-3 glyphs gives the chunks `gd` `ed` `fh`; feed those back through the set and you recover 865, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Leaving a note here so the next person doesn't lose the week I lost.

### 2032-01-16

Short session, just wanted to confirm a hunch. Working salt-myre today; two exits tied and the walk went the wrong way.

Replayed the save states on salt-myre. Seed 2008 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2032-01-23

Back on the capsule queue. Working salt-myre today; the loader printed `header check mismatch` and quit.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9NztzP...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=5, s=356, so the check is `(0 + 5 + 356) mod 9973 = 361`. Writing s=356 in set-3 glyphs gives the chunks `hb` `fh` `ed`; feed those back through the set and you recover 356, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Replayed the save states on salt-myre. Seed 6705 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2008 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2032-01-26

Picking this up again after the weekend. Working amber-transit today; the loader said the glyph value had odd length.

Decoded the room rows for amber-transit out of the cartridge directly. Room 1 carries `title_glyph` = `UEFYZFALVJKSPDMNWKHWXNUEVJWKUZ` — that is 15 chunks (UE FY ZF AL VJ KS PD MN WK HW XN UE VJ WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 3 to 2 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

If a future capsule breaks this, start by re-reading the header rules at the top.

### 2032-02-07

Long one today. Working amber-transit today; a guarded door never opened.

Decoded the room rows for amber-transit out of the cartridge directly. Room 4 carries `title_glyph` = `WKAEPDUEMNYJALQPXNUEMN` — that is 11 chunks (WK AE PD UE MN YJ AL QP XN UE MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 38 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on amber-transit. Seed 6914 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6340 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Cross-checked against two other capsules before believing it.

### 2032-02-12

Picking this up again after the weekend. Working amber-transit today; a body looked like flavour but changed the run.

Decoded the room rows for amber-transit out of the cartridge directly. Room 3 carries `title_glyph` = `PPVJJQJQMNWKALSGFYQVZF` — that is 11 chunks (PP VJ JQ JQ MN WK AL SG FY QV ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on amber-transit. Seed 2834 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6914 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Cross-checked against two other capsules before believing it.

### 2032-02-16

Slow day on the loader. Working tin-observatory today; the seed seemed to have no effect at all.

Replayed the save states on tin-observatory. Seed 877 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8138 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2032-02-25

Another rejection to chase down. Working verdant-hollow today; the entry room didn't match what the spec claimed.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9Nzt...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=5, s=800, so the check is `(0 + 5 + 800) mod 9973 = 805`. Writing s=800 in set-3 glyphs gives the chunks `gd` `af` `af`; feed those back through the set and you recover 800, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2032-03-04

Quiet afternoon, good time to dig. Working verdant-hollow today; the loader said the glyph value had odd length.

Replayed the save states on verdant-hollow. Seed 4120 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2032-03-06

Got pulled into this by a support ticket. Working amber-transit today; the loader printed `header check mismatch` and quit.

Decoded the room rows for amber-transit out of the cartridge directly. Room 3 carries `title_glyph` = `PPVJJQJQMNWKALSGFYQVZF` — that is 11 chunks (PP VJ JQ JQ MN WK AL SG FY QV ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 4 to 2 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2032-03-15

Got pulled into this by a support ticket. Working tin-observatory today; the transcript came out one room too short.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9Nz...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=8, s=693, so the check is `(2 + 8 + 693) mod 9973 = 703`. Writing s=693 in set-3 glyphs gives the chunks `ed` `ee` `hb`; feed those back through the set and you recover 693, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Replayed the save states on tin-observatory. Seed 877 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8138 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Leaving a note here so the next person doesn't lose the week I lost.

### 2032-03-22

Quiet afternoon, good time to dig. Working tin-observatory today; a run hung instead of finishing.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 5 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on tin-observatory. Seed 2803 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8138 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Adding this to the running list of things the loader never bothered to document.

### 2032-03-27

Notes before I forget the thread. Working salt-myre today; the decoded title came out as garbage.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9N...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=5, s=523, so the check is `(1 + 5 + 523) mod 9973 = 529`. Writing s=523 in set-3 glyphs gives the chunks `fh` `dc` `hb`; feed those back through the set and you recover 523, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2032-04-01

Long one today. Working tin-observatory today; the loader printed `header check mismatch` and quit.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 6 carries `title_glyph` = `YJWKVJJMZFMNYJALXNWKPPJRFYHWMN` — that is 15 chunks (YJ WK VJ JM ZF MN YJ AL XN WK PP JR FY HW MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPUxCWV...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=8, s=135, so the check is `(2 + 8 + 135) mod 9973 = 145`. Writing s=135 in set-3 glyphs gives the chunks `dd` `hb` `fh`; feed those back through the set and you recover 135, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

If a future capsule breaks this, start by re-reading the header rules at the top.

### 2032-04-05

Got pulled into this by a support ticket. Working verdant-hollow today; a guarded door never opened.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVNE...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=3, s=971, so the check is `(1 + 3 + 971) mod 9973 = 975`. Writing s=971 in set-3 glyphs gives the chunks `ee` `fg` `dd`; feed those back through the set and you recover 971, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2032-04-12

Picking this up again after the weekend. Working salt-myre today; the loader printed `header check mismatch` and quit.

Replayed the save states on salt-myre. Seed 6705 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2008 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for salt-myre out of the cartridge directly. Room 3 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 54 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Cross-checked against two other capsules before believing it.

### 2032-04-17

Picking this up again after the weekend. Working verdant-hollow today; the decoded title came out as garbage.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 3 carries `title_glyph` = `PDJQQVFYUEALJMXNWKWKMNZF` — that is 12 chunks (PD JQ QV FY UE AL JM XN WK WK MN ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 38 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on verdant-hollow. Seed 7448 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 4120 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Cross-checked against two other capsules before believing it.

### 2032-04-19

Short session, just wanted to confirm a hunch. Working salt-myre today; the loader said the glyph value had odd length.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9NztzPVh...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=9, s=576, so the check is `(1 + 9 + 576) mod 9973 = 586`. Writing s=576 in set-3 glyphs gives the chunks `fh` `fg` `ed`; feed those back through the set and you recover 576, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2032-04-24

Got pulled into this by a support ticket. Working tin-observatory today; the transcript came out one room too short.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPU...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=7, s=589, so the check is `(1 + 7 + 589) mod 9973 = 597`. Writing s=589 in set-3 glyphs gives the chunks `fh` `gd` `ee`; feed those back through the set and you recover 589, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 4 carries `title_glyph` = `JRAEPDJRALPPJRXNTFKSMNWK` — that is 12 chunks (JR AE PD JR AL PP JR XN TF KS MN WK), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Adding this to the running list of things the loader never bothered to document.

### 2031-01-05

Another rejection to chase down. Working amber-transit today; the transcript came out one room too short.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 1 to 5 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Decoded the room rows for amber-transit out of the cartridge directly. Room 3 carries `title_glyph` = `PPVJJQJQMNWKALSGFYQVZF` — that is 11 chunks (PP VJ JQ JQ MN WK AL SG FY QV ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Adding this to the running list of things the loader never bothered to document.

### 2031-01-08

Short session, just wanted to confirm a hunch. Working amber-transit today; a body looked like flavour but changed the run.

Decoded the room rows for amber-transit out of the cartridge directly. Room 3 carries `title_glyph` = `PPVJJQJQMNWKALSGFYQVZF` — that is 11 chunks (PP VJ JQ JQ MN WK AL SG FY QV ZF), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 4 to 3 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-01-13

Picking this up again after the weekend. Working tin-observatory today; a run hung instead of finishing.

Replayed the save states on tin-observatory. Seed 877 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8138 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 5 carries `title_glyph` = `BZXNWKALQVXNZFYJFYZFQP` — that is 11 chunks (BZ XN WK AL QV XN ZF YJ FY ZF QP), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Adding this to the running list of things the loader never bothered to document.

### 2031-01-22

Short session, just wanted to confirm a hunch. Working salt-myre today; two exits tied and the walk went the wrong way.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2008 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

If a future capsule breaks this, start by re-reading the header rules at the top.

### 2031-02-03

Picking this up again after the weekend. Working tin-observatory today; the loader printed `header check mismatch` and quit.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPUxC...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=9, s=241, so the check is `(0 + 9 + 241) mod 9973 = 250`. Writing s=241 in set-3 glyphs gives the chunks `dc` `bh` `dd`; feed those back through the set and you recover 241, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 4 carries `title_glyph` = `JRAEPDJRALPPJRXNTFKSMNWK` — that is 12 chunks (JR AE PD JR AL PP JR XN TF KS MN WK), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-02-12

Got pulled into this by a support ticket. Working amber-transit today; the seed seemed to have no effect at all.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9N...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=5, s=716, so the check is `(1 + 5 + 716) mod 9973 = 722`. Writing s=716 in set-3 glyphs gives the chunks `fg` `dd` `ed`; feed those back through the set and you recover 716, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Decoded the room rows for amber-transit out of the cartridge directly. Room 1 carries `title_glyph` = `UEFYZFALVJKSPDMNWKHWXNUEVJWKUZ` — that is 15 chunks (UE FY ZF AL VJ KS PD MN WK HW XN UE VJ WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Cross-checked against two other capsules before believing it.

### 2031-02-21

Quiet afternoon, good time to dig. Working tin-observatory today; a run hung instead of finishing.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=8, s=147, so the check is `(0 + 8 + 147) mod 9973 = 155`. Writing s=147 in set-3 glyphs gives the chunks `dd` `bh` `fg`; feed those back through the set and you recover 147, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Adding this to the running list of things the loader never bothered to document.

### 2031-02-27

Short session, just wanted to confirm a hunch. Working salt-myre today; the decoded title came out as garbage.

Replayed the save states on salt-myre. Seed 6705 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8897 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Decoded the room rows for salt-myre out of the cartridge directly. Room 1 carries `title_glyph` = `QVVJJMALKSWKFYYJQPMN` — that is 10 chunks (QV VJ JM AL KS WK FY YJ QP MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 70 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

If a future capsule breaks this, start by re-reading the header rules at the top.

### 2031-03-01

Quiet afternoon, good time to dig. Working verdant-hollow today; a body looked like flavour but changed the run.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on verdant-hollow. Seed 4120 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-03-07

Back on the capsule queue. Working amber-transit today; the loader printed `header check mismatch` and quit.

Replayed the save states on amber-transit. Seed 2834 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6340 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 2 to 4 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Cross-checked against two other capsules before believing it.

### 2031-03-09

Long one today. Working salt-myre today; the loader printed `header check mismatch` and quit.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-03-13

Short session, just wanted to confirm a hunch. Working salt-myre today; the seed seemed to have no effect at all.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Decoded the room rows for salt-myre out of the cartridge directly. Room 1 carries `title_glyph` = `QVVJJMALKSWKFYYJQPMN` — that is 10 chunks (QV VJ JM AL KS WK FY YJ QP MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 70 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-03-17

Got pulled into this by a support ticket. Working verdant-hollow today; the seed seemed to have no effect at all.

Replayed the save states on verdant-hollow. Seed 7448 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9Nzt...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=7, s=361, so the check is `(2 + 7 + 361) mod 9973 = 370`. Writing s=361 in set-3 glyphs gives the chunks `hb` `ed` `dd`; feed those back through the set and you recover 361, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Cross-checked against two other capsules before believing it.

### 2031-03-19

Short session, just wanted to confirm a hunch. Working verdant-hollow today; a body looked like flavour but changed the run.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVNE...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=3, s=564, so the check is `(2 + 3 + 564) mod 9973 = 569`. Writing s=564 in set-3 glyphs gives the chunks `fh` `ed` `bh`; feed those back through the set and you recover 564, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-03-27

Another rejection to chase down. Working amber-transit today; the seed seemed to have no effect at all.

Replayed the save states on amber-transit. Seed 6340 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2834 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9Nztz...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=7, s=174, so the check is `(2 + 7 + 174) mod 9973 = 183`. Writing s=174 in set-3 glyphs gives the chunks `dd` `fg` `bh`; feed those back through the set and you recover 174, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-04-05

Back on the capsule queue. Working amber-transit today; two exits tied and the walk went the wrong way.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzP...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=6, s=404, so the check is `(2 + 6 + 404) mod 9973 = 412`. Writing s=404 in set-3 glyphs gives the chunks `bh` `af` `bh`; feed those back through the set and you recover 404, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Mapped the full exit set for amber-transit. No guards on this capsule, so every `guard_glyph` is null and the only thing steering a walk is the seed and the label ordering. The edge from room 2 to 1 decodes to an ordinary choice word. Room 3 has the most exits (3), so that is the room where the seed's rotation offset changes which way the walk goes; everywhere with a single exit the seed is irrelevant because `seed_value mod 1` is always 0. `to_room` stays a plain integer; only the label is glyph-encoded on these rows.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-04-07

Long one today. Working verdant-hollow today; a guarded door never opened.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 1 carries `title_glyph` = `MNTFKSMNWKALYJVJPPSG` — that is 10 chunks (MN TF KS MN WK AL YJ VJ PP SG), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 73 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-04-09

Came back to an old TODO. Working salt-myre today; a body looked like flavour but changed the run.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9NztzP...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=8, s=468, so the check is `(0 + 8 + 468) mod 9973 = 476`. Writing s=468 in set-3 glyphs gives the chunks `bh` `ed` `gd`; feed those back through the set and you recover 468, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-04-17

Slow day on the loader. Working tin-observatory today; the transcript came out one room too short.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on tin-observatory. Seed 8138 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 877 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Cross-checked against two other capsules before believing it.

### 2031-04-23

Came back to an old TODO. Working verdant-hollow today; two exits tied and the walk went the wrong way.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Decoded the room rows for verdant-hollow out of the cartridge directly. Room 2 carries `title_glyph` = `PDUEFYQVQVALJMMNQVQV` — that is 10 chunks (PD UE FY QV QV AL JM MN QV QV), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 58 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Cross-checked against two other capsules before believing it.

### 2031-04-26

Another rejection to chase down. Working verdant-hollow today; a guarded door never opened.

Replayed the save states on verdant-hollow. Seed 7448 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVNEU0...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=4, s=140, so the check is `(1 + 4 + 140) mod 9973 = 145`. Writing s=140 in set-3 glyphs gives the chunks `dd` `bh` `af`; feed those back through the set and you recover 140, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-05-07

Picking this up again after the weekend. Working verdant-hollow today; the loader said the glyph value had odd length.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzP...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=4, s=301, so the check is `(0 + 4 + 301) mod 9973 = 305`. Writing s=301 in set-3 glyphs gives the chunks `hb` `af` `dd`; feed those back through the set and you recover 301, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Replayed the save states on verdant-hollow. Seed 4120 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

If a future capsule breaks this, start by re-reading the header rules at the top.

### 2031-05-13

Another rejection to chase down. Working salt-myre today; the decoded title came out as garbage.

Chased the guarded door in salt-myre. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 3 to room 6 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 4 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on salt-myre. Seed 6705 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 2008 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-05-16

Picking this up again after the weekend. Working verdant-hollow today; two exits tied and the walk went the wrong way.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9Nzt...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=5, s=575, so the check is `(0 + 5 + 575) mod 9973 = 580`. Writing s=575 in set-3 glyphs gives the chunks `fh` `fg` `fh`; feed those back through the set and you recover 575, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-05-25

Quiet afternoon, good time to dig. Working verdant-hollow today; a run hung instead of finishing.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9N...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=5, s=888, so the check is `(2 + 5 + 888) mod 9973 = 895`. Writing s=888 in set-3 glyphs gives the chunks `gd` `gd` `gd`; feed those back through the set and you recover 888, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Replayed the save states on verdant-hollow. Seed 7448 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 3933 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-05-28

Back on the capsule queue. Working tin-observatory today; a guarded door never opened.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 6 carries `title_glyph` = `YJWKVJJMZFMNYJALXNWKPPJRFYHWMN` — that is 15 chunks (YJ WK VJ JM ZF MN YJ AL XN WK PP JR FY HW MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-06-05

Quiet afternoon, good time to dig. Working tin-observatory today; a run hung instead of finishing.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPU...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=7, s=258, so the check is `(0 + 7 + 258) mod 9973 = 265`. Writing s=258 in set-3 glyphs gives the chunks `dc` `fh` `gd`; feed those back through the set and you recover 258, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Cross-checked against two other capsules before believing it.

### 2031-06-12

Got pulled into this by a support ticket. Working verdant-hollow today; the loader printed `header check mismatch` and quit.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9Nz...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=3, s=708, so the check is `(1 + 3 + 708) mod 9973 = 712`. Writing s=708 in set-3 glyphs gives the chunks `fg` `af` `gd`; feed those back through the set and you recover 708, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-06-21

Got pulled into this by a support ticket. Working amber-transit today; the decoded title came out as garbage.

Decoded the room rows for amber-transit out of the cartridge directly. Room 5 carries `title_glyph` = `HWMNWKYJXNZFUEALJRVJQVQVVJJM` — that is 14 chunks (HW MN WK YJ XN ZF UE AL JR VJ QV QV VJ JM), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 40 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=8, s=161, so the check is `(0 + 8 + 161) mod 9973 = 169`. Writing s=161 in set-3 glyphs gives the chunks `dd` `ed` `dd`; feed those back through the set and you recover 161, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-07-01

Picking this up again after the weekend. Working tin-observatory today; the transcript came out one room too short.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9NztzPUx...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=0, n=7, s=942, so the check is `(0 + 7 + 942) mod 9973 = 949`. Writing s=942 in set-3 glyphs gives the chunks `ee` `bh` `dc`; feed those back through the set and you recover 942, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-07-06

Another rejection to chase down. Working verdant-hollow today; the loader printed `header check mismatch` and quit.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on verdant-hollow. Seed 4120 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 7448 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Still no idea why T.R. encoded numbers as glyphs, but the rule holds.

### 2031-07-15

Another rejection to chase down. Working amber-transit today; a guarded door never opened.

Decoded the room rows for amber-transit out of the cartridge directly. Room 1 carries `title_glyph` = `UEFYZFALVJKSPDMNWKHWXNUEVJWKUZ` — that is 15 chunks (UE FY ZF AL VJ KS PD MN WK HW XN UE VJ WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Replayed the save states on amber-transit. Seed 2834 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6340 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-07-20

Another rejection to chase down. Working tin-observatory today; two exits tied and the walk went the wrong way.

Chased the guarded door in tin-observatory. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 1 to room 6 has a guard of `WKAEZFMNALPPJRFYUE`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 3 is the busiest in this capsule with 3 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Replayed the save states on tin-observatory. Seed 877 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 8138 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-07-27

Back on the capsule queue. Working tin-observatory today; the loader printed `header check mismatch` and quit.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9Nz...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=6, s=553, so the check is `(2 + 6 + 553) mod 9973 = 561`. Writing s=553 in set-3 glyphs gives the chunks `fh` `fh` `hb`; feed those back through the set and you recover 553, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 3 carries `title_glyph` = `WKAEPDUEMNYJALQPXNUEMN` — that is 11 chunks (WK AE PD UE MN YJ AL QP XN UE MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 54 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

That symptom in the heading turned out to be a decode mistake on my end, as usual.

### 2031-08-05

Back on the capsule queue. Working salt-myre today; two exits tied and the walk went the wrong way.

Replayed the save states on salt-myre. Seed 8897 produces the same walk every single time, which finally killed the theory that the seed feeds an RNG. It does not. Sort the legal exits at a room by label ascending, ties broken by `to_room`; the seed only chooses the *start index* into that sorted list, at `seed_value mod count`, wrapping past the end. From that start you take the first exit from which the run can still reach the exit room, backing out of dead ends. Switching to seed 6705 moves the start index, so at any room with a real choice a different exit wins — but the set of legal exits, and the sort, never change. A token picked up on a branch only counts while you stay on that branch; back out and you drop it, and a room you backed out of is fair game again on another branch. The emitted transcript is just the rooms you really walked: first line the entry title, every later line `label -> title`.

Pulled the spec for salt-myre. The `header` is one base64 token starting `ZT1FRztuPUxCO2c9NztzPV...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=3, s=571, so the check is `(1 + 3 + 571) mod 9973 = 575`. Writing s=571 in set-3 glyphs gives the chunks `fh` `fg` `dd`; feed those back through the set and you recover 571, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Confidence: high. Same behaviour on every capsule in the cartridge so far.

### 2031-08-10

Quiet afternoon, good time to dig. Working verdant-hollow today; the loader said the glyph value had odd length.

Pulled the spec for verdant-hollow. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPVN...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=5, s=400, so the check is `(2 + 5 + 400) mod 9973 = 407`. Writing s=400 in set-3 glyphs gives the chunks `bh` `af` `af`; feed those back through the set and you recover 400, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Chased the guarded door in verdant-hollow. Each `edges` row is one exit: a `label_glyph`, a plain `to_room`, and a nullable `guard_glyph`. The edge from room 2 to room 4 has a guard of `PDJQXNWKSGALPPVJFYQV`, which decodes to a token name. That door will not open until the player is already carrying that token, and the only source of a token is a `grant` clause in a room body visited earlier on the same path. So the blocked route was correct: my replay simply had not passed through the granting room yet. Room 4 is the busiest in this capsule with 5 exits, which is where the seed actually matters — more candidates to rotate through. `to_room` is a plain integer the whole time; it is the only number in the cartridge that is not glyph-encoded.

Leaving a note here so the next person doesn't lose the week I lost.

### 2031-08-17

Picking this up again after the weekend. Working tin-observatory today; the loader said the glyph value had odd length.

Decoded the room rows for tin-observatory out of the cartridge directly. Room 6 carries `title_glyph` = `YJWKVJJMZFMNYJALXNWKPPJRFYHWMN` — that is 15 chunks (YJ WK VJ JM ZF MN YJ AL XN WK PP JR FY HW MN), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `exit`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for tin-observatory. The `header` is one base64 token starting `ZT1FRztuPVlaO2c9Nz...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=1, n=4, s=889, so the check is `(1 + 4 + 889) mod 9973 = 894`. Writing s=889 in set-3 glyphs gives the chunks `gd` `gd` `ee`; feed those back through the set and you recover 889, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Adding this to the running list of things the loader never bothered to document.

### 2031-08-23

Short session, just wanted to confirm a hunch. Working amber-transit today; the entry room didn't match what the spec claimed.

Decoded the room rows for amber-transit out of the cartridge directly. Room 1 carries `title_glyph` = `UEFYZFALVJKSPDMNWKHWXNUEVJWKUZ` — that is 15 chunks (UE FY ZF AL VJ KS PD MN WK HW XN UE VJ WK UZ), even length, so it is well-formed; an odd length is the loader's other favourite complaint and always means a truncated payload. The `body_glyph` on that row is longer, 36 chunks, and decodes to a sentence. Most bodies are scenery, but I have learned to split each decoded body on periods and look for a `grant <token>` clause, because that clause is the runtime handing the player an item, not decoration. This row's `kind` is `normal`. As a sanity check I confirmed the `entry` row is id 0, which is exactly what the header `e` decodes to for this capsule — when the two disagree it is always my decode that is wrong, never the cartridge.

Pulled the spec for amber-transit. The `header` is one base64 token starting `ZT1FRztuPVhHO2c9NztzPU...`; decode it and you get the flat `;`-separated record again. The trap I keep falling into is reading the number fields as ordinary digits. They are not. Only `g` is plain. To make sure I still had the move, I rebuilt a scratch header by hand on the side: e=2, n=5, s=430, so the check is `(2 + 5 + 430) mod 9973 = 437`. Writing s=430 in set-3 glyphs gives the chunks `bh` `hb` `af`; feed those back through the set and you recover 430, then parse the integer. Same procedure on the real field: cut into 2-char chunks, resolve against the set `g` names, parse last. Once I did that the `header check mismatch` went away — it had been me, not the capsule. The decoded `k` is worth keeping even when it agrees, because a capsule with a bad check is still readable; the loader just refuses to *run* it.

Leaving a note here so the next person doesn't lose the week I lost.

