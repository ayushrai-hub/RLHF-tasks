# Glyph primer

Background for anyone who has not met a glyph-encoded cartridge before. A *glyph set* is a
plain substitution: each printable character the cartridge needs has been assigned a fixed
two-letter code, and every text payload in the cartridge is written as those codes back to
back. There are no separators because the width is constant — you read a payload by cutting
it into two-character pieces and translating each piece. A set lives in the `glyphs` table,
one row per character, tagged with a `table_id`; the current cartridge ships set 7.

The encoding is deliberately boring: it is not encryption, there is no key beyond the table
itself, and the table is sitting right there in the cartridge. What makes a capsule hard to
read is not the cipher, it is knowing *which* fields are encoded, which one (`g`) is left in
the clear, where the table id comes from, and how the decoded pieces are supposed to be
interpreted once you have them — a number, a title, a choice label, a guard token, or a
`grant` clause hiding inside a body. None of that is written on the cartridge; it is the
thing this whole journal exists to record.

A few practical notes. Decode is total: every two-character code in a well-formed payload
must exist in the named set, and a payload's length is always even. If you hit a code that
is not in the set, or an odd length, stop — the payload is damaged or you are using the
wrong set. Numbers are not special: a number field is decoded to text exactly like a title,
and only parsed as an integer afterwards. And the table is per-capsule by `g`, so never
assume the set carries over from the last capsule you read.

