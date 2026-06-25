# Glossary

**inline content** — the text of a single paragraph, before block structure; what
this renderer turns into HTML.

**delimiter run** — a maximal run of the same unescaped `*` or `_` character.

**left-flanking / right-flanking** — properties of a delimiter run determined by
the characters around it (see `EMPHASIS.md`), used to decide whether it can open
or close emphasis.

**can open / can close** — whether a delimiter run may begin or end an emphasis
span.

**rule of 3** — the constraint that blocks certain opener/closer pairs whose run
lengths sum to a multiple of 3 (see `EMPHASIS.md`).

**code span** — inline code delimited by matching backtick strings, rendered with
`<code>`.

**character reference** — an `&…;` entity, numeric or named, decoding to a
character.

**hard break / soft break** — a line ending rendered as `<br />` + newline, or as
a plain newline.
