# Character references and HTML escaping

## Character references

A character reference begins with `&` and ends with `;`:

- **Decimal numeric**: `&#` followed by 1–7 decimal digits then `;`. The digits
  are the Unicode code point.
- **Hexadecimal numeric**: `&#x` or `&#X` followed by 1–6 hex digits then `;`.
- **Named**: `&`, then a name of ASCII letters/digits, then `;`. Only these five
  names are recognised by this renderer (the grading inputs use no others):

  | name | character |
  |------|-----------|
  | `amp`  | `&` |
  | `lt`   | `<` |
  | `gt`   | `>` |
  | `quot` | `"` |
  | `apos` | `'` |

For a numeric reference, the code point `0`, and any value that is not a valid
Unicode scalar value, decode to U+FFFD (the replacement character). A reference
that does not match any form above (bad digits, missing `;`, unknown name) is not
a reference: the `&` is literal text and scanning continues after it.

A decoded character is ordinary text and is HTML-escaped on output like any other
text (so `&amp;` decodes to `&` and is then written back out as `&amp;`, while
`&#65;` decodes to `A` and is written as `A`).

## HTML escaping

When literal text — including a decoded character reference and the content of a
code span — is written to the output, the following characters are replaced:

| char | output |
|------|--------|
| `&` | `&amp;` |
| `<` | `&lt;` |
| `>` | `&gt;` |
| `"` | `&quot;` |

All other characters are written unchanged. (The emphasis delimiters `*` and `_`
are not HTML-special and, when they survive as literal text, are written as-is.)
