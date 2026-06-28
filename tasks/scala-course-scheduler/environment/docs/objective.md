# Scheduling Objective

The goal of the optimizer is to produce a schedule that satisfies all hard constraints while maximising a multi-objective soft score. The scoring model at `/opt/scheduler/model.py` combines four components into a single value between 0.0 and 1.0. The passing threshold is 0.80.

## Scoring Components

**Room utilization** measures how well each assigned room's capacity is used relative to the actual enrollment demand for the course placed in it. Assigning a large lecture hall to a tiny seminar wastes seats and lowers this component. The closer the enrollment is to the room's capacity (without exceeding it), the better.

**Faculty satisfaction** rewards placing each instructor in one of their declared preferred time slots. An instructor scheduled outside their preferred slots still contributes, but at a reduced rate. Maximising the fraction of instructors who land in a preferred slot raises this component.

**Conflict avoidance** is now both a hard constraint and a score component. Conflict groups represent cohorts of students who typically enrol in both courses simultaneously. Any same-slot collision inside a conflict group fails verification; schedules that preserve wider separation still receive the best score.

**Load balance** rewards distributing courses evenly across all eight available time slots. If most courses cluster into a few slots and others are nearly empty, this component is penalised. An ideal schedule assigns roughly three to four courses per slot.

## Additional hard optimisation layers

The optimizer must also account for prerequisite ordering, room blackout windows, cohort day-load limits, fixed placements, linked lecture/lab relationships, instructor daily credit caps, and room-zone travel gaps. These layers interact with the soft score: satisfying prerequisites often pushes course chains later in the week, fixed placements consume scarce high-capacity rooms, linked sections constrain local neighborhoods, and travel/load caps reduce feasible instructor sequences. A passing solution usually needs backtracking, local search, or constraint-aware repair rather than a single first-fit pass.
