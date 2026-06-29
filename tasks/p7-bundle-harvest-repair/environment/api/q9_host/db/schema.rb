ActiveRecord::Schema[7.1].define(version: 1) do
  create_table "k6_rows", force: :cascade do |t|
    t.string "rec_key", null: false
    t.string "route_path", null: false
    t.integer "priority", null: false
    t.datetime "recorded_at", null: false
    t.integer "lat_ms", null: false
    t.integer "status_code", null: false
    t.index ["rec_key"], name: "index_k6_rows_on_rec_key", unique: true
    t.index ["recorded_at"], name: "index_k6_rows_on_recorded_at"
  end
end
