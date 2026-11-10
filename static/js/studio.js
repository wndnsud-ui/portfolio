/* 글쓰기 스튜디오 — 보이는 그대로 쓰는 블록 편집, 디자인 즉시 반영, 자동 저장.
   가운데 캔버스는 공개 상세 화면과 같은 클래스(.post, .post-body, .b-*)를 써서 같은 모습으로 보인다. */
(() => {
  const form = document.getElementById('studio');
  if (!form) return;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const readJSON = (id) => JSON.parse(document.getElementById(id).textContent);

  const state = readJSON('studio-data');
  const books = readJSON('studio-books');
  const meta = readJSON('studio-meta');
  const kind = form.dataset.kind;
  const blockOrder = meta.blockTypes; // [[type, label], ...] 순서 유지
  meta.blockTypes = Object.fromEntries(blockOrder);
  const csrf = $('meta[name="csrf-token"]').content;
  const canvas = $('#canvas');
  const saveState = $('#save-state');
  const AUTOSAVE_MS = 3000;
  const localKey = () => `hy-studio:${kind}:${state.id || 'new'}`;

  state.blocks = Array.isArray(state.blocks) ? state.blocks : [];
  state.design = state.design || {};
  if (kind === 'reading' && !state.book) state.book = { id: null, title: '', rating: 0, status: 'reading' };

  let selected = -1;
  let dirty = false;
  let timer = null;
  let pending = null;

  // ------------------------------------------------------------ 경로로 읽고 쓰기 ('about.stats.0.value')
  const getPath = (path) => path.split('.').reduce((obj, key) => (obj == null ? undefined : obj[key]), state);
  const setPath = (path, value) => {
    const keys = path.split('.');
    let obj = state;
    keys.slice(0, -1).forEach((key, i) => {
      if (obj[key] == null) obj[key] = /^\d+$/.test(keys[i + 1]) ? [] : {};
      obj = obj[key];
    });
    obj[keys[keys.length - 1]] = value;
  };

  // ------------------------------------------------------------ DOM 도우미
  const h = (tag, attrs = {}, ...children) => {
    const el = document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => {
      if (value == null || value === false) return;
      if (key === 'class') el.className = value;
      else if (key.startsWith('on')) el.addEventListener(key.slice(2), value);
      else el.setAttribute(key, value === true ? '' : value);
    });
    children.flat().forEach((child) => child != null && el.append(child));
    return el;
  };

  let plainOnly = true;
  const makeEditable = (el) => {
    try {
      el.contentEditable = plainOnly ? 'plaintext-only' : 'true';
    } catch (error) {
      plainOnly = false;
      el.contentEditable = 'true';
    }
    if (!plainOnly) {
      el.addEventListener('paste', (event) => {
        event.preventDefault();
        document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
      });
    }
  };
  const readText = (el) => el.innerText.replace(/\n$/, '').replace(/ /g, ' ');

  const editable = (tag, cls, { path, value, onInput, placeholder, single = false, label }) => {
    const el = h(tag, { class: `${cls} editable`, 'data-placeholder': placeholder, role: 'textbox', 'aria-label': label || placeholder });
    makeEditable(el);
    el.textContent = path ? getPath(path) || '' : value || '';
    el.addEventListener('input', () => {
      const text = readText(el);
      if (!text) el.innerHTML = '';
      if (path) setPath(path, text);
      if (onInput) onInput(text);
      changed();
    });
    if (single) {
      el.addEventListener('keydown', (event) => event.key === 'Enter' && event.preventDefault());
    }
    return el;
  };

  const field = (path, placeholder, { type = 'text', label } = {}) => {
    const input = h('input', { class: 'inline-input', type, placeholder, 'aria-label': label || placeholder });
    input.value = getPath(path) || '';
    input.addEventListener('input', () => { setPath(path, input.value); changed(); });
    return input;
  };

  // ------------------------------------------------------------ 업로드
  async function upload(file, type = 'image') {
    const data = new FormData();
    data.append('file', file);
    data.append('type', type);
    showState('올리는 중…', 'busy');
    const response = await fetch(form.dataset.uploadUrl, { method: 'POST', headers: { 'X-CSRFToken': csrf }, body: data });
    const result = await response.json().catch(() => ({ ok: false, error: '업로드 응답을 읽지 못했습니다.' }));
    if (!result.ok) {
      showState(result.error || '업로드 실패', 'error');
      throw new Error(result.error);
    }
    showState('이미지를 올렸습니다', 'ok');
    return result.url;
  }

  // 이미지 칸: 끌어다 놓기 / 눌러서 선택 / 주소 붙여넣기
  const dropzone = (label, onUrl, { compact = false } = {}) => {
    const input = h('input', { type: 'file', accept: 'image/*', hidden: true });
    const zone = h('div', { class: `dropzone${compact ? ' compact' : ''}`, tabindex: 0, role: 'button', 'aria-label': label },
      h('strong', {}, label),
      h('small', {}, '끌어다 놓거나 눌러서 선택'),
      h('button', { type: 'button', class: 'linkish', onclick: (event) => {
        event.stopPropagation();
        const url = window.prompt('이미지 주소(https://…)');
        if (url) onUrl(url.trim());
      } }, '주소로 넣기'),
      input);
    const take = async (file) => {
      if (!file) return;
      zone.classList.add('is-busy');
      try { onUrl(await upload(file)); } catch (error) { zone.classList.remove('is-busy'); }
    };
    zone.addEventListener('click', () => input.click());
    zone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); input.click(); } });
    input.addEventListener('change', () => take(input.files[0]));
    zone.addEventListener('dragover', (event) => { event.preventDefault(); zone.classList.add('is-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('is-over'));
    zone.addEventListener('drop', (event) => { event.preventDefault(); zone.classList.remove('is-over'); take(event.dataTransfer.files[0]); });
    return zone;
  };

  const imageOrDrop = (url, label, onUrl, opts) => {
    if (!url) return dropzone(label, onUrl, opts);
    const wrap = h('div', { class: 'img-slot' },
      h('img', { src: url, alt: '' }),
      h('div', { class: 'img-slot-tools' },
        h('button', { type: 'button', onclick: () => onUrl('') }, '빼기')));
    return wrap;
  };

  // ------------------------------------------------------------ 커버 이미지
  const single = kind === 'about';
  const coverPath = kind === 'about' ? 'about.photo' : 'cover_image';
  const setCover = (url) => { setPath(coverPath, url); syncInputs(); render(); changed(); };
  const coverSlot = (opts) => imageOrDrop(getPath(coverPath), kind === 'about' ? '프로필 사진' : '커버 이미지 (21:9)', setCover, opts);

  // ------------------------------------------------------------ 블록
  const BLOCK_NEW = {
    paragraph: () => ({ type: 'paragraph', text: '' }),
    heading: () => ({ type: 'heading', text: '' }),
    image: () => ({ type: 'image', url: '', caption: '' }),
    image2: () => ({ type: 'image2', url: '', url2: '', caption: '' }),
    quote: () => ({ type: 'quote', text: '', cite: '' }),
    callout: () => ({ type: 'callout', text: '' }),
    divider: () => ({ type: 'divider' }),
    markdown: () => ({ type: 'markdown', text: '' }),
    youtube: () => ({ type: 'youtube', url: '', caption: '' }),
    instagram: () => ({ type: 'instagram', url: '', caption: '' }),
  };

  function insertBlock(type, at = selected >= 0 ? selected + 1 : state.blocks.length, focus = true) {
    state.blocks.splice(at, 0, BLOCK_NEW[type]());
    selected = at;
    render();
    changed();
    if (focus) focusBlock(at);
  }

  function focusBlock(index, atEnd = false) {
    const target = $(`.blk[data-index="${index}"] .embed-url, .blk[data-index="${index}"] .editable, .blk[data-index="${index}"] textarea`, canvas);
    if (!target) return;
    target.focus();
    if (atEnd && target.isContentEditable) {
      const range = document.createRange();
      range.selectNodeContents(target);
      range.collapse(false);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }
  }

  const caretAtEnd = (el) => {
    const selection = window.getSelection();
    if (!selection.rangeCount) return false;
    const range = selection.getRangeAt(0);
    const rest = range.cloneRange();
    rest.selectNodeContents(el);
    rest.setStart(range.endContainer, range.endOffset);
    return rest.toString().trim() === '';
  };

  // ------------------------------------------------------------ 꾸밀 수 있는 글 칸 (문단·인용·강조)
  const RICH = ['paragraph', 'quote', 'callout'];
  const escapeHtml = (text) => (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
  let activeRich = null;

  function richEditable(tag, cls, block, index, placeholder) {
    const el = h(tag, { class: `${cls} editable rich`, 'data-placeholder': placeholder, role: 'textbox', 'aria-multiline': 'true', 'aria-label': placeholder });
    el.contentEditable = 'true';
    el.innerHTML = block.rich || escapeHtml(block.text);
    const sync = () => {
      block.text = readText(el);
      block.rich = el.innerHTML;
      if (!block.text) { el.innerHTML = ''; block.rich = ''; }
      updateReadTime();
      changed();
    };
    el.addEventListener('input', sync);
    el.addEventListener('focus', () => { activeRich = el; updateToolbar(); });
    el.addEventListener('blur', () => { setTimeout(() => { if (document.activeElement !== el) { if (activeRich === el) activeRich = null; updateToolbar(); } }, 0); });
    el.addEventListener('paste', (event) => {
      event.preventDefault();
      document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
    });
    el.addEventListener('keydown', (event) => {
      if (event.isComposing) return;
      const mod = event.metaKey || event.ctrlKey;
      if (mod && ['b', 'i', 'u'].includes(event.key.toLowerCase())) {
        event.preventDefault();
        format({ b: 'bold', i: 'italic', u: 'underline' }[event.key.toLowerCase()]);
      } else if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (caretAtEnd(el)) insertBlock('paragraph', index + 1);
        else if (!document.execCommand('insertLineBreak')) document.execCommand('insertHTML', false, '<br>');
      } else if (event.key === 'Backspace' && !readText(el) && state.blocks.length > 1) {
        event.preventDefault();
        state.blocks.splice(index, 1);
        selected = Math.max(0, index - 1);
        render();
        changed();
        focusBlock(selected, true);
      }
    });
    return el;
  }

  function blockBody(block, index) {
    const textOf = (tag, cls, placeholder, single = false) => {
      const el = editable(tag, cls, { value: block.text, placeholder, single, onInput: (text) => {
        block.text = text;
        if (block.type === 'heading') renderToc();
        updateReadTime();
      } });
      el.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && (single || caretAtEnd(el))) {
          event.preventDefault();
          insertBlock('paragraph', index + 1);
        } else if (event.key === 'Backspace' && !block.text && state.blocks.length > 1) {
          event.preventDefault();
          state.blocks.splice(index, 1);
          selected = Math.max(0, index - 1);
          render();
          changed();
          focusBlock(selected, true);
        }
      });
      return el;
    };
    const al = block.align ? ` align-${block.align}` : '';
    switch (block.type) {
      case 'paragraph': return richEditable('p', `b-p${al}`, block, index, index === 0 && state.blocks.length === 1 ? '본문을 입력하세요. 위 도구로 사진·인용구를 넣고, 글자를 골라 꾸밀 수 있어요.' : '본문');
      case 'heading': return textOf('h2', `b-h${al}`, '소제목 — 목차에 자동으로 나와요', true);
      case 'callout': return h('div', { class: `b-callout${al}` }, richEditable('div', 'callout-text', block, index, '강조할 내용'));
      case 'quote': {
        const cite = editable('cite', '', { value: block.cite, placeholder: '출처 (선택)', single: true, onInput: (text) => { block.cite = text; } });
        return h('blockquote', { class: `b-quote${al}` }, richEditable('p', '', block, index, '인용문'), cite);
      }
      case 'divider': return h('hr', { class: 'b-hr' });
      case 'markdown': {
        const area = h('textarea', { class: 'md-input', rows: 6, placeholder: '마크다운 원문 (예전 글 이관용)', 'aria-label': '마크다운' });
        area.value = block.text || '';
        const fit = () => { area.style.height = 'auto'; area.style.height = `${area.scrollHeight + 2}px`; };
        area.addEventListener('input', () => { block.text = area.value; fit(); updateReadTime(); changed(); });
        requestAnimationFrame(fit);
        return h('div', { class: 'b-md is-editing' }, h('p', { class: 'md-label' }, '마크다운 · 공개 화면에서 서식이 적용됩니다'), area);
      }
      case 'image': {
        const caption = editable('figcaption', '', { value: block.caption, placeholder: '설명 (선택)', single: true, onInput: (text) => { block.caption = text; } });
        return h('figure', { class: 'b-img' }, imageOrDrop(block.url, '이미지', (url) => { block.url = url; render(); changed(); }), caption);
      }
      case 'image2': {
        const caption = editable('figcaption', '', { value: block.caption, placeholder: '설명 (선택)', single: true, onInput: (text) => { block.caption = text; } });
        return h('figure', { class: 'b-img2' },
          h('div', { class: 'b-img2-grid' },
            imageOrDrop(block.url, '왼쪽 이미지', (url) => { block.url = url; render(); changed(); }, { compact: true }),
            imageOrDrop(block.url2, '오른쪽 이미지', (url) => { block.url2 = url; render(); changed(); }, { compact: true })),
          caption);
      }
      case 'youtube':
      case 'instagram': {
        const isYt = block.type === 'youtube';
        const input = h('input', { class: 'inline-input embed-url', type: 'url', 'aria-label': isYt ? '유튜브 영상 주소' : '인스타그램 게시물 주소',
          placeholder: isYt ? '유튜브 영상 주소 붙여넣기 (youtube.com/watch?v=… · youtu.be/… · shorts)' : '인스타그램 게시물·릴스 주소 붙여넣기 (instagram.com/p/… · /reel/…)' });
        input.value = block.url || '';
        const preview = h('div', { class: 'embed-preview' });
        let shown = null;
        const paint = () => {
          const target = isYt ? youtubeId(block.url) : instagramPost(block.url);
          const key = target || (block.url ? '?' : '');
          if (key === shown) return;
          shown = key;
          if (!target) {
            preview.replaceChildren(h('p', { class: 'embed-empty' }, block.url ? '주소를 알아보지 못했어요. 영상/게시물 하나의 주소인지 확인해 주세요.' : (isYt ? '▶ 유튜브 영상이 여기에 보입니다' : '◎ 인스타그램 게시물이 여기에 보입니다')));
          } else if (isYt) {
            preview.replaceChildren(h('div', { class: 'embed-frame' }, h('iframe', { src: `https://www.youtube-nocookie.com/embed/${target}?rel=0`, title: '유튜브 미리보기', loading: 'lazy', allowfullscreen: true })));
          } else {
            preview.replaceChildren(h('iframe', { src: `${target}embed/`, title: '인스타그램 미리보기', loading: 'lazy', scrolling: 'no' }));
          }
        };
        input.addEventListener('input', () => { block.url = input.value.trim(); paint(); changed(); });
        paint();
        const caption = editable('figcaption', '', { value: block.caption, placeholder: '설명 (선택)', single: true, onInput: (text) => { block.caption = text; } });
        return h('figure', { class: `b-embed ${isYt ? 'b-youtube' : 'b-instagram'} is-editing` }, input, preview, caption);
      }
      default: return h('p', {}, '');
    }
  }

  // 서버(content.py)와 같은 규칙으로 주소를 알아본다
  function youtubeId(value) {
    const v = (value || '').trim();
    if (/^[A-Za-z0-9_-]{11}$/.test(v)) return v;
    const m = v.match(/(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|live\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
    return m ? m[1] : '';
  }
  function instagramPost(value) {
    const m = (value || '').trim().match(/^https?:\/\/(?:www\.)?instagram\.com\/(?:[A-Za-z0-9_.]+\/)?(p|reel|tv)\/([A-Za-z0-9_-]+)/);
    return m ? `https://www.instagram.com/${m[1]}/${m[2]}/` : '';
  }

  function moveBlock(index, delta) {
    const to = index + delta;
    if (to < 0 || to >= state.blocks.length) return;
    const [block] = state.blocks.splice(index, 1);
    state.blocks.splice(to, 0, block);
    selected = to;
    render();
    changed();
    $(`.blk[data-index="${to}"]`, canvas)?.focus();
  }

  function blockWrap(block, index) {
    const tools = h('div', { class: 'blk-tools', role: 'toolbar', 'aria-label': '블록 도구' },
      h('span', { class: 'blk-type' }, meta.blockTypes[block.type]),
      h('button', { type: 'button', title: '위로', 'aria-label': '위로', onclick: () => moveBlock(index, -1), disabled: index === 0 }, '↑'),
      h('button', { type: 'button', title: '아래로', 'aria-label': '아래로', onclick: () => moveBlock(index, 1), disabled: index === state.blocks.length - 1 }, '↓'),
      h('button', { type: 'button', class: 'danger', title: '삭제', 'aria-label': '블록 삭제', onclick: () => {
        state.blocks.splice(index, 1);
        selected = Math.min(index, state.blocks.length - 1);
        render();
        changed();
      } }, '삭제'));
    const wrap = h('div', { class: `blk blk-${block.type}${index === selected ? ' is-selected' : ''}`, 'data-index': index, tabindex: -1 },
      blockBody(block, index), tools);
    wrap.addEventListener('focusin', () => selectBlock(index));
    wrap.addEventListener('pointerdown', () => selectBlock(index));
    return wrap;
  }

  function selectBlock(index) {
    if (selected === index) return;
    selected = index;
    $$('.blk', canvas).forEach((el) => el.classList.toggle('is-selected', Number(el.dataset.index) === index));
    updateToolbar();
  }

  function addBlockMenu() {
    // 사진·인용구 등은 위 도구 막대에서 넣는다. 아래에는 이어 쓰기용 문단 추가만 둔다.
    return h('div', { class: 'add-wrap' },
      h('button', { type: 'button', class: 'add-chip', onclick: () => insertBlock('paragraph', state.blocks.length) }, '＋ 문단 추가'));
  }

  // ------------------------------------------------------------ 위 도구 막대 (네이버 블로그식)
  const bar = $('#editor-bar');
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const COLORS = [['기본', '--ink'], ['회색', '--muted'], ['버터', '--tint-butter-ink'], ['민트', '--tint-mint-ink'],
    ['하늘', '--tint-sky-ink'], ['핑크', '--tint-pink-ink'], ['라일락', '--tint-lilac-ink']];
  const ICONS = {
    image: '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="9" cy="10" r="1.6"/><path d="M21 16l-5-5-9 8"/>',
    image2: '<rect x="2.5" y="6" width="8.5" height="12" rx="2"/><rect x="13" y="6" width="8.5" height="12" rx="2"/>',
    youtube: '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10.2 9.2v5.6l4.8-2.8z"/>',
    instagram: '<rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17" cy="7" r=".6"/>',
    quote: '<path d="M6 17c-1.5-1-2-2.6-2-4.5C4 9.5 6 7 9 6.5M15 17c-1.5-1-2-2.6-2-4.5 0-3 2-5.5 5-6"/>',
    divider: '<path d="M4 12h16"/><path d="M8 7h8M8 17h8" opacity=".4"/>',
    heading: '<path d="M5 5v14M14 5v14M5 12h9M18 9l2-1v11"/>',
    callout: '<rect x="3.5" y="5" width="17" height="14" rx="3"/><path d="M8 10h8M8 14h5"/>',
    markdown: '<rect x="2.5" y="6" width="19" height="12" rx="2"/><path d="M6 15V9l2.5 3L11 9v6M15 9v6m-2-2 2 2 2-2"/>',
    notion: '<rect x="4" y="3.5" width="16" height="17" rx="3"/><path d="M9 16V8l6 8V8"/>',
  };
  const svg = (name) => {
    const wrap = document.createElement('span');
    wrap.className = 'tb-ico';
    wrap.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;
    return wrap;
  };
  const keep = (fn) => ({ onmousedown: (e) => e.preventDefault(), onclick: (e) => { e.preventDefault(); fn(); } });

  function format(command, value = null) {
    if (!activeRich) return;
    activeRich.focus();
    document.execCommand('styleWithCSS', false, false);
    document.execCommand(command, false, value);
    activeRich.dispatchEvent(new Event('input'));
    updateToolbar();
  }

  const photoInput = h('input', { type: 'file', accept: 'image/*', multiple: true, hidden: true });
  photoInput.addEventListener('change', async () => {
    let at = selected >= 0 ? selected + 1 : state.blocks.length;
    for (const file of photoInput.files) {
      try {
        const url = await upload(file);
        state.blocks.splice(at, 0, { type: 'image', url, caption: '' });
        selected = at; at += 1;
        render(); changed();
      } catch (error) { /* showState가 알렸다 */ }
    }
    photoInput.value = '';
  });

  function changeType(type) {
    const block = state.blocks[selected];
    if (!block || !['paragraph', 'heading', 'quote', 'callout'].includes(block.type) || block.type === type) return;
    block.type = type;
    if (type === 'heading') { block.text = (block.text || '').replace(/\n/g, ' '); delete block.rich; }
    render(); changed(); focusBlock(selected, true);
  }

  function setAlign(value) {
    const block = state.blocks[selected];
    if (!block || !['paragraph', 'heading', 'quote', 'callout'].includes(block.type)) return;
    if (value === 'left') delete block.align; else block.align = value;
    render(); changed(); focusBlock(selected, true);
  }

  let colorPop;
  let styleSelect;
  const fmtButtons = {};
  const alignButtons = {};

  function buildToolbar() {
    if (!bar) return;
    const insert = (type, label, action) => h('button', { type: 'button', class: 'tb-insert', 'data-insert-type': type, title: label, ...keep(action || (() => insertBlock(type))) }, svg(type), h('span', {}, label));
    const inserts = h('div', { class: 'tb-row tb-inserts' },
      insert('image', '사진', () => photoInput.click()),
      insert('image2', '사진 2장'),
      insert('youtube', '동영상'),
      insert('instagram', '인스타'),
      insert('quote', '인용구'),
      insert('divider', '구분선'),
      insert('heading', '소제목'),
      insert('callout', '강조'),
      insert('markdown', '마크다운'),
      form.dataset.notionPagesUrl ? insert('notion', '노션', openNotion) : null,
      photoInput);

    styleSelect = h('select', { class: 'tb-select', 'aria-label': '글 모양' },
      [['paragraph', '본문'], ['heading', '소제목'], ['quote', '인용구'], ['callout', '강조 상자']].map(([v, t]) => h('option', { value: v }, t)));
    styleSelect.addEventListener('change', () => changeType(styleSelect.value));
    const fmt = (command, label, text, cls) => {
      fmtButtons[command] = h('button', { type: 'button', class: `tb-btn ${cls || ''}`, title: label, 'aria-label': label, 'aria-pressed': 'false', ...keep(() => format(command)) }, text);
      return fmtButtons[command];
    };
    colorPop = h('div', { class: 'tb-pop', hidden: true, role: 'menu' },
      COLORS.map(([name, variable]) => h('button', { type: 'button', role: 'menuitem', title: name, 'aria-label': `글자색 ${name}`, style: `--sw:var(${variable})`,
        ...keep(() => { format('foreColor', css(variable)); colorPop.hidden = true; }) })));
    const colorBtn = h('button', { type: 'button', class: 'tb-btn tb-color', title: '글자색', 'aria-label': '글자색', 'aria-haspopup': 'menu',
      ...keep(() => { colorPop.hidden = !colorPop.hidden; }) }, h('span', {}, 'A'), h('i', { 'aria-hidden': 'true' }));
    const marker = h('button', { type: 'button', class: 'tb-btn tb-marker', title: '형광펜', 'aria-label': '형광펜',
      ...keep(() => format('hiliteColor', css('--marker'))) }, h('span', {}, '형광펜'));
    const unmark = h('button', { type: 'button', class: 'tb-btn', title: '꾸밈 지우기', 'aria-label': '꾸밈 지우기',
      ...keep(() => { format('removeFormat'); format('unlink'); }) }, 'Tx');
    const link = h('button', { type: 'button', class: 'tb-btn', title: '링크', 'aria-label': '링크',
      ...keep(() => {
        if (!activeRich) return;
        const url = window.prompt('링크 주소 (https://…)', 'https://');
        if (url && /^(https?:\/\/|mailto:)/.test(url.trim())) format('createLink', url.trim());
      }) }, '🔗');
    const align = (value, label, text) => {
      alignButtons[value] = h('button', { type: 'button', class: 'tb-btn', title: label, 'aria-label': label, 'aria-pressed': 'false', ...keep(() => setAlign(value)) }, text);
      return alignButtons[value];
    };
    const formats = h('div', { class: 'tb-row tb-formats' },
      styleSelect, h('span', { class: 'tb-sep' }),
      fmt('bold', '굵게 (⌘B)', 'B', 'is-b'), fmt('italic', '기울임 (⌘I)', 'I', 'is-i'), fmt('underline', '밑줄 (⌘U)', 'U', 'is-u'), fmt('strikeThrough', '취소선', 'S', 'is-s'),
      h('span', { class: 'tb-color-wrap' }, colorBtn, colorPop), marker, link, unmark,
      h('span', { class: 'tb-sep' }),
      align('left', '왼쪽 정렬', '⇤'), align('center', '가운데 정렬', '↔'), align('right', '오른쪽 정렬', '⇥'));
    bar.replaceChildren(inserts, formats);
    document.addEventListener('selectionchange', updateToolbar);
    document.addEventListener('click', (e) => { if (colorPop && !e.target.closest('.tb-color-wrap')) colorPop.hidden = true; });
  }

  // ------------------------------------------------------------ 노션에서 불러오기 (페이지를 골라 본문 블록으로 넣는다)
  let notionDlg = null;
  const notion = { pages: [], picked: new Set(), busy: '', error: '', url: '' };

  async function notionFetch(url) {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    const result = await response.json().catch(() => ({ ok: false, error: '응답을 읽지 못했어요.' }));
    if (!result.ok) throw new Error(result.error || '노션에서 가져오지 못했어요.');
    return result;
  }

  async function loadNotionPages(query) {
    notion.busy = '목록을 불러오는 중…'; notion.error = ''; notion.pages = []; notion.picked.clear(); paintNotion();
    try {
      notion.pages = (await notionFetch(`${form.dataset.notionPagesUrl}?${query}`)).pages;
    } catch (error) { notion.error = error.message; }
    notion.busy = ''; paintNotion();
  }

  function openNotion() {
    if (!notionDlg) {
      notionDlg = h('dialog', { class: 'notion-dlg', 'aria-label': '노션에서 불러오기' });
      notionDlg.addEventListener('click', (e) => { if (e.target === notionDlg) notionDlg.close(); });
      document.body.append(notionDlg);
    }
    const book = kind === 'reading' && state.book && books.find((b) => String(b.id) === String(state.book.id));
    paintNotion();
    notionDlg.showModal();
    if (book && book.notion && !notion.pages.length) loadNotionPages(`book_id=${book.id}`);
  }

  function paintNotion() {
    if (!notionDlg) return;
    const book = kind === 'reading' && state.book && books.find((b) => String(b.id) === String(state.book.id));
    const urlInput = h('input', { type: 'url', class: 'input', placeholder: '노션 페이지 주소 붙여 넣기', value: notion.url, 'aria-label': '노션 페이지 주소' });
    urlInput.addEventListener('input', () => { notion.url = urlInput.value; });
    urlInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); loadNotionPages(`url=${encodeURIComponent(notion.url)}`); } });
    const rows = notion.pages.map((page) => {
      const box = h('input', { type: 'checkbox', checked: notion.picked.has(page.id) });
      box.addEventListener('change', () => { box.checked ? notion.picked.add(page.id) : notion.picked.delete(page.id); paintNotion(); });
      return h('li', { style: `--depth:${page.depth}` }, h('label', {}, box, h('span', {}, page.depth === 0 ? `${page.title} (페이지 본문)` : page.title)));
    });
    const allBox = h('button', { type: 'button', class: 'btn btn-sub small', onclick: () => {
      const all = notion.picked.size === notion.pages.length;
      notion.picked = new Set(all ? [] : notion.pages.map((p) => p.id)); paintNotion();
    } }, notion.picked.size === notion.pages.length && notion.pages.length ? '모두 풀기' : '모두 고르기');
    notionDlg.replaceChildren(...[
      h('div', { class: 'pop-head' }, h('strong', {}, '노션에서 불러오기'),
        h('button', { type: 'button', class: 'icon-btn', 'aria-label': '닫기', onclick: () => notionDlg.close() }, '✕')),
      h('p', { class: 'muted' }, book && book.notion
        ? `「${book.title}」 노션 페이지와 그 안의 하위 페이지예요. 불러올 페이지를 골라 주세요. 지금 글의 고른 문단 아래(없으면 맨 끝)에 들어가요.`
        : '노션 페이지 주소를 붙여 넣으면 그 페이지와 하위 페이지 목록이 나와요. 그 페이지에 만든 연결이 추가돼 있어야 해요.'),
      h('div', { class: 'row notion-url' }, urlInput,
        h('button', { type: 'button', class: 'btn btn-sub small', onclick: () => loadNotionPages(`url=${encodeURIComponent(notion.url)}`) }, '목록 보기')),
      notion.error ? h('p', { class: 'notion-msg is-error', role: 'alert' }, notion.error) : null,
      notion.busy ? h('p', { class: 'notion-msg', role: 'status' }, notion.busy) : null,
      rows.length ? h('ul', { class: 'notion-list' }, rows) : null,
      h('div', { class: 'notion-foot' },
        rows.length ? allBox : h('span'),
        h('button', { type: 'button', class: 'btn btn-primary', disabled: !notion.picked.size || Boolean(notion.busy), onclick: importNotion },
          notion.picked.size ? `${notion.picked.size}개 불러오기` : '불러오기')),
    ].filter(Boolean));
  }

  async function importNotion() {
    const chosen = notion.pages.filter((p) => notion.picked.has(p.id));
    const added = [];
    const skipped = new Set();
    try {
      for (const [i, page] of chosen.entries()) {
        notion.busy = `불러오는 중… ${i + 1}/${chosen.length} 「${page.title}」`; notion.error = ''; paintNotion();
        const result = await notionFetch(`${form.dataset.notionBlocksUrl}?page=${page.id}`);
        if (chosen.length > 1 && page.depth > 0 && result.blocks.length) added.push({ type: 'heading', text: result.title || page.title });
        added.push(...result.blocks);
        result.skipped.forEach((k) => skipped.add(k));
        if (!(state.title || '').trim() && i === 0) state.title = result.title || page.title;
      }
    } catch (error) {
      notion.busy = ''; notion.error = error.message; paintNotion();
      if (!added.length) return;
    }
    const blank = state.blocks.every((b) => b.type === 'paragraph' && !(b.text || '').trim());
    if (blank) state.blocks = added;
    else state.blocks.splice(selected >= 0 ? selected + 1 : state.blocks.length, 0, ...added);
    notion.busy = '';
    notion.picked.clear();
    notionDlg.close();
    render();
    changed();
    toast(`노션에서 블록 ${added.length}개를 불러왔어요.${skipped.size ? ' 표·데이터베이스 같은 일부 블록은 빠졌어요.' : ''} 다듬은 뒤 발행해 주세요.`);
  }

  function toast(text) {
    const box = $('.toasts') || document.body.appendChild(h('div', { class: 'toasts', role: 'status', 'aria-live': 'polite' }));
    const item = h('p', { class: 'toast success' }, text);
    box.append(item);
    setTimeout(() => item.remove(), 5000);
  }

  function updateToolbar() {
    if (!bar || !styleSelect) return;
    const inRich = Boolean(activeRich && activeRich.contains(document.getSelection()?.anchorNode));
    Object.entries(fmtButtons).forEach(([command, button]) => {
      button.disabled = !activeRich;
      let on = false;
      try { on = inRich && document.queryCommandState(command); } catch (error) { on = false; }
      button.setAttribute('aria-pressed', String(on));
    });
    bar.classList.toggle('has-text', Boolean(activeRich));
    const block = state.blocks[selected];
    const textual = block && ['paragraph', 'heading', 'quote', 'callout'].includes(block.type);
    styleSelect.disabled = !textual;
    if (textual) styleSelect.value = block.type;
    Object.entries(alignButtons).forEach(([value, button]) => {
      button.disabled = !textual;
      button.setAttribute('aria-pressed', String(textual && (block.align || 'left') === value));
    });
  }

  // ------------------------------------------------------------ 종류별 칸
  const area = (path, placeholder, cls = '') => editable('p', cls, { path, placeholder });

  function projectFields() {
    return h('div', { class: 'info-cards editing' },
      h('div', { class: 'info-card' }, h('span', {}, '내 역할'), editable('strong', '', { path: 'project.role', placeholder: '서비스 기획, 데이터 구조 설계', single: true })),
      h('div', { class: 'info-card' }, h('span', {}, '기술'), h('strong', { class: 'mono', id: 'tech-chips' })),
      h('div', { class: 'info-card' }, h('span', {}, '기간'), editable('strong', '', { path: 'project.period', placeholder: '2026.06 – 2026.08', single: true })));
  }

  function projectCase() {
    const step = (no, tintName, title, ...body) => h('section', { class: 'case-step' },
      h('span', { class: `step-no tint-${tintName} mono` }, no), h('div', {}, h('h2', {}, title), ...body));
    return [
      area('project.description', '프로젝트를 한 문단으로 소개해 주세요 (목록·홈 카드에 보여요)', 'case-intro'),
      step('01', 'butter', '문제', area('project.problem', '어떤 불편이 있었나요?')),
      step('02', 'mint', '구조', area('project.action', '어떻게 정리하고 설계했나요?'),
        h('p', { class: 'field-hint' }, '진행 흐름 — 「→」로 나누면 칩으로 보여요'),
        area('project.process', 'Problem 정의 → 데이터 구조 → 매핑 검증', 'flow-input')),
      step('03', 'pink', '막힌 지점과 해결', h('div', { class: 'pair' },
        h('div', { class: 'pair-card tint-pink' }, h('span', {}, '막힌 지점'), area('project.trouble', '어디서 막혔나요?')),
        h('div', { class: 'pair-card tint-mint' }, h('span', {}, '이렇게 풀었어요'), area('project.solution', '어떻게 풀었나요?')))),
      step('04', 'sky', '결과', area('project.result', '무엇이 달라졌나요?')),
      h('div', { class: 'learned tint-butter' }, h('span', {}, '배운 점'), area('project.insight', '한 문장으로 남겨 주세요')),
      h('p', { class: 'field-hint' }, '아래 블록은 케이스 스터디 뒤에 이어서 보여요 (선택)'),
    ];
  }

  function stars() {
    const wrap = h('span', { class: 'stars editing', role: 'radiogroup', 'aria-label': '별점' });
    const paint = () => $$('button', wrap).forEach((b, i) => b.classList.toggle('on', i < Math.round(state.book.rating || 0)));
    for (let i = 1; i <= 5; i += 1) {
      wrap.append(h('button', { type: 'button', 'aria-label': `${i}점`, onclick: () => {
        state.book.rating = state.book.rating === i ? 0 : i;
        paint();
        changed();
      } }, '★'));
    }
    paint();
    return wrap;
  }

  // 카카오 책 검색: 고르면 제목·저자·출판사를 채우고, 표지는 우리 저장소로 복사한다
  const bookSearch = { query: '', results: [], busy: false, error: '' };

  async function runBookSearch() {
    if (!bookSearch.query.trim()) return;
    bookSearch.busy = true; bookSearch.error = ''; render();
    try {
      const response = await fetch(`${form.dataset.bookSearchUrl}?q=${encodeURIComponent(bookSearch.query)}`, { headers: { Accept: 'application/json' } });
      const result = await response.json().catch(() => ({ ok: false, error: '검색 응답을 읽지 못했습니다.' }));
      if (!result.ok) throw new Error(result.error || '검색 실패');
      bookSearch.results = result.results;
      if (!result.results.length) bookSearch.error = '검색 결과가 없습니다.';
    } catch (error) {
      bookSearch.results = []; bookSearch.error = error.message;
    }
    bookSearch.busy = false; render();
    const input = $('.book-search input'); if (input) input.focus();
  }

  async function pickBook(found) {
    Object.assign(state.book, { title: found.title, author: found.author, publisher: found.publisher });
    bookSearch.results = []; bookSearch.query = '';
    render(); changed();
    const urls = [found.cover, found.thumbnail].filter(Boolean);
    if (!urls.length) { showState('표지가 없는 책입니다', 'error'); return; }
    showState('표지를 가져오는 중…', 'busy');
    try {
      const response = await fetch(form.dataset.bookCoverUrl, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }, body: JSON.stringify({ urls }),
      });
      const result = await response.json().catch(() => ({ ok: false }));
      if (!result.ok) throw new Error(result.error || '표지 저장 실패');
      state.book.cover_image = result.url;
      showState('표지를 넣었습니다', 'ok');
    } catch (error) {
      showState(error.message, 'error');
    }
    render(); changed();
  }

  function bookSearchBox() {
    const input = h('input', { type: 'search', class: 'inline-input', placeholder: '카카오에서 책 검색 (제목·저자·ISBN)', value: bookSearch.query, 'aria-label': '책 검색' });
    input.addEventListener('input', () => { bookSearch.query = input.value; });
    input.addEventListener('keydown', (event) => { if (event.key === 'Enter') { event.preventDefault(); runBookSearch(); } });
    const results = bookSearch.results.map((b) => h('li', {},
      h('button', { type: 'button', onclick: () => pickBook(b) },
        b.thumbnail ? h('img', { src: b.thumbnail, alt: '', loading: 'lazy' }) : h('span', { class: 'no-cover' }),
        h('span', {}, h('strong', {}, b.title),
          h('small', {}, [b.author, b.translator && `${b.translator} 옮김`, b.publisher, b.year].filter(Boolean).join(' · '))))));
    return h('div', { class: 'book-search' },
      h('div', { class: 'row' }, input,
        h('button', { type: 'button', class: 'btn small', disabled: bookSearch.busy, onclick: runBookSearch }, bookSearch.busy ? '검색 중…' : '검색')),
      bookSearch.error ? h('p', { class: 'muted book-search-msg' }, bookSearch.error) : null,
      results.length ? h('ul', { class: 'book-results' }, results) : null);
  }

  function bookEditor() {
    const select = h('select', { class: 'inline-input', 'aria-label': '책 선택' },
      h('option', { value: '' }, '＋ 새 책 등록'),
      books.map((b) => h('option', { value: b.id, selected: String(b.id) === String(state.book.id) }, b.title)));
    select.addEventListener('change', () => {
      const found = books.find((b) => String(b.id) === select.value);
      state.book = found ? { ...found } : { id: null, title: '', author: '', publisher: '', genre: '', start_date: '', finish_date: '', rating: 0, cover_image: '', status: 'reading' };
      render();
      changed();
    });
    const status = h('select', { class: 'inline-input', 'aria-label': '읽기 상태' },
      meta.bookStatus.map(([value, label]) => h('option', { value, selected: (state.book.status || 'reading') === value }, label)));
    status.addEventListener('change', () => { state.book.status = status.value; changed(); });
    const row = (label, control) => h('div', {}, h('dt', {}, label), h('dd', {}, control));
    return [bookSearchBox(), h('div', { class: 'book-info tint-butter editing' },
      h('div', { class: 'book-cover small' }, imageOrDrop(state.book.cover_image, '표지', (url) => { state.book.cover_image = url; render(); changed(); }, { compact: true })),
      h('dl', { class: 'kv' },
        row('책', select),
        row('제목', field('book.title', '책 제목')),
        row('저자', field('book.author', '저자')),
        row('출판사', field('book.publisher', '출판사')),
        row('장르', field('book.genre', '소설')),
        row('기간', h('span', { class: 'row' }, field('book.start_date', '2026.10.01', { label: '읽기 시작' }), field('book.finish_date', '다 읽은 날', { label: '다 읽은 날' }))),
        row('상태', status),
        row('별점', stars())))];
  }

  // ------------------------------------------------------------ 소개: 경력·스킬 편집
  // 다시 그려도 펼친 카드와 입력 중인 칸이 유지되도록 기억해 둔다
  const openRows = new WeakSet();
  const emptyGroups = new Set(); // 아직 스킬이 없는 새 분류 (화면에만 있음)
  let focusKey = null;
  const rerender = (key = null) => { focusKey = key; render(); changed(); };
  const restoreFocus = () => {
    if (!focusKey) return;
    const el = $(`[data-focus-key="${focusKey}"]`, canvas);
    focusKey = null;
    if (el) el.focus();
  };

  const labeled = (label, control) => h('label', { class: 'f-row' }, h('span', {}, label), control);
  const textField = (path, placeholder, { multiline = false } = {}) => {
    const input = multiline
      ? h('textarea', { class: 'inline-input', rows: 2, placeholder })
      : h('input', { class: 'inline-input', type: 'text', placeholder });
    input.value = getPath(path) || '';
    const grow = () => { if (multiline) { input.style.height = 'auto'; input.style.height = `${input.scrollHeight + 2}px`; } };
    input.addEventListener('input', () => { setPath(path, input.value); grow(); changed(); });
    requestAnimationFrame(grow);
    return input;
  };
  const iconBtn = (label, text, onclick, { disabled = false, danger = false } = {}) =>
    h('button', { type: 'button', class: `icon-btn${danger ? ' danger' : ''}`, 'aria-label': label, title: label, disabled, onclick: (e) => { e.preventDefault(); e.stopPropagation(); onclick(); } }, text);

  function experienceEditor() {
    const list = getPath('about.experiences') || [];
    setPath('about.experiences', list);
    const move = (i, d) => { list.splice(i + d, 0, list.splice(i, 1)[0]); rerender(); };
    const items = list.map((row, i) => {
      const base = `about.experiences.${i}`;
      const period = [row.start_date, row.end_date].filter(Boolean).join(' – ');
      const card = h('details', { class: 'exp-card', open: openRows.has(row) },
        h('summary', {},
          h('span', { class: 'exp-sum' },
            h('small', {}, `${row.kind === 'edu' ? '교육' : '경력'} · ${period || '기간 미입력'}`),
            h('strong', {}, row.company || '새 경력'),
            row.position ? h('span', { class: 'muted' }, row.position) : null),
          h('span', { class: 'exp-tools' },
            iconBtn('위로', '↑', () => move(i, -1), { disabled: i === 0 }),
            iconBtn('아래로', '↓', () => move(i, 1), { disabled: i === list.length - 1 }),
            iconBtn('삭제', '✕', () => { list.splice(i, 1); rerender(); }, { danger: true }))),
        h('div', { class: 'exp-fields' },
          h('div', { class: 'f-period' },
            labeled('시작', textField(`${base}.start_date`, '2026.06')),
            labeled('끝', h('span', { class: 'f-inline' }, textField(`${base}.end_date`, '2026.11 또는 현재'),
              h('button', { type: 'button', class: 'chip-btn', onclick: () => { row.end_date = '현재'; rerender(); } }, '현재')))),
          labeled('구분', (() => {
            const sel = h('select', { class: 'inline-input' }, h('option', { value: 'work', selected: row.kind !== 'edu' }, '경력'), h('option', { value: 'edu', selected: row.kind === 'edu' }, '교육'));
            sel.addEventListener('change', () => { row.kind = sel.value; changed(); });
            return sel;
          })()),
          labeled('회사·과정', textField(`${base}.company`, '예: ㈜통일감정평가법인')),
          labeled('역할', textField(`${base}.position`, '예: 기업맞춤형 AI+X 융복합 인재 양성 과정')),
          labeled('한 일', textField(`${base}.description`, '무엇을 했는지 한두 문장', { multiline: true })),
          labeled('성과 (선택)', textField(`${base}.achievement`, '결과·수치', { multiline: true }))));
      card.addEventListener('toggle', () => { if (card.open) openRows.add(row); else openRows.delete(row); });
      return card;
    });
    const add = h('button', { type: 'button', class: 'add-block', onclick: () => {
      const row = { id: null, company: '', position: '', start_date: '', end_date: '', description: '', achievement: '', kind: 'work' };
      list.push(row); openRows.add(row); rerender();
    } }, '＋ 경력 추가');
    return h('div', { class: 'exp-editor' }, items, add);
  }

  function skillEditor() {
    const list = getPath('about.skills') || [];
    setPath('about.skills', list);
    // 분류별로 묶되 처음 나온 순서를 지킨다. 저장할 때는 다시 한 줄 목록으로 편다.
    const groups = [];
    list.forEach((s) => {
      const key = (s.category || '').trim();
      let g = groups.find((x) => x.key === key);
      if (!g) { g = { key, items: [] }; groups.push(g); }
      g.items.push(s);
    });
    emptyGroups.forEach((key) => {
      const g = groups.find((x) => x.key === key);
      if (g && g.items.length) emptyGroups.delete(key);
      else if (!g) groups.push({ key, items: [] });
    });
    const flatten = () => { list.splice(0, list.length, ...groups.flatMap((g) => g.items.map((s) => ({ ...s, category: g.key })))); };
    const moveGroup = (i, d) => { groups.splice(i + d, 0, groups.splice(i, 1)[0]); flatten(); rerender(); };

    const groupEls = groups.map((g, gi) => {
      const name = h('input', { class: 'inline-input skill-cat', type: 'text', value: g.key, placeholder: '분류 이름 (예: DATA)', 'aria-label': '분류 이름' });
      name.addEventListener('change', () => {
        if (emptyGroups.delete(g.key)) emptyGroups.add(name.value.trim());
        g.key = name.value.trim(); flatten(); rerender();
      });
      const adder = h('input', { class: 'inline-input skill-add', type: 'text', placeholder: '스킬 입력 후 Enter', 'aria-label': `${g.key || '분류'}에 스킬 추가`, 'data-focus-key': `skill-add-${gi}` });
      const addSkill = () => {
        const names = adder.value.split(',').map((x) => x.trim()).filter(Boolean);
        if (!names.length) return;
        names.forEach((n) => g.items.push({ id: null, category: g.key, name: n }));
        flatten(); rerender(`skill-add-${gi}`);
      };
      adder.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(); } });
      return h('div', { class: 'skill-group-edit' },
        h('div', { class: 'skill-group-head' }, name,
          h('span', { class: 'exp-tools' },
            iconBtn('분류 위로', '↑', () => moveGroup(gi, -1), { disabled: gi === 0 }),
            iconBtn('분류 아래로', '↓', () => moveGroup(gi, 1), { disabled: gi === groups.length - 1 }),
            iconBtn('분류 전체 삭제', '✕', () => { emptyGroups.delete(g.key); groups.splice(gi, 1); flatten(); rerender(); }, { danger: true }))),
        h('ul', { class: 'skill-chips' },
          g.items.map((s, si) => h('li', { class: 'skill-chip' },
            h('span', {}, s.name),
            iconBtn(`${s.name} 삭제`, '×', () => { g.items.splice(si, 1); flatten(); rerender(); }))),
          h('li', { class: 'skill-chip-add' }, adder)));
    });
    const newCat = h('input', { class: 'inline-input', type: 'text', placeholder: '새 분류 이름 (예: TOOLS) 입력 후 Enter', 'aria-label': '새 분류', 'data-focus-key': 'skill-new-cat' });
    newCat.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const key = newCat.value.trim();
      if (!key) return;
      // 빈 분류는 저장되지 않으므로 스킬을 넣기 전까지 화면에만 둔다
      if (!groups.some((g) => g.key === key)) emptyGroups.add(key);
      const index = groups.some((g) => g.key === key) ? groups.findIndex((g) => g.key === key) : groups.length;
      rerender(`skill-add-${index}`);
    });
    return h('div', { class: 'skill-editor' }, groupEls, h('div', { class: 'skill-new-cat' }, newCat),
      h('p', { class: 'muted f-hint' }, '쉼표로 여러 개를 한 번에 넣을 수 있어요. 예: Python, Pandas, SQL'));
  }
  function strengthEditor() {
    const list = getPath('about.strengths') || [];
    while (list.length < 4) list.push({ title: '', text: '' });
    setPath('about.strengths', list);
    const tints = ['butter', 'mint', 'sky', 'pink'];
    return h('div', { class: 'grid-4' }, list.slice(0, 4).map((s, i) => h('div', { class: `strength tint-${tints[i]}` },
      editable('h3', '', { path: `about.strengths.${i}.title`, placeholder: '잘하는 것', single: true }),
      editable('p', '', { path: `about.strengths.${i}.text`, placeholder: '한 문장 설명' }))));
  }

  function aboutSections() {
    return [
      h('section', { class: 'resume-sec' }, h('h2', { class: 'r-label' }, '한 줄 소개 · ==단어== 는 형광펜'),
        editable('p', 'resume-summary', { path: 'about.summary', placeholder: '이력서 맨 위에 보일 한두 문장' })),
      h('section', { class: 'resume-sec' }, h('h2', { class: 'r-title' }, '잘하는 것'), strengthEditor()),
      h('section', { class: 'resume-sec' }, h('h2', { class: 'r-title' }, '경력 · 교육'), experienceEditor()),
      h('section', { class: 'resume-sec' }, h('h2', { class: 'r-title' }, '기술'), skillEditor()),
    ];
  }

  // ------------------------------------------------------------ 캔버스 그리기
  const designClass = () => {
    const d = state.design;
    return `post cover-${d.cover} accent-${d.accent} width-${d.width} size-${d.size}`;
  };

  let readTimeEl;
  let crumbsEl;
  let chipEl;

  const renderToc = () => {};

  function updateReadTime() {
    if (!readTimeEl) return;
    const chars = state.blocks.reduce((sum, b) => sum + (b.text || '').length, 0);
    readTimeEl.textContent = `${Math.max(1, Math.round(chars / 500))}분 읽기`;
  }

  const isLife = () => (meta.lifeCategories || []).includes(state.category);
  function updateCrumbs() {
    if (crumbsEl) {
      crumbsEl.textContent = kind === 'project' ? '프로젝트 / 케이스 스터디' : kind === 'reading' ? '기록 / 독서' : `기록 / ${isLife() ? '일상' : '공부·업무'}`;
    }
    if (chipEl) {
      const label = kind === 'project' ? (state.project?.category || '분류 칩') : kind === 'reading' ? '독서' : (state.category || '분류');
      chipEl.textContent = label;
      chipEl.className = `chip tint-${state.design.accent}`;
    }
  }

  function updateTechChips() {
    const chips = $('#tech-chips', canvas);
    if (!chips) return;
    const list = (state.project?.tech_stack || '').split(/[\/,·]/).map((t) => t.trim()).filter(Boolean);
    chips.textContent = list.length ? list.join(' · ') : '오른쪽 「기술」 칸에 입력';
  }

  function renderAll() {
    const d = state.design;
    if (kind === 'about') {
      const head = h('header', { class: 'resume-head', 'data-stage-part': 'details' },
        h('span', { class: 'avatar avatar-lg avatar-edit' }, imageOrDrop(getPath('about.photo'), '사진', setCover, { compact: true })),
        h('div', { class: 'resume-who' },
          editable('h1', '', { path: 'about.name', placeholder: '이름', single: true }),
          editable('p', '', { path: 'about.tagline', placeholder: '업무운영 · 데이터 · AI 서비스 기획', single: true })));
      const article = h('article', { class: `resume ${designClass()}` }, head, h('div', { 'data-stage-part': 'content' }, aboutSections()),
        h('section', { class: 'resume-sec', 'data-stage-part': 'content' }, h('h2', { class: 'r-title' }, '더 적고 싶은 것 (선택)'),
          h('div', { class: 'post-body' }, state.blocks.map(blockWrap)), addBlockMenu()));
      canvas.replaceChildren(article);
    activeRich = null;
      restoreFocus();
      return;
    }
    crumbsEl = h('p', { class: 'crumbs' });
    readTimeEl = h('span');
    chipEl = h('span', { class: 'chip' });
    const header = h('header', { class: 'post-header', 'data-stage-part': 'details' },
      h('p', { class: 'chip-wrap' }, chipEl),
      editable('h1', 'post-title', { path: 'title', placeholder: '제목', single: true }),
      editable('p', 'post-summary', { path: kind === 'project' ? 'project.subtitle' : 'summary', placeholder: kind === 'project' ? '한 줄 소개' : '요약 — 목록과 검색 결과에 보여요' }),
      kind !== 'project' ? h('p', { class: 'post-meta' }, h('time', {}, new Date().toLocaleDateString('ko-KR')), readTimeEl) : null);
    const article = h('article', { class: designClass() },
      crumbsEl,
      d.cover === 'large' ? h('figure', { class: 'post-hero', 'data-stage-part': 'preview' }, coverSlot()) : null,
      header,
      kind === 'project' ? h('div', { 'data-stage-part': 'details' }, projectFields()) : null,
      kind === 'reading' ? h('div', { 'data-stage-part': 'details' }, bookEditor()) : null,
      kind === 'project' ? h('div', { 'data-stage-part': 'content' }, projectCase()) : null,
      h('div', { class: 'post-body', 'data-stage-part': 'content' }, state.blocks.map(blockWrap)),
      h('div', { 'data-stage-part': 'content', 'data-add-menu': '' }, addBlockMenu()));
    canvas.replaceChildren(article);
    activeRich = null;
    restoreFocus();
    updateCrumbs();
    updateReadTime();
    updateTechChips();
  }

  // ------------------------------------------------------------ 오른쪽 패널 연결
  function syncInputs() {
    $$('[data-bind]', form).forEach((input) => {
      const value = getPath(input.dataset.bind);
      if (input.type === 'checkbox') input.checked = Boolean(value);
      else if (document.activeElement !== input) input.value = value ?? '';
    });
    $$('[data-design]', form).forEach((radio) => { radio.checked = state.design[radio.dataset.design] === radio.value; });
  }

  $$('[data-bind]', form).forEach((input) => {
    const handler = () => {
      setPath(input.dataset.bind, input.type === 'checkbox' ? input.checked : input.value);
      if (input.dataset.bind === 'category' || input.dataset.bind === 'project.category') updateCrumbs();
      if (input.dataset.bind === 'project.tech_stack') updateTechChips();
      if (input.dataset.bind === coverPath) render();
      changed();
    };
    input.addEventListener(input.tagName === 'SELECT' || input.type === 'checkbox' ? 'change' : 'input', handler);
  });

  $$('[data-design]', form).forEach((radio) => radio.addEventListener('change', () => {
    state.design[radio.dataset.design] = radio.value;
    if (radio.dataset.design === 'cover' || kind === 'about') render();
    else { $('article.post', canvas).className = designClass(); updateCrumbs(); }
    changed();
  }));

  $$('.file-field', form).forEach((wrap) => {
    const file = $('input[type="file"]', wrap);
    file.addEventListener('change', async () => {
      if (!file.files[0]) return;
      try {
        const url = await upload(file.files[0], wrap.dataset.fileType || 'image');
        setPath(wrap.dataset.uploadTarget, url);
        syncInputs();
        if (wrap.dataset.uploadTarget === coverPath) render();
        changed();
      } catch (error) { /* showState가 이미 알렸다 */ }
      file.value = '';
    });
  });

  $$('[data-view]').forEach((button) => button.addEventListener('click', () => {
    $$('[data-view]').forEach((b) => b.setAttribute('aria-pressed', String(b === button)));
    $('#canvas-frame').classList.toggle('is-mobile', button.dataset.view === 'mobile');
  }));

  // ------------------------------------------------------------ 저장
  function showState(text, tone = '') {
    saveState.textContent = text;
    saveState.dataset.tone = tone;
  }

  const canAutosave = () => !single && !meta.published;

  function changed() {
    dirty = true;
    try { localStorage.setItem(localKey(), JSON.stringify({ at: Date.now(), state })); } catch (error) { /* private mode */ }
    showState('쓰는 중…', 'busy');
    clearTimeout(timer);
    timer = setTimeout(autosave, AUTOSAVE_MS);
  }

  async function autosave() {
    if (!dirty) return;
    if (!canAutosave()) {
      // 공개 중인 글·소개는 바로 바뀌면 안 되므로 브라우저에만 보관한다
      try { localStorage.setItem(localKey(), JSON.stringify({ at: Date.now(), state })); } catch (error) { /* 저장소 사용 불가 */ }
      showState(single ? '고친 내용이 있어요 · 「저장하기」를 눌러 주세요' : '고친 내용이 있어요 · 「고친 내용 공개」를 눌러 주세요', 'warn');
      return;
    }
    dirty = false;
    const run = fetch(form.dataset.autosaveUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(state),
    }).then((response) => response.json()).then((result) => {
      if (!result.ok) throw new Error(result.error);
      if (!state.id) {
        state.id = result.id;
        form.setAttribute('action', result.edit_url);
        history.replaceState(null, '', stageURL(stage, result.edit_url));
        updateStageLinks();
      }
      showState(`자동 저장됨 · ${result.saved_at}`, 'ok');
    }).catch(() => {
      dirty = true;
      showState('자동 저장 실패 · 연결을 확인하세요', 'error');
    });
    pending = run;
    await run;
    pending = null;
  }

  let submitting = false;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submitting) return;
    const action = event.submitter?.dataset.action || 'draft';
    clearTimeout(timer);
    if (pending) await pending;
    if (!(state.title || '').trim() && !single) {
      showState('제목을 적어 주세요', 'error');
      goStage('details');
      $('.post-title', canvas)?.focus();
      return;
    }
    submitting = true;
    dirty = false;
    try { localStorage.removeItem(localKey()); } catch (error) { /* 무시 */ }
    $('#payload').value = JSON.stringify(state);
    $('#action-input').value = action;
    HTMLFormElement.prototype.submit.call(form);
  });

  window.addEventListener('beforeunload', (event) => {
    if (dirty && !submitting) {
      event.preventDefault();
      event.returnValue = '';
    }
  });

  // 지난번에 브라우저에 보관한 수정본이 있으면 불러올지 묻는다
  function offerRestore() {
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(localKey()) || 'null'); } catch (error) { saved = null; }
    if (!saved || !saved.state) return;
    const when = new Date(saved.at).toLocaleString('ko-KR');
    const restore = h('button', { type: 'button', class: 'linkish', onclick: () => {
      Object.assign(state, saved.state);
      syncInputs();
      render();
      changed();
    } }, '불러오기');
    const discard = h('button', { type: 'button', class: 'linkish', onclick: () => {
      try { localStorage.removeItem(localKey()); } catch (error) { /* 무시 */ }
      showState('');
    } }, '버리기');
    saveState.replaceChildren(`브라우저에 보관된 수정본(${when}) `, restore, ' · ', discard);
    saveState.dataset.tone = 'warn';
  }

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.add-wrap')) $$('.add-menu', canvas).forEach((menu) => { menu.hidden = true; });
  });

  // ------------------------------------------------------------ 단계별 작성 페이지
  const STAGES = ['details', 'content', 'media', 'publish'];
  let stage = STAGES.includes(new URL(location.href).searchParams.get('step'))
    ? new URL(location.href).searchParams.get('step') : (form.dataset.step || 'details');
  const descriptions = {
    details: ['기본 정보부터 적어주세요', kind === 'reading' ? '책과 글 제목을 정하세요. 독서 내용은 다음 페이지에서 적습니다.' : '이 글을 알아볼 제목과 기본 정보를 적습니다.'],
    content: ['지금은 내용에만 집중하세요', '문단을 쓰고, 필요한 소제목과 인용을 넣으세요. 사진과 공개 설정은 다음 단계에 있습니다.'],
    media: ['사진과 분위기를 정하세요', '커버와 본문 사진을 따로 정리하세요. 글은 마지막 페이지에서 한 번에 확인할 수 있습니다.'],
    publish: ['공개하기 전에 확인하세요', single ? '수정한 소개를 확인하고 저장하세요.' : '본문을 확인하고 분류·태그·공개 시점을 정하세요. 아래 버튼을 눌러야 발행됩니다.'],
  };

  function stageURL(value, base = form.getAttribute('action')) {
    const url = new URL(base, location.href);
    url.searchParams.set('step', value);
    return url.pathname + url.search + url.hash;
  }

  function updateStageLinks() {
    $$('[data-stage-link]').forEach((link) => {
      link.href = stageURL(link.dataset.stageLink);
      if (link.dataset.stageLink === stage) link.setAttribute('aria-current', 'step');
      else link.removeAttribute('aria-current');
    });
  }

  function goStage(value, push = true) {
    if (!STAGES.includes(value)) return;
    stage = value;
    selected = -1;
    render();
    if (push) history.pushState(null, '', stageURL(stage));
    $('#studio .studio-center')?.scrollTo(0, 0);
    $('#stage-title')?.focus({ preventScroll: true });
  }

  function mediaEditor() {
    const images = state.blocks.map((block, index) => ({ block, index })).filter(({ block }) => ['image', 'image2', 'youtube', 'instagram'].includes(block.type));
    return h('section', { class: 'stage-media-editor' },
      h('h2', {}, single ? '프로필 사진' : '커버 이미지'),
      coverSlot(),
      h('p', { class: 'hint' }, single ? '프로필에 사용할 사진을 골라주세요.' : '위 사진은 글의 커버입니다. 본문에 넣을 사진은 아래에서 추가하세요.'),
      h('h2', {}, '본문 사진·영상'),
      images.length ? images.map(({ block, index }) => h('section', { class: 'stage-media-item' }, h('p', { class: 'hint' }, `본문 ${index + 1}번째 블록 · ${meta.blockTypes[block.type]}`), blockWrap(block, index))) : h('p', { class: 'hint' }, '아직 본문 사진이 없습니다. 사진 없이도 다음 단계로 갈 수 있어요.'),
      h('div', { class: 'stage-media-actions' },
        h('button', { type: 'button', class: 'btn btn-sub', onclick: () => insertBlock('image', state.blocks.length, false) }, '＋ 본문 사진'),
        h('button', { type: 'button', class: 'btn btn-sub', onclick: () => insertBlock('image2', state.blocks.length, false) }, '＋ 사진 2장'),
        h('button', { type: 'button', class: 'btn btn-sub', onclick: () => insertBlock('youtube', state.blocks.length, false) }, '＋ 동영상'),
        h('button', { type: 'button', class: 'btn btn-sub', onclick: () => insertBlock('instagram', state.blocks.length, false) }, '＋ 인스타')));
  }

  function readOnlyPreview(article) {
    $$('.blk-tools, .add-wrap, .book-search, [data-add-menu]', article).forEach((el) => el.remove());
    $$('[contenteditable]', article).forEach((el) => { el.contentEditable = 'false'; el.removeAttribute('role'); });
    $$('input, select, textarea', article).forEach((input) => {
      if (input.type === 'file' || input.type === 'hidden') { input.remove(); return; }
      const value = input.tagName === 'SELECT' ? input.selectedOptions[0]?.textContent : input.value;
      input.replaceWith(h('span', { class: 'stage-preview-value' }, value || '—'));
    });
    $$('.drop-actions, .empty-drop, .dropzone, .img-slot-tools', article).forEach((el) => el.remove());
    $$('button', article).forEach((button) => { button.disabled = true; button.tabIndex = -1; });
  }

  function render() {
    renderAll();
    const article = $('article', canvas);
    if (!article) return;
    if (stage !== 'publish') {
      $$('[data-stage-part]', article).forEach((part) => { if (part.dataset.stagePart !== stage) part.remove(); });
      $('.crumbs', article)?.remove();
      if (stage === 'media') article.append(mediaEditor());
      if (stage === 'content') {
        $$('.blk-image, .blk-image2, .blk-youtube, .blk-instagram', article).forEach((block) => {
          block.replaceChildren(h('div', { class: 'stage-media-placeholder' },
            h('span', {}, '사진·영상 블록'),
            h('button', { type: 'button', class: 'text-btn', onclick: () => goStage('media') }, '사진 단계에서 보기 →')));
        });
      }
    } else readOnlyPreview(article);
    form.dataset.step = stage;
    $('#writing-step').value = stage;
    $('#stage-title').textContent = descriptions[stage][0];
    $('#stage-description').textContent = descriptions[stage][1];
    $('#stage-context').textContent = single ? '소개 페이지' : (state.title || '새 글');
    $('#editor-bar').hidden = stage !== 'content';
    $$('[data-review-only]').forEach((el) => { el.hidden = stage !== 'publish'; });
    const options = $('#publish-pop');
    $$('[data-stage-option]', options).forEach((part) => { part.hidden = part.dataset.stageOption !== stage; });
    options.hidden = !(stage === 'media' || stage === 'publish' || (single && stage === 'details'));
    $('#stage-options-title').textContent = stage === 'media' ? '꾸미기' : stage === 'details' ? '소개 정보' : single ? '저장' : '공개 설정';
    $('.studio-cols').classList.toggle('has-stage-options', !options.hidden);
    $('#stage-prev').disabled = stage === 'details';
    const nextButton = $('#stage-next');
    const finalLabel = single ? '저장하기' : meta.published ? '수정 내용 공개' : '발행하기';
    nextButton.type = stage === 'publish' ? 'submit' : 'button';
    nextButton.textContent = stage === 'publish' ? finalLabel : '다음 →';
    if (stage === 'publish') nextButton.dataset.action = 'publish';
    else delete nextButton.dataset.action;
    $$('[data-stage-go="publish"]').forEach((button) => {
      button.dataset.stageLabel ||= button.textContent;
      button.type = stage === 'publish' ? 'submit' : 'button';
      button.textContent = stage === 'publish' ? finalLabel : button.dataset.stageLabel;
      if (stage === 'publish') button.dataset.action = 'publish';
      else delete button.dataset.action;
    });
    $('#stage-count').textContent = `${STAGES.indexOf(stage) + 1} / ${STAGES.length}`;
    updateStageLinks();
  }

  $$('[data-stage-link]').forEach((link) => link.addEventListener('click', (event) => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); goStage(link.dataset.stageLink);
  }));
  $$('[data-stage-go]').forEach((button) => button.addEventListener('click', (event) => {
    if (button.type === 'submit') return;
    event.preventDefault(); goStage(button.dataset.stageGo);
  }));
  $('#stage-prev').addEventListener('click', () => goStage(STAGES[STAGES.indexOf(stage) - 1]));
  $('#stage-next').addEventListener('click', (event) => {
    if (stage === 'publish') return;
    event.preventDefault(); goStage(STAGES[STAGES.indexOf(stage) + 1]);
  });
  window.addEventListener('popstate', () => {
    const next = new URL(location.href).searchParams.get('step');
    if (STAGES.includes(next)) goStage(next, false);
  });
  history.replaceState(null, '', stageURL(stage, location.href));

  buildToolbar();
  syncInputs();
  render();
  updateToolbar();
  offerRestore();
  if (!state.id && !single) $('.post-title', canvas)?.focus();
})();
