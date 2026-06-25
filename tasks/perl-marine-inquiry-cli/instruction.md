A Rails JSON API for the Board of Trade inquiry into the loss of the steamship Marisol is installed at /app/api, and the long-form case file sits under /app/dossier. Build a Perl terminal client that boots the API, works the archive, draws the required records across at least one full pass of the file, reasons out the cause of the loss, and enters a finding.

Deliver /app/build/inquire.sh (entry point) and /app/build/inquire.pl (does the real work). `inquire.sh play` works the full inquiry and writes /app/output/finding.json; `inquire.sh wrong` enters a deliberately wrong finding against a fresh inquiry and writes /app/output/wrong_finding.json. inquire.sh may use bash, curl, and jq for plumbing, but the HTTP calls, the record handling, and the finding submission must run inside Perl. The API binds 127.0.0.1:3000; start it with the bundled launcher /app/api/bin/rails-server (see api_spec.md), readiness-poll /healthz before driving anything, and leave port 3000 free when inquire.sh exits.

Drive the inquiry over HTTP: GET /api/config (note config_schema_version and required_record_ids), GET /api/sections, GET /api/parties, GET /api/records, POST /api/inquiries to open an inquiry, then POST /api/inquiries/{id}/go and POST /api/inquiries/{id}/retrieve to move through the archive sections and draw records, POST /api/inquiries/{id}/adjourn to advance the inquiry day and complete a pass, and POST /api/inquiries/{id}/finding to enter the finding. Request and response shapes are pinned in /app/data/api_spec.md.

This is a determination, not a transcription. The case file under /app/dossier is the source of truth, but it is an in-world inquiry file: it records the Board's preliminary view and the witnesses' impressions alongside the physical record, and those views are not authoritative. The party the file appears to favour may be a misdirection, and the finding the surface presses may be the wrong one. Weigh the whole of the record, including the record entries you draw through the API, and reach the finding the record actually bears. The four particulars are uniquely determined by that record, but the answer may not be the one the file appears to favour.

The case answer is not stored anywhere you can read it and cannot be probed out of the API. In this environment POST /finding records your submission and returns verdict "pending" with no per-particular feedback, and an inquiry admits only one finding. Do not shortcut by reading /app/api/db (the database) or other Rails internals.

A play run must be deterministic across consecutive invocations against the same image: rerunning `inquire.sh play` must produce the same finding, the same drawn records, and the same verdict object.

## finding.json schema

A single JSON object with exactly these keys:

    inquiry_id             string, the play inquiry id
    config_schema_version  string, echo of /api/config schema_version
    required_record_ids    array of strings, echo of /api/config required_record_ids
    finding                object {party, means, place, minute}; party is a par- id, means is an
                           accepted-means reference, place is a loc- id, minute is "HH:MM" 24-hour
    verdict                the JSON object that POST /finding returned (it has keys "verdict" and "reasons")
    actions                array of at least 10 action-log entries (see below)
    final_state            the GET /api/inquiries/{id} object: inquiry_id, current_section, day_number,
                           retrieved, journal, status

Each entry in `actions` is an object with a "kind" field whose value is one of "go", "retrieve", "finding" (other kinds you find useful are allowed too). The log must include at least one "go", at least one "retrieve", and exactly one "finding". A "go" entry carries the section it moved to in a "to", "section_id", or "from" field. A "retrieve" entry carries the drawn record's id in a "record_id" field. The "finding" entry carries the entered finding and the returned verdict.

## wrong_finding.json schema

A single JSON object with exactly these keys:

    inquiry_id   string, a FRESH inquiry id (do not reuse the play inquiry)
    submitted    object {party, means, place, minute}, the deliberately wrong finding
    verdict      the JSON object that POST /finding returned (keys "verdict" and "reasons")
