import { useEffect, useRef } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js';
import { useEditStore } from '../../store/editStore';
import { usePlayerStore } from '../../store/playerStore';
import type { Chapter } from '../../types/ai';
import type { Cut } from '../../types/edit';
import type { PeaksDoc } from '../../types/episode';

interface Props {
  peaks: PeaksDoc | null;
  duration: number;
  chapters: Chapter[];
  cuts: Cut[];
  /** 잘린 구간 가장자리를 끌어 조정했을 때 */
  onCutsChange: (cuts: Cut[]) => void;
}

const CUT_COLOR = 'rgba(185, 28, 28, 0.18)';
const CUT_COLOR_EDIT = 'rgba(185, 28, 28, 0.3)';
const SEL_COLOR = 'rgba(37, 99, 235, 0.25)';
const SEL_ID = 'selection';
const DRAG_ID = 'drag';

/**
 * 서버 peaks를 그리는 파형. 브라우저에서 전체 오디오를 디코딩하지 않는다.
 * media 옵션으로 단일 <audio> 요소에 연결되어, 파형 클릭도 같은 요소를 seek한다.
 * 편집 모드: 드래그 = 구간 선택(파란색), 잘린 구간(빨간색)은 가장자리를 끌어 조정.
 */
export function Waveform({ peaks, duration, chapters, cuts, onCutsChange }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const audio = usePlayerStore((s) => s.audio);
  const editMode = useEditStore((s) => s.active);
  const selection = useEditStore((s) => s.selection);
  const zoom = useEditStore((s) => s.zoom);
  const wsRef = useRef<WaveSurfer | null>(null);
  const regionsRef = useRef<RegionsPlugin | null>(null);
  const rebuilding = useRef(false);
  const onCuts = useRef(onCutsChange);
  onCuts.current = onCutsChange;

  useEffect(() => {
    if (!container.current || !audio || !peaks || !duration) return;
    const ws = WaveSurfer.create({
      container: container.current,
      media: audio,
      peaks: [peaks.data],
      duration,
      height: 56,
      waveColor: '#CBC7DE',
      progressColor: '#5B3FE0',
      cursorColor: '#2E1A99',
      cursorWidth: 2,
      barWidth: 2,
      barGap: 2,
      barRadius: 2,
      normalize: true,
      interact: true,
      autoScroll: true,
      autoCenter: false,
    });
    const regions = ws.registerPlugin(RegionsPlugin.create());
    wsRef.current = ws;
    regionsRef.current = regions;

    regions.on('region-created', (r) => {
      if (rebuilding.current || r.id !== DRAG_ID) return;
      // 드래그가 끝나면 그 영역을 새 선택 구간으로 바꾼다 (선택 영역은 아래 effect가 다시 그린다)
      const sel = { start_time: r.start, end_time: r.end };
      r.remove();
      useEditStore.getState().setSelection(sel);
    });
    regions.on('region-updated', (r) => {
      if (rebuilding.current) return;
      if (r.id === SEL_ID) {
        useEditStore.getState().setSelection({ start_time: r.start, end_time: r.end });
        return;
      }
      const list = regions
        .getRegions()
        .filter((x) => x.id.startsWith('cut-'))
        .map((x) => ({ start_time: x.start, end_time: x.end }));
      onCuts.current(list);
    });
    ws.on('interaction', () => usePlayerStore.getState()._sync({ stopAt: null }));
    return () => {
      wsRef.current = null;
      regionsRef.current = null;
      ws.destroy();
    };
  }, [audio, peaks, duration]);

  // 잘린 구간 + 선택 구간 그리기
  useEffect(() => {
    const regions = regionsRef.current;
    if (!regions) return;
    rebuilding.current = true;
    regions.clearRegions();
    cuts.forEach((c, i) =>
      regions.addRegion({
        id: `cut-${i}`,
        start: c.start_time,
        end: c.end_time,
        color: editMode ? CUT_COLOR_EDIT : CUT_COLOR,
        drag: false,
        resize: editMode,
      }),
    );
    if (editMode && selection) {
      regions.addRegion({
        id: SEL_ID,
        start: selection.start_time,
        end: selection.end_time,
        color: SEL_COLOR,
        drag: true,
        resize: true,
      });
    }
    rebuilding.current = false;
  }, [cuts, editMode, selection, peaks, audio, duration]);

  // 편집 모드에서만 드래그 선택
  useEffect(() => {
    const regions = regionsRef.current;
    if (!regions || !editMode) return;
    return regions.enableDragSelection({ id: DRAG_ID, color: SEL_COLOR });
  }, [editMode, peaks, audio, duration]);

  // 확대 (0 = 화면에 맞춤)
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws) return;
    try {
      ws.zoom(editMode ? zoom : 0);
    } catch {
      /* 아직 그려지기 전 */
    }
  }, [zoom, editMode, peaks, audio, duration]);

  const seek = usePlayerStore((s) => s.seek);
  const zoomed = editMode && zoom > 0;

  return (
    <div className="wave-wrap">
      {!zoomed && (
        <div className="chapter-marks">
          {duration > 0 &&
            chapters.map((c, i) => (
              <button
                key={c.id}
                type="button"
                className="chapter-mark"
                style={{
                  left: `${Math.min(97, (c.start_time / duration) * 100)}%`,
                  // 다음 챕터 표시와 겹치지 않게 이름 폭을 제한
                  maxWidth: `calc(${(((chapters[i + 1]?.start_time ?? duration) - c.start_time) / duration) * 100}% - 4px)`,
                }}
                onClick={() => seek(c.start_time)}
                title={c.title}
              >
                <span>{c.title}</span>
              </button>
            ))}
        </div>
      )}
      {peaks ? (
        <div ref={container} className={`wave${editMode ? ' cut-mode' : ''}`} aria-hidden="true" />
      ) : (
        <div className="wave-empty">파형을 불러오는 중…</div>
      )}
    </div>
  );
}
