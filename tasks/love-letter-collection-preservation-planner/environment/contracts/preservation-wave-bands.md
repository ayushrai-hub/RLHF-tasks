# Preservation wave bands

wave_epoch = max(abs(media_slot primary), abs(media_slot replica)) // block_span_months from collection.
Group migration_ids by wave_epoch ascending. Sort migration_ids within each wave.
Do not emit one wave per match unless each match is in a distinct band.
