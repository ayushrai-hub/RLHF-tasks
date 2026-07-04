CREATE TABLE nonce_seen (
    issuer TEXT NOT NULL,
    jti TEXT NOT NULL,
    alg TEXT NOT NULL,
    assertion_id TEXT NOT NULL,
    recorded_at INTEGER NOT NULL,
    PRIMARY KEY (issuer, jti, alg)
);
