-- Payments ingress certificate inventory schema
CREATE TABLE IF NOT EXISTS cert_inventory (
    serial TEXT PRIMARY KEY,
    subject_cn TEXT NOT NULL,
    sha256_hex TEXT NOT NULL,
    fingerprint_md5 TEXT NOT NULL,
    not_before DATE NOT NULL,
    not_after DATE NOT NULL,
    role_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS revocation_events (
    serial TEXT PRIMARY KEY REFERENCES cert_inventory(serial),
    revoked_at DATE NOT NULL,
    reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS role_bindings (
    service_name TEXT PRIMARY KEY,
    role_tag TEXT NOT NULL,
    client_ca_serial TEXT NOT NULL REFERENCES cert_inventory(serial)
);
