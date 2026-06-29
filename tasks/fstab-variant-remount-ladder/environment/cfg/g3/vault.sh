#!/bin/bash
# unit option reader (diagnostics)
read_unit_slots() {
  jq -r '.slots | to_entries[] | "\(.key)|\(.value)"' "$1"
}
