/**
 * Parse an ISO 8601 UTC string from the database to a Date object.
 * Handles both 'Z' suffix and '+00:00' forms.
 */
export function parseTimestamp(ts: string): Date {
  return new Date(ts);
}

/**
 * Convert a Date to an ISO 8601 string with milliseconds and Z suffix.
 */
export function toISOString(d: Date): string {
  return d.toISOString();
}

/**
 * Compute the difference between two Date values in hours.
 */
export function diffHours(a: Date, b: Date): number {
  return (b.getTime() - a.getTime()) / (1000 * 3600);
}

/**
 * Return true if the given date falls within [windowStart, windowEnd] inclusive.
 */
export function isInWindow(d: Date, windowStart: Date, windowEnd: Date): boolean {
  return d >= windowStart && d <= windowEnd;
}

/**
 * Parse a date string like "2024-01-08" or "January 8, 2024" to a Date (UTC midnight).
 */
export function parseDateLoose(s: string): Date | null {
  const iso = Date.parse(s);
  if (!isNaN(iso)) {
    return new Date(iso);
  }
  return null;
}

/**
 * Given a sorted array of Date objects, return indices where gaps exceed gapThresholdMs.
 */
export function findGapIndices(timestamps: Date[], gapThresholdMs: number): number[] {
  const gaps: number[] = [];
  for (let i = 1; i < timestamps.length; i++) {
    if (timestamps[i].getTime() - timestamps[i - 1].getTime() > gapThresholdMs) {
      gaps.push(i);
    }
  }
  return gaps;
}
