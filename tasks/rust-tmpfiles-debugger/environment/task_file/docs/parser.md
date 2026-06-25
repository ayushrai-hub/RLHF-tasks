# Parser Notes

The parser is deliberately small but must handle operator input rather than a
toy line format. Quoted values preserve whitespace and `#` characters, while a
comment starts only outside quotes. A backslash escapes the next character.

Paths are normalized before any rule participates in planning. Invalid paths are
reported as rule errors and skipped, but they do not stop later lines in the same
file from being used.
