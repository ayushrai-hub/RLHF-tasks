# Priority seeding

Seed order uses priority_score descending, artifact_id ascending tie-break.
priority_score = redundancy - len(crossref) - abs(media_slot)/12.
Do not sort priority_queue lexicographically alone.
