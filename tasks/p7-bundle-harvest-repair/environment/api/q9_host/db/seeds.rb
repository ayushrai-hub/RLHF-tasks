# frozen_string_literal: true

K6Row.delete_all

rows = [
  ["k6-001", "/api/v1/users/10/items/20", 0, "2024-06-01T06:00:00Z", 40, 200],
  ["k6-002", "/api/v1/users/11/items/21", 1, "2024-06-01T07:00:00Z", 55, 200],
  ["k6-003", "/api/v1/users/12/items/22", 2, "2024-06-01T08:00:00Z", 120, 500],
  ["k6-004", "/api/v1/users/13/items/23", 3, "2024-06-01T09:00:00Z", 30, 200],
  ["k6-005", "/api/v1/users/14/items/24", 1, "2024-06-01T10:00:00Z", 90, 404],
  ["k6-006", "/api/v1/users/15/items/25", 0, "2024-06-01T11:00:00Z", 200, 200],
  ["k6-007", "/api/v1/users/16/items/26", 2, "2024-06-01T11:30:00Z", 75, 200],
  ["k6-008", "/api/v1/users/17/items/27", 1, "2024-06-01T12:00:00Z", 150, 503],
  ["k6-009", "/api/v1/users/18/items/28", 3, "2024-06-01T13:00:00Z", 60, 200],
  ["k6-010", "/api/v1/users/19/items/29", 1, "2024-06-01T14:00:00Z", 300, 200],
  ["k6-011", "/api/v1/users/20/items/30", 0, "2024-06-01T15:00:00Z", 45, 200],
  ["k6-012", "/api/v1/users/21/items/31", 2, "2024-06-01T16:00:00Z", 180, 500],
  ["k6-013", "/api/v1/users/22/items/32", 1, "2024-06-01T17:00:00Z", 95, 200],
  ["k6-014", "/api/v1/users/23/items/33", 1, "2024-06-01T18:00:00Z", 110, 200],
  ["k6-015", "/api/v1/users/24/items/34", 3, "2024-06-01T19:00:00Z", 70, 200],
  ["k6-016", "/api/v1/users/25/items/35", 0, "2024-06-01T20:00:00Z", 250, 200],
  ["k6-017", "/api/v1/users/26/items/36", 1, "2024-06-01T21:00:00Z", 85, 404],
  ["k6-018", "/api/v1/users/27/items/37", 2, "2024-06-01T22:00:00Z", 130, 200],
  ["k6-019", "/api/v1/users/28/items/38", 1, "2024-06-01T23:00:00Z", 400, 200],
  ["k6-020", "/api/v1/users/29/items/39", 0, "2024-06-01T23:30:00Z", 50, 200]
]

rows.each do |key, route, pri, at, lat, stat|
  K6Row.create!(
    rec_key: key,
    route_path: route,
    priority: pri,
    recorded_at: Time.iso8601(at),
    lat_ms: lat,
    status_code: stat
  )
end
