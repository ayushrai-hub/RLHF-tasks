class RecordsController < ApplicationController
  def index
    rows = db.execute("SELECT id, name, section_id FROM records ORDER BY id")
    render json: { records: rows }
  end

  def show
    row = db.get_first_row("SELECT * FROM records WHERE id = ?", [params[:id]])
    return render_not_found("record") unless row
    render json: {
      id: row["id"],
      name: row["name"],
      section_id: row["section_id"],
      description: row["description"],
      tags: parse_json(row["tags"]) || [],
    }
  end
end
