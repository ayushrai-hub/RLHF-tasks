# Stage Pipeline

## Padding

Per ITU-T X.224 §7.1.2, padding is applied BEFORE checksum
to match wire-format verification at intermediate relay nodes.

## Checksum

stage_checksum = hash(padded_data, stage_id) XOR seed
