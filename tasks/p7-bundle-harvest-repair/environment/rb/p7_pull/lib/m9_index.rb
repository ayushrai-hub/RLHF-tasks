# frozen_string_literal: true

module M9Index
  module_function

  def build(profiles, corpus_root)
    {
      "count" => profiles.length,
      "root" => corpus_root,
      "keys" => profiles.map { |p| p["id"] }
    }
  end

  def export_diag(corpus_root, count)
    path = File.join(corpus_root, "diag_index.txt")
    File.write(path, "profiles=#{count}\n")
  end
end
