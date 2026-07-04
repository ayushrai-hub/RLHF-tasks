use timeseries_downsampler::causal::CausalBuffer;
use timeseries_downsampler::models::Event;

#[test]
fn evict_lowest_subtree_value() {
    let mut buf = CausalBuffer::new();
    // A depends on X. Value = 10
    buf.process_event(Event { timestamp_ms: 100, event_id: "A".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: vec!["X".to_string()] });
    // B depends on X. Value = 20
    buf.process_event(Event { timestamp_ms: 100, event_id: "B".to_string(), name: "cpu".to_string(), value: 20.0, dependency_ids: vec!["X".to_string()] });
    // C depends on X. Value = 5
    buf.process_event(Event { timestamp_ms: 100, event_id: "C".to_string(), name: "cpu".to_string(), value: 5.0, dependency_ids: vec!["X".to_string()] });
    
    // Subtree values: A=10, B=20, C=5. Capacity = 2. C should be evicted.
    let evicted = buf.evict_over_capacity(2);
    assert_eq!(evicted.len(), 1);
    assert_eq!(evicted[0].event_id, "C");
    assert!(buf.deadletter_ids.contains("C"));
}

#[test]
fn cascading_eviction_and_recalculation() {
    let mut buf = CausalBuffer::new();
    // A depends on X. Value = 10
    buf.process_event(Event { timestamp_ms: 100, event_id: "A".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: vec!["X".to_string()] });
    // B depends on A. Value = 50. Total Subtree(A) = 60
    buf.process_event(Event { timestamp_ms: 100, event_id: "B".to_string(), name: "cpu".to_string(), value: 50.0, dependency_ids: vec!["A".to_string()] });
    
    // C depends on X. Value = 40. Total Subtree(C) = 40
    buf.process_event(Event { timestamp_ms: 100, event_id: "C".to_string(), name: "cpu".to_string(), value: 40.0, dependency_ids: vec!["X".to_string()] });
    // D depends on C. Value = 10. Total Subtree(C) = 50. Total Subtree(D) = 10
    buf.process_event(Event { timestamp_ms: 100, event_id: "D".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: vec!["C".to_string()] });
    
    // If capacity = 2:
    // Pass 1: Lowest is D (10). Evict D. Remaining: A(60), B(50), C(40). Count = 3 > 2.
    // Pass 2: Lowest is C (40). Evict C. Remaining: A(60), B(50). Count = 2. Done.
    
    let mut evicted = buf.evict_over_capacity(2);
    evicted.sort_by(|a, b| a.event_id.cmp(&b.event_id));
    
    assert_eq!(evicted.len(), 2);
    assert_eq!(evicted[0].event_id, "C");
    assert_eq!(evicted[1].event_id, "D");
    assert!(buf.deadletter_ids.contains("C"));
    assert!(buf.deadletter_ids.contains("D"));
}

#[test]
fn tie_breaking_by_event_id() {
    let mut buf = CausalBuffer::new();
    // A depends on X. Value = 10
    buf.process_event(Event { timestamp_ms: 100, event_id: "Z".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: vec!["X".to_string()] });
    // B depends on X. Value = 10
    buf.process_event(Event { timestamp_ms: 100, event_id: "Y".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: vec!["X".to_string()] });
    
    // Tie between Z and Y. Lexicographically, Y < Z. So Y should be evicted if capacity = 1.
    let evicted = buf.evict_over_capacity(1);
    assert_eq!(evicted.len(), 1);
    assert_eq!(evicted[0].event_id, "Y");
}

#[test]
fn cascading_eviction_of_dependent_subtree() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 100, event_id: "A".to_string(), name: "cpu".to_string(), value: 100.0, dependency_ids: vec!["X".to_string()] });
    buf.process_event(Event { timestamp_ms: 100, event_id: "B".to_string(), name: "cpu".to_string(), value: 5.0, dependency_ids: vec!["X".to_string()] });
    buf.process_event(Event { timestamp_ms: 100, event_id: "C".to_string(), name: "cpu".to_string(), value: 1.0, dependency_ids: vec!["B".to_string()] });
    
    let evicted = buf.evict_over_capacity(1);
    assert_eq!(evicted.len(), 2);
    use std::collections::HashSet;
    let ids: HashSet<_> = evicted.iter().map(|e| e.event_id.as_str()).collect();
    assert!(ids.contains("B") && ids.contains("C"));
    assert!(!buf.deadletter_ids.contains("A"));

    // After eviction, verify no empty Vecs remain in orphans map
    for (_, v) in buf.orphans.iter() {
        assert!(!v.is_empty(), "Empty Vec left in orphans map");
    }
}

#[test]
fn transitive_subtree_value_calculation() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 100, event_id: "B".to_string(), name: "cpu".to_string(), value: 2.0, dependency_ids: vec!["A_dep".to_string()] });
    buf.process_event(Event { timestamp_ms: 100, event_id: "C".to_string(), name: "cpu".to_string(), value: 1.0, dependency_ids: vec!["B".to_string()] });
    buf.process_event(Event { timestamp_ms: 100, event_id: "D".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: vec!["A_dep".to_string()] });
    
    let evicted = buf.evict_over_capacity(2);
    assert_eq!(evicted.len(), 1);
    assert_eq!(evicted[0].event_id, "C");
}

#[test]
fn deduplication_in_return_value() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 100, event_id: "E".to_string(), name: "cpu".to_string(), value: 1.0, dependency_ids: vec!["X".to_string(), "Y".to_string()] });
    let evicted = buf.evict_over_capacity(0);
    assert_eq!(evicted.iter().filter(|e| e.event_id == "E").count(), 1);
}
