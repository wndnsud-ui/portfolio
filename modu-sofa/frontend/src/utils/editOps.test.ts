import { describe, expect, it } from 'vitest';
import { cutSelection, fmtPrecise, keepOnly, normalize, parseTime, restoreSelection, snapToSegments } from './editOps';

const R = (a: number, b: number) => ({ start_time: a, end_time: b });

describe('편집 연산', () => {
  it('겹치거나 맞닿은 구간을 합친다', () => {
    expect(normalize([R(30, 40), R(5, 10), R(9, 12), R(-3, 1)], 100)).toEqual([R(0, 1), R(5, 12), R(30, 40)]);
  });

  it('선택 구간 삭제', () => {
    expect(cutSelection([R(10, 20)], R(15, 25), 100)).toEqual([R(10, 25)]);
  });

  it('여기만 살리기: 선택 밖을 모두 자른다', () => {
    expect(keepOnly([], R(20, 30), 100)).toEqual([R(0, 20), R(30, 100)]);
    expect(keepOnly([R(22, 24)], R(20, 30), 100)).toEqual([R(0, 20), R(22, 24), R(30, 100)]);
  });

  it('되살리기: 잘린 구간에서 선택 부분만 뺀다', () => {
    expect(restoreSelection([R(10, 40)], R(20, 25), 100)).toEqual([R(10, 20), R(25, 40)]);
    expect(restoreSelection([R(10, 20), R(30, 40)], R(0, 35), 100)).toEqual([R(35, 40)]);
  });

  it('문장 경계에 맞추기', () => {
    const segs = [R(0, 4.8), R(5.2, 9.9), R(10.5, 15)];
    expect(snapToSegments(R(6.3, 11.1), segs)).toEqual(R(5.2, 15));
    expect(snapToSegments(R(5.0, 9.0), segs)).toEqual(R(0, 9.9));
  });

  it('시각 입력 파싱', () => {
    expect(parseTime('01:23.4')).toBeCloseTo(83.4);
    expect(parseTime('1:02:03')).toBe(3723);
    expect(parseTime('12.5')).toBe(12.5);
    expect(parseTime('abc')).toBeNull();
    expect(fmtPrecise(83.44)).toBe('01:23.4');
  });
});
