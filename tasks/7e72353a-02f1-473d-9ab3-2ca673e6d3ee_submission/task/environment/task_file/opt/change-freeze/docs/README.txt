change-freeze turns the inbox request stream into a compact deployment plan.
It reads policy.json plus sorted patches from policy.d and writes plan.json
and manifest.json under /var/lib/change-freeze/out.

The engine code is a small local module under vendor/freezeengine. Rebuilds do
not consume the live vendor copy directly; the wrapper refreshes it from
vendor_templates first.
