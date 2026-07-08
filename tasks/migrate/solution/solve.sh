#!/bin/bash
set -euo pipefail
mkdir -p /app/out
cat > /app/planner.py << 'PYEOF'
"""remake: build planner with normal prerequisites and order-only prerequisites.

Rule line:  target: dep1 &odep2 dep3 ...
  - a plain name is a NORMAL prerequisite
  - a name prefixed with '&' is an ORDER-ONLY prerequisite
  - names never on the left-hand side are source files

Staleness (which targets rebuild) -- ORDER-ONLY prereqs are ignored here:
  - target missing from state                                  -> rebuild
  - target with no normal prerequisites (phony)                -> rebuild
  - a normal prereq missing / stale / with mtime >= target     -> rebuild (equal counts)
  - rebuild cascades through normal prereqs

Order (rebuild order) -- BOTH normal and order-only prereqs constrain order:
  among the rebuild set, a prereq that is itself in the rebuild set must be
  emitted before the target; when several targets are ready at once, emit the
  one defined LATEST in the file first (incremental: re-evaluate after each).
"""


def parse_rules(text):
    rules = []
    for line in text.split("\n"):
        s = line.strip()
        if s == "" or s.startswith("#"):
            continue
        lhs, _, rhs = s.partition(":")
        normal, order = [], []
        for tok in rhs.split():
            if tok.startswith("&"):
                order.append(tok[1:])
            else:
                normal.append(tok)
        rules.append((lhs.strip(), normal, order))
    return rules


def parse_state(text):
    st = {}
    for line in text.split("\n"):
        s = line.strip()
        if s == "" or s.startswith("#"):
            continue
        n, m = s.split()
        st[n] = int(m)
    return st


def _emit(rules, S):
    di = {t: i for i, (t, _n, _o) in enumerate(rules)}
    allprq = {t: (n + o) for t, n, o in rules}          # normal + order-only, for ordering
    prq_in_S = {t: [d for d in allprq[t] if d in S] for t in S}
    indeg = {t: len(prq_in_S[t]) for t in S}
    dependents = {t: [] for t in S}
    for t in S:
        for d in prq_in_S[t]:
            dependents[d].append(t)
    ready = [t for t in S if indeg[t] == 0]
    order = []
    while ready:
        ready.sort(key=lambda x: di[x])
        t = ready.pop()                                  # highest definition index first
        order.append(t)
        for u in dependents[t]:
            indeg[u] -= 1
            if indeg[u] == 0:
                ready.append(u)
    return "\n".join(order) + ("\n" if order else "")


def run1(dep_text, state_text):        # recursive-memo staleness
    rules = parse_rules(dep_text)
    state = parse_state(state_text)
    normal_of = {t: n for t, n, _o in rules}
    is_t = set(normal_of)
    memo = {}

    def stale(t):
        if t not in is_t:
            return False
        if t in memo:
            return memo[t]
        memo[t] = False
        nd = normal_of[t]
        res = False
        if t not in state:
            res = True
        elif not nd:
            res = True
        else:
            tm = state[t]
            for d in nd:
                if d in is_t:
                    if (d not in state) or stale(d) or state.get(d, 1 << 62) >= tm:
                        res = True
                        break
                elif state.get(d, 1 << 62) >= tm:
                    res = True
                    break
        memo[t] = res
        return res

    S = {t for t in is_t if stale(t)}
    return _emit(rules, S)


def run2(dep_text, state_text):        # iterative-fixpoint staleness
    rules = parse_rules(dep_text)
    state = parse_state(state_text)
    normal_of = {t: n for t, n, _o in rules}
    is_t = set(normal_of)
    S = set()
    for t in is_t:
        if t not in state or not normal_of[t]:
            S.add(t)
    changed = True
    while changed:
        changed = False
        for t in is_t:
            if t in S:
                continue
            tm = state.get(t)
            hit = False
            for d in normal_of[t]:
                if d in is_t and (d in S or d not in state):
                    hit = True
                    break
                if tm is not None and state.get(d, 1 << 62) >= tm:
                    hit = True
                    break
            if hit:
                S.add(t)
                changed = True
    return _emit(rules, S)


def main():
    import pathlib
    out = pathlib.Path("/app/out"); out.mkdir(parents=True, exist_ok=True)
    for mk in sorted(pathlib.Path("/app/cases").glob("*.mk")):
        state = mk.with_suffix(".state")
        st = state.read_text() if state.exists() else ""
        (out / f"{mk.stem}.txt").write_text(run1(mk.read_text(), st))


if __name__ == "__main__":
    main()
PYEOF
python3 /app/planner.py
echo "planned $(ls /app/cases/*.mk | wc -l) scenarios"
