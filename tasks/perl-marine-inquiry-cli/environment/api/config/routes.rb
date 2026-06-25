Rails.application.routes.draw do
  get "/healthz", to: "health#show"

  scope :api do
    get "config", to: "config#show"

    get "sections",     to: "sections#index"
    get "sections/:id", to: "sections#show", constraints: { id: %r{[^/]+} }

    get "parties",     to: "parties#index"
    get "parties/:id", to: "parties#show", constraints: { id: %r{[^/]+} }

    get "records",     to: "records#index"
    get "records/:id", to: "records#show", constraints: { id: %r{[^/]+} }

    post "inquiries",     to: "sessions#create"
    get  "inquiries/:id", to: "sessions#show", constraints: { id: %r{[^/]+} }

    post "inquiries/:id/go",       to: "actions#go",       constraints: { id: %r{[^/]+} }
    post "inquiries/:id/retrieve", to: "actions#retrieve", constraints: { id: %r{[^/]+} }
    post "inquiries/:id/adjourn",  to: "actions#adjourn",  constraints: { id: %r{[^/]+} }
    post "inquiries/:id/finding",  to: "findings#create",  constraints: { id: %r{[^/]+} }
  end
end
