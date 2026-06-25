#!/bin/bash
direct_ctx() {
  local tag="${1:-}"
  echo "ctx=direct:${tag}"
}
