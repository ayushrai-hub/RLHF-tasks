//! Error type for the inference crate.

#[derive(Debug)]
pub enum InferError {
    Parse,
    Missing,
    Io,
}

impl std::fmt::Display for InferError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            InferError::Parse => write!(f, "failed to parse configuration"),
            InferError::Missing => write!(f, "missing required configuration section"),
            InferError::Io => write!(f, "i/o error"),
        }
    }
}

impl std::error::Error for InferError {}
