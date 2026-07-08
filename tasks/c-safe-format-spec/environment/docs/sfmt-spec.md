# SFmt formatting contract

SFmt is the type-checked formatting core of this library. It renders a format
string against an explicit, typed argument array and returns bytes. It never
takes a C `va_list`: every argument carries its own type tag, and the renderer
checks that tag against the conversion that consumes it. Output is deterministic
and locale independent: the same inputs produce the same bytes on every platform.

`sf_format` is the single entry point:

```c
int sf_format(const char *fmt, const sf_arg *args, size_t nargs,
              char *out, size_t outcap);
```

It writes the rendered bytes into `out` (capacity `outcap`) and returns the
number of bytes written, a non-negative count, on success. On any violation of
this contract it writes nothing and returns a negative `SF_ERR_*` code. If the
rendered output would exceed `outcap` it returns `SF_ERR_NOMEM`.

The argument array element is a tagged value:

```c
typedef enum {
    SF_ARG_I64,     /* signed integer   */
    SF_ARG_U64,     /* unsigned integer */
    SF_ARG_STR,     /* byte string: str, slen */
    SF_ARG_BYTE,    /* one byte, 0..255 */
    SF_ARG_SCALAR   /* Unicode scalar, 0..0x10FFFF */
} sf_argtype;

typedef struct {
    sf_argtype  type;
    int64_t     i64;
    uint64_t    u64;   /* also holds BYTE and SCALAR values */
    const char *str;
    size_t      slen;
} sf_arg;
```

## Format grammar

A format string is a byte sequence. Every byte is copied to the output verbatim
except a conversion, which begins with `%`. The grammar of a conversion is:

```
%[ index $ ][ flags ][ width ][ . precision ] conv
```

- **index`$`**: an optional 1-based argument selector. It is one or more decimal
  digits immediately after `%`, followed by `$`. See "Argument binding".
- **flags**: any run of the bytes `-` `+` (space) `#` `0` `'`, in any order. A
  repeated flag is the same as one.
- **width**: an optional minimum field width in bytes, written either as a
  decimal integer or as `*`. A `*` takes the width from the next argument (see
  "Dynamic width and precision").
- **`.`precision**: an optional `.` followed by either a decimal integer or `*`.
  A bare `.` means precision zero; a `.*` takes the precision from an argument.
  Precision meaning depends on the conversion.
- **conv**: exactly one of `d i u x X o b c C s n %`.

There are no length modifiers (`l`, `h`, `z`); arguments are already sized.

`%%` renders a single `%`. It takes no argument and admits no index, flag, width,
or precision; any of those before the second `%` is `SF_ERR_BAD_SPEC`.

An incomplete conversion (a `%` at end of string, a `$` with no digits, an
unknown `conv` byte, a `*`, a length modifier, or a width/precision that
overflows) is `SF_ERR_BAD_SPEC`.

## Argument binding

A format uses either **sequential** or **positional** binding, never both:

- Sequential: no conversion carries an `index$`. Each argument-consuming
  conversion takes the next argument, left to right, starting at the first.
- Positional: every argument-consuming conversion carries an `index$`. An index
  may repeat (an argument may be rendered more than once).

Mixing the two, one conversion with `index$` and another without, is
`SF_ERR_MIX`, reported at the second, conflicting conversion.

`%%` and `%n` consume no argument and take part in neither count.

Argument accounting, checked when the format is otherwise valid:

- Sequential: the number of argument-consuming conversions must equal `nargs`
  exactly. Fewer conversions than arguments, or a conversion that runs past the
  last argument, is `SF_ERR_ARG_COUNT`.
- Positional: every index must lie in `1..nargs`, and every argument in
  `1..nargs` must be referenced at least once. An out-of-range index or an
  unreferenced argument is `SF_ERR_ARG_COUNT`.

## Type checking

Each conversion requires a specific argument type. A mismatch is
`SF_ERR_ARG_TYPE`.

| conv        | required type   |
|-------------|-----------------|
| `d` `i`     | `SF_ARG_I64`    |
| `u` `x` `X` `o` `b` | `SF_ARG_U64` |
| `c`         | `SF_ARG_BYTE`   |
| `C`         | `SF_ARG_SCALAR` |
| `s`         | `SF_ARG_STR`    |

A `*` width argument and a `.*` precision argument each require `SF_ARG_I64`.

## Dynamic width and precision

A `*` in the width position, or `.*` in the precision position, takes that value
from an argument rather than the format text. These are only valid in sequential
binding: a conversion that carries an `index$` together with `*` or `.*` is
`SF_ERR_BAD_SPEC`.

When both are present the arguments are consumed in this order, before the value
argument: the width argument, then the precision argument, then the value. Each
`*`/`.*` argument must be `SF_ARG_I64`.

- A negative `*` width left-justifies in a field of the absolute width (as if the
  `-` flag were set).
- A negative `.*` precision means no precision at all.
- A width or precision magnitude above 4096 is `SF_ERR_BAD_SPEC`.

## Conversions

Errors are reported at the first offending conversion, scanning left to right,
before any output is produced.

### Signed integers: `d`, `i` (type I64)

Base ten. A leading `-` is emitted for a negative value. For a non-negative
value, the `+` flag emits a leading `+`, or failing that the space flag emits a
leading space; `+` outranks space. Digits are produced from the magnitude.

### Unsigned integers: `u` (base 10), `x`/`X` (base 16), `o` (base 8), `b` (base 2)

No sign is ever emitted; `+` and space are ignored. `x` uses lower-case
`0-9a-f`, `X` upper-case `0-9A-F`. The `#` flag prepends an alternate-form prefix
**only when the value is non-zero**: `0x` for `x`, `0X` for `X`, `0o` for `o`,
`0b` for `b`. A zero value takes no prefix, so `%#x`, `%#X`, `%#o`, and `%#b` of
`0` all render as a bare `0`. There is no alternate prefix for `u`.

### Precision on integers (all of `d i u x X o b`)

Precision is the minimum number of digits; the magnitude is left-padded with `0`
to reach it. Precision zero applied to the value zero produces no digits at all
(the empty string), before any prefix or sign. When a precision is present the
`0` flag is ignored.

### Grouping on decimals (`d i u`), flag `'`

When the `'` flag is present on a base-ten conversion, an `_` is inserted between
every group of three digits counted from the right, over the digit string after
precision padding. Grouping never applies to `x X o b`.

When `'` combines with the `0` flag and a width (and no precision and no `-`),
the field is zero-filled with grouping: leading zeros are added and the whole
digit run is grouped, so the separators fall on every third digit counted from
the right across the padded field. Fill the field of width `W - len(sign)` this
way. If landing on the exact width would place a separator at the leftmost
position, put a `0` there instead (a field never begins with `_`). If the grouped
magnitude is already at least `W - len(sign)` bytes wide, no zeros are added and
it is emitted unchanged (the general width rule then applies). A magnitude of
fewer than four digits is never given a separator. Grouping applies to `u` just
as it does to `d` and `i`. Worked: `%'015d` of 1234 is `000_000_001_234`;
`%'08d` of 1234 is `0001_234`; `%'010d` of 1234 is `00_001_234`.

### Byte: `c` (type BYTE)

Renders the single byte held by the argument (0..255). Precision is ignored.

### Unicode scalar: `C` (type SCALAR)

Renders the argument as its UTF-8 encoding (1 to 4 bytes). A value above
`0x10FFFF`, or a surrogate in `0xD800..0xDFFF`, is `SF_ERR_BAD_SCALAR`. Precision
is ignored.

### String: `s` (type STR)

Without a precision, the argument bytes are copied verbatim. With a precision,
the output is the first *precision* Unicode code points of the argument, cut on a
code-point boundary; if the string has fewer code points, all of it is used.
A string that is not valid UTF-8 is `SF_ERR_BAD_UTF8` **only when a precision is
present** (verbatim copy does not inspect the bytes). Note the asymmetry:
precision counts code points, width counts bytes.

### `n`

`%n` is never rendered. Encountering it is `SF_ERR_PERCENT_N`.

## Width and justification

Width is the minimum field width in **bytes**, applied after the conversion has
produced its token (sign/prefix/digits, or the string/byte/scalar bytes). If the
token is at least `width` bytes, it is emitted unchanged. Otherwise:

- with the `-` flag, the token is emitted followed by spaces to `width`;
- else with the `0` flag, and only for numeric conversions, and only when no
  precision and no `'` grouping apply, `0` bytes are inserted between the
  sign/prefix and the digits to reach `width`;
- else spaces are emitted before the token (right justification).

For `s`, `c`, `C` the `0` flag is ignored (padding is always spaces).

## Error tokens

Each `SF_ERR_*` code has a stable name. Callers that surface errors as text use
the exact spelling below:

| code                    | token                    |
|-------------------------|--------------------------|
| `SF_ERR_NOT_IMPLEMENTED`| `@ERR:NOT_IMPLEMENTED`   |
| `SF_ERR_BAD_SPEC`       | `@ERR:BAD_SPEC`          |
| `SF_ERR_MIX`            | `@ERR:MIX`               |
| `SF_ERR_ARG_COUNT`      | `@ERR:ARG_COUNT`         |
| `SF_ERR_ARG_TYPE`       | `@ERR:ARG_TYPE`          |
| `SF_ERR_PERCENT_N`      | `@ERR:PERCENT_N`         |
| `SF_ERR_BAD_UTF8`       | `@ERR:BAD_UTF8`          |
| `SF_ERR_BAD_SCALAR`     | `@ERR:BAD_SCALAR`        |
| `SF_ERR_NOMEM`          | `@ERR:NOMEM`             |

## Worked examples

| format        | args              | output      |
|---------------|-------------------|-------------|
| `[%d]`        | i64 -42           | `[-42]`     |
| `[%+d]`       | i64 42            | `[+42]`     |
| `[% d]`       | i64 42            | `[ 42]`     |
| `[%05d]`      | i64 -42           | `[-0042]`   |
| `[%5.3d]`     | i64 7             | `[  007]`   |
| `[%'d]`       | i64 1234567       | `[1_234_567]` |
| `[%x]`        | u64 255           | `[ff]`      |
| `[%#X]`       | u64 255           | `[0XFF]`    |
| `[%#o]`       | u64 8             | `[0o10]`    |
| `[%#b]`       | u64 5             | `[0b101]`   |
| `[%o]`        | u64 0             | `[0]`       |
| `[%#x]`       | u64 0             | `[0]`       |
| `[%#o]`       | u64 0             | `[0]`       |
| `[%#b]`       | u64 0             | `[0]`       |
| `[%.0d]`      | i64 0             | `[]`        |
| `[%-6s]`      | str `hi`          | `[hi    ]`  |
| `[%.3s]`      | str `héllo`       | `[hél]`     |
| `[%c]`        | byte 65           | `[A]`       |
| `[%C]`        | scalar 0x1F600    | `[😀]`      |
| `[%2$d %1$d]` | i64 1, i64 2      | `[2 1]`     |
| `[%'015d]`    | i64 1234          | `[000_000_001_234]` |
| `[%'08d]`     | i64 1234          | `[0001_234]` |
| `[%*d]`       | i64 8, i64 42     | `[      42]` |
| `[%*d]`       | i64 -8, i64 42    | `[42      ]` |
| `[%.*d]`      | i64 4, i64 42     | `[0042]`    |
| `[%*.*x]`     | i64 -10, i64 6, u64 255 | `[0000ff    ]` |
| `%%`          | (none)            | `%`         |
