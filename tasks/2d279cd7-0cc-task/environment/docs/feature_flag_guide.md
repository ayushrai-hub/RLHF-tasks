# Feature Flag Parsing Guide

Feature flags are boolean variables that alter the active dependency edges.
We support operators:
- `&` (logical AND)
- `|` (logical OR)
- `!` (logical NOT)
- parentheses `(`, `)`
- empty strings (always true)
- whitespace is ignored.
