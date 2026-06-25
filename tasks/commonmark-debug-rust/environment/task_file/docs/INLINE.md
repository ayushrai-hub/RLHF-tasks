# Inline scanning: escapes, code spans, character references, breaks

Inline content is scanned left to right. Most characters are literal text. The
following constructs are recognised during the scan; emphasis delimiters (`*`,
`_`) are recorded here and paired later (`docs/EMPHASIS.md`). When two constructs
could begin at the same position, the order of precedence is the order a left to
right scan reaches them, with code spans, autolinks and raw HTML binding more
tightly than emphasis — of those, only code spans are in scope, and a code-span
opener found before an emphasis run wins.

## Backslash escapes

A backslash followed by an ASCII punctuation character
(``!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~``) is a literal of that punctuation
character; the punctuation loses any special meaning (e.g. `\*` is a literal
`*`, not an emphasis delimiter). A backslash followed by a line ending is a hard
line break (see below). A backslash before any other character is a literal
backslash followed by that character.

## Code spans

A backtick string is a run of one or more backtick (`` ` ``) characters. A code
span opens with a backtick string and closes with the next backtick string of
**exactly** the same length. The characters between (not including either
backtick string) are the code span's content, with this normalisation:

1. line endings are converted to spaces;
2. then, if the result both begins and ends with a space character and contains
   at least one non-space character, exactly one space is removed from each end.

If no closing backtick string of the right length exists, the opening backtick
string is literal text and scanning continues after it. A code span renders as
`<code>` + the HTML-escaped content + `</code>`.

## Character references

See `docs/TEXT.md`.

## Line breaks

A line ending within the inline content is a line break. Spaces at the end of
the line (before the line ending) are removed, and spaces at the start of the
next line are removed. The break is a **hard** break — rendered as `<br />`
followed by a newline — if the line ending was preceded by **two or more**
spaces, or by a backslash; otherwise it is a **soft** break, rendered as a
single newline.
