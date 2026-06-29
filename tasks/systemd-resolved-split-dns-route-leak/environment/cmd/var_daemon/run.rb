# frozen_string_literal: true

require "json"
require "fileutils"
require "stringio"

require_relative "../../r7_lane/types"
require_relative "../../r7_lane/merge_k2"
require_relative "../../r7_lane/step_q2"
require_relative "../../n4_cache/bucket"
require_relative "../../n4_cache/evict_p5"
require_relative "../../v8_scope/bands"
require_relative "../../v8_scope/fold_m1"
require_relative "../../q3_trace/arena"
require_relative "../../q3_trace/emit_h3"

module VarDaemon
  ROOT = File.expand_path("../..", __dir__)
  STATE_DIR = File.join(ROOT, "var", "state")
  TRACE_DIR = File.join(ROOT, "var", "trace")
  ANCHOR_DIR = File.join(ROOT, "var", "anchor")

  module Run
    module_function

    def execute_profile(profile_path, path_kind:)
      profile = JSON.parse(File.read(profile_path))
      FileUtils.mkdir_p(STATE_DIR)
      FileUtils.mkdir_p(TRACE_DIR)

      lane = R7Lane::LaneView.new
      bucket = N4Cache::Bucket.new
      bands = V8Scope::BandSet.new
      arena = Q3Trace::Arena.new

      active_link = 1
      seq = 0
      steps = profile.fetch("steps", [])
      steps = reorder_vpn(steps) if profile["reorder_vpn"]

      steps.each do |step|
        case R7Lane::StepQ2.phase_label(step)
        when "link"
          iface = R7Lane::StepQ2.link_id(step)
          bump = step.fetch("epoch_bump", false)
          epoch = lane.attach(iface: iface, domain: step.fetch("domain"), bump: bump)
          active_link = iface
          evict_p5(bucket, epoch)
          bands.push(link_id: iface, downgrade_level: step.fetch("downgrade", 0))
        when "nx"
          bucket.remember(qname: step.fetch("qname"), link_epoch: lane.current_epoch)
        when "resolve"
          qclass = step.fetch("qclass", 1)
          scope = step.fetch("scope", active_link == 1 ? 1 : 2)
          seq += 1
          arena.record(
            qname: step.fetch("qname"),
            qclass_code: qclass,
            scope_code: scope,
            seq: seq,
            epoch: lane.current_epoch
          )
        end
      end

      band_class = fold_m1(bands, arena)

      lane_sink = StringIO.new
      merge_k2(lane, lane_sink)

      trace_path = File.join(TRACE_DIR, "#{profile.fetch('key')}_#{path_kind}.txt")
      row_maps = nil
      File.open(trace_path, "w") do |sink|
        row_maps = emit_h3(arena, sink)
      end
      header = R7Lane::RtPack.pack_header(
        epoch: lane.current_epoch,
        link_id: active_link,
        band_class: band_class,
        row_count: row_maps.size
      )
      bytes = R7Lane::RtPack.canonical_bytes(header: header, rows: row_maps)
      canonical = File.join(STATE_DIR, "#{profile.fetch('key')}_#{path_kind}.rt")
      File.binwrite(canonical, bytes)
      {
        "profile_key" => profile.fetch("key"),
        "path_kind" => path_kind,
        "route_fingerprint" => R7Lane::RtPack.digest_hex(bytes),
        "band_class" => band_class,
        "internal_leak_count" => count_leaks(row_maps),
        "canonical_path" => canonical
      }
    end

    def reorder_vpn(steps)
      links, rest = steps.partition { |s| R7Lane::StepQ2.phase_label(s) == "link" }
      links.reverse + rest
    end

    def count_leaks(row_maps)
      row_maps.count { |r| r[:qclass_code] == 2 && r[:scope_code] == 1 }
    end
  end
end
