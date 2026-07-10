package com.acme.rift;

import java.util.Set;

public interface SchemaIndexProvider {
    String canonicalize(String descriptor);
    boolean supports(String descriptor);
    Set<String> canonicalDescriptors();
}
