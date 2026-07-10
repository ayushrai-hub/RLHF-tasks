package com.acme.rift;

public final class SchemaDescriptor {
    public final String inputDescriptor;
    public final String canonicalDescriptor;
    public final boolean supported;

    public SchemaDescriptor(String inputDescriptor, String canonicalDescriptor, boolean supported) {
        this.inputDescriptor = inputDescriptor;
        this.canonicalDescriptor = canonicalDescriptor;
        this.supported = supported;
    }
}
