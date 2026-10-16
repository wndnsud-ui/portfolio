import type { SVGProps } from 'react';

type P = SVGProps<SVGSVGElement> & { size?: number };

const stroke = (size: number, rest: SVGProps<SVGSVGElement>) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  ...rest,
});

export const IconHome = ({ size = 18, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" /></svg>
);
export const IconFolder = ({ size = 18, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /></svg>
);
export const IconUpload = ({ size = 18, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M12 16V4M7 9l5-5 5 5M4 20h16" /></svg>
);
export const IconPlus = ({ size = 16, ...p }: P) => (
  <svg {...stroke(size, { strokeWidth: 2.2, ...p })}><path d="M12 5v14M5 12h14" /></svg>
);
export const IconBack = ({ size = 18, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M15 5l-7 7 7 7" /></svg>
);
export const IconCheck = ({ size = 16, ...p }: P) => (
  <svg {...stroke(size, { strokeWidth: 2.6, ...p })}><path d="m5 12 5 5 9-10" /></svg>
);
export const IconX = ({ size = 14, ...p }: P) => (
  <svg {...stroke(size, { strokeWidth: 3, ...p })}><path d="M6 6l12 12M18 6 6 18" /></svg>
);
export const IconAlert = ({ size = 14, ...p }: P) => (
  <svg {...stroke(size, { strokeWidth: 3, ...p })}><path d="M12 7v6M12 17h.01" /></svg>
);
export const IconMusic = ({ size = 20, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M9 18V6l10-2v12" /><circle cx="6.5" cy="18" r="2.5" /><circle cx="16.5" cy="16" r="2.5" /></svg>
);
export const IconPencil = ({ size = 16, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M4 20h4L19 9l-4-4L4 16z" /><path d="m13.5 6.5 4 4" /></svg>
);
export const IconTrash = ({ size = 16, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></svg>
);
export const IconSearch = ({ size = 16, ...p }: P) => (
  <svg {...stroke(size, p)}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
);
export const IconSparkle = ({ size = 20, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M12 3l2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2z" /></svg>
);
export const IconRedo = ({ size = 16, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M20 12a8 8 0 1 1-2.3-5.7" /><path d="M20 4v4h-4" /></svg>
);
export const IconBack10 = ({ size = 22, ...p }: P) => (
  <svg {...stroke(size, p)}>
    <path d="M4 12a8 8 0 1 0 2.3-5.7" />
    <path d="M4 4v4h4" />
    <text x="12" y="15.5" fontSize="7" textAnchor="middle" fill="currentColor" stroke="none" fontFamily="sans-serif">10</text>
  </svg>
);
export const IconFwd10 = ({ size = 22, ...p }: P) => (
  <svg {...stroke(size, p)}>
    <path d="M20 12a8 8 0 1 1-2.3-5.7" />
    <path d="M20 4v4h-4" />
    <text x="12" y="15.5" fontSize="7" textAnchor="middle" fill="currentColor" stroke="none" fontFamily="sans-serif">10</text>
  </svg>
);
export const IconVolume = ({ size = 20, ...p }: P) => (
  <svg {...stroke(size, p)}><path d="M4 9v6h4l5 4V5L8 9z" /><path d="M16.5 8.5a5 5 0 0 1 0 7" /></svg>
);
export const IconPlayFill = ({ size = 12, color = '#3A23B8' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4v16l13-8z" fill={color} /></svg>
);
export const IconPlayBig = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" fill="#FFFFFF" /></svg>
);
export const IconPauseBig = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
    <rect x="6" y="5" width="4" height="14" rx="1" fill="#FFFFFF" />
    <rect x="14" y="5" width="4" height="14" rx="1" fill="#FFFFFF" />
  </svg>
);
export const LogoMark = ({ width = 26, height = 22 }: { width?: number; height?: number }) => (
  <svg width={width} height={height} viewBox="0 0 26 22" aria-hidden="true">
    <g stroke="#5B3FE0" strokeWidth="2.4" strokeLinecap="round">
      <line x1="2" y1="8" x2="2" y2="14" />
      <line x1="7" y1="4" x2="7" y2="18" />
      <line x1="12" y1="1" x2="12" y2="21" />
      <line x1="17" y1="5" x2="17" y2="17" />
      <line x1="22" y1="8" x2="22" y2="14" />
    </g>
  </svg>
);
export const KakaoSymbol = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
    <path
      d="M12 3.5c-5 0-9 3.1-9 7 0 2.5 1.7 4.7 4.2 6l-1 3.7c-.1.3.3.6.6.4l4.3-2.9c.3 0 .6.1.9.1 5 0 9-3.1 9-7s-4-7.3-9-7.3z"
      fill="#000000"
    />
  </svg>
);
export const IconScissors = ({ size = 16, ...p }: P) => (
  <svg {...stroke(size, p)}>
    <circle cx="6" cy="6" r="3" />
    <circle cx="6" cy="18" r="3" />
    <path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12" />
  </svg>
);
