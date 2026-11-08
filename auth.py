"""관리자 1명 로그인. 사용자 테이블 없이 환경변수(ADMIN_USERNAME, ADMIN_PASSWORD_HASH)로 확인한다."""
import hmac
import time
from functools import wraps

from flask import current_app, redirect, request, session, url_for
from werkzeug.security import check_password_hash

MAX_FAILURES = 5
LOCK_SECONDS = 10 * 60
_failures = {}  # ip -> (실패 횟수, 마지막 실패 시각)


def client_ip():
    # ProxyFix가 프록시 한 단계의 X-Forwarded-For로 remote_addr를 맞춰 준다. 헤더를 직접 읽으면 위조할 수 있다.
    return request.remote_addr or "unknown"


def locked_seconds(ip):
    count, last = _failures.get(ip, (0, 0))
    if count >= MAX_FAILURES:
        left = LOCK_SECONDS - (time.time() - last)
        if left > 0:
            return int(left)
        _failures.pop(ip, None)
    return 0


def check_credentials(username, password):
    cfg = current_app.config
    expected_user, password_hash = cfg.get("ADMIN_USERNAME"), cfg.get("ADMIN_PASSWORD_HASH")
    if not expected_user or not password_hash:
        return False
    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    try:
        password_ok = check_password_hash(password_hash, password)
    except ValueError:
        password_ok = False
    return user_ok and password_ok


def record_failure(ip):
    count, _ = _failures.get(ip, (0, 0))
    _failures[ip] = (count + 1, time.time())


def clear_failures(ip):
    _failures.pop(ip, None)


def login_admin():
    session.clear()
    session["admin"] = True
    session.permanent = True


def is_admin():
    return bool(session.get("admin"))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin():
            if request.is_json or request.path.startswith("/admin/api/"):
                return {"ok": False, "error": "login required"}, 401
            return redirect(url_for("admin.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped
