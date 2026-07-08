local files = {
  "/app/policies/splice/glass_a.lua",
  "/app/policies/splice/glass_b.lua",
  "/app/policies/splice/glass_c.lua",
  "/app/policies/splice/deep_armor.lua",
  "/app/policies/splice/shore_transition.lua"
}
print("family,kit,bonus")
for _, file in ipairs(files) do
  local rules = dofile(file)
  for _, row in ipairs(rules) do
    print(row.family .. "," .. row.kit .. "," .. row.bonus)
  end
end
