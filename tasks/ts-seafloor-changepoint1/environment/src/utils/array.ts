/**
 * Return elements at positions [start, end) from arr.
 */
export function slice<T>(arr: T[], start: number, end: number): T[] {
  return arr.slice(start, end);
}

/**
 * Yield successive overlapping windows of length `size` with step `step`.
 */
export function* slidingWindow<T>(
  arr: T[],
  size: number,
  step = 1,
): Generator<{ start: number; end: number; window: T[] }> {
  for (let i = 0; i + size <= arr.length; i += step) {
    yield { start: i, end: i + size, window: arr.slice(i, i + size) };
  }
}

/**
 * Split arr into non-overlapping chunks of `size`.
 */
export function chunk<T>(arr: T[], size: number): T[][] {
  const result: T[][] = [];
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size));
  }
  return result;
}

/**
 * Return indices where predicate is true.
 */
export function findIndices<T>(arr: T[], predicate: (v: T, i: number) => boolean): number[] {
  return arr.reduce<number[]>((acc, v, i) => {
    if (predicate(v, i)) acc.push(i);
    return acc;
  }, []);
}

/**
 * Return the index of the maximum value in arr, or -1 if empty.
 */
export function argmax(arr: number[]): number {
  if (arr.length === 0) return -1;
  let best = 0;
  for (let i = 1; i < arr.length; i++) {
    if (arr[i] > arr[best]) best = i;
  }
  return best;
}
