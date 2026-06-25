class SessionsController < ApplicationController
  START_SECTION = "sec-records-room".freeze

  def create
    id = "inq-#{SecureRandom.hex(8)}"
    db.execute(
      "INSERT INTO sessions (id, current_section, day_number, retrieved, journal, status) " \
      "VALUES (?, ?, 1, '[]', '[]', 'active')",
      [id, START_SECTION],
    )
    render json: state_payload(id)
  end

  def show
    s = db.get_first_row("SELECT * FROM sessions WHERE id = ?", [params[:id]])
    return render_not_found("inquiry") unless s
    render json: state_payload(params[:id])
  end

  private

  def state_payload(id)
    s = db.get_first_row("SELECT * FROM sessions WHERE id = ?", [id])
    {
      inquiry_id: s["id"],
      current_section: s["current_section"],
      day_number: s["day_number"],
      retrieved: parse_json(s["retrieved"]) || [],
      journal: parse_json(s["journal"]) || [],
      status: s["status"],
    }
  end
end
