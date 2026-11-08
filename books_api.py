"""카카오 책 검색. 키는 서버에만 두고, 고른 표지는 우리 저장소(Supabase Storage)로 복사한다."""
import json
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL = "https://dapi.kakao.com/v3/search/book"
COVER_HOSTS = {"search1.kakaocdn.net", "t1.daumcdn.net", "t1.kakaocdn.net"}
MAX_COVER_BYTES = 5 * 1024 * 1024
IMAGE_MAGIC = ((b"\xff\xd8\xff", "jpg"), (b"\x89PNG", "png"), (b"GIF8", "gif"), (b"RIFF", "webp"))


class BookSearchError(Exception):
    pass


def _large_cover(thumbnail):
    """검색 결과의 작은 썸네일(120×174) 대신 원본 이미지 주소를 쓴다. 없으면 썸네일 그대로."""
    if not thumbnail:
        return ""
    query = urllib.parse.parse_qs(urllib.parse.urlparse(thumbnail).query)
    original = (query.get("fname") or [""])[0]
    if original.startswith("http://"):
        original = "https://" + original[len("http://"):]
    return original if is_cover_url(original) else thumbnail


def search(api_key, query, size=10):
    if not api_key:
        raise BookSearchError("카카오 REST API 키(KAKAO_REST_API_KEY)가 설정되지 않았습니다.")
    query = (query or "").strip()[:100]
    if not query:
        return []
    url = f"{SEARCH_URL}?{urllib.parse.urlencode({'query': query, 'size': size})}"
    request = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {api_key}"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise BookSearchError("카카오 API 키가 올바르지 않거나 권한이 없습니다.") from error
        raise BookSearchError(f"카카오 검색 오류 ({error.code})") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise BookSearchError("카카오 서버에 연결하지 못했습니다.") from error
    results = []
    for doc in data.get("documents", []):
        results.append({
            "title": doc.get("title", ""),
            "author": ", ".join(doc.get("authors") or []),
            "translator": ", ".join(doc.get("translators") or []),
            "publisher": doc.get("publisher", ""),
            "year": (doc.get("datetime") or "")[:4],
            "isbn": doc.get("isbn", ""),
            "thumbnail": doc.get("thumbnail", ""),
            "cover": _large_cover(doc.get("thumbnail", "")),
        })
    return results


def is_cover_url(url):
    parsed = urllib.parse.urlparse(url or "")
    return parsed.scheme == "https" and parsed.hostname in COVER_HOSTS


def download_cover(url):
    """카카오 이미지 서버의 표지만 받는다(다른 주소는 거부). (바이트, 확장자)를 돌려준다."""
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not is_cover_url(url):
        raise BookSearchError("카카오 표지 주소만 가져올 수 있습니다.")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "hy-archive"}), timeout=10) as response:
            data = response.read(MAX_COVER_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as error:
        raise BookSearchError("표지 이미지를 받지 못했습니다.") from error
    if len(data) > MAX_COVER_BYTES:
        raise BookSearchError("표지 이미지가 너무 큽니다.")
    for magic, extension in IMAGE_MAGIC:
        if data.startswith(magic):
            return data, extension
    raise BookSearchError("표지가 이미지 파일이 아닙니다.")
