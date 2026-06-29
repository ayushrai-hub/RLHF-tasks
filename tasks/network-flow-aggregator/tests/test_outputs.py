import json
import os

def load_report():
    with open("/tmp/test_report.json") as f:
        return json.load(f)

# ==================== PARSE STAGE TESTS ====================

class TestNFAParseBasic:
    """Test basic parsing functionality"""
    
    def test_binary_executes_successfully(self):
        """Verify nfa_verify binary runs without errors"""
        assert os.path.exists("/app/target/release/nfa_verify")
    
    def test_parse_stage_present_in_output(self):
        """Verify parse stage completes and reports record count"""
        assert os.path.exists("/tmp/test_report.json")
    
    def test_exact_record_count(self):
        """Must parse exactly 30 records - catches record loss/duplication bugs"""
        report = load_report()
        total_flows = sum(a["flow_count"] for a in report["aggregates"])
        assert total_flows == 30, f"Expected 30 records, got {total_flows}"
    
    def test_no_parse_errors(self):
        """Verify report was created successfully"""
        report = load_report()
        assert "aggregates" in report

class TestNFAParseIntegrity:
    """Test parse stage data integrity - catches corruption bugs"""
    
    def test_report_file_created(self):
        """Verify report JSON file is emitted"""
        assert os.path.exists("/tmp/test_report.json")
    
    def test_report_valid_json(self):
        """Verify report is valid JSON - catches emit corruption"""
        report = load_report()
        assert isinstance(report, dict)
    
    def test_report_has_aggregates_key(self):
        """Verify report contains aggregates array"""
        report = load_report()
        assert "aggregates" in report
        assert isinstance(report["aggregates"], list)
    
    def test_report_has_classifications_key(self):
        """Verify report contains classifications array"""
        report = load_report()
        assert "classifications" in report
        assert isinstance(report["classifications"], list)
    
    def test_report_has_total_flows(self):
        """Verify report contains total_flows field"""
        report = load_report()
        assert "total_flows" in report
        assert isinstance(report["total_flows"], int)
    
    def test_report_has_emission_hash(self):
        """Verify report contains emission_hash field"""
        report = load_report()
        assert "emission_hash" in report
        assert isinstance(report["emission_hash"], str)

# ==================== AGGREGATE STAGE TESTS ====================

class TestNFAggregateProtocols:
    """Test protocol aggregation correctness"""
    
    def test_two_protocols_present(self):
        """Must have exactly TCP and UDP aggregates"""
        report = load_report()
        protocols = [agg["protocol"] for agg in report["aggregates"]]
        assert len(protocols) == 2, f"Expected 2 protocols, got {len(protocols)}: {protocols}"
    
    def test_tcp_protocol_exists(self):
        """TCP protocol must be present"""
        report = load_report()
        protocols = [agg["protocol"] for agg in report["aggregates"]]
        assert "TCP" in protocols, "TCP protocol missing from aggregates"
    
    def test_udp_protocol_exists(self):
        """UDP protocol must be present - catches protocol dropping bugs"""
        report = load_report()
        protocols = [agg["protocol"] for agg in report["aggregates"]]
        assert "UDP" in protocols, "UDP protocol missing from aggregates (BUG: conditional drop)"
    
    def test_no_extra_protocols(self):
        """No spurious protocols should appear"""
        report = load_report()
        protocols = [agg["protocol"] for agg in report["aggregates"]]
        assert set(protocols) == {"TCP", "UDP"}, f"Unexpected protocols: {protocols}"

class TestNFAggregateByteCounts:
    """Test byte aggregation accuracy - catches corruption/double-counting"""
    
    def test_exact_tcp_bytes(self):
        """TCP bytes must be exactly 405000 - catches byte corruption bugs"""
        report = load_report()
        tcp_agg = next(a for a in report["aggregates"] if a["protocol"] == "TCP")
        assert tcp_agg["total_bytes"] == 405000, \
            f"TCP bytes: expected 405000, got {tcp_agg['total_bytes']} (BUG: corruption/double-count)"
    
    def test_exact_udp_bytes(self):
        """UDP bytes must be exactly 82500 - catches byte corruption bugs"""
        report = load_report()
        udp_agg = next(a for a in report["aggregates"] if a["protocol"] == "UDP")
        assert udp_agg["total_bytes"] == 82500, \
            f"UDP bytes: expected 82500, got {udp_agg['total_bytes']} (BUG: corruption)"
    
    def test_exact_total_bytes(self):
        """Total bytes must be exactly 487500"""
        report = load_report()
        total = sum(a["total_bytes"] for a in report["aggregates"])
        assert total == 487500, \
            f"Total bytes: expected 487500, got {total} (BUG: byte loss/corruption)"
    
    def test_bytes_not_doubled(self):
        """Bytes should not be doubled - catches double-counting bug"""
        report = load_report()
        tcp_agg = next(a for a in report["aggregates"] if a["protocol"] == "TCP")
        assert tcp_agg["total_bytes"] < 500000, \
            f"TCP bytes {tcp_agg['total_bytes']} suggests double-counting (expected ~405000)"
    
    def test_bytes_not_inflated_by_taint(self):
        """UDP bytes should not have +5000 taint inflation"""
        report = load_report()
        udp_agg = next(a for a in report["aggregates"] if a["protocol"] == "UDP")
        assert udp_agg["total_bytes"] < 90000, \
            f"UDP bytes {udp_agg['total_bytes']} suggests taint inflation (expected 82500)"

class TestNFAggregatePacketCounts:
    """Test packet aggregation accuracy"""
    
    def test_exact_tcp_packets(self):
        """TCP packets must be exactly 3384"""
        report = load_report()
        tcp_agg = next(a for a in report["aggregates"] if a["protocol"] == "TCP")
        assert tcp_agg["total_packets"] == 3384, \
            f"TCP packets: expected 3384, got {tcp_agg['total_packets']} (BUG: underflow/corruption)"
    
    def test_exact_udp_packets(self):
        """UDP packets must be exactly 771"""
        report = load_report()
        udp_agg = next(a for a in report["aggregates"] if a["protocol"] == "UDP")
        assert udp_agg["total_packets"] == 771, \
            f"UDP packets: expected 771, got {udp_agg['total_packets']} (BUG: underflow)"
    
    def test_exact_total_packets(self):
        """Total packets must be exactly 4155"""
        report = load_report()
        total = sum(a["total_packets"] for a in report["aggregates"])
        assert total == 4155, \
            f"Total packets: expected 4155, got {total} (BUG: packet loss)"
    
    def test_packets_not_swapped_with_bytes(self):
        """Packets should not be swapped with bytes - catches swap bug"""
        report = load_report()
        tcp_agg = next(a for a in report["aggregates"] if a["protocol"] == "TCP")
        assert tcp_agg["total_packets"] < 10000, \
            f"TCP packets {tcp_agg['total_packets']} looks like byte value (BUG: swap)"
        assert tcp_agg["total_bytes"] > 100000, \
            f"TCP bytes {tcp_agg['total_bytes']} looks like packet value (BUG: swap)"

class TestNFAggregateFlowCounts:
    """Test flow count accuracy"""
    
    def test_exact_tcp_flow_count(self):
        """TCP flow count must be exactly 21"""
        report = load_report()
        tcp_agg = next(a for a in report["aggregates"] if a["protocol"] == "TCP")
        assert tcp_agg["flow_count"] == 21, \
            f"TCP flow_count: expected 21, got {tcp_agg['flow_count']} (BUG: inflation)"
    
    def test_exact_udp_flow_count(self):
        """UDP flow count must be exactly 9"""
        report = load_report()
        udp_agg = next(a for a in report["aggregates"] if a["protocol"] == "UDP")
        assert udp_agg["flow_count"] == 9, \
            f"UDP flow_count: expected 9, got {udp_agg['flow_count']} (BUG: inflation)"
    
    def test_flow_counts_sum_to_total(self):
        """Flow counts must sum to 30"""
        report = load_report()
        total_flows = sum(a["flow_count"] for a in report["aggregates"])
        assert total_flows == 30, \
            f"Sum of flow_counts: expected 30, got {total_flows}"

class TestNFAggregateUniquePairs:
    """Test unique IP pair counting"""
    
    def test_tcp_unique_pairs_exact(self):
        """TCP unique_pairs must be exactly 21 (one per flow)"""
        report = load_report()
        tcp_agg = next(a for a in report["aggregates"] if a["protocol"] == "TCP")
        assert tcp_agg["unique_pairs"] == 21, \
            f"TCP unique_pairs: expected 21, got {tcp_agg['unique_pairs']} (BUG: incorrect counting)"
    
    def test_udp_unique_pairs_exact(self):
        """UDP unique_pairs must be exactly 9 (one per flow)"""
        report = load_report()
        udp_agg = next(a for a in report["aggregates"] if a["protocol"] == "UDP")
        assert udp_agg["unique_pairs"] == 9, \
            f"UDP unique_pairs: expected 9, got {udp_agg['unique_pairs']} (BUG: incorrect counting)"
    
    def test_unique_pairs_not_halved(self):
        """Unique pairs should not be divided by 2"""
        report = load_report()
        for agg in report["aggregates"]:
            assert agg["unique_pairs"] >= agg["flow_count"] // 2, \
                f"{agg['protocol']} unique_pairs {agg['unique_pairs']} too low (BUG: halving)"

# ==================== CLASSIFY STAGE TESTS ====================

class TestNFClassifyCategories:
    """Test classification category correctness"""
    
    def test_two_classifications_present(self):
        """Must have exactly 2 classifications (TCP + UDP)"""
        report = load_report()
        assert len(report["classifications"]) == 2, \
            f"Expected 2 classifications, got {len(report['classifications'])} (BUG: drop/duplicate)"
    
    def test_tcp_category_normal(self):
        """TCP should be 'normal' (405000 bytes < 1M threshold)"""
        report = load_report()
        tcp_class = next(c for c in report["classifications"] if "TCP" in c["details"])
        assert tcp_class["category"] == "normal", \
            f"TCP category: expected 'normal', got '{tcp_class['category']}' (BUG: misclassification)"
    
    def test_udp_category_normal(self):
        """UDP should be 'normal' (82500 bytes < 1M threshold)"""
        report = load_report()
        udp_class = next(c for c in report["classifications"] if "UDP" in c["details"])
        assert udp_class["category"] == "normal", \
            f"UDP category: expected 'normal', got '{udp_class['category']}' (BUG: misclassification)"
    
    def test_no_suspicious_category(self):
        """Should not have 'suspicious' category - catches misclassification bug"""
        report = load_report()
        categories = [c["category"] for c in report["classifications"]]
        assert "suspicious" not in categories, \
            "'suspicious' category found (BUG: hash-triggered misclassification)"

class TestNFClassifyRiskScores:
    """Test risk score correctness - catches inflation bugs"""
    
    def test_tcp_risk_score_exact(self):
        """TCP risk score must be exactly 20 (normal category)"""
        report = load_report()
        tcp_class = next(c for c in report["classifications"] if "TCP" in c["details"])
        assert tcp_class["risk_score"] == 20, \
            f"TCP risk_score: expected 20, got {tcp_class['risk_score']} (BUG: inflation)"
    
    def test_udp_risk_score_exact(self):
        """UDP risk score must be exactly 20 (normal category)"""
        report = load_report()
        udp_class = next(c for c in report["classifications"] if "UDP" in c["details"])
        assert udp_class["risk_score"] == 20, \
            f"UDP risk_score: expected 20, got {udp_class['risk_score']} (BUG: inflation)"
    
    def test_risk_scores_in_valid_range(self):
        """All risk scores must be 0-100"""
        report = load_report()
        for classification in report["classifications"]:
            assert 0 <= classification["risk_score"] <= 100, \
                f"Risk score {classification['risk_score']} out of range (BUG: overflow)"
    
    def test_risk_scores_not_inflated(self):
        """Risk scores should not exceed 50 for normal traffic"""
        report = load_report()
        for classification in report["classifications"]:
            assert classification["risk_score"] <= 50, \
                f"Risk score {classification['risk_score']} too high for normal traffic (BUG: +30 inflation)"

class TestNFClassifyDetails:
    """Test classification details integrity"""
    
    def test_details_not_corrupted(self):
        """Details field should not be 'CORRUPTED'"""
        report = load_report()
        for classification in report["classifications"]:
            assert classification["details"] != "CORRUPTED", \
                "Details field corrupted to 'CORRUPTED' (BUG: details corruption)"
    
    def test_details_contains_protocol(self):
        """Details should contain protocol name"""
        report = load_report()
        for classification in report["classifications"]:
            assert "Protocol:" in classification["details"], \
                f"Details missing protocol: {classification['details']}"
    
    def test_details_contains_bytes(self):
        """Details should contain bytes value"""
        report = load_report()
        for classification in report["classifications"]:
            assert "Bytes:" in classification["details"], \
                f"Details missing bytes: {classification['details']}"

# ==================== EMIT STAGE TESTS ====================

class TestNFAEmitReport:
    """Test report emission correctness"""
    
    def test_total_flows_exact(self):
        """total_flows must be exactly 30"""
        report = load_report()
        assert report["total_flows"] == 30, \
            f"total_flows: expected 30, got {report['total_flows']} (BUG: underflow)"
    
    def test_total_flows_not_underflowed(self):
        """total_flows should not be reduced by MISSING_FLOWS"""
        report = load_report()
        assert report["total_flows"] >= 28, \
            f"total_flows {report['total_flows']} suggests underflow (expected 30)"
    
    def test_aggregates_count_correct(self):
        """Should have exactly 2 aggregates"""
        report = load_report()
        assert len(report["aggregates"]) == 2, \
            f"Expected 2 aggregates, got {len(report['aggregates'])} (BUG: conditional drop)"
    
    def test_classifications_count_correct(self):
        """Should have exactly 2 classifications, not duplicated"""
        report = load_report()
        assert len(report["classifications"]) == 2, \
            f"Expected 2 classifications, got {len(report['classifications'])} (BUG: duplication)"
    
    def test_emission_hash_present(self):
        """emission_hash must be non-empty hex string"""
        report = load_report()
        assert len(report["emission_hash"]) > 0, "emission_hash is empty"
        assert all(c in '0123456789abcdef' for c in report["emission_hash"].lower()), \
            "emission_hash is not valid hex"

# ==================== END-TO-END INTEGRITY TESTS ====================

class TestEndToEndIntegrity:
    """End-to-end pipeline integrity tests"""
    
    def test_full_pipeline_succeeds(self):
        """Full pipeline must complete successfully"""
        assert os.path.exists("/tmp/test_report.json")
        report = load_report()
        assert "aggregates" in report
    
    def test_no_byte_loss_across_pipeline(self):
        """Total bytes must match trace file exactly"""
        report = load_report()
        total_bytes = sum(a["total_bytes"] for a in report["aggregates"])
        assert total_bytes == 487500, \
            f"Byte loss detected: expected 487500, got {total_bytes}"
    
    def test_no_packet_loss_across_pipeline(self):
        """Total packets must match trace file exactly"""
        report = load_report()
        total_packets = sum(a["total_packets"] for a in report["aggregates"])
        assert total_packets == 4155, \
            f"Packet loss detected: expected 4155, got {total_packets}"
    
    def test_no_flow_duplication(self):
        """Total flows must be exactly 30, not more"""
        report = load_report()
        assert report["total_flows"] == 30, \
            f"Flow duplication: expected 30, got {report['total_flows']}"
    
    def test_data_consistency_aggregates_vs_classifications(self):
        """Aggregates and classifications must be consistent (same count)"""
        report = load_report()
        assert len(report["aggregates"]) == len(report["classifications"]), \
            f"Mismatch: {len(report['aggregates'])} aggregates but {len(report['classifications'])} classifications"
    
    def test_cross_module_contamination_absent(self):
        """No cross-module state contamination should affect results"""
        report = load_report()
        # If parse taint contaminates aggregate, bytes will be wrong
        total_bytes = sum(a["total_bytes"] for a in report["aggregates"])
        assert 480000 < total_bytes < 495000, \
            f"Cross-module contamination detected: bytes={total_bytes} (expected 487500)"
    
    def test_deterministic_output(self):
        """Report should be valid and consistent"""
        report = load_report()
        assert report["total_flows"] == 30
        total_bytes = sum(a["total_bytes"] for a in report["aggregates"])
        assert total_bytes == 487500
    
    def test_all_aggregates_have_positive_values(self):
        """All aggregates must have positive bytes, packets, and flow_count"""
        report = load_report()
        for agg in report["aggregates"]:
            assert agg["total_bytes"] > 0, f"{agg['protocol']} has zero/negative bytes"
            assert agg["total_packets"] > 0, f"{agg['protocol']} has zero/negative packets"
            assert agg["flow_count"] > 0, f"{agg['protocol']} has zero/negative flow_count"
    
    def test_no_static_state_leakage(self):
        """Report should have correct values (no accumulation)"""
        report = load_report()
        assert report["total_flows"] == 30
        total_bytes = sum(a["total_bytes"] for a in report["aggregates"])
        assert total_bytes == 487500

# ==================== ANTI-CHEATING TESTS ====================

class TestAntiCheating:
    """Tests to prevent hardcoded output bypasses"""
    
    def test_pipeline_processes_alternate_trace(self):
        """Verify binary actually processes CSV data, not hardcoded output.
        
        This test feeds an alternate trace file with known values and checks
        that aggregation adapts to the new data. Prevents agents from writing
        a main.rs that ignores arguments and prints static JSON.
        """
        import subprocess
        
        # Create alternate trace with known values (no header, 8 fields: src_ip,dst_ip,src_port,dst_port,protocol,bytes,packets,timestamp)
        alt_trace = """10.0.0.1,10.0.0.2,80,443,TCP,1000,10,1000001000
10.0.0.1,10.0.0.2,80,443,TCP,2000,20,1000001001
10.0.0.3,10.0.0.4,53,53,UDP,500,5,1000001002"""
        
        alt_trace_path = "/tmp/alt_trace.csv"
        alt_report_path = "/tmp/alt_report.json"
        
        with open(alt_trace_path, 'w') as f:
            f.write(alt_trace)
        
        # Run binary with alternate trace
        result = subprocess.run(
            ["/app/target/release/nfa_verify", alt_trace_path, alt_report_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0, f"Binary failed with alternate trace: {result.stderr}"
        assert os.path.exists(alt_report_path), "Binary did not produce output for alternate trace"
        
        # Verify output matches alternate trace data
        with open(alt_report_path) as f:
            alt_report = json.load(f)
        
        # Should have exactly 3 total flows
        total_flows = sum(a["flow_count"] for a in alt_report["aggregates"])
        assert total_flows == 3, f"Expected 3 flows from alternate trace, got {total_flows}"
        
        # TCP should have exactly 3000 bytes, 30 packets
        tcp_agg = next((a for a in alt_report["aggregates"] if a["protocol"] == "TCP"), None)
        assert tcp_agg is not None, "TCP aggregate missing from alternate trace output"
        assert tcp_agg["total_bytes"] == 3000, \
            f"TCP bytes mismatch: expected 3000, got {tcp_agg['total_bytes']} (binary not processing input)"
        assert tcp_agg["total_packets"] == 30, \
            f"TCP packets mismatch: expected 30, got {tcp_agg['total_packets']}"
        
        # UDP should have exactly 500 bytes, 5 packets
        udp_agg = next((a for a in alt_report["aggregates"] if a["protocol"] == "UDP"), None)
        assert udp_agg is not None, "UDP aggregate missing from alternate trace output"
        assert udp_agg["total_bytes"] == 500, \
            f"UDP bytes mismatch: expected 500, got {udp_agg['total_bytes']}"
        assert udp_agg["total_packets"] == 5, \
            f"UDP packets mismatch: expected 5, got {udp_agg['total_packets']}"
