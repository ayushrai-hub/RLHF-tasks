Two data-integrity systems in /app are allowing incorrect or corrupted records to be read back.

The platform keeps an audit trail of session booking activity. When a caller retrieves audit history for a specific booking, it should receive only the records for that booking. Records must remain stable after they are stored — if a caller modifies the data object originally passed to the audit system, the stored record must be unaffected. Similarly, retrieving audit entries must return independent records that callers cannot inadvertently corrupt.

The event log has a similar problem: reading entries from the log returns objects that share internal state with the stored records. A caller who modifies a returned entry's data can unintentionally corrupt what the log holds.
