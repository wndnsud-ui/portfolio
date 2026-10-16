import { create } from 'zustand';
import type { Range } from '../utils/editOps';
import { useEpisodeStore } from './episodeStore';

const MAX_HISTORY = 50;

interface EditState {
  /** 편집 모드 */
  active: boolean;
  /** 현재 선택 구간 (파형 드래그 또는 문장 클릭) */
  selection: Range | null;
  undoStack: Range[][];
  redoStack: Range[][];
  zoom: number; // 초당 픽셀, 0 = 화면에 맞춤
  setActive: (v: boolean) => void;
  setSelection: (r: Range | null) => void;
  setZoom: (z: number) => void;
  /** 잘린 구간을 바꾸고 되돌리기 기록에 남긴다 */
  apply: (next: Range[]) => void;
  undo: () => void;
  redo: () => void;
  reset: () => void;
}

const save = (cuts: Range[]) => void useEpisodeStore.getState().saveCuts(cuts);
const same = (a: Range[], b: Range[]) =>
  a.length === b.length && a.every((r, i) => r.start_time === b[i].start_time && r.end_time === b[i].end_time);

export const useEditStore = create<EditState>((set, get) => ({
  active: false,
  selection: null,
  undoStack: [],
  redoStack: [],
  zoom: 0,
  setActive: (v) => set({ active: v, selection: v ? get().selection : null }),
  setSelection: (r) => set({ selection: r && r.end_time - r.start_time >= 0.05 ? r : null }),
  setZoom: (z) => set({ zoom: z }),

  apply: (next) => {
    const cur = useEpisodeStore.getState().cuts;
    if (same(cur, next)) return;
    set({ undoStack: [...get().undoStack, cur].slice(-MAX_HISTORY), redoStack: [] });
    save(next);
  },
  undo: () => {
    const { undoStack, redoStack } = get();
    const prev = undoStack[undoStack.length - 1];
    if (!prev) return;
    set({ undoStack: undoStack.slice(0, -1), redoStack: [...redoStack, useEpisodeStore.getState().cuts] });
    save(prev);
  },
  redo: () => {
    const { undoStack, redoStack } = get();
    const next = redoStack[redoStack.length - 1];
    if (!next) return;
    set({ redoStack: redoStack.slice(0, -1), undoStack: [...undoStack, useEpisodeStore.getState().cuts] });
    save(next);
  },
  reset: () => set({ active: false, selection: null, undoStack: [], redoStack: [], zoom: 0 }),
}));
