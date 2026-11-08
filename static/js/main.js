// 모바일 메뉴 (폭 760px 이하)
const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('.site-nav');
if (toggle && nav) {
  const setOpen = (open) => {
    nav.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
  };
  toggle.addEventListener('click', () => setOpen(!nav.classList.contains('is-open')));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && nav.classList.contains('is-open')) { setOpen(false); toggle.focus(); }
  });
}

// 알림은 몇 초 뒤 사라진다
document.querySelectorAll('.toast').forEach((toast) => {
  setTimeout(() => toast.classList.add('is-leaving'), 3500);
  setTimeout(() => toast.remove(), 4000);
});

// 되돌릴 수 없는 동작은 페이지 안에서 한 번 더 묻는다 (버튼 글자가 「정말 삭제할까요?」로 바뀐다)
// 오래 걸리는 버튼: 누르면 글자를 바꾸고 두 번 눌리지 않게 막는다
document.querySelectorAll('[data-loading]').forEach((button) => {
  button.form?.addEventListener('submit', () => {
    setTimeout(() => { button.disabled = true; button.textContent = button.dataset.loading; });
  });
});

document.querySelectorAll('form[data-confirm]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    const button = event.submitter || form.querySelector('button[type="submit"]');
    if (form.dataset.armed === '1') return;
    event.preventDefault();
    form.dataset.armed = '1';
    if (button) {
      button.dataset.label = button.textContent;
      button.textContent = form.dataset.confirmLabel || '한 번 더 누르면 삭제돼요';
      button.classList.add('is-armed');
    }
    setTimeout(() => {
      form.dataset.armed = '';
      if (button && button.dataset.label) { button.textContent = button.dataset.label; button.classList.remove('is-armed'); }
    }, 4000);
  });
});

// 정렬을 바꾸면 바로 적용
document.querySelectorAll('select[data-autosubmit]').forEach((select) => {
  select.addEventListener('change', () => select.form.submit());
});

// 댓글 글자 수
document.querySelectorAll('textarea[data-counter]').forEach((area) => {
  const out = area.form.querySelector('[data-counter-out]');
  const update = () => { out.textContent = `${area.value.length} / ${area.maxLength}`; };
  area.addEventListener('input', update);
  update();
});

// 링크 복사
document.querySelectorAll('[data-copy-link]').forEach((button) => {
  button.addEventListener('click', async () => {
    const label = button.lastChild;
    try {
      await navigator.clipboard.writeText(window.location.href.split('#')[0]);
      label.textContent = '복사했어요';
    } catch (error) {
      label.textContent = '주소창에서 복사해 주세요';
    }
    setTimeout(() => { label.textContent = '링크 복사'; }, 2000);
  });
});

// 이력서: PDF로 저장 (인쇄 대화상자)
document.querySelectorAll('[data-print]').forEach((button) => button.addEventListener('click', () => window.print()));

// 홈 최근 기록: 분류 필터 (분류마다 최대 3개)
document.querySelectorAll('[data-recent]').forEach((panel) => {
  const rows = [...panel.querySelectorAll('.post-row')];
  const empty = panel.querySelector('.rows-empty');
  const apply = (type) => {
    let shown = 0;
    rows.forEach((row) => {
      const show = (!type || row.dataset.type === type) && shown < 3;
      row.hidden = !show;
      if (show) shown += 1;
    });
    if (empty) empty.hidden = shown > 0;
  };
  panel.querySelectorAll('[data-filter]').forEach((button) => {
    button.addEventListener('click', () => {
      panel.querySelectorAll('[data-filter]').forEach((b) => {
        b.classList.toggle('is-active', b === button);
        b.setAttribute('aria-pressed', String(b === button));
      });
      apply(button.dataset.filter);
    });
  });
  apply('');
});

// 목차: 지금 읽는 소제목 표시
const tocLinks = [...document.querySelectorAll('.toc a[href^="#"]')];
if (tocLinks.length && 'IntersectionObserver' in window) {
  const targets = tocLinks.map((a) => document.getElementById(decodeURIComponent(a.hash.slice(1)))).filter(Boolean);
  const mark = (id) => tocLinks.forEach((a) => a.classList.toggle('is-active', decodeURIComponent(a.hash.slice(1)) === id));
  const observer = new IntersectionObserver((entries) => {
    const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
    if (visible.length) mark(visible[0].target.id);
  }, { rootMargin: '-80px 0px -65% 0px' });
  targets.forEach((t) => observer.observe(t));
  if (targets[0]) mark(targets[0].id);
}

// 유튜브 미리보기: 누를 때만 플레이어를 넣는다 (페이지를 열 때는 썸네일만)
const modal = document.getElementById('video-modal');
if (modal) {
  const frame = modal.querySelector('[data-frame]');
  let opener = null;
  const close = () => {
    frame.replaceChildren();
    if (modal.open) modal.close();
    if (opener) opener.focus();
  };
  document.querySelectorAll('[data-video]').forEach((card) => {
    card.addEventListener('click', () => {
      opener = card;
      const iframe = document.createElement('iframe');
      iframe.src = `https://www.youtube-nocookie.com/embed/${card.dataset.video}?autoplay=1&rel=0`;
      iframe.title = card.dataset.title || '유튜브 영상';
      iframe.allow = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; web-share';
      iframe.referrerPolicy = 'strict-origin-when-cross-origin';
      iframe.allowFullscreen = true;
      frame.replaceChildren(iframe);
      modal.querySelector('[data-title]').textContent = card.dataset.title || '';
      modal.querySelector('[data-date]').textContent = card.dataset.date || '';
      modal.querySelector('[data-watch]').href = card.dataset.watch;
      modal.showModal();
    });
  });
  modal.querySelector('[data-close]').addEventListener('click', close);
  modal.addEventListener('click', (event) => { if (event.target === modal) close(); });
  modal.addEventListener('cancel', (event) => { event.preventDefault(); close(); });
}
