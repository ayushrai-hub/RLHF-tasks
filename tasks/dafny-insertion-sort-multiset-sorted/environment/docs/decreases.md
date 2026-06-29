# Termination in Dafny

Dafny requires every loop to have a termination argument unless you explicitly
annotate it with `decreases *` (which asserts non-termination is acceptable, typically
only on `Main` or test harnesses). For loops in methods with postconditions, Dafny
insists on provable termination.

A `decreases` clause specifies a measure that must strictly decrease on each loop
iteration and must have a lower bound. Dafny checks that the measure is a valid
termination witness: it is at least 0 (for integer measures), and the loop body
reduces it by at least 1.

Each loop in the method needs its own `decreases` clause. The right measure for a
loop is whatever quantity is strictly shrinking as the loop makes progress toward
termination; the measure should reflect what is making progress, not just the loop
counter.

Without `decreases` clauses, Dafny may still accept a loop if it can infer the
termination measure automatically. However, for loops with complex invariants, Dafny
often needs the hint. Providing explicit `decreases` clauses also makes the proof
more readable and prevents Dafny from spending resources on termination inference.
