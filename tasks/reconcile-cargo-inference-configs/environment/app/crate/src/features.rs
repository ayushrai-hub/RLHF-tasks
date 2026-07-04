//! Compile-time feature detection helpers.
//!
//! These report which cargo features were compiled in. The release-plan feature
//! set is derived separately from the crate default list per the dossier rules
//! (telemetry stripped in production, gpu-cuda excluded on the CPU path, etc.).

pub fn compiled_features() -> Vec<&'static str> {
    let mut out = Vec::new();
    if cfg!(feature = "cpu-avx2") {
        out.push("cpu-avx2");
    }
    if cfg!(feature = "gpu-cuda") {
        out.push("gpu-cuda");
    }
    if cfg!(feature = "quantized-int8") {
        out.push("quantized-int8");
    }
    if cfg!(feature = "quantized-bf16") {
        out.push("quantized-bf16");
    }
    if cfg!(feature = "dynamic-batching") {
        out.push("dynamic-batching");
    }
    if cfg!(feature = "telemetry") {
        out.push("telemetry");
    }
    out
}
