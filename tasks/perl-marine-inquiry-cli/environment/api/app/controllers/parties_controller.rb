class PartiesController < ApplicationController
  def index
    rows = db.execute("SELECT id, name, role FROM parties ORDER BY sort_order")
    render json: { parties: rows }
  end

  def show
    p = db.get_first_row("SELECT * FROM parties WHERE id = ?", [params[:id]])
    return render_not_found("party") unless p
    render json: { id: p["id"], name: p["name"], role: p["role"], description: p["description"] }
  end
end
