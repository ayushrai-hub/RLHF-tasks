Two storage systems in /app are tracking state incorrectly.

Wheels can be placed on a temporary hold while a student completes their booking. If a hold expires before the booking is confirmed, the wheel should be free for another student to book. The system is not correctly releasing wheels from expired holds.

The platform uses a cache to avoid repeating expensive lookups. The cache's combined load-and-store operation does not correctly handle a stored result of "nothing found" — it re-runs the load on every subsequent access instead of serving the stored result.
