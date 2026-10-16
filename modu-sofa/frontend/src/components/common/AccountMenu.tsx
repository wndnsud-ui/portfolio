import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { initials } from '../../utils/format';

export function AccountMenu({ size = 44 }: { size?: number }) {
  const nickname = useAuth((s) => s.nickname);
  const signOut = useAuth((s) => s.signOut);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  return (
    <div className="menu-wrap" ref={ref}>
      <button
        type="button"
        className="avatar-btn"
        style={{ width: size, height: size }}
        aria-label="계정"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
      >
        {initials(nickname)}
      </button>
      {open && (
        <div className="menu" role="menu">
          <div className="menu-head">{nickname ?? '내 계정'}</div>
          <button
            type="button"
            role="menuitem"
            onClick={async () => {
              await signOut();
              navigate('/login', { replace: true });
            }}
          >
            로그아웃
          </button>
        </div>
      )}
    </div>
  );
}
