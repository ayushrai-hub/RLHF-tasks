# Worked examples

Inputs are shown as the literal `text`; outputs are the rendered inline HTML.

## Code spans

```
a `code` b            -> a <code>code</code> b
`` `backtick` ``      -> <code>`backtick`</code>
`  padded  `          -> <code> padded </code>
a ``b`c`` d           -> a <code>b`c</code> d
`unclosed             -> `unclosed
```

(The middle code span keeps the inner backtick because the closing run must be the
same length as the opener. `` `  padded  ` `` strips exactly one space from each
end, leaving ` padded ` with one space on each side.)

## Backslash escapes and character references

```
a \* literal \_ b                 -> a * literal _ b
&amp; &lt; &gt; &#65; &#x21;       -> &amp; &lt; &gt; A !
x &notreal; y                     -> x &amp;notreal; y
```

(`\*` is a literal asterisk, so it is not an emphasis delimiter. `&notreal;` is
not a recognised reference, so its `&` is literal and escapes to `&amp;`.)

## Emphasis

```
*foo*            -> <em>foo</em>
**foo**          -> <strong>foo</strong>
***foo***        -> <em><strong>foo</strong></em>
**foo*bar***     -> <strong>foo<em>bar</em></strong>
*foo**bar**baz*  -> <em>foo<strong>bar</strong>baz</em>
foo_bar_baz      -> foo_bar_baz
*(*foo*)*        -> <em>(<em>foo</em>)</em>
```

## Line breaks

```
one
soft             -> one{newline}soft
hard  {2 spaces}
break            -> hard<br />{newline}break
```
