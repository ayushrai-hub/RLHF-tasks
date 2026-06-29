# Loop Invariants in Dafny

A loop invariant in Dafny is a boolean expression that holds before the loop starts,
is maintained by every iteration of the loop body, and is available after the loop
exits. Invariants are declared with the `invariant` keyword immediately after the
`while` condition and before the loop body `{`.

```dafny
while condition
  invariant expr1
  invariant expr2
  decreases measure
{
  // body
}
```

You can have multiple `invariant` clauses; all must hold simultaneously. Dafny checks
three things for each invariant: it holds before the loop (established), it holds at
the end of the loop body assuming it held at the start (maintained), and it implies
the postcondition when the loop condition is false (useful).

The `decreases` clause provides a termination argument. It must be an expression that
decreases strictly with each iteration and has a lower bound. For a loop index `k`
counting up to `n`, the measure `n - k` decreases by one each step and is bounded
below by zero.

Ghost lemmas are called like regular method calls. They can appear anywhere in the
method body, including inside loops. When a loop body performs an action that must
be reflected in a loop invariant, the placement of any supporting ghost-lemma
calls relative to that action matters for what state the lemma reasons about.
