#!/usr/bin/env bash
set -euo pipefail

cat > /app/carillon-planner <<'RUBY'
#!/usr/bin/env ruby
require "json"
require "time"
require "set"

TIERS = {"novice" => 0, "competent" => 1, "experienced" => 2, "conductor" => 3}

def minutes(iso)
  Time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").to_i / 60
end

def overlap?(a, b)
  a["start"] < b["end"] && b["start"] < a["end"]
end

def duration(p)
  minutes(p["end"]) - minutes(p["start"])
end

def proposal_ringers(p)
  p["assignments"].sort_by { |a| a["bell"] }.map { |a| a["ringer"] }
end

def internal_conflict?(a, b)
  shared = proposal_ringers(a).to_set & proposal_ringers(b).to_set
  return true if a["tower"] == b["tower"] && overlap?(a, b)
  return true if !shared.empty? && overlap?(a, b)
  return false if shared.empty?

  gap = [minutes(a["start"]), minutes(b["start"])].max -
        [minutes(a["end"]), minutes(b["end"])].min
  gap < 30
end

def within_minute_caps?(data, items)
  towers = data["towers"].to_h { |t| [t["id"], t] }
  ringers = data["ringers"].to_h { |r| [r["name"], r] }
  tower_minutes = towers.keys.to_h { |id| [id, 0] }
  ringer_minutes = ringers.keys.to_h { |name| [name, 0] }

  items.each do |p|
    length = duration(p)
    tower_minutes[p["tower"]] += length
    proposal_ringers(p).to_set.each { |name| ringer_minutes[name] += length }
  end

  tower_minutes.all? { |id, used| used <= towers[id]["max_minutes"] } &&
    ringer_minutes.all? { |name, used| used <= ringers[name]["max_minutes"] }
end

def first_reason(data, p)
  towers = data["towers"].to_h { |t| [t["id"], t] }
  ringers = data["ringers"].to_h { |r| [r["name"], r] }
  tower = towers[p["tower"]]
  return "tower_unknown" if tower.nil?
  return "method_unsupported" unless tower["methods"].include?(p["method"])
  return "bad_interval" if p["end"] <= p["start"]

  bells = p["assignments"].map { |a| a["bell"] }
  return "bad_assignments" unless bells.sort == (1..tower["bells"]).to_a

  names = p["assignments"].map { |a| a["ringer"] }
  return "ringer_unknown" if names.any? { |name| !ringers.key?(name) }
  return "duplicate_ringer" if names.uniq.length != names.length

  p["assignments"].each do |assignment|
    bell = assignment["bell"]
    tier = ringers[assignment["ringer"]]["tier"]
    needed = if bell == tower["bells"]
               "experienced"
             elsif bell > tower["bells"] / 2
               "competent"
             else
               "novice"
             end
    return "tier_mismatch" if TIERS[tier] < TIERS[needed]
  end

  data["maintenance"].each do |row|
    return "maintenance" if row["kind"] == "hard" && row["tower"] == p["tower"] && overlap?(row, p)
  end

  assigned = names.to_set
  data["existing_sessions"].each do |session|
    next unless session["status"] == "scheduled" && overlap?(session, p)
    return "tower_busy" if session["tower"] == p["tower"]
    return "ringer_busy" unless (assigned & session["ringers"].to_set).empty?
  end
  nil
end

def compatible?(items)
  items.combination(2).all? { |a, b| !internal_conflict?(a, b) }
end

def feasible?(data, items)
  compatible?(items) && within_minute_caps?(data, items)
end

def better?(candidate, incumbent)
  return true if incumbent.nil?

  c_ids = candidate.map { |p| p["id"] }.sort.join(",")
  i_ids = incumbent.map { |p| p["id"] }.sort.join(",")
  c_key = [candidate.sum { |p| p["score"] }, candidate.length, -candidate.sum { |p| duration(p) }]
  i_key = [incumbent.sum { |p| p["score"] }, incumbent.length, -incumbent.sum { |p| duration(p) }]
  (c_key <=> i_key) == 1 || (c_key == i_key && c_ids < i_ids)
end

def solve(data)
  usable = []
  rejected_by_rule = {}
  data["proposals"].each do |p|
    reason = first_reason(data, p)
    if reason.nil?
      usable << p
    else
      rejected_by_rule[p["id"]] = reason
    end
  end

  mandatory = usable.select { |p| p["mandatory"] }
  unless feasible?(data, mandatory)
    rejected = data["proposals"].map do |p|
      reason = if rejected_by_rule.key?(p["id"])
                 rejected_by_rule[p["id"]]
               elsif p["mandatory"]
                 "mandatory_conflict"
               else
                 "blocked_by_mandatory_conflict"
               end
      {"id" => p["id"], "reason" => reason}
    end
    return {"status" => "infeasible", "selected" => [], "rejected" => rejected, "total_score" => 0}
  end

  optional = usable.reject { |p| p["mandatory"] }.sort_by { |p| [-p["score"], p["id"]] }
  towers = data["towers"].to_h { |t| [t["id"], t] }
  ringers = data["ringers"].to_h { |r| [r["name"], r] }
  tower_ids = towers.keys.sort
  ringer_names = ringers.keys.sort
  tower_pos = tower_ids.each_with_index.to_h
  ringer_pos = ringer_names.each_with_index.to_h

  base_tower = Array.new(tower_ids.length, 0)
  base_ringer = Array.new(ringer_names.length, 0)
  mandatory.each do |p|
    length = duration(p)
    base_tower[tower_pos[p["tower"]]] += length
    proposal_ringers(p).to_set.each { |name| base_ringer[ringer_pos[name]] += length }
  end

  n = optional.length
  durations = optional.map { |p| duration(p) }
  conflict = Array.new(n, 0)
  blocked = 0
  optional.each_with_index do |p, i|
    if mandatory.any? { |m| internal_conflict?(p, m) }
      blocked |= (1 << i)
      next
    end
    ((i + 1)...n).each do |j|
      next unless internal_conflict?(p, optional[j])
      conflict[i] |= (1 << j)
      conflict[j] |= (1 << i)
    end
  end

  best = nil
  score_cache = {}

  score_bound = lambda do |mask|
    score_cache[mask] ||= begin
      total = 0
      m = mask
      while m != 0
        bit = m & -m
        idx = bit.bit_length - 1
        total += optional[idx]["score"]
        m ^= bit
      end
      total
    end
  end

  can_add = lambda do |idx, tower_used, ringer_used|
    p = optional[idx]
    length = durations[idx]
    tower_idx = tower_pos[p["tower"]]
    return nil if tower_used[tower_idx] + length > towers[p["tower"]]["max_minutes"]

    new_tower = tower_used.dup
    new_tower[tower_idx] += length
    new_ringer = ringer_used.dup
    proposal_ringers(p).to_set.each do |name|
      ringer_idx = ringer_pos[name]
      return nil if new_ringer[ringer_idx] + length > ringers[name]["max_minutes"]
      new_ringer[ringer_idx] += length
    end
    [new_tower, new_ringer]
  end

  current_items = lambda { |selected_optional| mandatory + selected_optional.map { |i| optional[i] } }

  search = nil
  search = lambda do |mask, selected_optional, tower_used, ringer_used, current_score|
    if !best.nil? && current_score + score_bound.call(mask) < best.sum { |p| p["score"] }
      return
    end
    if mask == 0
      trial = current_items.call(selected_optional)
      best = trial if better?(trial, best)
      return
    end
    bit = mask & -mask
    idx = bit.bit_length - 1
    rest = mask ^ bit
    added = can_add.call(idx, tower_used, ringer_used)
    unless added.nil?
      new_tower, new_ringer = added
      search.call(rest & ~conflict[idx], selected_optional + [idx], new_tower, new_ringer,
                  current_score + optional[idx]["score"])
    end
    search.call(rest, selected_optional, tower_used, ringer_used, current_score)
  end

  all_optional = ((1 << n) - 1) & ~blocked
  if (0...n).all? { |i| (conflict[i] & all_optional) == 0 }
    start_state = [base_tower, base_ringer]
    dp = {start_state => []}
    (0...n).each do |idx|
      next if (all_optional & (1 << idx)) == 0
      updates = dp.dup
      dp.each do |state, selected_optional|
        tower_used, ringer_used = state
        added = can_add.call(idx, tower_used, ringer_used)
        next if added.nil?
        trial_selected = selected_optional + [idx]
        existing = updates[added]
        if existing.nil? || better?(current_items.call(trial_selected), current_items.call(existing))
          updates[added] = trial_selected
        end
      end
      dp = updates
    end
    dp.values.each do |selected_optional|
      trial = current_items.call(selected_optional)
      best = trial if better?(trial, best)
    end
  else
    search.call(all_optional, [], base_tower, base_ringer, mandatory.sum { |p| p["score"] })
  end

  chosen = (best || []).sort_by { |p| p["id"] }
  chosen_ids = chosen.map { |p| p["id"] }.to_set
  rejected = []
  data["proposals"].each do |p|
    if rejected_by_rule.key?(p["id"])
      rejected << {"id" => p["id"], "reason" => rejected_by_rule[p["id"]]}
    elsif !chosen_ids.include?(p["id"])
      rejected << {"id" => p["id"], "reason" => "conflicts_with_selected"}
    end
  end

  {
    "status" => "ok",
    "selected" => chosen.map do |p|
      {
        "id" => p["id"],
        "tower" => p["tower"],
        "start" => p["start"],
        "end" => p["end"],
        "score" => p["score"],
        "ringers" => proposal_ringers(p)
      }
    end,
    "rejected" => rejected,
    "total_score" => chosen.sum { |p| p["score"] }
  }
end

if ARGV.length != 2
  warn "usage: carillon-planner input.json output.json"
  exit 2
end

data = JSON.parse(File.read(ARGV[0], encoding: "UTF-8"))
result = solve(data)
File.write(ARGV[1], JSON.generate(result))
RUBY

chmod +x /app/carillon-planner
mkdir -p /app/output
/app/carillon-planner /app/input/august_rota_requests.json /app/output/plan.json
