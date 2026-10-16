import type { AiResult } from '../../types/ai';

export function SummaryCard({ ai, onRerun, busy }: { ai: AiResult; onRerun: () => void; busy: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <p style={{ fontSize: 14, color: 'var(--ink-2)' }}>{ai.summary}</p>
      {ai.keywords.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }} aria-label="키워드">
          {ai.keywords.map((k) => (
            <span key={k} className="chip" style={{ fontSize: 13, padding: '4px 10px' }}>
              {k}
            </span>
          ))}
        </div>
      )}
      <button type="button" className="btn btn-sm" style={{ alignSelf: 'flex-start' }} onClick={onRerun} disabled={busy}>
        AI 분석 다시 실행
      </button>
      <p className="xsmall muted">고친 문장을 기준으로 분석하고, 삭제한 문장은 빼고 분석해요.</p>
    </div>
  );
}
