use std::collections::{HashMap, HashSet, VecDeque};

pub fn reachable(shores: &[String], edges: &[(String, String)]) -> HashSet<String> {
    let mut adj: HashMap<String, Vec<String>> = HashMap::new();
    for (a, b) in edges {
        adj.entry(a.clone()).or_default().push(b.clone());
        adj.entry(b.clone()).or_default().push(a.clone());
    }
    let mut seen = HashSet::new();
    let mut q = VecDeque::new();
    for s in shores {
        seen.insert(s.clone());
        q.push_back(s.clone());
    }
    while let Some(node) = q.pop_front() {
        if let Some(nexts) = adj.get(&node) {
            for nxt in nexts {
                if seen.insert(nxt.clone()) {
                    q.push_back(nxt.clone());
                }
            }
        }
    }
    seen
}
