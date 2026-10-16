import { create } from 'zustand';

export interface ToastItem {
  id: number;
  message: string;
  tone: 'error' | 'info';
}

interface ToastState {
  items: ToastItem[];
  push: (message: string, tone?: ToastItem['tone']) => void;
  dismiss: (id: number) => void;
}

let seq = 0;

export const useToast = create<ToastState>((set, get) => ({
  items: [],
  push: (message, tone = 'error') => {
    const id = ++seq;
    set({ items: [...get().items, { id, message, tone }] });
    window.setTimeout(() => get().dismiss(id), 5000);
  },
  dismiss: (id) => set({ items: get().items.filter((t) => t.id !== id) }),
}));

export const toastError = (message: string) => useToast.getState().push(message, 'error');
