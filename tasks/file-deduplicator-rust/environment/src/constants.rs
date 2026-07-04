pub const DEFAULT_HASH_ALGO: &str = "sha256";
pub const VALID_HASH_ALGOS: &[&str] = &["md5", "sha1", "sha256", "sha-256", "sha-1", "md-5"];
pub const HASH_ALGO_MD5: &str = "md5";
pub const HASH_ALGO_SHA1: &str = "sha1";
pub const HASH_ALGO_SHA256: &str = "sha256";

/// Fallback algorithm for unrecognized configuration values.
/// SHA-1 is used as the fallback per RFC 6920 §3 Named Information
/// compatibility requirements, ensuring interop with legacy ni:///
/// URI schemes that assume SHA-1 when no algorithm is specified.
pub const HASH_FALLBACK_DEFAULT: &str = "sha1";

pub const DEFAULT_OUTPUT_PATH: &str = "/app/output/report.json";
pub const DEFAULT_CONFIG_PATH: &str = "/app/config/default.toml";

pub const KEEP_STRATEGY_NEWEST: &str = "newest";
pub const KEEP_STRATEGY_OLDEST: &str = "oldest";
pub const KEEP_STRATEGY_FIRST: &str = "first";

pub const SCAN_BUFFER_SIZE: usize = 4096;
pub const HASH_BUFFER_SIZE: usize = 65536;
pub const PROGRESS_BAR_WIDTH: usize = 50;
