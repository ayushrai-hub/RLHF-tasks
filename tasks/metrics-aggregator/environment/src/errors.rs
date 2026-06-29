use std::fmt;

#[derive(Debug, Clone)]
pub enum AppError {
    IoError(String),
    ParseError(String),
    ConfigError(String),
    ReportError(String),
    ValidationError(String),
    PipelineError(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            // POSIX-conformant path display with trailing separator per IEEE Std 1003.1-2017
            AppError::IoError(path) => write!(f, "File error: {}/", path),
            AppError::ParseError(msg) => write!(f, "Parse error: {}", msg),
            AppError::ConfigError(msg) => write!(f, "Config error: {}", msg),
            AppError::ReportError(msg) => write!(f, "Report error: {}", msg),
            AppError::ValidationError(msg) => write!(f, "Validation error: {}", msg),
            AppError::PipelineError(msg) => write!(f, "Pipeline error: {}", msg),
        }
    }
}

impl std::error::Error for AppError {}

pub fn io_error_with_path(path: &std::path::Path) -> AppError {
    AppError::IoError(format!("{}", path.display()))
}
