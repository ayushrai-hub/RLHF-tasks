# Config format

Each config line has up to seven fields:

`type path mode user group age argument`

Missing trailing fields are treated as `-`. More than seven fields is an error.
Whitespace separates fields. Single-quoted and double-quoted fields are
supported. Quotes are removed from the parsed value, and a backslash escapes the
next character inside or outside quotes. A `#` starts a comment only when it is
outside quotes.

The type field is one of `d`, `f`, `L`, `z`, `r`, `R`, or `x`.

The mode field is either `-` or three or four octal digits. For example, `755`
is stored as `0o755`, and `2755` is stored as `0o2755`.

The user and group fields are either `-` or an opaque non-empty string.

The age field for `r` and `R` is either `-`, `0`, or one or more positive
integer/unit parts with no separator. Supported units are:

- `h`: hours
- `d`: days
- `w`: weeks

The comparison is inclusive: an entry with `mtime_hours_ago == 48` satisfies
`2d`, and an entry with `mtime_hours_ago == 219` satisfies `1w2d3h`. `-` and
`0` mean always eligible.

Glob paths are allowed for `z`, `r`, `R`, and `x`. Supported glob
metacharacters are `*`, `?`, and bracket classes such as `[abc]` and `[a-z]`.
Bracket classes do not support negation. Glob matching is over the whole
normalized path, including slashes.
