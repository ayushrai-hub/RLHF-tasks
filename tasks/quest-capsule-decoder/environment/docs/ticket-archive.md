# Support ticket archive

Closed tickets about the loader, kept because the explanations are the clearest statement of how the format behaves in practice. Every one of these was a misunderstanding of the format, not a defect in the loader.

### Ticket #1000 — seed appears to do nothing on tin-observatory

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 8138 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1001 — seed appears to do nothing on salt-myre

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 8897 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1002 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1003 — seed appears to do nothing on tin-observatory

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 2803 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1004 — a run never terminates on salt-myre

Their walker had no visited check, so it looped between two rooms. On a single path a target that is already on the path is not a legal exit; with that in place the walk reaches the exit room and stops. They also had not implemented the guard rule, so it was trying doors it could not legally open.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1005 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1006 — odd-length glyph value crashes the decoder

A glyph value must be an even number of characters because every symbol is exactly two characters. An odd length means the payload was truncated upstream; the loader is right to refuse it. Told them to treat odd length as a hard error, not to pad it.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1007 — guarded door on tin-observatory looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1008 — titles render as nonsense for capsule verdant-hollow

They were decoding `title_glyph` with the wrong glyph set — set 7 is what the current cartridge uses, but they had hard-coded an older set. Reminder for everyone: decode every `_glyph` column with the set the *header* names in `g`, not whatever you used last.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1009 — titles render as nonsense for capsule salt-myre

They were decoding `title_glyph` with the wrong glyph set — set 7 is what the current cartridge uses, but they had hard-coded an older set. Reminder for everyone: decode every `_glyph` column with the set the *header* names in `g`, not whatever you used last.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1010 — seed appears to do nothing on salt-myre

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 6705 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1011 — guarded door on tin-observatory looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1012 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1013 — seed appears to do nothing on salt-myre

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 8897 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1014 — seed appears to do nothing on tin-observatory

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 877 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1015 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1016 — a run never terminates on tin-observatory

Their walker had no visited check, so it looped between two rooms. On a single path a target that is already on the path is not a legal exit; with that in place the walk reaches the exit room and stops. They also had not implemented the guard rule, so it was trying doors it could not legally open.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1017 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1018 — titles render as nonsense for capsule verdant-hollow

They were decoding `title_glyph` with the wrong glyph set — set 7 is what the current cartridge uses, but they had hard-coded an older set. Reminder for everyone: decode every `_glyph` column with the set the *header* names in `g`, not whatever you used last.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1019 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1020 — guarded door on amber-transit looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1021 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1022 — a run never terminates on tin-observatory

Their walker had no visited check, so it looped between two rooms. On a single path a target that is already on the path is not a legal exit; with that in place the walk reaches the exit room and stops. They also had not implemented the guard rule, so it was trying doors it could not legally open.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1023 — guarded door on amber-transit looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1024 — seed appears to do nothing on amber-transit

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 6914 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1025 — seed appears to do nothing on salt-myre

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 6705 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1026 — guarded door on tin-observatory looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1027 — a run never terminates on tin-observatory

Their walker had no visited check, so it looped between two rooms. On a single path a target that is already on the path is not a legal exit; with that in place the walk reaches the exit room and stops. They also had not implemented the guard rule, so it was trying doors it could not legally open.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1028 — titles render as nonsense for capsule verdant-hollow

They were decoding `title_glyph` with the wrong glyph set — set 7 is what the current cartridge uses, but they had hard-coded an older set. Reminder for everyone: decode every `_glyph` column with the set the *header* names in `g`, not whatever you used last.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1029 — seed appears to do nothing on tin-observatory

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 8138 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1030 — guarded door on salt-myre looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1031 — a run never terminates on amber-transit

Their walker had no visited check, so it looped between two rooms. On a single path a target that is already on the path is not a legal exit; with that in place the walk reaches the exit room and stops. They also had not implemented the guard rule, so it was trying doors it could not legally open.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1032 — odd-length glyph value crashes the decoder

A glyph value must be an even number of characters because every symbol is exactly two characters. An odd length means the payload was truncated upstream; the loader is right to refuse it. Told them to treat odd length as a hard error, not to pad it.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1033 — a run never terminates on salt-myre

Their walker had no visited check, so it looped between two rooms. On a single path a target that is already on the path is not a legal exit; with that in place the walk reaches the exit room and stops. They also had not implemented the guard rule, so it was trying doors it could not legally open.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1034 — seed appears to do nothing on amber-transit

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 2834 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1035 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1036 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1037 — titles render as nonsense for capsule tin-observatory

They were decoding `title_glyph` with the wrong glyph set — set 7 is what the current cartridge uses, but they had hard-coded an older set. Reminder for everyone: decode every `_glyph` column with the set the *header* names in `g`, not whatever you used last.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1038 — seed appears to do nothing on verdant-hollow

Expected — half their rooms have a single exit, and `seed_value mod 1` is 0, so the start index never moves there. The seed only changes the outcome at rooms with two or more legal exits. Gave them seed 7448 and a two-exit room to see the rotation actually bite.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1039 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1040 — loader rejects every capsule with 'header check mismatch'

The reporter was parsing the glyph number fields straight as integers. Walked them through decoding `e`, `n`, `s` from glyphs first, then `(e + n + s) mod 9973`, comparing to the decoded `k`. Their `g` was already plain, which is the one field you do not decode. Closed once they chunked the values two characters at a time before parsing.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1041 — guarded door on salt-myre looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1042 — guarded door on tin-observatory looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1043 — guarded door on salt-myre looks like a content bug

Not a bug. The door has a `guard_glyph`; it stays shut until the player holds the matching token, and the token comes from a `grant` clause in an upstream room body. Their route simply skipped the granting room. Pointed them at splitting each decoded body on periods to find the grant.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1044 — odd-length glyph value crashes the decoder

A glyph value must be an even number of characters because every symbol is exactly two characters. An odd length means the payload was truncated upstream; the loader is right to refuse it. Told them to treat odd length as a hard error, not to pad it.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

### Ticket #1045 — titles render as nonsense for capsule tin-observatory

They were decoding `title_glyph` with the wrong glyph set — set 7 is what the current cartridge uses, but they had hard-coded an older set. Reminder for everyone: decode every `_glyph` column with the set the *header* names in `g`, not whatever you used last.

Resolution: explained the format, no code change to the loader. Folding the explanation back into the field notes so the next ticket like it can be closed faster.

