/** 편집 연산. 잘라낼 구간(cuts)은 항상 정렬 · 병합된 상태로 유지한다. 시간 단위는 초. */

export interface Range {
  start_time: number;
  end_time: number;
}

const MIN = 0.05;
const r3 = (n: number) => Math.round(n * 1000) / 1000;

export function normalize(ranges: Range[], duration: number): Range[] {
  const cleaned = ranges
    .map((r) => ({
      start_time: r3(Math.max(0, Math.min(r.start_time, r.end_time))),
      end_time: r3(Math.min(duration, Math.max(r.start_time, r.end_time))),
    }))
    .filter((r) => r.end_time - r.start_time >= MIN)
    .sort((a, b) => a.start_time - b.start_time);
  const out: Range[] = [];
  for (const r of cleaned) {
    const last = out[out.length - 1];
    if (last && r.start_time <= last.end_time + 0.01) last.end_time = Math.max(last.end_time, r.end_time);
    else out.push({ ...r });
  }
  return out;
}

/** 선택 구간 삭제 */
export function cutSelection(cuts: Range[], sel: Range, duration: number): Range[] {
  return normalize([...cuts, sel], duration);
}

/** 선택 구간만 살리기: 선택 밖을 모두 잘라낸다 (선택 안에 이미 잘린 구간은 그대로) */
export function keepOnly(cuts: Range[], sel: Range, duration: number): Range[] {
  return normalize(
    [...cuts, { start_time: 0, end_time: sel.start_time }, { start_time: sel.end_time, end_time: duration }],
    duration,
  );
}

/** 선택 구간 되살리기: 잘린 구간에서 선택 부분을 뺀다 */
export function restoreSelection(cuts: Range[], sel: Range, duration: number): Range[] {
  const out: Range[] = [];
  for (const c of cuts) {
    if (c.end_time <= sel.start_time || c.start_time >= sel.end_time) {
      out.push(c);
      continue;
    }
    if (c.start_time < sel.start_time) out.push({ start_time: c.start_time, end_time: sel.start_time });
    if (c.end_time > sel.end_time) out.push({ start_time: sel.end_time, end_time: c.end_time });
  }
  return normalize(out, duration);
}

/** 선택 구간을 문장 경계에 맞춘다: 시작은 그 시각이 속한 문장의 시작, 끝은 그 시각이 속한 문장의 끝 */
export function snapToSegments(sel: Range, segments: Range[]): Range {
  if (!segments.length) return sel;
  const startSeg =
    [...segments].reverse().find((s) => s.start_time <= sel.start_time + 0.01) ?? segments[0];
  const endSeg = segments.find((s) => s.end_time >= sel.end_time - 0.01) ?? segments[segments.length - 1];
  const start_time = startSeg.start_time;
  const end_time = Math.max(endSeg.end_time, start_time + MIN);
  return { start_time, end_time };
}

export const totalLength = (ranges: Range[]) => ranges.reduce((a, r) => a + (r.end_time - r.start_time), 0);

/** "mm:ss.s" / "h:mm:ss.s" / "초" → 초. 잘못된 입력이면 null */
export function parseTime(text: string): number | null {
  const t = text.trim();
  if (!t) return null;
  const parts = t.split(':').map((p) => p.trim());
  if (parts.some((p) => !/^\d+(\.\d+)?$/.test(p)) || parts.length > 3) return null;
  return parts.reduce((acc, p) => acc * 60 + Number(p), 0);
}

/** 초 → "mm:ss.s" */
export function fmtPrecise(sec: number): string {
  const s = Math.max(0, sec);
  const m = Math.floor(s / 60);
  const rest = s - m * 60;
  return `${String(m).padStart(2, '0')}:${rest.toFixed(1).padStart(4, '0')}`;
}
