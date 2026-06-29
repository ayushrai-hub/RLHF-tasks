# frozen_string_literal: true

require_relative "bucket"

module N4Cache
  module Vault
    module_function

    def load_fixture(path)
      bucket = Bucket.new
      return bucket unless File.file?(path)

      File.readlines(path, chomp: true).each do |line|
        qname, epoch_s = line.split(":", 2)
        bucket.remember(qname: qname, link_epoch: epoch_s.to_i)
      end
      bucket
    end
  end
end
