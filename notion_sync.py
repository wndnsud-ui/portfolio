"""노션 독서 DB → 사이트 한 방향 동기화.

- 노션 DB의 각 페이지 = 책 1권(books). 페이지 본문이 있으면 독서 노트(archive, content_type=reading)도 만든다.
- 속성 이름은 흔한 이름(제목·저자·출판사·장르·상태·시작일·완독일·별점·한줄평·표지)을 찾아 맞춘다.
- 노션에서 고친 시간이 그대로면 건너뛴다. 처음 들어온 노트는 임시저장으로 두고, 관리자가 확인한 뒤 발행한다.
- 노션 파일 주소는 1시간 뒤 만료되므로 표지·본문 이미지는 내려받아 Storage에 다시 올린다.

필요한 환경변수: NOTION_TOKEN (내부 통합 시크릿), NOTION_READING_DB (DB 주소나 ID)
"""
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import escape

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

# 속성 이름 후보 (소문자·공백 제거 후 비교)
PROP_NAMES = {
    "author": ["저자", "작가", "지은이", "글쓴이", "author", "writer"],
    "publisher": ["출판사", "publisher"],
    "genre": ["장르", "분류", "카테고리", "genre", "category"],
    "status": ["상태", "읽기상태", "독서상태", "진행", "status"],
    "start_date": ["시작일", "시작", "읽기시작", "시작한날", "startdate", "start"],
    "finish_date": ["완독일", "종료일", "다읽은날", "끝난날", "완료일", "finishdate", "enddate", "finish", "end"],
    "date": ["기간", "읽은기간", "날짜", "date", "period"],
    "rating": ["별점", "평점", "점수", "rating", "score", "stars"],
    "summary": ["한줄평", "한줄요약", "요약", "한줄", "summary", "review"],
    "record_type": ["기록방식", "기록유형", "기록형식", "recordtype"],
    "cover": ["표지", "커버", "cover", "image"],
}
PROP_CONTAINS = {
    "start_date": ["시작"], "finish_date": ["완독", "완료", "종료", "끝"], "date": ["기간", "날짜"],
    "status": ["상태"], "rating": ["별점", "평점"], "author": ["저자", "작가"], "publisher": ["출판"],
    "genre": ["장르", "분야"], "summary": ["한줄", "요약", "평"], "cover": ["표지", "커버"],
}
PROP_TYPES = {
    "start_date": ("date",), "finish_date": ("date",), "date": ("date",), "status": ("status", "select"),
    "rating": ("number", "select", "rich_text", "formula"), "author": ("rich_text", "select", "multi_select", "people"),
    "publisher": ("rich_text", "select"), "genre": ("select", "multi_select", "rich_text"),
    "summary": ("rich_text",), "cover": ("files",),
}
STATUS_MAP = [
    ("hold", ["보류", "중단", "멈춤", "hold", "paused", "dropped"]),  # 보류한 책은 가져오지 않는다
    ("completed", ["완독", "다읽", "완료", "읽음", "done", "complete", "finished", "read"]),
    ("reading", ["읽는", "진행", "reading", "inprogress", "doing"]),
    ("wish", ["읽고싶", "예정", "시작전", "위시", "wish", "want", "todo", "notstarted", "toread"]),
]
NOTION_COLOR = {"yellow": "butter", "orange": "butter", "brown": "muted", "gray": "muted", "green": "mint",
                "blue": "sky", "red": "pink", "pink": "pink", "purple": "lilac"}


class NotionError(Exception):
    pass


def database_id(value):
    """DB 주소나 ID에서 32자리 ID를 뽑는다."""
    value = (value or "").split("?")[0]
    found = re.findall(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value)
    return found[-1].replace("-", "") if found else ""


class Client:
    def __init__(self, token):
        if not token:
            raise NotionError("NOTION_TOKEN이 비어 있어요.")
        self.token = token
        self.calls = 0

    def request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(4):
            req = urllib.request.Request(API + path, data=data, method=method, headers={
                "Authorization": f"Bearer {self.token}", "Notion-Version": VERSION, "Content-Type": "application/json"})
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=20) as res:
                    return json.loads(res.read())
            except urllib.error.HTTPError as error:
                if error.code == 429 and attempt < 3:  # 초당 3회 제한
                    time.sleep(float(error.headers.get("Retry-After") or 1))
                    continue
                try:
                    detail = json.loads(error.read()).get("message", "")
                except Exception:
                    detail = ""
                if error.code == 401:
                    raise NotionError("노션 키가 맞지 않아요. NOTION_TOKEN을 확인해 주세요.") from None
                if error.code == 404:
                    raise NotionError("찾지 못했어요. 주소가 맞는지, 그 페이지의 ··· › 연결에 만든 연결을 추가했는지 확인해 주세요.") from None
                raise NotionError(f"노션 API 오류 {error.code}: {detail}") from None
            except urllib.error.URLError as error:
                raise NotionError(f"노션에 연결하지 못했어요: {error.reason}") from None
        raise NotionError("노션 요청이 너무 많아요. 잠시 뒤 다시 해 주세요.")

    def paginate(self, method, path, body=None):
        cursor = None
        while True:
            if method == "POST":
                payload = dict(body or {}, page_size=100, **({"start_cursor": cursor} if cursor else {}))
                page = self.request("POST", path, payload)
            else:
                sep = "&" if "?" in path else "?"
                page = self.request("GET", f"{path}{sep}page_size=100" + (f"&start_cursor={cursor}" if cursor else ""))
            yield from page.get("results", [])
            if not page.get("has_more"):
                return
            cursor = page.get("next_cursor")

    def database(self, db_id):
        return self.request("GET", f"/databases/{db_id}")

    def resolve(self, db_id, prefer=("도서", "책", "독서", "book")):
        """DB ID면 그대로, 페이지 ID면 그 안의 표 중 이름이 가장 맞는 것을 고른다. (DB ID, DB 정보)"""
        try:
            return db_id, self.database(db_id)
        except NotionError as error:
            first = error
        try:
            found = [b for b in self.paginate("GET", f"/blocks/{db_id}/children") if b.get("type") == "child_database"]
        except NotionError:
            raise first from None
        if not found:
            raise NotionError("이 페이지 안에서 표(DB)를 찾지 못했어요. 표가 있는 페이지 주소인지 확인해 주세요.")
        title = lambda b: b.get("child_database", {}).get("title", "")
        found.sort(key=lambda b: next((i for i, w in enumerate(prefer) if w in title(b)), len(prefer)))
        target = found[0]["id"].replace("-", "")
        return target, self.database(target)

    def pages(self, db_id):
        return self.paginate("POST", f"/databases/{db_id}/query", {})

    def children(self, block_id):
        return list(self.paginate("GET", f"/blocks/{block_id}/children"))


# ---------------------------------------------------------------- 속성 읽기
def _key(name):
    return re.sub(r"[\s_\-·]", "", (name or "").lower())


def match_properties(schema):
    """DB 속성 정의 {이름: {type: ...}} → {필드: 속성 이름}. 제목 속성은 type으로 찾는다."""
    found, used = {}, set()
    for name, prop in schema.items():
        if prop.get("type") == "title":
            found["title"] = name
            used.add(name)
    for field, names in PROP_NAMES.items():
        for name in schema:
            if name not in used and _key(name) in names:
                found[field] = name
                used.add(name)
                break
    for field, words in PROP_CONTAINS.items():  # 「독서 시작일」처럼 앞뒤에 말이 붙은 이름
        if field in found:
            continue
        for name, prop in schema.items():
            if name not in used and prop.get("type") in PROP_TYPES[field] and any(w in _key(name) for w in words):
                found[field] = name
                used.add(name)
                break
    if "cover" not in found:  # 이름이 달라도 파일 속성이 하나뿐이면 표지로 본다
        files = [n for n, p in schema.items() if p.get("type") == "files" and n not in used]
        if len(files) == 1:
            found["cover"] = files[0]
    return found


def plain_text(rich):
    return "".join(part.get("plain_text", "") for part in rich or []).strip()


def prop_value(prop):
    """속성 하나를 글자·숫자·날짜(시작, 끝)·파일 주소 목록으로 바꾼다."""
    if not prop:
        return None
    kind = prop.get("type")
    value = prop.get(kind)
    if kind in ("title", "rich_text"):
        return plain_text(value)
    if kind in ("select", "status"):
        return (value or {}).get("name")
    if kind == "multi_select":
        return ", ".join(v.get("name", "") for v in value or [])
    if kind == "number":
        return value
    if kind == "date":
        return ((value or {}).get("start"), (value or {}).get("end")) if value else None
    if kind == "people":
        return ", ".join(p.get("name", "") for p in value or [] if p.get("name"))
    if kind == "files":
        return [f.get(f.get("type"), {}).get("url") for f in value or [] if f.get(f.get("type"), {}).get("url")]
    if kind == "url":
        return value
    if kind == "formula":
        return (value or {}).get((value or {}).get("type"))
    if kind == "rollup":
        inner = (value or {}).get("array") or []
        return ", ".join(str(prop_value(v) or "") for v in inner) if inner else (value or {}).get("number")
    return None


def to_status(value):
    key = _key(str(value or ""))
    for status, words in STATUS_MAP:
        if any(w in key for w in words):
            return status
    return None


def to_rating(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        rating = float(value)
    else:
        text = str(value)
        stars = text.count("★") + text.count("⭐") + 0.5 * text.count("½")
        number = re.search(r"\d+(\.\d+)?", text)
        rating = stars or (float(number.group()) if number else 0)
    if rating > 5:  # 10점 만점 → 5점
        rating = rating / 2
    return round(rating * 2) / 2 if rating else None


def short_date(value):
    return value[:10].replace("-", ".") if value else None


def book_fields(page, mapping):
    props = page.get("properties", {})
    get = lambda field: prop_value(props.get(mapping[field])) if field in mapping else None
    data = {"title": get("title") or "제목 없음"}
    for field in ("author", "publisher", "genre", "summary", "record_type"):
        value = get(field)
        if value not in (None, ""):
            data[field] = str(value)[:2000 if field == "summary" else 160]
    status = to_status(get("status"))
    if status:
        data["status"] = status
    rating = to_rating(get("rating"))
    if rating is not None:
        data["rating"] = rating
    start, end = get("start_date"), get("finish_date")
    period = get("date")
    if isinstance(period, tuple):
        start = start or (period[0], None)
        end = end or (period[1] and (period[1], None))
    if isinstance(start, tuple):
        data["start_date"] = short_date(start[0])
    if isinstance(end, tuple):
        data["finish_date"] = short_date(end[0])
    if "status" not in data and data.get("finish_date"):  # 상태를 비워 둬도 완독일이 있으면 다 읽은 책
        data["status"] = "completed"
    data["title"] = data["title"].strip(" /")
    covers = get("cover")
    page_cover = (page.get("cover") or {})
    cover = (covers[0] if isinstance(covers, list) and covers else None) or page_cover.get(page_cover.get("type"), {}).get("url")
    if cover and "notion.so/images/page-cover" not in cover:  # 노션 기본 배경 그림은 표지가 아니다
        data["cover_source"] = cover
    return data


# ---------------------------------------------------------------- 본문 블록 → 사이트 블록
def rich_html(rich):
    """노션 글자 조각 → 사이트가 허용하는 꾸밈 HTML (저장 전에 sanitize_rich를 한 번 더 거친다)."""
    out = []
    for part in rich or []:
        text = escape(part.get("plain_text", "")).replace("\n", "<br>")
        if not text:
            continue
        note = part.get("annotations", {})
        if note.get("code"):
            text = f"<strong>{text}</strong>"
        if note.get("bold"):
            text = f"<strong>{text}</strong>"
        if note.get("italic"):
            text = f"<em>{text}</em>"
        if note.get("underline"):
            text = f"<u>{text}</u>"
        if note.get("strikethrough"):
            text = f"<s>{text}</s>"
        color = note.get("color", "default")
        if color.endswith("_background"):
            text = f'<mark class="hl">{text}</mark>'
        elif color in NOTION_COLOR:
            text = f'<span class="c-{NOTION_COLOR[color]}">{text}</span>'
        link = (part.get("href") or "")
        if link.startswith(("http://", "https://", "mailto:")):
            text = f'<a href="{escape(link)}">{text}</a>'
        out.append(text)
    return "".join(out)


def md_text(rich):
    """목록·표 같은 마크다운 블록 안에서 쓸 글자 (굵게·링크만 살린다)."""
    out = []
    for part in rich or []:
        text = part.get("plain_text", "")
        if not text.strip():
            out.append(text)
            continue
        if part.get("annotations", {}).get("bold"):
            text = f"**{text.strip()}**"
        if (part.get("href") or "").startswith(("http://", "https://")):
            text = f"[{text}]({part['href']})"
        out.append(text)
    return "".join(out).replace("\n", " ")


class Converter:
    def __init__(self, client, upload_image):
        self.client = client
        self.upload_image = upload_image  # (원본 주소) → 사이트 주소 또는 ""
        self.skipped = set()

    def file_url(self, block):
        data = block.get(block["type"], {})
        url = data.get(data.get("type"), {}).get("url", "")
        if data.get("type") == "file" and url:  # 1시간짜리 서명 주소 → 다시 올린다
            return self.upload_image(url)
        return url

    def convert(self, blocks, depth=0):
        result, pending = [], []  # pending: 이어지는 목록 줄을 마크다운 하나로 모은다

        def flush():
            if pending:
                result.append({"type": "markdown", "text": "\n".join(pending)})
                pending.clear()

        number = 0
        for block in blocks:
            kind = block.get("type")
            data = block.get(kind, {}) if kind else {}
            children = self.client.children(block["id"]) if block.get("has_children") and kind not in ("child_page", "child_database") else []
            if kind in ("bulleted_list_item", "numbered_list_item", "to_do"):
                number = number + 1 if kind == "numbered_list_item" else 0
                pending.extend(self.list_lines(block, children, 0, number))
                continue
            number = 0
            flush()
            text = rich_html(data.get("rich_text"))
            if kind == "paragraph":
                if text:
                    result.append({"type": "paragraph", "rich": text, "text": plain_text(data.get("rich_text"))})
            elif kind in ("heading_1", "heading_2", "heading_3"):
                if text:
                    result.append({"type": "heading", "text": plain_text(data.get("rich_text"))})
            elif kind == "quote":
                if text:
                    result.append({"type": "quote", "rich": text, "text": plain_text(data.get("rich_text"))})
            elif kind == "callout":
                if text:
                    result.append({"type": "callout", "rich": text, "text": plain_text(data.get("rich_text"))})
            elif kind == "toggle":
                if text:
                    result.append({"type": "paragraph", "rich": f"<strong>{text}</strong>", "text": plain_text(data.get("rich_text"))})
            elif kind == "divider":
                result.append({"type": "divider"})
            elif kind == "image":
                url = self.file_url(block)
                if url:
                    result.append({"type": "image", "url": url, "caption": plain_text(data.get("caption"))})
            elif kind in ("video", "embed", "bookmark", "link_preview"):
                url = data.get("url") or data.get(data.get("type"), {}).get("url", "")
                if "youtu" in url:
                    result.append({"type": "youtube", "url": url, "caption": plain_text(data.get("caption"))})
                elif "instagram.com" in url:
                    result.append({"type": "instagram", "url": url})
                elif url.startswith("http"):
                    result.append({"type": "paragraph", "rich": f'<a href="{escape(url)}">{escape(plain_text(data.get("caption")) or url)}</a>', "text": url})
            elif kind == "code":
                code = plain_text(data.get("rich_text"))
                if code:
                    result.append({"type": "markdown", "text": f"```\n{code}\n```"})
            elif kind == "table":
                rows = [[md_text(cell) for cell in row.get("table_row", {}).get("cells", [])] for row in children]
                if rows:
                    lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * len(rows[0])]
                    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
                    result.append({"type": "markdown", "text": "\n".join(lines)})
                continue
            elif kind in ("column_list", "column", "synced_block"):
                pass  # 안쪽 블록만 꺼낸다
            elif kind == "child_page":
                self.skipped.add(kind)
                continue  # 하위 페이지는 따로 불러온다
            elif kind:
                self.skipped.add(kind)
            if children and kind != "table":
                result.extend(self.convert(children, depth + 1))
        flush()
        return result

    def list_lines(self, block, children, indent, number):
        kind = block["type"]
        data = block.get(kind, {})
        text = md_text(data.get("rich_text"))
        if kind == "to_do":
            bullet = "- " + ("☑ " if data.get("checked") else "☐ ")
        elif kind == "numbered_list_item":
            bullet = f"{number}. "
        else:
            bullet = "- "
        lines = ["    " * indent + bullet + text]
        n = 0
        for child in children:
            ckind = child.get("type")
            if ckind in ("bulleted_list_item", "numbered_list_item", "to_do"):
                n = n + 1 if ckind == "numbered_list_item" else 0
                grand = self.client.children(child["id"]) if child.get("has_children") else []
                lines.extend(self.list_lines(child, grand, indent + 1, n))
            else:
                inner = md_text(child.get(ckind, {}).get("rich_text"))
                if inner:
                    lines.append("    " * (indent + 1) + inner)
        return lines


# ---------------------------------------------------------------- 실행
def upload_notion_image(url):
    """노션 파일(1시간짜리 주소)을 내려받아 Storage notion/에 올린다. 실패하면 ""."""
    from storage import put_bytes
    try:
        with urllib.request.urlopen(url, timeout=30) as res:
            kind = res.headers.get("Content-Type", "").split(";")[0]
            ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}.get(kind)
            return put_bytes(res.read(), ext, "notion") if ext else ""
    except Exception:
        return ""


def page_title(page):
    for prop in (page.get("properties") or {}).values():
        if prop.get("type") == "title":
            return plain_text(prop.get("title"))
    return ""


def page_tree(token, root_id, max_depth=2, limit=300):
    """페이지와 그 아래 하위 페이지 목록 [{id, title, depth}] (본문은 읽지 않는다)."""
    client = Client(token)
    root = client.request("GET", f"/pages/{root_id}")
    items = [{"id": root_id, "title": page_title(root) or "제목 없음", "depth": 0}]

    def walk(block_id, depth):
        for block in client.paginate("GET", f"/blocks/{block_id}/children"):
            if len(items) >= limit:
                return
            if block.get("type") == "child_page":
                items.append({"id": block["id"].replace("-", ""), "title": block["child_page"].get("title") or "제목 없음", "depth": depth})
                if depth < max_depth and block.get("has_children"):
                    walk(block["id"], depth + 1)
            elif block.get("has_children") and block.get("type") in ("toggle", "column_list", "column", "synced_block", "callout"):
                walk(block["id"], depth)

    walk(root_id, 1)
    return items


def page_blocks(token, page_id):
    """페이지 하나의 본문 → 사이트 블록. 하위 페이지는 따로 불러오므로 넣지 않는다."""
    from content import normalize_blocks
    client = Client(token)
    page = client.request("GET", f"/pages/{page_id}")
    converter = Converter(client, upload_notion_image)
    blocks = normalize_blocks(converter.convert(client.children(page_id)))
    converter.skipped.discard("child_page")
    converter.skipped.discard("child_database")
    return {"title": page_title(page), "blocks": blocks, "skipped": sorted(converter.skipped)}


def ignored_pages():
    from models import Profile
    profile = Profile.query.first()
    return set((profile.extra or {}).get("notion_ignore") or []) if profile else set()


def ignore_page(page_id):
    """사이트에서 지운 노션 책은 다음 가져오기 때 다시 만들지 않는다."""
    from models import Profile
    profile = Profile.query.first()
    if profile and page_id:
        extra = dict(profile.extra or {})
        extra["notion_ignore"] = sorted(set(extra.get("notion_ignore") or []) | {page_id})
        profile.extra = extra

def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None) if value else None


def inspect(token, db_value):
    """연결 확인용: DB 이름, 속성 목록, 맞춘 속성을 돌려준다 (내용은 읽지 않는다)."""
    client = Client(token)
    db_id = database_id(db_value)
    if not db_id:
        raise NotionError("NOTION_READING_DB에서 DB ID를 찾지 못했어요. DB 주소를 그대로 넣어 주세요.")
    db_id, info = client.resolve(db_id)
    schema = info.get("properties", {})
    return {"title": plain_text(info.get("title")) or "제목 없는 DB",
            "properties": {name: p.get("type") for name, p in schema.items()},
            "mapping": match_properties(schema)}


def kakao_fill(book, put_bytes):
    """표지가 없는 책은 카카오 책 검색으로 표지·출판사·저자를 채운다. 키가 없거나 못 찾으면 그냥 둔다."""
    import books_api
    from flask import current_app

    key = current_app.config.get("KAKAO_REST_API_KEY")
    if not key or book.cover_image:
        return False
    plain = re.sub(r"\(.*?\)|\[.*?\]", " ", book.title)          # 「(7월의 도서)」 같은 꾸밈 떼기
    plain = re.sub(r"[.\-·,/?!]+", " ", plain).strip()              # 총.균.쇠 → 총 균 쇠
    want = _key(re.sub(r"[:].*$", "", plain)).replace(" ", "")
    hit = None
    for query in (f"{book.title} {book.author or ''}".strip(), plain, re.sub(r"[:].*$", "", plain)):
        try:
            results = books_api.search(key, query, size=5)
        except books_api.BookSearchError:
            return False
        norm = lambda t: re.sub(r"[^\w]", "", t.lower())
        hit = next((r for r in results if want and norm(want) in norm(r["title"])), None) or \
              next((r for r in results if norm(r["title"]) and norm(r["title"]) in norm(want)), None)
        if hit:
            break
    if not hit:
        return False
    if not book.publisher and hit["publisher"]:
        book.publisher = hit["publisher"][:160]
    if not book.author and hit["author"]:
        book.author = hit["author"][:160]
    try:
        data, ext = books_api.download_cover(hit["cover"] or hit["thumbnail"])
        book.cover_image = put_bytes(data, ext, "covers")
    except Exception:
        return False
    return True


def sync(token, db_value, full=False, with_notes=False):
    """노션 → DB. 결과 dict(created, updated, notes, skipped, unchanged, message)를 돌려준다. commit은 부른 쪽에서.
    with_notes=False면 책 정보(책장)만 가져오고, 페이지 본문(독서 노트)은 건드리지 않는다."""
    from admin import unique_slug
    from content import normalize_blocks
    from models import Archive, Book, db
    from storage import put_bytes

    client = Client(token)
    db_id = database_id(db_value)
    if not db_id:
        raise NotionError("NOTION_READING_DB에서 DB ID를 찾지 못했어요. DB 주소를 그대로 넣어 주세요.")
    db_id, info = client.resolve(db_id)
    schema = info.get("properties", {})
    mapping = match_properties(schema)

    upload_image = upload_notion_image
    ignore = ignored_pages()
    converter = Converter(client, upload_image)
    stats = {"created": 0, "updated": 0, "notes": 0, "unchanged": 0, "skipped": 0, "held": 0, "covers": 0}
    now = datetime.utcnow()
    for page in client.pages(db_id):
        if page.get("archived") or page.get("in_trash"):
            stats["skipped"] += 1
            continue
        page_id = page["id"].replace("-", "")
        if page_id in ignore:
            stats["skipped"] += 1
            continue
        edited = parse_time(page.get("last_edited_time"))
        book = Book.query.filter_by(notion_page_id=page_id).first() or Book.query.filter_by(notion_url=page.get("url")).first()
        if book and not full and book.notion_last_edited_at and edited and book.notion_last_edited_at >= edited:
            stats["unchanged"] += 1
            continue
        data = book_fields(page, mapping)
        if data.get("status") == "hold":
            stats["held"] += 1
            if book is not None and not Archive.query.filter_by(book_id=book.id).count():
                db.session.delete(book)  # 이미 꽂혀 있던 책을 보류로 바꾸면 책장에서 뺀다 (노트가 달린 책은 남긴다)
                stats["removed"] = stats.get("removed", 0) + 1
            continue
        if book is None:
            book = Book.query.filter(Book.notion_page_id.is_(None), Book.title == data["title"]).first()  # 손으로 넣은 같은 책
        if book is None:
            book = Book(title=data["title"], status="reading")
            db.session.add(book)
            stats["created"] += 1
        else:
            stats["updated"] += 1
        for field in ("title", "author", "publisher", "genre", "record_type", "summary", "status", "rating", "start_date", "finish_date"):
            if field in data:
                setattr(book, field, data[field])
        if data.get("cover_source"):
            src = data["cover_source"]
            stored = upload_image(src) if "amazonaws.com" in src or "notion" in src.split("/")[2] else src
            if stored:
                book.cover_image = stored
        if kakao_fill(book, put_bytes):
            stats["covers"] += 1
        book.notion_page_id, book.notion_url = page_id, page.get("url")
        book.notion_last_edited_at, book.synced_at = edited, now
        db.session.flush()
        if not with_notes:
            continue

        blocks = normalize_blocks(converter.convert(client.children(page["id"])))
        post = Archive.query.filter_by(source_type="notion", source_url=page.get("url")).first()
        if not blocks and post is None:
            continue
        if post is None:
            post = Archive(title=book.title, category="독서 노트", content_type="reading", status="draft",
                           source_type="notion", source_url=page.get("url"), design={"accent": "mint"})
            post.slug = unique_slug(Archive, book.title, None)
            db.session.add(post)
            stats["notes"] += 1
        post.book_id = book.id
        post.blocks = blocks
        if not post.summary and book.summary:
            post.summary = book.summary[:300]
        post.notion_last_edited_at, post.synced_at = edited, now
        db.session.flush()

    unmapped = [n for n in schema if n not in mapping.values()]
    message = f"DB 속성 연결: {', '.join(f'{k}←{v}' for k, v in mapping.items())}"
    if unmapped:
        message += f" · 안 쓴 속성: {', '.join(unmapped)}"
    if converter.skipped:
        message += f" · 옮기지 않은 블록: {', '.join(sorted(converter.skipped))}"
    stats["message"] = message[:500]
    stats["calls"] = client.calls
    return stats
