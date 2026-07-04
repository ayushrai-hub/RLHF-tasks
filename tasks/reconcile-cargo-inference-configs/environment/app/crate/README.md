# sentiment-infer

CPU inference crate for the `sentiment-transformer` text-classification model.

The crate package name (`sentiment-infer`) is not the model name. The model name
is carried by the experiment tracker export and is `sentiment-transformer`.

Runtime configuration is split across `Cargo.toml` (compile-time feature flags)
and `serving.toml` (serving ceilings and evaluation thresholds). The constants in
`src/*.rs` are compile-time fallbacks used only when no configuration file is
present; they are not the values used when cutting a release. Release cuts are
governed by the platform team's dossier, not by these fallbacks.

## Features

See `[features]` in `Cargo.toml`. The `telemetry` feature is compiled in by
default for local development but is governed by data-retention policy for
production builds.
