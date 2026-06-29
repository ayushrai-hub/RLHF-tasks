Rails.application.routes.draw do
  get "/health", to: proc { [200, { "Content-Type" => "text/plain" }, ["ok"]] }
  get "/v1/k6/entries", to: "entries#index"
end
