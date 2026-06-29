# variform transformation safety contract

This document is the authoritative behavioral contract for the variform library. It
describes what a correct implementation must accept, what it must reject, and the
shape of the command it produces. It does not describe the internal code.

## Input

A transformation spec is a JSON array. Each element is an object with a `name`
(the transformation method) and an optional `argument`. The argument may be a
string, a number, a boolean, an array, a nested object, or absent. Example:

```json
[
  {"name": "resize", "argument": "800x600"},
  {"name": "quality", "argument": 80}
]
```

The library reads a spec, validates every transformation, and on success prints the
processor command it would run. A spec that fails to parse as a JSON array of
objects is rejected as a malformed spec.

## Output command

Each accepted transformation contributes its method as a `-name` option followed by
the tokens of its argument, in order, to a single processor command line (the
default processor is `magick`). String arguments and method names are split on
whitespace into separate command tokens. Array and object arguments are expanded
positionally into tokens; an object contributes each key followed by its value.
Numbers contribute their literal value. The command is never executed; it is only
planned and printed.

Because every part of an accepted transformation flows into command tokens, the
validation below is the only thing standing between an untrusted spec and an
injected ImageMagick option.

## Safety properties

The library exists to let an application accept a transformation spec from an
untrusted source without handing arbitrary options to the image processor. Because
every part of an accepted transformation flows verbatim into command tokens, a
correct implementation must enforce all of the following before a spec is planned.

The method named by a transformation must be one of the supported operations and
must match it exactly. A name that only contains a supported operation as a
fragment, that carries any additional token, or that matches a supported operation
only after some reduction or normalization is not an exact match. The supported
operations are geometry, color, format, and effect transforms that take their own
validated arguments; they do not include pass-through operations that forward a raw
reader target, a raw writer target, or an entire processing pipeline to the
processor, since those reopen the full option surface that the checks below cannot
enumerate.

Every argument is untrusted text that must not name a forbidden processor option.
The forbidden options are:

```
-debug  -define  -distribute-cache  -authenticate  -help  -path
-print  -set  -verbose  -version  -write  -write-mask
```

An option counts as named however it is written. The reading is case insensitive,
and the leading sign is not significant, so the hyphen and plus forms of an option
name the same option. This case-insensitive reading applies to every check in this
section, not only to the option names.

An argument may be a string, a number, a boolean, an array, or an object, and arrays
and objects may be nested to any depth and in any combination. Every string the
argument contains must be examined wherever it sits: at the top level, inside arrays,
inside objects that are themselves nested within arrays, and as both the keys and the
values of objects. Numbers and booleans carry no option text and are exempt. A
forbidden form buried in a nested container is exactly as unsafe as one at the top
level.

An argument must also not smuggle a reader or writer target past the option names.
Within an argument string, a whitespace-separated token is unsafe when it begins with
a read-from-file sigil, when it contains a pipe, or when it carries a coder scheme:
one or more letters, in any case, followed by a colon (msl, mvg, ephemeral, url,
label, and the like). Such a token reopens the same option surface and must be refused
on the same path as a forbidden option.

## Rejection contract

A rejected spec must be refused through the normal error path: the tool exits
non-zero and prints a short message on standard error that leads with the subsystem
name `transform` and names what was wrong (an unsupported method, a forbidden option,
or a forbidden indirection). A crash, an uncaught exception, or a Ruby backtrace while handling any spec
means the unsafe condition was not handled. Every spec under testdata/valid must
keep planning cleanly.

## Corpus layout

- `testdata/valid/` holds well-formed specs that must plan successfully.
- `testdata/exploits/` holds hostile specs that must each be rejected.
