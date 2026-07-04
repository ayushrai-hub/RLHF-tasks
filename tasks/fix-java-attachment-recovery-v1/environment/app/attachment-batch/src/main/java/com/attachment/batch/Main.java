package com.attachment.batch;

import com.attachment.core.AttachmentConfigLoader;
import com.attachment.core.AttachmentParser;
import com.attachment.engine.AttachmentProcessor;
import com.attachment.report.ReportGenerator;

import java.nio.file.Path;

public class Main {
    public static void main(String[] args) throws Exception {
        Path configPath = Path.of("/app/config/attachment-rules.properties");
        Path inputPath = Path.of("/app/data/attachments.json");
        Path outputPath = Path.of("/app/output/attachment-report.json");

        var config = AttachmentConfigLoader.load(configPath);
        var parser = new AttachmentParser();
        var processor = new AttachmentProcessor(config);
        var reportGenerator = new ReportGenerator();

        var attachments = parser.parse(inputPath);
        var processed = processor.process(attachments);
        reportGenerator.writeReport(processed, outputPath);
    }
}
