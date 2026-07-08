#ifndef SFMT_LOGGER_H
#define SFMT_LOGGER_H

#include "sfmt/record.h"
#include "sfmt/sink.h"

typedef struct {
    sf_sink sink;
    sf_level min;
} sf_logger;

void sf_logger_init(sf_logger *lg, sf_sink sink, sf_level min);

int sf_logger_emit(sf_logger *lg, const sf_record *r);

#endif
