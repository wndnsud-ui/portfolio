import { useToast } from './toastStore';

export function Toasts() {
  const items = useToast((s) => s.items);
  const dismiss = useToast((s) => s.dismiss);
  return (
    <div className="toasts" role="status" aria-live="polite">
      {items.map((t) => (
        <div key={t.id} className={`toast ${t.tone}`}>
          <span style={{ flex: 1 }}>{t.message}</span>
          <button type="button" aria-label="알림 닫기" onClick={() => dismiss(t.id)}>
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
