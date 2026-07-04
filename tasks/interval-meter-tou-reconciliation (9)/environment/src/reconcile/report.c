#include "reconcile/report.h"

#include <stdio.h>
#include <string.h>

static void write_meter_json(FILE *fp, const MeterReport *meter) {
    fprintf(fp, "        \"%s\": {\n", meter->meter_id);
    fprintf(fp, "          \"interval_count\": %d,\n", meter->stats.interval_count);
    fprintf(fp, "          \"total_kwh\": %.3f,\n", meter->stats.total_kwh);
    fprintf(fp, "          \"tier_kwh\": {\n");
    fprintf(fp, "            \"off_peak\": %.3f,\n", meter->stats.tier_off_peak);
    fprintf(fp, "            \"mid_peak\": %.3f,\n", meter->stats.tier_mid_peak);
    fprintf(fp, "            \"on_peak\": %.3f\n", meter->stats.tier_on_peak);
    fprintf(fp, "          },\n");
    fprintf(fp, "          \"demand_peak_kw\": %.3f,\n", meter->stats.demand_peak_kw);
    fprintf(fp, "          \"rollover_events\": %d,\n", meter->stats.rollover_events);
    fprintf(fp, "          \"gap_intervals\": %d,\n", meter->stats.gap_intervals);
    fprintf(fp, "          \"reconciled\": %s,\n", meter->stats.reconciled ? "true" : "false");
    fprintf(fp, "          \"register_delta_kwh\": %.3f\n", meter->stats.register_delta_kwh);
    fprintf(fp, "        }");
}

int write_report_json(const ReconciliationReport *report, const char *out_path) {
    FILE *fp = fopen(out_path, "w");
    if (!fp) {
        return -1;
    }
    fprintf(fp, "{\n");
    fprintf(fp, "  \"timezone\": \"%s\",\n", report->timezone);
    fprintf(fp, "  \"all_reconciled\": %s,\n", report->all_reconciled ? "true" : "false");
    fprintf(fp, "  \"fixture_sets\": [\n");
    for (int i = 0; i < report->fixture_count; i++) {
        const FixtureReport *fx = &report->fixtures[i];
        fprintf(fp, "    {\n");
        fprintf(fp, "      \"name\": \"%s\",\n", fx->name);
        fprintf(fp, "      \"meters\": {\n");
        for (int j = 0; j < fx->meter_count; j++) {
            write_meter_json(fp, &fx->meters[j]);
            if (j + 1 < fx->meter_count) {
                fprintf(fp, ",\n");
            } else {
                fprintf(fp, "\n");
            }
        }
        fprintf(fp, "      }\n");
        fprintf(fp, "    }");
        if (i + 1 < report->fixture_count) {
            fprintf(fp, ",\n");
        } else {
            fprintf(fp, "\n");
        }
    }
    fprintf(fp, "  ]\n");
    fprintf(fp, "}\n");
    fclose(fp);
    return 0;
}
