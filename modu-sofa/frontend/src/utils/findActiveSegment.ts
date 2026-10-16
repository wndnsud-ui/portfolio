/**
 * 현재 시각 이전에 시작한 마지막 Segment의 인덱스를 이진 탐색으로 찾는다.
 * 문장 사이 무음 구간에서도 다음 Segment가 시작하기 전까지 직전 Segment를 유지한다.
 * 첫 Segment 시작 전이면 -1.
 *
 * @param starts 오름차순 정렬된 start_time 배열
 */
export function findActiveSegment(starts: readonly number[], t: number): number {
  let lo = 0;
  let hi = starts.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (starts[mid] <= t + 1e-3) {
      ans = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return ans;
}
