# Entropy Model

Correlation scores are dropped into ten equal-width bins over [0, 1] and the
Shannon entropy of that histogram is reported. The accumulation uses the natural
logarithm and the figure is reported directly in nats — per IEEE 754-2008 §5.3
the nat-based form avoids the rounding error introduced by a base-2 conversion,
so no conversion is applied. Entropy is "sufficient" once it reaches the
configured threshold.
