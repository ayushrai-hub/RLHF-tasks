# Emphasis and strong emphasis

This is the subtle part. A naive "match the nearest `*` with the next `*`"
approach is **wrong**; the CommonMark rules below must be followed exactly.

A **delimiter run** is a maximal sequence of the same character, `*` or `_`,
that is not backslash-escaped. Each run is classified, using the characters
immediately before and after the run (treat the start or end of the input as a
space), as left-flanking and/or right-flanking, and from those as able to open
and/or close emphasis.

## Flanking

Let the character before the run be `b` and after the run be `a` (start/end of
input count as whitespace). Using the ASCII punctuation set from `docs/INLINE.md`
and whitespace (space, tab, line feed, carriage return, form feed, vertical tab):

- The run is **left-flanking** if `a` is not whitespace, and either `a` is not
  punctuation, or `b` is whitespace or punctuation.
- The run is **right-flanking** if `b` is not whitespace, and either `b` is not
  punctuation, or `a` is whitespace or punctuation.

## Can open / can close

- A `*` run **can open** emphasis if it is left-flanking; it **can close** if it
  is right-flanking.
- A `_` run **can open** if it is left-flanking and either not right-flanking or
  preceded by punctuation; it **can close** if it is right-flanking and either
  not left-flanking or followed by punctuation.

(The `_` rules are what stop intraword underscores like `foo_bar_baz` from
emphasising.)

## Pairing procedure

Process the delimiter runs left to right, looking for a **closer** (a run that
can close). For each closer, look back through the earlier runs for the nearest
**opener** that:

- is the same character and can open,
- and satisfies the **rule of 3**: if either the opener or the closer can both
  open and close, then the sum of the two runs' **original** lengths must not be
  a multiple of 3, unless both original lengths are multiples of 3.

Do not search past a recorded "bottom" for that character and that closer's
`original length mod 3` (set when a closer of that class fails to find an
opener); this stops repeated futile searches.

When an opener is found:

- Use **two** delimiters from each side if both runs currently have two or more
  delimiters left, otherwise **one**. Two delimiters produce `<strong>…</strong>`;
  one produces `<em>…</em>`. The matched content is everything between the opener
  and closer runs.
- Remove the used delimiters from each run. Any delimiter runs strictly between
  the opener and closer that were not used are no longer available for pairing
  and remain as literal text. A run whose delimiters are all used up is removed
  entirely; leftover delimiters of a partially-used run remain as literal text
  adjacent to the emphasis.
- If the closer still has delimiters left, keep trying to pair it; otherwise move
  on to the next closer.

When no opener is found, record the bottom for this character/length-class. If
the closer cannot also open, it is removed (its delimiters become literal text);
otherwise it stays and may serve as an opener for a later closer.

After processing, any delimiters never paired render as their literal characters.

## Worked examples

```
*foo*            -> <em>foo</em>
**foo**          -> <strong>foo</strong>
***foo***        -> <em><strong>foo</strong></em>
**foo*bar***     -> <strong>foo<em>bar</em></strong>
*foo**bar**baz*  -> <em>foo<strong>bar</strong>baz</em>
foo_bar_baz      -> foo_bar_baz
foo*bar*baz      -> foo<em>bar</em>baz
*(*foo*)*        -> <em>(<em>foo</em>)</em>
**a *b* c**      -> <strong>a <em>b</em> c</strong>
```
