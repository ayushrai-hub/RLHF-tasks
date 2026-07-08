#pragma once

#include "model/beam.hpp"

#include <optional>
#include <string>
#include <unordered_map>

namespace beam::cache {

std::string envelope_cache_key(const CommittedState& state, const std::string& combination_name);

class EnvelopeStore {
  public:
    std::optional<EnvelopeValues> lookup(const std::string& key) const;
    void store(const std::string& key, const EnvelopeValues& values);

  private:
    std::unordered_map<std::string, EnvelopeValues> entries_;
};

}  // namespace beam::cache
