package com.attachment.core;

import java.nio.file.Path;

public final class ConfigPaths {
    public static final Path PRODUCTION_CONFIG = Path.of("/app/config/attachment-rules.properties");
    public static final Path STAGING_OVERRIDE = Path.of("/app/config/attachment-rules.override.properties");
    private ConfigPaths() {}
}
