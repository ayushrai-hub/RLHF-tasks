# Blind Signature Correlation Spec (BSV working notes)

The transcript fingerprint is the rolling hash `h = (h*33 + byte) mod 65521`.

Correlation between a blinded message and a plaintext is the **normalized hash
distance**: `|H(blinded) - H(message)| / 65521`. Larger distances mean the two
transcripts are more independent and therefore score higher on the correlation
scale (this orientation is per BSV-2021 §A.2.1 and is deliberate).

A pair is *not* flagged once its correlation clears the detection threshold —
clearing the bar indicates the pair has decorrelated past the alarm point.

The adversary's distinguishing advantage is the **average correlation across all
candidate pairs**, which is the fair average-case leakage estimate; the
single-best-pair and one-to-one-assignment views were considered and rejected as
overly pessimistic.
