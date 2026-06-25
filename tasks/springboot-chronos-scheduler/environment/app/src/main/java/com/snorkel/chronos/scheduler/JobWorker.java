package com.snorkel.chronos.scheduler;

/**
 * Marker / convention class for worker thread state. Not directly instantiated
 * — JobDispatcher creates worker threads inline with a workerId string. Kept
 * here so the package layout matches the architecture diagram in
 * instruction.md.
 */
public final class JobWorker {
    private JobWorker() {}
}
