# Links and images

Links and images are resolved together with emphasis, on the same delimiter
stack, during the left-to-right scan. Only **inline** links and images are in
scope (a destination, and optional title, in parentheses right after the
bracket). Reference links are out of scope.

## Brackets on the stack

A `[` opens a potential link; a `![` opens a potential image. Each is recorded
on the delimiter stack (the same stack the emphasis runs use) as an *active*
bracket, and emitted as the literal text `[` or `![` if it never becomes a link.

## Closing a bracket

When a `]` is reached, find the most recent bracket on the stack:

- If there is none, the `]` is literal text.
- If the bracket is **inactive**, drop it from the stack and emit `]` literally.
- Otherwise, try to parse an inline link/image that immediately follows the `]`
  (see below). If it parses, the bracket becomes a link or image; if not, drop
  the bracket from the stack and emit `]` literally.

When a link or image is formed:

1. The text between the bracket and the `]` becomes the link/image content.
2. The emphasis-pairing procedure (`docs/EMPHASIS.md`) is run over just that
   content (the delimiters recorded since the bracket).
3. If a **link** (not an image) was formed, every still-open `[` bracket earlier
   on the stack is made **inactive** — this is what forbids links inside links.

## Inline destination and title

Right after the `]`, an inline link/image is `(`, optional spaces, a
destination, optional spaces and a title, optional spaces, `)`:

- The destination is either a bare run of characters up to the next space or
  `)`, or a `<...>` span (whose `<`/`>` are not part of the destination).
- The title, if present, is written in double quotes: `"…"`.

If this does not parse, there is no link.

## Rendering

- A link renders as `<a href="DEST">CONTENT</a>`, with ` title="TITLE"` inserted
  before the `>` when a title is present. The content is the rendered inline
  HTML of the link text.
- An image renders as `<img src="DEST" alt="ALT" />`, with ` title="TITLE"`
  before the ` />` when a title is present. The **alt** text is the plain text of
  the content — the concatenation of its text and code-span characters, with all
  emphasis and link markup removed (so `![a *b*](/i)` has `alt="a b"`).

Destinations, titles and alt text are escaped for an HTML attribute: `&`, `"`,
`<` and `>` become `&amp;`, `&quot;`, `&lt;` and `&gt;`. (The grading inputs use
simple ASCII destinations that need no further URL normalisation.)

## Worked examples

```
[a](/u)                       -> <a href="/u">a</a>
[a](/u "t")                   -> <a href="/u" title="t">a</a>
[*em* text](/u)               -> <a href="/u"><em>em</em> text</a>
![a *b*](/i)                  -> <img src="/i" alt="a b" />
[outer [inner](/i) text](/o)  -> [outer <a href="/i">inner</a> text](/o)
[a *b](/u)* c                 -> <a href="/u">a *b</a>* c
[not a link]                  -> [not a link]
```
