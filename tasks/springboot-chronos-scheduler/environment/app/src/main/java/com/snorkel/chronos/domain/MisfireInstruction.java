package com.snorkel.chronos.domain;

public enum MisfireInstruction {
    FIRE_NOW,
    DO_NOTHING,
    FIRE_NEXT_WITH_REMAINING_COUNT
}
