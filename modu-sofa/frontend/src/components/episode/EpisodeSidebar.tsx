import { useEffect, useMemo } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useEpisodeStore } from '../../store/episodeStore';
import { displayTitle, episodeHref, episodeNumbers, epLabel } from '../../utils/episodeStatus';
import { fmtDate, fmtTime } from '../../utils/format';
import { IconFolder, IconHome, IconPlus, IconUpload, LogoMark } from '../common/Icons';

export function EpisodeSidebar({ activeId, showRecent = false }: { activeId?: string; showRecent?: boolean }) {
  const episodes = useEpisodeStore((s) => s.episodes);
  const listLoaded = useEpisodeStore((s) => s.listLoaded);
  const loadList = useEpisodeStore((s) => s.loadList);

  useEffect(() => {
    if (showRecent && !listLoaded) void loadList();
  }, [showRecent, listLoaded, loadList]);

  const numbers = useMemo(() => episodeNumbers(episodes), [episodes]);
  const recent = episodes.slice(0, 6);

  return (
    <nav className="sidebar" aria-label="메인 메뉴">
      <Link to="/" className="sidebar-logo">
        <LogoMark />
        <span className="brand">
          모두의 <b>소파</b>
        </span>
        <span className="beta">Beta</span>
      </Link>

      <div className="nav-list">
        <Link to="/" className="nav-item">
          <IconHome />홈
        </Link>
        <NavLink
          to="/"
          end
          className={({ isActive }) => `nav-item${isActive || activeId ? ' active' : ''}`}
          aria-current={activeId ? 'page' : undefined}
        >
          <IconFolder />
          프로젝트
        </NavLink>
        <NavLink to="/upload" className="nav-item">
          <IconUpload />
          파일 업로드
        </NavLink>
      </div>

      {showRecent && (
        <div className="recent">
          <div className="recent-head">
            <span>최근 프로젝트</span>
            <Link to="/upload" aria-label="새 에피소드" className="icon-btn icon-btn-sm" style={{ width: 28, height: 28 }}>
              <IconPlus />
            </Link>
          </div>
          {recent.map((ep) => {
            const n = numbers.get(ep.id);
            const on = ep.id === activeId;
            return (
              <Link
                key={ep.id}
                to={episodeHref(ep)}
                className={`recent-item${on ? ' active' : ''}`}
                aria-current={on ? 'page' : undefined}
              >
                <span className="recent-thumb" aria-hidden="true">
                  {n ? String(n).padStart(2, '0') : '–'}
                </span>
                <span style={{ minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                  <span className="recent-title">
                    {n ? `${epLabel(n)} ` : ''}
                    {displayTitle(ep)}
                  </span>
                  <span className="xsmall muted">
                    {fmtTime(ep.duration)} · {fmtDate(ep.created_at)}
                  </span>
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
}
