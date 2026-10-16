/** 초 → "mm:ss" (1시간 이상은 "h:mm:ss") */
export function fmtTime(sec: number | null | undefined): string {
  const s = Math.max(0, Math.floor(sec ?? 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(r).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** 초 → "42분 13초" */
export function fmtDurationKo(sec: number | null | undefined): string {
  const s = Math.max(0, Math.round(sec ?? 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}시간 ${m}분`;
  if (m > 0) return `${m}분 ${r}초`;
  return `${r}초`;
}

/** 서버 시각 파싱. SQLite는 시간대 없이 UTC를 보내므로 시간대가 없으면 UTC로 본다. */
export function parseServerDate(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
}

export function fmtDate(iso: string, sep = '.'): string {
  const d = parseServerDate(iso);
  const p = (n: number) => String(n).padStart(2, '0');
  return [d.getFullYear(), p(d.getMonth() + 1), p(d.getDate())].join(sep);
}

export function fmtRelative(iso: string): string {
  const diff = (Date.now() - parseServerDate(iso).getTime()) / 1000;
  if (diff < 120) return '방금 업로드';
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}일 전`;
  return fmtDate(iso);
}

export function fmtMB(bytes: number | null | undefined): string {
  return `${((bytes ?? 0) / 1024 / 1024).toFixed(1)}MB`;
}

export function initials(name: string | null | undefined): string {
  const n = (name ?? '').trim();
  if (!n) return '나';
  const parts = n.split(/\s+/);
  if (/^[A-Za-z]/.test(n)) {
    return (parts.length > 1 ? parts[0][0] + parts[1][0] : n.slice(0, 2)).toUpperCase();
  }
  return Array.from(n).slice(0, 2).join('');
}
