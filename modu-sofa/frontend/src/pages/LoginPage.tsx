import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { errorMessage } from '../api/client';
import { KakaoSymbol, LogoMark } from '../components/common/Icons';
import { useAuth } from '../hooks/useAuth';
import { isDevAuth } from '../lib/supabase';

export function LoginPage() {
  const token = useAuth((s) => s.token);
  const signIn = useAuth((s) => s.signInWithKakao);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/';

  if (token) return <Navigate to={from} replace />;

  return (
    <div style={{ minHeight: '100vh', padding: '48px 16px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <section
        aria-label="로그인"
        className="panel-card"
        style={{ width: '100%', maxWidth: 420, padding: '44px 32px 32px', display: 'flex', flexDirection: 'column', gap: 28 }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, textAlign: 'center' }}>
          <LogoMark width={34} height={28} />
          <h1 className="brand" style={{ fontSize: 24 }}>
            모두의 <b>소파</b>
          </h1>
          <p className="muted">녹음 파일을 올리면 화자별 대본과 요약을 만들어 드려요.</p>
        </div>

        <button
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              await signIn();
              if (isDevAuth) navigate(from, { replace: true });
            } catch (e) {
              setError(errorMessage(e, '카카오 로그인에 실패했어요. 다시 시도해 주세요.'));
              setBusy(false);
            }
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
            height: 52,
            border: 0,
            borderRadius: 12,
            background: '#FEE500',
            color: 'rgba(0, 0, 0, 0.85)',
            fontWeight: 600,
            fontSize: 15,
          }}
        >
          <KakaoSymbol />
          카카오 로그인
        </button>

        {error && (
          <p role="alert" className="small" style={{ color: 'var(--danger-ink)', textAlign: 'center' }}>
            {error}
          </p>
        )}

        <p className="xsmall muted" style={{ textAlign: 'center' }}>
          처음이면 카카오 계정으로 바로 가입돼요.
          <br />
          내 에피소드와 음성 파일은 나만 볼 수 있어요.
        </p>
        {isDevAuth && (
          <p className="xsmall" style={{ textAlign: 'center', color: 'var(--warn-badge-ink)' }}>
            개발 모드: Supabase 설정이 없어 개발용 계정으로 로그인해요.
          </p>
        )}
      </section>
    </div>
  );
}
