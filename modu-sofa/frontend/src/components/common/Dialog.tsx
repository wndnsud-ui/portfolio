import { useEffect, useId, useRef, type ReactNode } from 'react';

interface Props {
  title: string;
  description?: ReactNode;
  onClose: () => void;
  children?: ReactNode;
  actions: ReactNode;
  wide?: boolean;
}

/** 모달 대화상자. Esc로 닫고, 열릴 때 첫 버튼에 포커스, 닫히면 이전 포커스로 돌아간다. */
export function Dialog({ title, description, onClose, children, actions, wide = false }: Props) {
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLElement>('button, [href], input, select, textarea')?.focus();
    return () => prev?.focus?.();
  }, []);

  return (
    <div
      className="overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        className={`dialog${wide ? ' wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${id}-t`}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.stopPropagation();
            onClose();
          }
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <h2 id={`${id}-t`}>{title}</h2>
          {description && <p className="muted small">{description}</p>}
        </div>
        {children}
        <div className="dialog-actions">{actions}</div>
      </div>
    </div>
  );
}
