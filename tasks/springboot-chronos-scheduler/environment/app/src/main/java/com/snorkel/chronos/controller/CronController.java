package com.snorkel.chronos.controller;

import com.snorkel.chronos.cron.CronParseException;
import com.snorkel.chronos.cron.CronField;
import com.snorkel.chronos.cron.QuartzCronExpression;
import com.snorkel.chronos.dto.CronNextRequest;
import com.snorkel.chronos.dto.CronNextResponse;
import com.snorkel.chronos.dto.CronParseRequest;
import com.snorkel.chronos.dto.CronParseResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping("/api/cron")
public class CronController {

    @PostMapping("/parse")
    public ResponseEntity<CronParseResponse> parse(@RequestBody CronParseRequest req) {
        CronParseResponse r = new CronParseResponse();
        try {
            QuartzCronExpression expr = QuartzCronExpression.parse(req.expression);
            r.valid = true;
            r.fields = new ArrayList<>();
            for (CronField f : expr.getFields()) {
                CronParseResponse.FieldSummary fs = new CronParseResponse.FieldSummary();
                fs.name = f.getType().name();
                fs.raw = f.getRaw();
                fs.values = f.getValues();
                fs.special = f.getSpecial();
                r.fields.add(fs);
            }
            return ResponseEntity.ok(r);
        } catch (CronParseException e) {
            r.valid = false;
            r.error = e.getMessage();
            return ResponseEntity.badRequest().body(r);
        } catch (Exception e) {
            r.valid = false;
            r.error = e.getClass().getSimpleName() + ": " + e.getMessage();
            return ResponseEntity.badRequest().body(r);
        }
    }

    @PostMapping("/next")
    public ResponseEntity<CronNextResponse> next(@RequestBody CronNextRequest req) {
        QuartzCronExpression expr = QuartzCronExpression.parse(req.expression);
        ZoneId zone = req.zone == null ? ZoneId.of("UTC") : ZoneId.of(req.zone);
        ZonedDateTime from = (req.from == null || req.from.isEmpty())
                ? ZonedDateTime.now(zone)
                : Instant.parse(req.from).atZone(zone);
        int count = req.count == null ? 1 : Math.max(1, req.count);
        List<String> out = new ArrayList<>();
        ZonedDateTime cursor = from;
        for (int i = 0; i < count; i++) {
            ZonedDateTime nxt = expr.nextExecutionTime(cursor);
            if (nxt == null) break;
            out.add(nxt.toInstant().toString());
            cursor = nxt;
        }
        CronNextResponse r = new CronNextResponse();
        r.executions = out;
        return ResponseEntity.ok(r);
    }
}
