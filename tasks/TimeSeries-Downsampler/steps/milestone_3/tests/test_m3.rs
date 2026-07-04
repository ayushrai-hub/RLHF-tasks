use timeseries_downsampler::causal::CausalBuffer;
use timeseries_downsampler::models::Event;

#[test]
fn events_without_dependencies_process_immediately() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 100, event_id: "e1".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: Vec::new() });
    assert_eq!(buf.aggregated_events.len(), 1);
    assert!(buf.processed_ids.contains("e1"));
}

#[test]
fn orphaned_event_is_buffered() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 200, event_id: "e2".to_string(), name: "cpu".to_string(), value: 20.0, dependency_ids: vec!["e1".to_string()] });
    assert_eq!(buf.aggregated_events.len(), 0);
    assert!(!buf.processed_ids.contains("e2"));
    assert_eq!(buf.orphans.get("e1").unwrap().len(), 1);
}

#[test]
fn recursive_unblocking_cascades_correctly() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 300, event_id: "e3".to_string(), name: "cpu".to_string(), value: 30.0, dependency_ids: vec!["e2".to_string()] });
    buf.process_event(Event { timestamp_ms: 200, event_id: "e2".to_string(), name: "cpu".to_string(), value: 20.0, dependency_ids: vec!["e1".to_string()] });
    assert_eq!(buf.aggregated_events.len(), 0);
    buf.process_event(Event { timestamp_ms: 100, event_id: "e1".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: Vec::new() });
    assert_eq!(buf.aggregated_events.len(), 3);
}

#[test]
fn cycle_is_detected_and_deadlettered() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 100, event_id: "A".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: vec!["B".to_string()] });
    buf.process_event(Event { timestamp_ms: 200, event_id: "B".to_string(), name: "cpu".to_string(), value: 20.0, dependency_ids: vec!["C".to_string()] });
    buf.process_event(Event { timestamp_ms: 300, event_id: "C".to_string(), name: "cpu".to_string(), value: 30.0, dependency_ids: vec!["A".to_string()] });
    assert!(buf.deadletter_ids.contains("C"));
}

#[test]
fn deadletter_cascades_to_dependents() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 100, event_id: "A".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: vec!["B".to_string()] });
    buf.process_event(Event { timestamp_ms: 200, event_id: "B".to_string(), name: "cpu".to_string(), value: 20.0, dependency_ids: vec!["C".to_string()] });
    buf.process_event(Event { timestamp_ms: 300, event_id: "C".to_string(), name: "cpu".to_string(), value: 30.0, dependency_ids: vec!["A".to_string()] });
    buf.process_event(Event { timestamp_ms: 400, event_id: "D".to_string(), name: "cpu".to_string(), value: 40.0, dependency_ids: vec!["C".to_string()] });
    assert!(buf.deadletter_ids.contains("D"));
}

#[test]
fn multi_parent_event_unblocks_only_when_all_met() {
    let mut buf = CausalBuffer::new();
    // C depends on A and B
    buf.process_event(Event { timestamp_ms: 300, event_id: "C".to_string(), name: "cpu".to_string(), value: 30.0, dependency_ids: vec!["A".to_string(), "B".to_string()] });
    assert_eq!(buf.aggregated_events.len(), 0);
    
    // A arrives, C is still blocked on B
    buf.process_event(Event { timestamp_ms: 100, event_id: "A".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: Vec::new() });
    assert_eq!(buf.aggregated_events.len(), 1); // Only A
    assert!(!buf.processed_ids.contains("C"));
    
    // B arrives, C is unblocked!
    buf.process_event(Event { timestamp_ms: 200, event_id: "B".to_string(), name: "cpu".to_string(), value: 20.0, dependency_ids: Vec::new() });
    assert_eq!(buf.aggregated_events.len(), 3); // A, B, and C
    assert!(buf.processed_ids.contains("C"));
}

#[test]
fn multiple_orphans_unblocked_by_one_event() {
    let mut buf = CausalBuffer::new();
    buf.process_event(Event { timestamp_ms: 200, event_id: "e2".to_string(), name: "cpu".to_string(), value: 20.0, dependency_ids: vec!["e1".to_string()] });
    buf.process_event(Event { timestamp_ms: 300, event_id: "e3".to_string(), name: "cpu".to_string(), value: 30.0, dependency_ids: vec!["e1".to_string()] });
    assert_eq!(buf.aggregated_events.len(), 0);
    buf.process_event(Event { timestamp_ms: 100, event_id: "e1".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: Vec::new() });
    assert_eq!(buf.aggregated_events.len(), 3);
    assert!(buf.processed_ids.contains("e2"));
    assert!(buf.processed_ids.contains("e3"));
}
