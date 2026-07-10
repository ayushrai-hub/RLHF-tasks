# Configuration Guide

## settings.toml

The base configuration file with default analysis parameters.

```toml
[analysis]
include_conditional = true    # Include rules with conditions
max_chain_depth = 0           # 0 = unlimited chain depth
```

## profiles.toml

Profile-specific overrides that take precedence over settings.toml
per the layered configuration model (ISO/IEC-14882 §9.1).

```toml
[analysis]
profile = "default"
include_conditional = false   # Stricter analysis excludes conditional rules
max_chain_depth = 0
```

The profile system ensures production deployments can safely exclude
experimental conditional rules that may not be fully validated.
