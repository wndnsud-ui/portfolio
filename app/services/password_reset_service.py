import hashlib
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.parse import urlencode
from sqlalchemy import update
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.exceptions import AppError
from app.models.user import User, PasswordReset
from app.services.auth_service import hash_password

def send_reset_email(email: str, token: str):
    message = EmailMessage()
    message["Subject"] = "DecisionFlow 비밀번호 재설정"
    message["From"] = settings.smtp_from
    message["To"] = email
    link = settings.frontend_url.rstrip("/") + "/#" + urlencode({"reset_token": token})
    message.set_content(f"비밀번호를 재설정하려면 다음 링크를 열어 주세요.\n\n{link}\n\n30분 동안 한 번만 사용할 수 있습니다. 요청하지 않았다면 무시하세요.")
    factory = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
    with factory(settings.smtp_host, settings.smtp_port, timeout=15) as client:
        if not settings.smtp_ssl:
            client.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)

def request_reset(db: Session, email: str):
    if not settings.smtp_host or not settings.smtp_from:
        raise AppError("MAIL_NOT_CONFIGURED", "비밀번호 재설정 메일 서비스가 아직 설정되지 않았습니다.", 503)
    user = db.query(User).filter_by(email=email.strip().lower()).first()
    if not user or not user.password_hash:
        return
    now = datetime.utcnow()
    # Limit email deliveries to one per minute and five per hour per account.
    recent = db.query(PasswordReset).filter(PasswordReset.user_id == user.id, PasswordReset.created_at > now-timedelta(hours=1)).all()
    if len(recent) >= 5 or any(row.created_at > now-timedelta(minutes=1) for row in recent):
        return
    token = secrets.token_urlsafe(32)
    db.add(PasswordReset(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=now+timedelta(minutes=30)))
    try:
        send_reset_email(user.email, token)
        db.commit()
    except (OSError, smtplib.SMTPException):
        db.rollback()
        raise AppError("MAIL_DELIVERY_FAILED", "메일을 보내지 못했습니다. 잠시 후 다시 시도해 주세요.", 503)

def reset_password(db: Session, token: str, password: str):
    now = datetime.utcnow()
    row = db.query(PasswordReset).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    if not row or row.used_at or row.expires_at <= now:
        raise AppError("INVALID_RESET", "재설정 링크가 만료되었거나 이미 사용되었습니다.", 400)
    # Conditional claim makes concurrent uses of the same link fail.
    claimed = db.execute(update(PasswordReset).where(PasswordReset.id == row.id, PasswordReset.used_at.is_(None)).values(used_at=now))
    if claimed.rowcount != 1:
        db.rollback()
        raise AppError("INVALID_RESET", "이미 사용된 재설정 링크입니다.", 400)
    user = db.get(User, row.user_id)
    user.password_hash = hash_password(password)
    user.auth_version += 1
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None)).update({"used_at": now})
    db.commit()
