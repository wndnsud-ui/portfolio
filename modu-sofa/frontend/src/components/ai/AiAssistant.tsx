import { useState } from 'react';
import { useEpisodeStore } from '../../store/episodeStore';
import { usePlayerStore } from '../../store/playerStore';
import { IconSparkle } from '../common/Icons';
import { ChapterList } from './ChapterList';
import { HighlightCard } from './HighlightCard';
import { SummaryCard } from './SummaryCard';
import { TitleSuggestions } from './TitleSuggestions';

type Tab = 'summary' | 'titles' | 'chapters' | 'highlights';
const TABS: [Tab, string][] = [
  ['summary', '요약'],
  ['titles', '제목 추천'],
  ['chapters', '챕터'],
  ['highlights', '하이라이트'],
];

export function AiAssistant() {
  const ai = useEpisodeStore((s) => s.ai);
  const episode = useEpisodeStore((s) => s.episode);
  const runAi = useEpisodeStore((s) => s.runAi);
  const cancelAi = useEpisodeStore((s) => s.cancelAi);
  const selectTitle = useEpisodeStore((s) => s.selectTitle);
  const seek = usePlayerStore((s) => s.seek);
  const [tab, setTab] = useState<Tab>('summary');

  const status = episode?.ai_status ?? ai?.ai_status ?? 'none';
  const hasResult = !!ai?.summary;

  return (
    <aside className="card ai-panel" aria-label="AI 어시스턴트">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <IconSparkle stroke="#5B3FE0" />
        <h2 style={{ fontSize: 17, fontWeight: 700 }}>AI Assistant</h2>
      </div>

      {status === 'failed' && (
        <div role="alert" className="alert alert-warn" style={{ gap: 10, padding: 16 }}>
          <span className="alert-title">AI 분석에 실패했어요</span>
          <span className="alert-body">대본과 재생은 그대로 쓸 수 있어요. 요약 · 제목 추천 · 챕터 · 하이라이트만 다시 만들면 돼요.</span>
          {ai?.error_message && <span className="xsmall" style={{ color: 'var(--warn-ink-2)' }}>사유: {ai.error_message}</span>}
          <button type="button" className="btn btn-primary" style={{ alignSelf: 'flex-start', height: 40 }} onClick={() => void runAi()}>
            AI 분석 다시 실행
          </button>
        </div>
      )}

      {status === 'running' && (
        <div role="status" style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 16, borderRadius: 12, background: 'var(--primary-softer)' }}>
          <span style={{ fontWeight: 600, color: 'var(--primary-deep)' }}>{hasResult ? 'AI가 다시 분석하고 있어요' : 'AI가 분석하고 있어요'}</span>
          <span className="progress thin indeterminate" style={{ background: 'var(--primary-ring)' }}>
            <span />
          </span>
          <span className="small" style={{ color: 'var(--ink-3)' }}>
            고친 문장을 기준으로 요약해요. 삭제한 문장은 빼고 분석해요.
          </span>
          <button type="button" className="btn btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => void cancelAi()}>
            분석 취소
          </button>
        </div>
      )}

      {status === 'none' && !hasResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 16, borderRadius: 12, background: 'var(--primary-softer)' }}>
          <span style={{ fontWeight: 600 }}>아직 AI 분석 결과가 없어요</span>
          <span className="small muted">요약 · 제목 추천 · 챕터 · 하이라이트를 만들어요.</span>
          <button type="button" className="btn btn-primary" style={{ alignSelf: 'flex-start', height: 40 }} onClick={() => void runAi()}>
            AI 분석 실행
          </button>
        </div>
      )}

      {hasResult && ai && status !== 'running' && (
        <>
          <div role="tablist" aria-label="AI 결과" className="pills">
            {TABS.map(([k, label]) => (
              <button key={k} type="button" role="tab" className="pill-tab" aria-selected={tab === k} onClick={() => setTab(k)}>
                {label}
              </button>
            ))}
          </div>
          <div role="tabpanel">
            {tab === 'summary' && <SummaryCard ai={ai} onRerun={() => void runAi()} busy={false} />}
            {tab === 'titles' && (
              <TitleSuggestions candidates={ai.title_candidates} current={episode?.title ?? null} onPick={(t) => void selectTitle(t)} />
            )}
            {tab === 'chapters' && <ChapterList chapters={ai.chapters} onSeek={(t) => seek(t)} />}
            {tab === 'highlights' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <p className="small muted">AI가 중요한 발언 구간을 골랐어요. 인용문은 실제 문장 그대로예요.</p>
                {ai.highlights.length ? (
                  ai.highlights.map((h) => <HighlightCard key={h.id} highlight={h} />)
                ) : (
                  <p className="small muted">하이라이트가 없어요.</p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
