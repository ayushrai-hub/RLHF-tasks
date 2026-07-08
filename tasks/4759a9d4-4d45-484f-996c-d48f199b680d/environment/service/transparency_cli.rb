#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "fiddle"
require "fiddle/import"

module LedgerNative
  extend Fiddle::Importer
  dlload "/app/native/libledger_verify.so"
  extern "int ledger_canonicalize_row(const char*, char*, size_t)"
  extern "int ledger_verify_signature(const char*, const char*, const char*, const char*)"
  extern "int ledger_row_digest(const char*, const char*, char*, size_t)"
  extern "int ledger_compute_chain_root(const char**, size_t, char*, size_t)"
end

LEDGER_PATH = "/app/data/ledger_fixture.csv"

def load_rows
  File.readlines(LEDGER_PATH, chomp: true).reject(&:empty?)
end

def receipt_id_for(seq)
  # BUG: wrong prefix breaks valid receipts
  "rcpt-LEG-#{seq.rjust(4, '0')}"
end

def verify_row(csv_row)
  canonical = " " * 4096
  LedgerNative.ledger_canonicalize_row(csv_row, canonical, canonical.bytesize)
  parts = csv_row.split(",")
  sig = parts[6]
  signer = parts[5]
  posted_at = parts[4]
  LedgerNative.ledger_verify_signature(canonical.strip, sig, signer, posted_at)
end

def chain_root
  digests = []
  load_rows.each do |row|
    canonical = " " * 4096
    LedgerNative.ledger_canonicalize_row(row, canonical, canonical.bytesize)
    parts = row.split(",")
    digest = " " * 128
    LedgerNative.ledger_row_digest(canonical.strip, parts[6], digest, digest.bytesize)
    digests << digest.strip
  end
  ptrs = digests.map { |d| Fiddle::Pointer[d] }
  root = " " * 128
  LedgerNative.ledger_compute_chain_root(ptrs.pack("p*"), digests.length, root, root.bytesize)
  root.strip
end

if __FILE__ == $PROGRAM_NAME
  case ARGV[0]
  when "root"
    puts chain_root
  when "verify"
    row = ARGV[1]
    exit(verify_row(row).zero? ? 0 : 1)
  when "receipt"
    seq = ARGV[1]
    puts receipt_id_for(seq)
  else
    warn "usage: transparency_cli.rb [root|verify|receipt] ..."
    exit 2
  end
end
