//! Quantization mode handling.
//!
//! The crate can be built for either eight-bit integer weights or bf16 weights.
//! The CPU serving path is certified only for int8. bf16 remains available for
//! the GPU trial but is not certified for CPU serving.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QuantMode {
    Int8,
    Bf16,
}

impl QuantMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            QuantMode::Int8 => "int8",
            QuantMode::Bf16 => "bf16",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "int8" => Some(QuantMode::Int8),
            "bf16" => Some(QuantMode::Bf16),
            _ => None,
        }
    }

    /// Whether this mode is certified for the CPU serving path.
    pub fn cpu_certified(&self) -> bool {
        matches!(self, QuantMode::Int8)
    }
}
