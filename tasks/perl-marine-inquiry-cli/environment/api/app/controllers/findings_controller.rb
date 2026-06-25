class FindingsController < ApplicationController
  REQUIRED_KEY = "required_record_ids".freeze

  def create
    s = db.get_first_row("SELECT * FROM sessions WHERE id = ?", [params[:id]])
    return render_not_found("inquiry") unless s

    # One finding per inquiry. Once entered, the inquiry is closed; a different
    # finding needs a fresh inquiry worked through again. Denies fishing for the
    # answer by entering guesses in a loop.
    unless s["status"] == "active"
      return render_bad("inquiry_closed_for_finding", status: s["status"])
    end

    body = load_body
    party  = body["party"].to_s
    means  = body["means"].to_s
    place  = body["place"].to_s
    minute = body["minute"].to_s

    missing = []
    missing << "party"  if party.empty?
    missing << "means"  if means.empty?
    missing << "place"  if place.empty?
    missing << "minute" if minute.empty?
    return render_bad("missing_particulars", particulars: missing) unless missing.empty?
    return render_bad("invalid_minute") unless minute.match?(/\A\d{1,2}:\d{2}\z/)

    entered = { party: party, means: means, place: place, minute: minute }
    truth = db.get_first_row("SELECT * FROM truth WHERE id = 1")

    # No sealed solution is loaded in the working environment. The office records
    # the finding, closes the inquiry, and returns a "pending" verdict; the finding
    # is adjudicated only at submission review against the office's own sealed
    # conclusion. There is no live sound/unsound signal and no per-particular
    # feedback to fish against, so the answer must be reasoned from the record.
    unless truth
      db.execute("UPDATE sessions SET status = ? WHERE id = ?", ["entered", s["id"]])
      return render json: {
        inquiry_id: s["id"],
        verdict: "pending",
        entered: entered,
        reasons: [],
        missing_records: [],
        passes_completed: s["day_number"].to_i - 1,
      }
    end

    retrieved = parse_json(s["retrieved"]) || []
    req_row = db.get_first_row("SELECT value FROM config WHERE key = ?", [REQUIRED_KEY])
    required = req_row ? (parse_json(req_row["value"]) || []) : []
    missing_records = required - retrieved

    passes = s["day_number"].to_i - 1
    minp_row = db.get_first_row("SELECT value FROM config WHERE key = 'min_days_before_finding'")
    min_passes = minp_row ? minp_row["value"].to_i : 1

    reasons = []
    reasons << "party_wrong"  if party  != truth["party"]
    reasons << "means_wrong"  if means  != truth["means"]
    reasons << "place_wrong"  if place  != truth["place"]
    reasons << "minute_wrong" if minute != truth["minute"]
    reasons << "missing_records" unless missing_records.empty?
    reasons << "incomplete_pass" if passes < min_passes

    verdict = reasons.empty? ? "sound" : "unsound"
    db.execute(
      "UPDATE sessions SET status = ? WHERE id = ?",
      [verdict == "sound" ? "closed-sound" : "closed-unsound", s["id"]],
    )

    render json: {
      inquiry_id: s["id"],
      verdict: verdict,
      entered: entered,
      reasons: reasons,
      missing_records: missing_records,
      passes_completed: passes,
    }
  end
end
