fn main() {
    cc::Build::new()
        .file("../wav_h8/src/t8.c")
        .file("../wav_h8/src/wave.c")
        .file("../wav_h8/src/diag.c")
        .include("../wav_h8/include")
        .compile("wav_h8");
    println!("cargo:rustc-link-lib=dylib=wav_h8");
}
