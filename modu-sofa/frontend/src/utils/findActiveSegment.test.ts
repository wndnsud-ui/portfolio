import { describe, expect, it } from 'vitest';
import { findActiveSegment } from './findActiveSegment';
import { parseServerDate } from './format';

describe('findActiveSegment', () => {
  const starts = [0.5, 8, 14, 28, 42];

  it('첫 Segment 이전이면 -1', () => {
    expect(findActiveSegment(starts, 0)).toBe(-1);
  });

  it('정확히 시작 시각이면 그 Segment', () => {
    expect(findActiveSegment(starts, 14)).toBe(2);
  });

  it('무음 구간에서는 직전 Segment 유지', () => {
    expect(findActiveSegment(starts, 27.9)).toBe(2);
  });

  it('마지막 이후에는 마지막 Segment', () => {
    expect(findActiveSegment(starts, 9999)).toBe(4);
  });

  it('빈 배열', () => {
    expect(findActiveSegment([], 3)).toBe(-1);
  });
});

describe('parseServerDate', () => {
  it('시간대 없는 시각은 UTC로 읽는다', () => {
    expect(parseServerDate('2026-10-16T15:17:08').toISOString()).toBe('2026-10-16T15:17:08.000Z');
    expect(parseServerDate('2026-10-16T15:17:08+00:00').toISOString()).toBe('2026-10-16T15:17:08.000Z');
    expect(parseServerDate('2026-10-17T00:17:08+09:00').toISOString()).toBe('2026-10-16T15:17:08.000Z');
  });
});
