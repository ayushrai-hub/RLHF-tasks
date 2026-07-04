use timeseries_downsampler::models::Event;
use timeseries_downsampler::sliding::SlidingWindowAggregator;

#[test]
fn single_event_populates_multiple_windows() {
    let mut agg = SlidingWindowAggregator::new(300000, 60000);
    let event = Event { timestamp_ms: 300000, event_id: "e1".to_string(), name: "mem".to_string(), value: 10.0, dependency_ids: Vec::new() };
    agg.add_event(&event);
    
    assert_eq!(agg.flush_window(0).len(), 0);
    
    let w60 = agg.flush_window(60000);
    assert_eq!(w60.len(), 1);
    assert_eq!(w60[0].window_start_ms, 60000);
    assert_eq!(w60[0].window_end_ms, 360000);
    assert_eq!(w60[0].name, "mem");
    assert_eq!(w60[0].avg, 10.0);
    assert_eq!(w60[0].count, 1);

    assert_eq!(agg.flush_window(120000).len(), 1);
    assert_eq!(agg.flush_window(180000).len(), 1);
    assert_eq!(agg.flush_window(240000).len(), 1);
    assert_eq!(agg.flush_window(300000).len(), 1); 
    assert_eq!(agg.flush_window(300000).len(), 0); // verify cleared
    assert_eq!(agg.flush_window(360000).len(), 0); 
}

#[test]
fn sliding_window_boundaries_correct() {
    let mut agg = SlidingWindowAggregator::new(100, 50);
    let event = Event { timestamp_ms: 100, event_id: "e1".to_string(), name: "mem".to_string(), value: 10.0, dependency_ids: Vec::new() };
    agg.add_event(&event);
    
    assert_eq!(agg.flush_window(0).len(), 0);
    assert_eq!(agg.flush_window(50).len(), 1);
    assert_eq!(agg.flush_window(100).len(), 1);
}

#[test]
fn multiple_events_aggregate_across_slides() {
    let mut agg = SlidingWindowAggregator::new(100, 50);
    agg.add_event(&Event { timestamp_ms: 60, event_id: "e1".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: Vec::new() });
    agg.add_event(&Event { timestamp_ms: 90, event_id: "e2".to_string(), name: "cpu".to_string(), value: 20.0, dependency_ids: Vec::new() });
    
    let r0 = agg.flush_window(0);
    assert_eq!(r0[0].count, 2);
    assert_eq!(r0[0].avg, 15.0);
    assert!((r0[0].median - 15.0).abs() < 1e-9); // N=2, Median of 10.0 and 20.0 is 15.0
    assert_eq!(r0[0].min, 10.0);
    assert_eq!(r0[0].max, 20.0);
    
    let r50 = agg.flush_window(50);
    assert_eq!(r50[0].count, 2);
    assert_eq!(r50[0].avg, 15.0);
    
    let r100 = agg.flush_window(100);
    assert_eq!(r100.len(), 0);
}

#[test]
fn duplicate_events_apply_bitwise_xor() {
    let mut agg = SlidingWindowAggregator::new(100, 50);
    agg.add_event(&Event { timestamp_ms: 60, event_id: "e1".to_string(), name: "cpu".to_string(), value: 10.0, dependency_ids: Vec::new() });
    agg.add_event(&Event { timestamp_ms: 70, event_id: "e1".to_string(), name: "cpu".to_string(), value: 15.0, dependency_ids: Vec::new() }); 
    
    // 10.0 in f64 bits XOR 15.0 in f64 bits
    let v1 = 10.0f64.to_bits();
    let v2 = 15.0f64.to_bits();
    let expected_xor = f64::from_bits(v1 ^ v2);
    
    agg.add_event(&Event { timestamp_ms: 90, event_id: "e2".to_string(), name: "cpu".to_string(), value: 15.0, dependency_ids: Vec::new() });
    
    let r0 = agg.flush_window(0);
    assert_eq!(r0[0].count, 2); // e1 and e2
    assert_eq!(r0[0].avg, (expected_xor + 15.0) / 2.0);
}

#[test]
fn median_computation_even() {
    let mut agg = SlidingWindowAggregator::new(100, 50);
    for i in 1..=20 {
        agg.add_event(&Event { timestamp_ms: 60, event_id: format!("e{}",i), name: "cpu".into(), value: i as f64, dependency_ids: Vec::new() });
    }
    let r = agg.flush_window(0);
    // Median of 1..=20 is (10 + 11) / 2 = 10.5
    assert!((r[0].median - 10.5).abs() < 1e-9);
}
