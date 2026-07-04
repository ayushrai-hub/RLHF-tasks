#ifndef TOU_TIMEZONE_H
#define TOU_TIMEZONE_H

typedef struct {
    int year;
    int month;
    int day;
    int hour;
    int minute;
    int second;
} LocalParts;

int parse_timestamp(const char *iso, LocalParts *parts);
long long timestamp_epoch_minutes(const char *iso);

#endif
