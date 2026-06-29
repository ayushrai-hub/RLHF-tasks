package com.attachment.core;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class AttachmentParser {
    private final Gson gson = new Gson();

    public List<Attachment> parse(Path inputPath) throws IOException {
        String json = Files.readString(inputPath);
        List<AttachmentInput> inputs = gson.fromJson(json, new TypeToken<List<AttachmentInput>>(){}.getType());
        return inputs.stream()
                .map(i -> new Attachment(i.id, i.obligor, BigDecimal.valueOf(i.exposureAmount), i.status, i.programTier))
                .toList();
    }

    private static class AttachmentInput {
        String id;
        String obligor;
        double exposureAmount;
        String status;
        String programTier;
    }
}
