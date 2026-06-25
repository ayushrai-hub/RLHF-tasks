class SectionsController < ApplicationController
  def index
    rows = db.execute("SELECT id, name, short_description FROM sections ORDER BY sort_order")
    render json: { sections: rows }
  end

  def show
    s = db.get_first_row("SELECT * FROM sections WHERE id = ?", [params[:id]])
    return render_not_found("section") unless s
    exits = db.execute("SELECT to_section, direction FROM exits WHERE from_section = ?", [params[:id]])
    record_ids = db.execute("SELECT id FROM records WHERE section_id = ? ORDER BY id", [params[:id]]).map { |r| r["id"] }
    render json: {
      id: s["id"],
      name: s["name"],
      short_description: s["short_description"],
      long_description: s["long_description"],
      exits: exits.map { |e| { to: e["to_section"], direction: e["direction"] } },
      record_ids: record_ids,
    }
  end
end
