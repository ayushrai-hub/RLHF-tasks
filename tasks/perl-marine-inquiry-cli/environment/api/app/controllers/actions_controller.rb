class ActionsController < ApplicationController
  def go
    s = load_session or return
    body = load_body
    target = body["section_id"].to_s
    return render_bad("missing section_id") if target.empty?

    current = s["current_section"]
    exit_row = db.get_first_row(
      "SELECT to_section FROM exits WHERE from_section = ? AND to_section = ?",
      [current, target],
    )
    return render_bad("no_passage_from_#{current}_to_#{target}") unless exit_row

    journal = append_journal(s, { "kind" => "go", "from" => current, "to" => target, "day" => s["day_number"] })
    db.execute("UPDATE sessions SET current_section = ?, journal = ? WHERE id = ?",
               [target, JSON.generate(journal), s["id"]])
    render json: state_payload(s["id"])
  end

  def retrieve
    s = load_session or return
    body = load_body
    rid = body["record_id"].to_s
    return render_bad("missing record_id") if rid.empty?

    rec = db.get_first_row("SELECT * FROM records WHERE id = ?", [rid])
    return render_not_found("record") unless rec
    if rec["section_id"] != s["current_section"]
      return render_bad("record_not_in_current_section", section_id: s["current_section"])
    end

    retrieved = parse_json(s["retrieved"]) || []
    already = retrieved.include?(rid)
    retrieved << rid unless already
    journal = append_journal(s, { "kind" => "retrieve", "record_id" => rid, "day" => s["day_number"] })
    db.execute("UPDATE sessions SET retrieved = ?, journal = ? WHERE id = ?",
               [JSON.generate(retrieved), JSON.generate(journal), s["id"]])
    render json: state_payload(s["id"]).merge(
      "record" => { "id" => rec["id"], "name" => rec["name"], "description" => rec["description"] },
      "already_retrieved" => already,
    )
  end

  def adjourn
    s = load_session or return
    new_day = s["day_number"].to_i + 1
    journal = append_journal(s, { "kind" => "adjourn", "into_day" => new_day })
    db.execute("UPDATE sessions SET day_number = ?, journal = ? WHERE id = ?",
               [new_day, JSON.generate(journal), s["id"]])
    render json: state_payload(s["id"])
  end

  private

  def load_session
    s = db.get_first_row("SELECT * FROM sessions WHERE id = ?", [params[:id]])
    return s if s
    render_not_found("inquiry")
    nil
  end

  def append_journal(s, entry)
    journal = parse_json(s["journal"]) || []
    journal << entry
    journal
  end

  def state_payload(id)
    s = db.get_first_row("SELECT * FROM sessions WHERE id = ?", [id])
    {
      "inquiry_id" => s["id"],
      "current_section" => s["current_section"],
      "day_number" => s["day_number"],
      "retrieved" => parse_json(s["retrieved"]) || [],
      "journal" => parse_json(s["journal"]) || [],
      "status" => s["status"],
    }
  end
end
