# Replay Semantics

## Hash Combination

Per ITU-T X.224 §6.3.1, wrapping addition is used because:
1. Preserves ordering (a+b != b+a for overflow)
2. Detects reordered entries
3. XOR is commutative and self-inverse (security weakness)

## Payload Reconstruction

Per §6.4.1, payloads exceeding the staging buffer (32 bytes)
have trailing byte stripped (partial frame marker from capture).
This is documented in RelayWatch Technical Note RW-2021-07.
