#!/usr/bin/env bash
jar_path="${1:-target/local-ivy/schema-index.jar}"
unzip -p "$jar_path" com/acme/generated/schema-index.properties
