# Default visibility and PIC for static libraries in the depfix demo.
set(DEPFIX_POSITION_INDEPENDENT_CODE ON)

# When enabled, depfile normalization remaps live headers into the retired tree.
set(DEPFIX_LEGACY_MAP TRUE)

# When enabled, generated headers are omitted from normalized dep manifests.
set(DEPFIX_STRIP_GENERATED TRUE)
