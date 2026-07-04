use timeseries_downsampler::models::Event;
use timeseries_downsampler::parser::parse_event;
use timeseries_downsampler::tumbling::TumblingWindowAggregator;

#[test]
fn parse_valid_event() {
    let event = parse_event("1700000000000|evt1|cpu|45.5|parent_evt").unwrap();
    assert_eq!(event.timestamp_ms, 1700000000000);
    assert_eq!(event.event_id, "evt1");
    assert_eq!(event.name, "cpu");
    assert_eq!(event.value, 45.5);
    assert_eq!(event.dependency_ids, vec!["parent_evt".to_string()]);
    
    // Without dependency
    let event2 = parse_event("1700000000000|evt1|cpu|45.5|").unwrap();
    assert!(event2.dependency_ids.is_empty());

    // Multiple dependencies
    let event3 = parse_event("1700000000000|evt1|cpu|45.5|dep1,dep2").unwrap();
    assert_eq!(event3.dependency_ids, vec!["dep1".to_string(), "dep2".to_string()]);
}

#[test]
fn parse_b64_event() {
    // 45.5 in IEEE 754 f64 little endian is: 00 00 00 00 00 C0 46 40
    // b64 encoded: AAAAAADARkA=
    let event = parse_event("1700000000000|evt1|cpu|b64:AAAAAADARkA=|").unwrap();
    assert_eq!(event.value, 45.5);
}

#[test]
fn parse_valid_event_with_quotes() {
    let event = parse_event("1700000000000|evt1|\"cpu|usage\"|45.5|").unwrap();
    assert_eq!(event.timestamp_ms, 1700000000000);
    assert_eq!(event.event_id, "evt1");
    assert_eq!(event.name, "cpu|usage");
    assert_eq!(event.value, 45.5);
    assert!(event.dependency_ids.is_empty());
}

#[test]
fn parse_invalid_events_returns_none() {
    assert!(parse_event("").is_none());
    assert!(parse_event("1700|evt1|cpu").is_none());
    assert!(parse_event("invalid|evt1|cpu|45.5").is_none());
}

#[test]
fn tumbling_window_calculates_correct_bounds() {
    let mut agg = TumblingWindowAggregator::new(60000); // 1 minute
    let event = parse_event("60500|e1|mem|10.0").unwrap();
    agg.add_event(&event);
    
    let results = agg.flush_window(60000);
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].window_start_ms, 60000);
    assert_eq!(results[0].window_end_ms, 120000);
}

#[test]
fn tumbling_window_aggregates_stats() {
    let mut agg = TumblingWindowAggregator::new(60000);
    agg.add_event(&parse_event("60100|e1|cpu|10.0").unwrap());
    agg.add_event(&parse_event("60200|e2|mem|50.0").unwrap());
    agg.add_event(&parse_event("60300|e3|cpu|30.0").unwrap());
    agg.add_event(&parse_event("60400|e4|cpu|20.0").unwrap());
    
    for i in 1..=20 {
        let line = format!("60500|e{}|disk|{}.0", i, i);
        agg.add_event(&parse_event(&line).unwrap());
    }
    
    let results = agg.flush_window(60000);
    assert_eq!(results.len(), 3);
    
    let cpu = results.iter().find(|r| r.name == "cpu").unwrap();
    assert_eq!(cpu.count, 3);
    assert_eq!(cpu.min, 10.0);
    assert_eq!(cpu.max, 30.0);
    assert_eq!(cpu.avg, 20.0);
    // Median for [10.0, 20.0, 30.0] -> N=3 (odd), middle is 20.0
    assert_eq!(cpu.median, 20.0);
    
    let mem = results.iter().find(|r| r.name == "mem").unwrap();
    assert_eq!(mem.count, 1);
    assert_eq!(mem.avg, 50.0);
    assert_eq!(mem.median, 50.0);

    let disk = results.iter().find(|r| r.name == "disk").unwrap();
    // disk values: 1.0 to 20.0 (N=20) (even)
    // Median is (10.0 + 11.0) / 2 = 10.5
    assert_eq!(disk.median, 10.5);
}

#[test]
fn flush_window_removes_data() {
    let mut agg = TumblingWindowAggregator::new(60000);
    agg.add_event(&parse_event("60100|e1|cpu|10.0").unwrap());
    
    let results_first = agg.flush_window(60000);
    assert_eq!(results_first.len(), 1);
    
    let results_second = agg.flush_window(60000);
    assert_eq!(results_second.len(), 0);
}
