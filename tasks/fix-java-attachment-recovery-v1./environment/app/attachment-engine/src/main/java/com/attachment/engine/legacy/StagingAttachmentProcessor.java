package com.attachment.engine.legacy;

import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;
import com.attachment.report.ProcessedAttachment;

import java.util.Collections;
import java.util.List;

/** Staging-only processor stub — production uses AttachmentProcessor. */
public class StagingAttachmentProcessor {
    public List<ProcessedAttachment> process(List<Attachment> attachments, AttachmentConfig config) {
        return Collections.emptyList();
    }
}
