# frozen_string_literal: true

require "digest"
require "fileutils"

root = File.expand_path("..", __dir__)
blk = File.join(root, "fixtures", "blk")
seed = File.join(root, "fixtures", "seed", "arena_seed.bin")
FileUtils.mkdir_p(blk)
FileUtils.mkdir_p(File.dirname(seed))

def pack_slice(epoch:, link_id:, band_class:, rows:)
  magic = "RTv1"
  header = magic.b + [epoch, link_id, band_class, rows.size].pack("NnnN")
  body = rows.map do |r|
    r[:digest] + [r[:qclass], r[:scope], r[:seq], 0].pack("NNNN")
  end.join
  header + body
end

rows = [
  { qname: "portal.corp.internal", qclass: 2, scope: 2, seq: 1, digest: Digest::SHA256.digest("portal.corp.internal")[0, 16] },
  { qname: "www.wan.home", qclass: 1, scope: 1, seq: 2, digest: Digest::SHA256.digest("www.wan.home")[0, 16] }
]
File.binwrite(File.join(blk, "tc.rt"), pack_slice(epoch: 2, link_id: 2, band_class: 0, rows: rows))

rows2 = rows.map { |r| r.merge(seq: r[:seq] + 1) }
File.binwrite(File.join(blk, "td.rt"), pack_slice(epoch: 3, link_id: 2, band_class: 1, rows: rows2))

anchor = [2].pack("N") + Digest::SHA256.digest("lane-anchor-v1")[0, 12]
File.binwrite(seed, anchor)
