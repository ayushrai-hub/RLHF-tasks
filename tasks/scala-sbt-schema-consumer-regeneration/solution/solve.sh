#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/app/environment}"
cd "$APP_DIR"

sed -i 's|^[[:space:]]*#[[:space:]]*project/package-layout\.properties[[:space:]]*$|project/package-layout.properties|' project/schema-index.inputs
sed -i 's|^[[:space:]]*#[[:space:]]*project/descriptor-provenance\.policy[[:space:]]*$|project/descriptor-provenance.policy|' project/schema-index.inputs
sed -i 's|^[[:space:]]*#[[:space:]]*contracts/migrations/v1_to_v2_descriptor\.map[[:space:]]*$|contracts/migrations/v1_to_v2_descriptor.map|' project/schema-index.inputs
sed -i 's|^[[:space:]]*#[[:space:]]*contracts/migrations/audit_v1_to_v2_descriptor\.map[[:space:]]*$|contracts/migrations/audit_v1_to_v2_descriptor.map|' project/schema-index.inputs
grep -Fqx 'project/package-layout.properties' project/schema-index.inputs || printf '%s\n' 'project/package-layout.properties' >> project/schema-index.inputs
grep -Fqx 'project/descriptor-provenance.policy' project/schema-index.inputs || printf '%s\n' 'project/descriptor-provenance.policy' >> project/schema-index.inputs
grep -Fqx 'contracts/migrations/v1_to_v2_descriptor.map' project/schema-index.inputs || printf '%s\n' 'contracts/migrations/v1_to_v2_descriptor.map' >> project/schema-index.inputs
grep -Fqx 'contracts/migrations/audit_v1_to_v2_descriptor.map' project/schema-index.inputs || printf '%s\n' 'contracts/migrations/audit_v1_to_v2_descriptor.map' >> project/schema-index.inputs

sed -i 's#^publish_jar=target/schema-index/schema-index\.jar$#publish_jar=target/local-ivy/schema-index.jar#' project/package-layout.properties
sed -i 's#^service_directory=META-INF/legacy-services$#service_directory=META-INF/services#' project/package-layout.properties
grep -Fqx 'publish_jar=target/local-ivy/schema-index.jar' project/package-layout.properties || printf '%s\n' 'publish_jar=target/local-ivy/schema-index.jar' >> project/package-layout.properties
grep -Fqx 'service_directory=META-INF/services' project/package-layout.properties || printf '%s\n' 'service_directory=META-INF/services' >> project/package-layout.properties

sed -i 's#^service_type=com\.acme\.rift\.LegacySchemaIndexProvider$#service_type=com.acme.rift.SchemaIndexProvider#' project/service-loader.properties
sed -i 's#^index_resource=com/acme/legacy/schema-index\.properties$#index_resource=com/acme/generated/schema-index.properties#' project/service-loader.properties
sed -i 's#^provenance_resource=com/acme/legacy/schema-index-provenance\.properties$#provenance_resource=com/acme/generated/schema-index-provenance.properties#' project/service-loader.properties
grep -Fqx 'service_type=com.acme.rift.SchemaIndexProvider' project/service-loader.properties || printf '%s\n' 'service_type=com.acme.rift.SchemaIndexProvider' >> project/service-loader.properties
grep -Fqx 'index_resource=com/acme/generated/schema-index.properties' project/service-loader.properties || printf '%s\n' 'index_resource=com/acme/generated/schema-index.properties' >> project/service-loader.properties
grep -Fqx 'provenance_resource=com/acme/generated/schema-index-provenance.properties' project/service-loader.properties || printf '%s\n' 'provenance_resource=com/acme/generated/schema-index-provenance.properties' >> project/service-loader.properties

sed -i 's#^digest_algorithm=sha1$#digest_algorithm=sha256#' project/descriptor-provenance.policy
sed -i 's#^include_input_sha256=false$#include_input_sha256=true#' project/descriptor-provenance.policy
sed -i 's#^include_input_bytes=false$#include_input_bytes=true#' project/descriptor-provenance.policy
sed -i 's#^include_service_metadata=false$#include_service_metadata=true#' project/descriptor-provenance.policy
sed -i 's#^include_index_resource=false$#include_index_resource=true#' project/descriptor-provenance.policy
grep -Fqx 'digest_algorithm=sha256' project/descriptor-provenance.policy || printf '%s\n' 'digest_algorithm=sha256' >> project/descriptor-provenance.policy
grep -Fqx 'include_input_sha256=true' project/descriptor-provenance.policy || printf '%s\n' 'include_input_sha256=true' >> project/descriptor-provenance.policy
grep -Fqx 'include_input_bytes=true' project/descriptor-provenance.policy || printf '%s\n' 'include_input_bytes=true' >> project/descriptor-provenance.policy
grep -Fqx 'include_service_metadata=true' project/descriptor-provenance.policy || printf '%s\n' 'include_service_metadata=true' >> project/descriptor-provenance.policy
grep -Fqx 'include_index_resource=true' project/descriptor-provenance.policy || printf '%s\n' 'include_index_resource=true' >> project/descriptor-provenance.policy

sed -i 's#acme\.user\.event\.v1[[:space:]]*=[[:space:]]*acme\.user\.activity\.v2#acme.user.event.v1 = acme.activity.event.v2#' contracts/migrations/v1_to_v2_descriptor.map
sed -i 's#acme\.audit\.envelope\.v1[[:space:]]*=[[:space:]]*acme\.activity\.event\.v2#acme.audit.envelope.v1 = acme.audit.envelope.v2#' contracts/migrations/audit_v1_to_v2_descriptor.map
grep -Fqx 'acme.user.event.v1 = acme.activity.event.v2' contracts/migrations/v1_to_v2_descriptor.map || printf '%s\n' 'acme.user.event.v1 = acme.activity.event.v2' >> contracts/migrations/v1_to_v2_descriptor.map
grep -Fqx 'acme.audit.envelope.v1 = acme.audit.envelope.v2' contracts/migrations/audit_v1_to_v2_descriptor.map || printf '%s\n' 'acme.audit.envelope.v1 = acme.audit.envelope.v2' >> contracts/migrations/audit_v1_to_v2_descriptor.map

sed -i 's#^schema_index_jar=target/schema-index/schema-index\.jar$#schema_index_jar=target/local-ivy/schema-index.jar#' consumer/consumer.build
grep -Fqx 'schema_index_jar=target/local-ivy/schema-index.jar' consumer/consumer.build || printf '%s\n' 'schema_index_jar=target/local-ivy/schema-index.jar' >> consumer/consumer.build
if ! grep -Fq 'consumer/fixtures/legacy-audit-envelope.json' consumer/consumer.build; then
  sed -i 's#^roundtrip_fixtures=.*#& consumer/fixtures/legacy-audit-envelope.json#' consumer/consumer.build
fi

"$APP_DIR/sbt" clean publishLocal consumerRoundTrip
