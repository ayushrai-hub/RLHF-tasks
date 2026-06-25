# Marisol Inquiry API contract

Reference for the HTTP endpoints the client must drive. instruction.md is the prompt and the goal; this file pins the request and response shapes for the endpoints named in the prompt.

## Starting the API

The Rails app lives at /app/api and listens on 127.0.0.1:3000. Start it by running the bundled launcher /app/api/bin/rails-server (it execs `bundle exec puma -C config/puma.rb config.ru` with RAILS_ENV=production and PORT=3000). inquire.sh owns the lifecycle: start the server in the background, readiness-poll GET /healthz until it answers, drive it, then stop it before inquire.sh exits so port 3000 is left free.

## HTTP endpoints

- GET /healthz returns {ok: true, ...}.
- GET /api/config returns the inquiry configuration. Notable keys: schema_version, case_title, case_date, inquiry_days, min_days_before_finding, accepted_means, accepted_places, required_record_ids.
- GET /api/sections returns {sections: [{id, name, short_description}, ...]} for every archive section.
- GET /api/sections/{id} returns the full section record with its exits and the record_ids filed in that section.
- GET /api/parties returns {parties: [{id, name, role}, ...]}.
- GET /api/parties/{id} returns the party record (name, role, description).
- GET /api/records returns {records: [{id, name, section_id}, ...]}.
- GET /api/records/{id} returns the full record with its description and tags.
- POST /api/inquiries opens a new inquiry and returns {inquiry_id, current_section, day_number, retrieved, journal, status}. The inquiry starts in sec-records-room at day_number 1.
- GET /api/inquiries/{id} returns the same state shape.
- POST /api/inquiries/{id}/go {"section_id": "..."} moves to a connected section. The target must be in the current section's exits list.
- POST /api/inquiries/{id}/retrieve {"record_id": "..."} draws a record into the working file if it is filed in the current section, and returns the record (id, name, description), so the record descriptions are read at runtime through this endpoint.
- POST /api/inquiries/{id}/adjourn advances the inquiry by one day (day_number increments). A full pass of the file is complete once day_number has passed min_days_before_finding, that is once day_number is at least 2.
- POST /api/inquiries/{id}/finding {"party": "par-...", "means": "...", "place": "loc-...", "minute": "HH:MM"} enters the finding and returns {inquiry_id, verdict, entered, reasons, missing_records, passes_completed}. `entered` echoes the four particulars. `verdict` is "sound", "unsound", or "pending". An inquiry admits only ONE finding: once a finding has been entered the inquiry is closed and any further finding on it is rejected. When no sealed conclusion is loaded in the environment (the normal working case), the endpoint records the finding, closes the inquiry, and returns verdict "pending" with empty reasons; there is no live sound/unsound and no per-particular feedback to probe against. The finding is adjudicated at submission review: a sound finding requires every required_record id from /api/config in the working file, day_number greater than min_days_before_finding, and all four particulars (party, means, place, minute) matching the case truth; otherwise the verdict is "unsound" and `reasons` lists the wrong particulars (party_wrong, means_wrong, place_wrong, minute_wrong) and any unmet precondition. On a sound finding, `reasons` is an empty array.

Times are HH:MM in 24-hour form, with a leading zero for hours under ten and the colon required.
