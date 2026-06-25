# Config Masking

Tmpfiles fragments are selected by basename before their rules are parsed. This
mirrors the way host images override vendor defaults: an `/etc/tmpfiles.d/foo`
file masks `/usr/lib/tmpfiles.d/foo`, even when the vendor file contains lines
that would otherwise be valid or invalid.

The selected files are then processed by basename order. This means masking and
ordering are separate concerns: first pick the winning file for every basename,
then read those winners in sorted basename order.
