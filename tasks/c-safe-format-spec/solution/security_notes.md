# Security Notes, c-safe-format-spec

Inspired by the uncontrolled format string class (CWE-134). The codebase under
/app/environment/ is an original safe-formatting library; it is not a copy of any
upstream project.

- **Uncontrolled format string** (CWE-134), the core of `src/format.c`. A C
  `printf`-family call that forwards an attacker-influenced format string exposes
  a memory read and, through `%n`, an arbitrary write primitive. SFmt removes that
  surface by taking a typed argument array instead of a `va_list` and by checking
  every conversion against the type of the argument it consumes, so a format and
  its arguments can never disagree at runtime.

- **The `%n` write primitive** is refused outright: encountering `%n` returns
  `SF_ERR_PERCENT_N` and produces no output, rather than writing a byte count
  back into caller memory the way the C library does.

- **Type confusion between a conversion and its argument** (CWE-686/CWE-843 in
  spirit) is a returned `SF_ERR_ARG_TYPE`, and an argument-count mismatch is
  `SF_ERR_ARG_COUNT`, so the renderer never walks off the end of the argument
  list. The renderer is also locale independent and rejects malformed UTF-8 and
  out-of-range scalars on the normal error path, never by crashing.
