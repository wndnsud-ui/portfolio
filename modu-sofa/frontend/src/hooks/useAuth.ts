import { create } from 'zustand';
import { isDevAuth, supabase } from '../lib/supabase';

const DEV_KEY = 'modu-sofa.dev-session';

interface AuthState {
  ready: boolean;
  token: string | null;
  nickname: string | null;
  init: () => Promise<void>;
  signInWithKakao: () => Promise<void>;
  signOut: () => Promise<void>;
}

let initialized = false;

export const useAuth = create<AuthState>((set) => ({
  ready: false,
  token: null,
  nickname: null,

  init: async () => {
    if (initialized) return;
    initialized = true;
    if (isDevAuth || !supabase) {
      let nickname: string | null = null;
      try {
        nickname = localStorage.getItem(DEV_KEY);
      } catch {
        /* 저장소 접근 불가 */
      }
      set({ ready: true, nickname, token: nickname ? `dev:${encodeURIComponent(nickname)}` : null });
      return;
    }
    const { data } = await supabase.auth.getSession();
    const apply = (session: typeof data.session) => {
      const meta = (session?.user?.user_metadata ?? {}) as Record<string, string | undefined>;
      set({
        ready: true,
        token: session?.access_token ?? null,
        // 화면에 표시할 이름은 카카오 닉네임
        nickname: meta.name ?? meta.full_name ?? meta.nickname ?? meta.preferred_username ?? null,
      });
    };
    apply(data.session);
    supabase.auth.onAuthStateChange((_e, session) => apply(session));
  },

  signInWithKakao: async () => {
    if (isDevAuth || !supabase) {
      const nickname = '개발자';
      try {
        localStorage.setItem(DEV_KEY, nickname);
      } catch {
        /* 무시 */
      }
      set({ nickname, token: `dev:${encodeURIComponent(nickname)}` });
      return;
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'kakao',
      options: { redirectTo: `${window.location.origin}/` },
    });
    if (error) throw error;
  },

  signOut: async () => {
    if (supabase) await supabase.auth.signOut();
    try {
      localStorage.removeItem(DEV_KEY);
    } catch {
      /* 무시 */
    }
    set({ token: null, nickname: null });
  },
}));

export const getToken = () => useAuth.getState().token;
