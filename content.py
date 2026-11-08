"""본문 블록·디자인 설정의 검증과 화면용 변환.

블록과 디자인 값은 정해진 목록 안에서만 허용한다. 목록에 없는 값은 기본값으로 바꾼다.
"""
import html
import re
import unicodedata

import markdown
from html.parser import HTMLParser
from markupsafe import Markup, escape

# ---------------------------------------------------------------- 콘텐츠 종류
# 글쓰기에서 고르는 종류는 4가지(프로젝트·기록·독서·소개). 기록은 분류에 따라 공부·업무(notes)와 일상(life)으로 저장된다.
KINDS = {
    "project": {"label": "프로젝트"},
    "notes": {"label": "기록"},
    "reading": {"label": "독서"},
    "about": {"label": "소개"},
}
SINGLE_KINDS = ("about",)
POST_KINDS = ("notes", "life", "reading")

NOTES_CATEGORIES = ["AI / ML", "DATA", "DEVELOPMENT", "PROJECT", "LECTURE", "CERTIFICATION", "WORK", "THINKING"]
LIFE_CATEGORIES = ["맛집 · 카페", "여행", "사주 연구", "독서 모임", "일상"]
READING_CATEGORIES = ["독서 노트"]
CATEGORIES = {"notes": NOTES_CATEGORIES, "life": LIFE_CATEGORIES, "reading": READING_CATEGORIES}

# 기록 목록의 분류 탭: 주소의 ?type= 값 → (이름, content_type)
NOTE_TYPES = {"study": ("공부·업무", "notes"), "reading": ("독서", "reading"), "life": ("일상", "life")}
TYPE_OF_KIND = {kind: key for key, (_, kind) in NOTE_TYPES.items()}

# ---------------------------------------------------------------- 의미별 파스텔 (7-2장)
# 같은 것은 어느 화면에서나 같은 색. 새 분류를 넣으면 여기에만 한 줄 더한다. 없으면 기본값(하늘).
TINTS = ("butter", "mint", "sky", "pink", "lilac")
CATEGORY_TINT = {
    # 콘텐츠 종류
    "project": "sky", "notes": "sky", "study": "sky", "reading": "butter", "life": "pink", "about": "pink",
    # 기록 분류
    "AI / ML": "pink", "DATA": "sky", "DEVELOPMENT": "mint", "PROJECT": "sky", "LECTURE": "pink",
    "CERTIFICATION": "pink", "WORK": "butter", "THINKING": "butter", "독서 노트": "butter",
    "맛집 · 카페": "pink", "여행": "pink", "사주 연구": "lilac", "독서 모임": "butter", "일상": "pink",
    # 기술 묶음
    "AI": "pink",
    # 운영 중인 곳
    "rest": "mint", "sofa": "lilac",
    # 경력 종류
    "work": "mint", "edu": "pink",
}
SKILL_GROUPS = {"DATA": "데이터", "AI": "AI", "DEVELOPMENT": "개발", "WORK": "일하는 방식"}
BOOK_STATUS = {"reading": "읽는 중", "completed": "다 읽음", "wish": "읽고 싶은"}
BOOK_STATUS_TINT = {"reading": "mint", "completed": "sky", "wish": "butter"}


def tint(key, default="sky"):
    value = CATEGORY_TINT.get(key or "", default)
    return value if value in TINTS else default


# ---------------------------------------------------------------- 디자인 설정 (글쓰기 오른쪽 패널)
# 글꼴은 사이트 톤을 위해 고정. 커버·포인트 색·본문 폭·글자 크기만 고른다.
DESIGN_OPTIONS = {
    "cover": [("none", "커버 없음"), ("large", "큰 커버")],
    "accent": [("butter", "버터"), ("mint", "민트"), ("sky", "하늘"), ("pink", "핑크")],
    "width": [("narrow", "좁게"), ("wide", "넓게")],
    "size": [("s", "작게"), ("m", "보통"), ("l", "크게")],
}
DESIGN_DEFAULTS = {"cover": "none", "accent": "sky", "width": "narrow", "size": "m"}
LEGACY_ACCENT = {"olive": "mint", "blue": "sky", "terracotta": "pink", "charcoal": "butter"}


def normalize_design(raw, kind=None):
    """목록에 없는 값은 기본값으로. 예전 값(layout·올리브 등)은 새 값으로 옮겨 읽는다."""
    raw = dict(raw) if isinstance(raw, dict) else {}
    if "cover" not in raw and raw.get("layout") in ("magazine", "side"):
        raw["cover"] = "large"
    if raw.get("accent") in LEGACY_ACCENT:
        raw["accent"] = LEGACY_ACCENT[raw["accent"]]
    defaults = dict(DESIGN_DEFAULTS, accent=tint(kind))
    design = {}
    for key, options in DESIGN_OPTIONS.items():
        allowed = {value for value, _ in options}
        value = raw.get(key)
        design[key] = value if value in allowed else defaults[key]
    return design


def design_classes(design):
    d = normalize_design(design)
    return f"cover-{d['cover']} accent-{d['accent']} width-{d['width']} size-{d['size']}"


# ---------------------------------------------------------------- 블록
BLOCK_TYPES = {
    "paragraph": "문단",
    "heading": "소제목",
    "image": "이미지",
    "image2": "이미지 2단",
    "quote": "인용",
    "callout": "강조 상자",
    "divider": "구분선",
    "markdown": "마크다운",
    "youtube": "유튜브 영상",
    "instagram": "인스타그램 게시물",
}
TEXT_LIMIT = 20000
URL_RE = re.compile(r"^(https?://|/static/)[^\s\"'<>]+$")


def clean_url(value):
    value = (value or "").strip()
    return value if URL_RE.match(value) else ""


def clean_text(value, limit=TEXT_LIMIT):
    value = value if isinstance(value, str) else ""
    return value.replace("\r\n", "\n").replace(" ", " ").strip()[:limit]


def normalize_blocks(raw):
    """사용자 입력(JSON 목록)을 허용된 블록 목록으로 정리한다."""
    if not isinstance(raw, list):
        return []
    blocks = []
    for item in raw[:300]:
        if not isinstance(item, dict) or item.get("type") not in BLOCK_TYPES:
            continue
        kind = item["type"]
        if kind in ("paragraph", "heading", "quote", "callout"):
            rich = sanitize_rich(item.get("rich")) if kind in RICH_BLOCKS and isinstance(item.get("rich"), str) else ""
            text = rich_to_text(rich)[:TEXT_LIMIT] if rich else clean_text(item.get("text"), 300 if kind == "heading" else TEXT_LIMIT)
            if text:
                block = {"type": kind, "text": text}
                if rich and rich != str(escape(text)).replace("\n", "<br>"):
                    block["rich"] = rich  # 꾸밈이 있을 때만 저장
                if item.get("align") in ("center", "right"):
                    block["align"] = item["align"]
                if kind == "quote" and item.get("cite"):
                    block["cite"] = clean_text(item.get("cite"), 200)
                blocks.append(block)
        elif kind == "markdown":
            text = clean_text(item.get("text"), 100000)
            if text:
                blocks.append({"type": "markdown", "text": text})
        elif kind == "image":
            url = clean_url(item.get("url"))
            if url:
                blocks.append({"type": "image", "url": url, "caption": clean_text(item.get("caption"), 300)})
        elif kind == "image2":
            url, url2 = clean_url(item.get("url")), clean_url(item.get("url2"))
            if url or url2:
                blocks.append({"type": "image2", "url": url, "url2": url2, "caption": clean_text(item.get("caption"), 300)})
        elif kind == "divider":
            blocks.append({"type": "divider"})
        elif kind == "youtube":
            video = youtube_id(item.get("url") or item.get("video_id"))
            if video:
                blocks.append({"type": "youtube", "video_id": video, "url": f"https://www.youtube.com/watch?v={video}",
                               "caption": clean_text(item.get("caption"), 300)})
        elif kind == "instagram":
            post = instagram_post(item.get("url"))
            if post:
                blocks.append({"type": "instagram", "url": post, "caption": clean_text(item.get("caption"), 300)})
    return blocks


# ---------------------------------------------------------------- 글자 꾸미기 (네이버 블로그식)
# 문단·인용·강조 상자 안에서만 쓴다. 허용 목록 밖의 태그·속성은 버리고 글자만 남긴다.
RICH_BLOCKS = ("paragraph", "quote", "callout")
TEXT_COLORS = {"butter": "#6e5a12", "mint": "#2f6b45", "sky": "#2b5a8a", "pink": "#9a3a4a", "lilac": "#5a4a9a",
               "muted": "#6b6861"}  # tokens.css의 글자색과 같게
MARKER_COLOR = "#fff0b3"
TAG_ALIAS = {"b": "strong", "strong": "strong", "i": "em", "em": "em", "u": "u", "s": "s", "strike": "s", "del": "s"}
SAFE_HREF = re.compile(r"^(https?://|mailto:|/)[^\s\"'<>]*$", re.I)


def _hex(value):
    """'#abc' · '#aabbcc' · 'rgb(1, 2, 3)' → '#aabbcc'"""
    value = (value or "").strip().lower()
    m = re.match(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", value)
    if m:
        return "#" + "".join(f"{min(255, int(n)):02x}" for n in m.groups())
    if re.match(r"^#[0-9a-f]{3}$", value):
        return "#" + "".join(c * 2 for c in value[1:])
    return value if re.match(r"^#[0-9a-f]{6}$", value) else ""


def _style(attrs, name):
    for part in (dict(attrs).get("style") or "").split(";"):
        key, _, val = part.partition(":")
        if key.strip().lower() == name:
            return val.strip()
    return ""


class _RichCleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.skip = [], [], 0

    def _br(self):
        if self.out and self.out[-1] != "<br>":
            self.out.append("<br>")

    def handle_starttag(self, tag, attrs):
        attrs = [(k, v or "") for k, v in attrs]
        if tag in ("script", "style", "template", "iframe", "object", "svg"):
            self.skip += 1
            return
        if tag == "br":
            self.out.append("<br>")
            return
        if tag in ("div", "p", "li"):
            self._br()
            self.stack.append(None)
            return
        opened = None
        if tag in TAG_ALIAS:
            opened = TAG_ALIAS[tag]
            self.out.append(f"<{opened}>")
        elif tag == "a":
            href = dict(attrs).get("href", "").strip()
            if SAFE_HREF.match(href):
                opened = "a"
                extra = ' target="_blank" rel="noopener"' if href.lower().startswith("http") else ""
                self.out.append(f'<a href="{escape(href)}"{extra}>')
        elif tag == "mark":
            opened = "mark"
            self.out.append('<mark class="hl">')
        elif tag in ("span", "font"):
            classes = set((dict(attrs).get("class") or "").split())
            background = _hex(_style(attrs, "background-color") or _style(attrs, "background"))
            color = _hex(dict(attrs).get("color") if tag == "font" else _style(attrs, "color"))
            named = next((c[2:] for c in classes if c.startswith("c-") and c[2:] in TEXT_COLORS), None)
            named = named or next((k for k, v in TEXT_COLORS.items() if v == color), None)
            if background == MARKER_COLOR or "hl" in classes:
                opened = "mark"
                self.out.append('<mark class="hl">')
            elif named:
                opened = "span"
                self.out.append(f'<span class="c-{named}">')
        self.stack.append(opened)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template", "iframe", "object", "svg"):
            self.skip = max(0, self.skip - 1)
            return
        if tag == "br" or not self.stack:
            return
        opened = self.stack.pop()
        if opened:
            self.out.append(f"</{opened}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(str(escape(data)))

    def result(self):
        while self.stack:
            opened = self.stack.pop()
            if opened:
                self.out.append(f"</{opened}>")
        text = "".join(self.out)
        text = re.sub(r"<(strong|em|u|s|mark class=\"hl\"|span class=\"c-\w+\")></(strong|em|u|s|mark|span)>", "", text)
        return re.sub(r"^(<br>)+|(<br>)+$", "", text)


def sanitize_rich(value):
    value = (value or "")[:TEXT_LIMIT * 2]
    if not value.strip():
        return ""
    cleaner = _RichCleaner()
    cleaner.feed(value.replace("\r\n", "\n").replace("\n", "<br>"))
    cleaner.close()
    return cleaner.result()


def rich_to_text(value):
    text = re.sub(r"<br\s*/?>", "\n", value or "")
    return html.unescape(re.sub(r"<[^>]+>", "", text)).replace("\xa0", " ").strip()


YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_URL = re.compile(r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})")
INSTAGRAM_URL = re.compile(r"^https?://(?:www\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(p|reel|tv)/([A-Za-z0-9_-]+)")


def youtube_id(value):
    """유튜브 주소(일반·짧은 주소·shorts·embed)나 영상 ID에서 11자리 ID를 뽑는다."""
    value = (value or "").strip()
    if YOUTUBE_ID.match(value):
        return value
    match = YOUTUBE_URL.search(value)
    return match.group(1) if match else ""


def instagram_post(value):
    """인스타그램 게시물·릴스 주소를 https://www.instagram.com/p/<코드>/ 꼴로 맞춘다."""
    match = INSTAGRAM_URL.match((value or "").strip())
    return f"https://www.instagram.com/{match.group(1)}/{match.group(2)}/" if match else ""


def social_url(value, hosts):
    """채널 주소: https이고 지정한 도메인일 때만 받는다."""
    value = clean_url(value)
    if not value.startswith("https://"):
        return ""
    host = value.split("/")[2].lower()
    return value if any(host == h or host.endswith("." + h) for h in hosts) else ""


def slugify(value):
    value = unicodedata.normalize("NFKC", value or "").strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value).strip("-")
    return value[:120]


def _anchor(text, used):
    base = slugify(text) or "section"
    anchor, n = base, 2
    while anchor in used:
        anchor, n = f"{base}-{n}", n + 1
    used.add(anchor)
    return anchor


def render_body(blocks):
    """화면용 블록과 목차, 읽는 시간(분)을 돌려준다."""
    rendered, toc, used, chars = [], [], set(), 0
    for block in normalize_blocks(blocks):
        block = dict(block)
        text = block.get("text", "")
        chars += len(text)
        if block["type"] == "heading":
            block["anchor"] = _anchor(text, used)
            toc.append({"text": text, "anchor": block["anchor"], "level": 2})
        elif block["type"] == "markdown":
            md = markdown.Markdown(extensions=["extra", "fenced_code", "tables", "sane_lists", "toc"],
                                   extension_configs={"toc": {"slugify": lambda v, sep: _anchor(v, used)}})
            block["html"] = Markup(md.convert(text))
            for token in md.toc_tokens:
                toc.append({"text": html.unescape(token["name"]), "anchor": token["id"], "level": min(token["level"], 3)})
                for child in token.get("children", []):
                    toc.append({"text": html.unescape(child["name"]), "anchor": child["id"], "level": 3})
        rendered.append(block)
    minutes = max(1, round(chars / 500))
    return rendered, toc, minutes


def plain_excerpt(blocks, limit=140):
    parts = []
    for block in normalize_blocks(blocks):
        if block.get("text"):
            parts.append(re.sub(r"[#>*_`\[\]()!-]+", " ", block["text"]))
        if sum(len(p) for p in parts) > limit:
            break
    text = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def blocks_text(blocks):
    return " ".join(b.get("text", "") for b in normalize_blocks(blocks))


def nl2br(value):
    return Markup("<br>".join(escape(line) for line in (value or "").split("\n")))


HIGHLIGHT = re.compile(r"==(.+?)==")


def highlight(value):
    """제목 속 ==핵심 단어== 를 형광펜 밑줄로. 나머지는 그대로 이스케이프한다."""
    text = str(escape(value or ""))
    text = HIGHLIGHT.sub(r'<mark class="hl">\1</mark>', text)
    return Markup(text.replace("\n", "<br>"))


def plain(value):
    """형광펜 표시(==)를 뺀 글자 (title·meta 태그용)."""
    return HIGHLIGHT.sub(r"\1", value or "")


def read_minutes(blocks):
    return max(1, round(len(blocks_text(blocks)) / 500))


def youtube_thumb(video_id):
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
