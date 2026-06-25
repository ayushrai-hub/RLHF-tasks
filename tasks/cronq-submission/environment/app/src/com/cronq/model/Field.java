package com.cronq.model;

import java.util.Collections;
import java.util.Set;
import java.util.TreeSet;

public final class Field {
    private final Set<Integer> allowed;
    private final boolean restricted;
    private final String raw;

    public Field(Set<Integer> allowed, boolean restricted, String raw) {
        this.allowed = Collections.unmodifiableSet(new TreeSet<>(allowed));
        this.restricted = restricted;
        this.raw = raw;
    }

    public boolean allows(int value) {
        return allowed.contains(value);
    }

    /** True when the field constrains the date (anything that isn't a leading '*'). */
    public boolean isRestricted() {
        return restricted;
    }

    public Set<Integer> values() {
        return allowed;
    }

    public String raw() {
        return raw;
    }
}
