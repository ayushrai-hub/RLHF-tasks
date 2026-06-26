# Digest width policy (archived)

Staging builds before the pin migration rendered tail-chunk digests from the **high** 32 bits of the FNV state. Full-width chunks continued to use the low limb.

That split was retired when export moved to a single limb rule, but some tail paths may still call the old helper.

See the current digest note for the active rendering rule.
