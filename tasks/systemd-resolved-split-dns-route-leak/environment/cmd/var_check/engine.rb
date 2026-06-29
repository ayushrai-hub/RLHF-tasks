# frozen_string_literal: true

require "json"
require "fileutils"

require_relative "../var_daemon/run"
require_relative "../../r7_lane/types"

module VarCheck
  ROOT = File.expand_path("../..", __dir__)
  PROFILE_DIR = File.join(ROOT, "profiles")

  module Engine
    module_function

    def run_matrix(out_path)
      profiles = %w[run_a run_b run_c run_d]
      runs = []

      profiles.each do |key|
        profile_path = File.join(PROFILE_DIR, "#{key}.json")
        uninterrupted = VarDaemon::Run.execute_profile(profile_path, path_kind: "uninterrupted")
        recovered = run_recovered(profile_path, key)
        match = uninterrupted[:route_fingerprint] == recovered[:route_fingerprint] ? 1 : 0
        [uninterrupted, recovered].each do |row|
          runs << row.merge("cross_path_match" => match, "profile_key" => key)
        end
      end

      report = { "matrix_runs" => runs }
      FileUtils.mkdir_p(File.dirname(out_path))
      File.write(out_path, JSON.pretty_generate(report))
      validate!(report)
      report
    end

    def run_recovered(profile_path, _key)
      profile = JSON.parse(File.read(profile_path))
      if profile["recover_twice"]
        `/app/environment/migrations/mig9.sh --recover /app/environment/fixtures/seed/arena_seed.bin`
        `/app/environment/migrations/mig9.sh --recover /app/environment/fixtures/seed/arena_seed.bin`
      elsif profile.fetch("recover_once", true)
        `/app/environment/migrations/mig9.sh --recover /app/environment/fixtures/seed/arena_seed.bin`
      end
      VarDaemon::Run.execute_profile(profile_path, path_kind: "recovered")
    end

    def validate!(report)
      report["matrix_runs"].each do |row|
        canonical = row["canonical_path"]
        bytes = File.binread(canonical)
        computed = R7Lane::RtPack.digest_hex(bytes)
        raise "byte bind mismatch for #{row['profile_key']} #{row['path_kind']}" unless row["route_fingerprint"] == computed
        raise "leak on #{row['profile_key']}" if row["internal_leak_count"].positive?
        raise "band too wide on #{row['profile_key']}" if row["band_class"] > 1
      end

      by_profile = report["matrix_runs"].group_by { |r| r["profile_key"] }
      by_profile.each do |key, rows|
        kinds = rows.map { |r| r["path_kind"] }.sort
        raise "missing paths for #{key}" unless kinds == %w[recovered uninterrupted]
        fp = rows.map { |r| [r["path_kind"], r["route_fingerprint"]] }.to_h
        raise "cross path mismatch #{key}" unless fp["uninterrupted"] == fp["recovered"]
      end
    end
  end
end
