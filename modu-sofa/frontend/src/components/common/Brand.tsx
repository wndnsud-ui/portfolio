import { LogoMark } from './Icons';

export function Brand({ size = 18, mark = false }: { size?: number; mark?: boolean }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      {mark && <LogoMark width={22} height={18} />}
      <span className="brand" style={{ fontSize: size }}>
        모두의 <b>소파</b>
      </span>
    </span>
  );
}
