import { create } from 'zustand';
import { aiApi } from '../api/aiApi';
import { errorMessage } from '../api/client';
import { episodeApi } from '../api/episodeApi';
import { speakerApi } from '../api/speakerApi';
import { editApi } from '../api/editApi';
import { transcriptApi } from '../api/transcriptApi';
import { toastError } from '../components/common/toastStore';
import type { AiResult } from '../types/ai';
import type { Cut } from '../types/edit';
import type { Episode, EpisodeDetail } from '../types/episode';
import type { LastMerge, Speaker, SpeakersResponse } from '../types/speaker';
import type { Segment } from '../types/transcript';

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

interface EpisodeState {
  // 대시보드
  episodes: Episode[];
  listLoaded: boolean;
  loadList: () => Promise<void>;

  // 업로드 화면으로 넘길 파일 (대시보드 드롭존 → 업로드 화면)
  pendingFiles: File[];
  setPendingFiles: (files: File[]) => void;

  // 에디터
  episodeId: string | null;
  episode: EpisodeDetail | null;
  segments: Segment[];
  speakers: Speaker[];
  lastMerge: LastMerge | null;
  mergeCount: number;
  ai: AiResult | null;
  /** 잘라낼 구간 (비파괴, 내보낼 때 적용) */
  cuts: Cut[];
  loading: boolean;
  loadError: string | null;
  save: SaveState;

  load: (id: string) => Promise<void>;
  refreshEpisode: () => Promise<EpisodeDetail | null>;
  refreshAi: () => Promise<void>;

  updateSegment: (id: string, body: { edited_text?: string; speaker_id?: string }) => Promise<boolean>;
  revertSegment: (id: string) => Promise<void>;
  deleteSegment: (id: string) => Promise<void>;
  restoreSegment: (id: string) => Promise<void>;

  renameSpeaker: (id: string, name: string) => Promise<void>;
  mergeSpeakers: (fromId: string, intoId: string) => Promise<boolean>;
  undoMerge: () => Promise<void>;

  saveCuts: (cuts: Cut[]) => Promise<void>;
  renameEpisode: (title: string) => Promise<void>;
  selectTitle: (title: string) => Promise<void>;
  runAi: () => Promise<void>;
  cancelAi: () => Promise<void>;
}

export const useEpisodeStore = create<EpisodeState>((set, get) => {
  /** 편집 요청을 감싸 "자동 저장됨" 상태를 관리한다. */
  async function saving<T>(fn: () => Promise<T>): Promise<T | undefined> {
    set({ save: 'saving' });
    try {
      const r = await fn();
      set({ save: 'saved' });
      return r;
    } catch (e) {
      set({ save: 'error' });
      toastError(errorMessage(e, '저장하지 못했어요.'));
      return undefined;
    }
  }

  const replaceSegment = (seg: Segment) =>
    set({ segments: get().segments.map((s) => (s.id === seg.id ? seg : s)) });

  const applySpeakers = async (r: SpeakersResponse, reloadSegments = false) => {
    set({ speakers: r.speakers, lastMerge: r.last_merge });
    if (reloadSegments && get().episodeId) {
      const t = await transcriptApi.get(get().episodeId!);
      set({ segments: t.segments, mergeCount: t.merge_count });
    }
  };

  return {
    episodes: [],
    listLoaded: false,
    loadList: async () => {
      try {
        const episodes = await episodeApi.list();
        set({ episodes, listLoaded: true });
      } catch (e) {
        set({ listLoaded: true });
        toastError(errorMessage(e, '에피소드 목록을 불러오지 못했어요.'));
      }
    },

    pendingFiles: [],
    setPendingFiles: (files) => set({ pendingFiles: files }),

    episodeId: null,
    episode: null,
    segments: [],
    speakers: [],
    lastMerge: null,
    mergeCount: 0,
    ai: null,
    cuts: [],
    loading: false,
    loadError: null,
    save: 'idle',

    load: async (id) => {
      if (get().episodeId !== id) {
        set({ episodeId: id, episode: null, segments: [], speakers: [], ai: null, cuts: [], lastMerge: null, save: 'idle' });
      }
      set({ loading: true, loadError: null });
      try {
        const [episode, transcript, speakers, ai, cuts] = await Promise.all([
          episodeApi.get(id),
          transcriptApi.get(id),
          speakerApi.list(id),
          aiApi.get(id),
          editApi.cuts(id),
        ]);
        if (get().episodeId !== id) return;
        set({
          episode,
          segments: transcript.segments,
          speakers: speakers.speakers,
          lastMerge: speakers.last_merge,
          mergeCount: transcript.merge_count,
          ai,
          cuts,
          loading: false,
        });
      } catch (e) {
        set({ loading: false, loadError: errorMessage(e, '에피소드를 불러오지 못했어요.') });
      }
    },

    refreshEpisode: async () => {
      const id = get().episodeId;
      if (!id) return null;
      try {
        const episode = await episodeApi.get(id);
        if (get().episodeId === id) set({ episode });
        return episode;
      } catch {
        return null;
      }
    },

    refreshAi: async () => {
      const id = get().episodeId;
      if (!id) return;
      const ai = await aiApi.get(id);
      if (get().episodeId === id) set({ ai });
    },

    updateSegment: async (id, body) => {
      const seg = await saving(() => transcriptApi.update(id, body));
      if (seg) {
        replaceSegment(seg);
        if (body.speaker_id) {
          const r = await speakerApi.list(get().episodeId!);
          set({ speakers: r.speakers, lastMerge: r.last_merge });
        }
      }
      return !!seg;
    },
    revertSegment: async (id) => {
      const seg = await saving(() => transcriptApi.revert(id));
      if (seg) replaceSegment(seg);
    },
    deleteSegment: async (id) => {
      const seg = await saving(() => transcriptApi.remove(id));
      if (seg) replaceSegment(seg);
    },
    restoreSegment: async (id) => {
      const seg = await saving(() => transcriptApi.restore(id));
      if (seg) replaceSegment(seg);
    },

    renameSpeaker: async (id, name) => {
      const r = await saving(() => speakerApi.update(id, { display_name: name.trim() || null }));
      if (r) await applySpeakers(r);
    },
    mergeSpeakers: async (fromId, intoId) => {
      const id = get().episodeId!;
      const r = await saving(() => speakerApi.merge(id, fromId, intoId));
      if (r) await applySpeakers(r, true);
      return !!r;
    },
    undoMerge: async () => {
      const id = get().episodeId!;
      const r = await saving(() => speakerApi.undo(id));
      if (r) await applySpeakers(r, true);
    },

    saveCuts: async (cuts) => {
      const id = get().episodeId!;
      set({ cuts }); // 화면은 바로 반영
      const saved = await saving(() => editApi.saveCuts(id, cuts));
      if (saved) set({ cuts: saved });
    },
    renameEpisode: async (title) => {
      const id = get().episodeId!;
      const ep = await saving(() => episodeApi.update(id, { title: title.trim() || null }));
      if (ep && get().episode) set({ episode: { ...get().episode!, title: ep.title } });
    },
    selectTitle: async (title) => {
      const id = get().episodeId!;
      const ep = await saving(() => aiApi.selectTitle(id, title));
      if (ep && get().episode) set({ episode: { ...get().episode!, title: ep.title } });
    },
    cancelAi: async () => {
      const id = get().episodeId!;
      try {
        const r = await transcriptApi.cancel(id);
        if (get().episode) set({ episode: { ...get().episode!, ai_status: r.ai_status ?? 'none' } });
        await get().refreshAi();
      } catch (e) {
        toastError(errorMessage(e, '취소하지 못했어요.'));
      }
    },
    runAi: async () => {
      const id = get().episodeId!;
      try {
        await aiApi.analyze(id);
        set({ ai: { ...(get().ai as AiResult), ai_status: 'running', error_message: null } });
        if (get().episode) set({ episode: { ...get().episode!, ai_status: 'running' } });
      } catch (e) {
        toastError(errorMessage(e, 'AI 분석을 시작하지 못했어요.'));
      }
    },
  };
});
