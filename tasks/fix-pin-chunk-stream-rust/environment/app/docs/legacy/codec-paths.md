# Codec paths (archived)

Pre-pin export routed tail digests through `codec::tail_hex` while full chunks used `codec::chunk_hex`. That split matched the retired high-limb tail policy.

Current export is supposed to unify limbs, but tail emission may still call the codec tail helper during soak runs.
