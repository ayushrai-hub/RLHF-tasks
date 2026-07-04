-- Deterministic inventory after emergency CA rollover (reference clock 2026-06-01)
INSERT INTO cert_inventory (serial, subject_cn, sha256_hex, fingerprint_md5, not_before, not_after, role_tag) VALUES
  ('SN-API', 'payments-api-ca', '102030405060708090a0b0c0d0e0f000112233445566778899aabbccddeeff00', '7d865e959b2466918c9863afca940d05', '2024-01-01', '2027-12-31', 'api_ingress'),
  ('SN-LEDGER', 'ledger-client-ca', '202030405060708090a0b0c0d0e0f000112233445566778899aabbccddeeff001', 'c4ca4238a0b923820dcc509a6f75849b', '2024-01-01', '2027-12-31', 'ledger_client'),
  ('SN-FRAUD', 'fraud-client-ca', '302030405060708090a0b0c0d0e0f000112233445566778899aabbccddeeff002', 'c81e728d9d4c2f636f067f89cc14862c', '2024-01-01', '2027-12-31', 'fraud_scoring_ca'),
  ('SN-FRAUD-LEGACY', 'fraud-client-ca-legacy', '502030405060708090a0b0c0d0e0f000112233445566778899aabbccddeeff004', 'a87ff679a2f3e71d9181a67b7542122d', '2024-01-01', '2027-12-31', 'fraud_client'),
  ('SN-SETTLE', 'settlement-client-ca', '402030405060708090a0b0c0d0e0f000112233445566778899aabbccddeeff003', 'eccbc87e4b5ce2fe28308fd9f2a7baf3', '2024-01-01', '2027-12-31', 'settlement_client'),
  ('SN-LIVE-ANCHOR', 'rollover-anchor-live', 'aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899', 'a87ff679a2f3e71d9181a67b7542122c', '2024-06-01', '2027-06-01', 'trust_anchor'),
  ('SN-GRACE-EDGE', 'grace-window-anchor', 'bbccddeeff00112233445566778899aabbccddeeff0011223344556677889900', 'e4da3b7fbbce2345d7772b0674a318f5', '2024-06-01', '2026-06-10', 'trust_anchor'),
  ('SN-EXPIRED', 'expired-anchor', 'ccddeeff00112233445566778899aabbccddeeff001122334455667788990011', '1679091c5a880faf6fb5e6087eb1b2dc', '2023-01-01', '2026-05-01', 'trust_anchor'),
  ('SN-REVOKED', 'revoked-anchor', 'ddeeff00112233445566778899aabbccddeeff00112233445566778899001122', '8f14e45fceea167a5a36dedd4bea2543', '2023-01-01', '2027-01-01', 'trust_anchor');

INSERT INTO revocation_events (serial, revoked_at, reason) VALUES
  ('SN-REVOKED', '2026-03-01', 'superseded');

INSERT INTO role_bindings (service_name, role_tag, client_ca_serial) VALUES
  ('payments-api', 'api_ingress', 'SN-API'),
  ('ledger-writer', 'ledger_client', 'SN-LEDGER'),
  ('fraud-scorer', 'fraud_client', 'SN-FRAUD'),
  ('settlement-gw', 'settlement_client', 'SN-SETTLE');
