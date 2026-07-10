# Build metadata

The schema index is generated from the paths listed in `schema-index.inputs`. The service-loader configuration names the JVM service type and provider class that are packaged into the jar. The release audit reads these files as build metadata, not as generated output.

Maintenance note: local runners may set APP_DIR to point at a copied workspace root, but the release workspace itself is /app/environment.
