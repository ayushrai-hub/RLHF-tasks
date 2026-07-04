#include "util/timezone.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int days_before_month(int month) {
    static const int days[] = {0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};
    if (month < 1 || month > 12) {
        return 0;
    }
    return days[month];
}

static long long utc_epoch_from_parts(int year, int month, int day, int hour, int minute, int second) {
    long long y = year;
    long long days = (y - 1970) * 365 + (y - 1969) / 4 - (y - 1901) / 100 + (y - 1601) / 400;
    days += days_before_month(month) + (day - 1);
    if (month > 2 && ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0)) {
        days += 1;
    }
    return days * 86400LL + hour * 3600LL + minute * 60LL + second;
}

static void apply_fixed_cst(long long utc_epoch, LocalParts *out) {
    long long local = utc_epoch - 6LL * 3600LL;
    if (local < 0) {
        local = 0;
    }
    int sec = (int)(local % 60);
    local /= 60;
    int minute = (int)(local % 60);
    local /= 60;
    int hour = (int)(local % 24);
    local /= 24;

    int year = 1970;
    while (1) {
        int leap = ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) ? 1 : 0;
        int year_days = leap ? 366 : 365;
        if (local < year_days) {
            break;
        }
        local -= year_days;
        year += 1;
    }

    int month = 1;
    while (month <= 12) {
        int md = 31;
        if (month == 4 || month == 6 || month == 9 || month == 11) {
            md = 30;
        } else if (month == 2) {
            int leap = ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) ? 1 : 0;
            md = leap ? 29 : 28;
        }
        if (local < md) {
            break;
        }
        local -= md;
        month += 1;
    }

    out->year = year;
    out->month = month;
    out->day = (int)local + 1;
    out->hour = hour;
    out->minute = minute;
    out->second = sec;
}

int parse_timestamp(const char *iso, LocalParts *parts) {
    int year = 0, month = 0, day = 0, hour = 0, minute = 0, second = 0;
    char sign = '+';
    int off_h = 0, off_m = 0;
    if (sscanf(iso, "%d-%d-%dT%d:%d:%d%c%d:%d", &year, &month, &day, &hour, &minute, &second, &sign,
               &off_h, &off_m) < 6) {
        return -1;
    }
    int offset_minutes = off_h * 60 + off_m;
    if (sign == '-') {
        offset_minutes = -offset_minutes;
    }
    long long utc = utc_epoch_from_parts(year, month, day, hour, minute, second);
    utc -= (long long)offset_minutes * 60LL;
    apply_fixed_cst(utc, parts);
    return 0;
}

long long timestamp_epoch_minutes(const char *iso) {
    LocalParts parts;
    if (parse_timestamp(iso, &parts) != 0) {
        return 0;
    }
    return parts.hour * 60LL + parts.minute + parts.day * 24LL * 60LL;
}
