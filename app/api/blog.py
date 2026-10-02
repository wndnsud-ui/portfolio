import re
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.blog_post import BlogPost
from app.models.meeting import Meeting
from app.models.project import Project
from app.models.user import User
from app.schemas.blog import BlogGenerateRequest, BlogPostCreate, BlogPostRead, BlogPostUpdate

router = APIRouter(prefix="/blog", tags=["Blog"])


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", title.strip().lower()).strip("-")
    return slug or f"post-{int(datetime.utcnow().timestamp())}"


def unique_slug(db: Session, title: str) -> str:
    base = slugify(title)
    slug = base
    index = 2
    while db.query(BlogPost).filter(BlogPost.slug == slug).first():
        slug = f"{base}-{index}"
        index += 1
    return slug


def get_owned_post(db: Session, post_id: int, user: User) -> BlogPost:
    post = db.query(BlogPost).filter(BlogPost.id == post_id, BlogPost.user_id == user.id).first()
    if not post:
        raise AppError("BLOG_POST_NOT_FOUND", "Blog post not found.", 404)
    return post


@router.post("", response_model=BlogPostRead)
async def create_blog_post(payload: BlogPostCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> BlogPost:
    post = BlogPost(**payload.model_dump(), user_id=current_user.id, slug=unique_slug(db, payload.title))
    if post.status == "published":
        post.published_at = datetime.utcnow()
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("", response_model=list[BlogPostRead])
async def list_blog_posts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[BlogPost]:
    return db.query(BlogPost).filter(BlogPost.user_id == current_user.id).order_by(BlogPost.updated_at.desc()).all()


@router.get("/public", response_model=list[BlogPostRead])
async def list_public_posts(db: Session = Depends(get_db)) -> list[BlogPost]:
    return db.query(BlogPost).filter(BlogPost.status == "published").order_by(BlogPost.published_at.desc()).all()


@router.get("/{slug}", response_model=BlogPostRead)
async def read_public_post(slug: str, db: Session = Depends(get_db)) -> BlogPost:
    post = db.query(BlogPost).filter(BlogPost.slug == slug, BlogPost.status == "published").first()
    if not post:
        raise AppError("BLOG_POST_NOT_FOUND", "Blog post not found.", 404)
    return post


@router.patch("/{post_id}", response_model=BlogPostRead)
async def update_blog_post(post_id: int, payload: BlogPostUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> BlogPost:
    post = get_owned_post(db, post_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"] != post.title:
        post.slug = unique_slug(db, data["title"])
    for key, value in data.items():
        setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=204)
async def delete_blog_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    db.delete(get_owned_post(db, post_id, current_user))
    db.commit()


@router.post("/generate", response_model=BlogPostRead)
async def generate_blog_post(payload: BlogGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> BlogPost:
    if payload.source_type == "meeting":
        source = db.query(Meeting).filter(Meeting.id == payload.source_id, Meeting.user_id == current_user.id).first()
        if not source:
            raise AppError("SOURCE_NOT_FOUND", "Meeting source not found.", 404)
        title = f"{source.title} 정리"
        content = f"# {title}\n\n## 배경\n{source.summary or '회의 내용을 바탕으로 초안을 작성했습니다.'}\n\n## 주요 내용\n{source.discussion or ''}\n\n## 배운 점\n원문 기록을 확인하며 보완해 주세요."
    elif payload.source_type == "project":
        source = db.query(Project).filter(Project.id == payload.source_id, Project.user_id == current_user.id).first()
        if not source:
            raise AppError("SOURCE_NOT_FOUND", "Project source not found.", 404)
        title = f"{source.name} 개발 기록"
        content = f"# {title}\n\n## 개요\n{source.description or ''}\n\n## 진행 과정\n프로젝트 기록을 바탕으로 내용을 보완해 주세요."
    else:
        raise AppError("UNSUPPORTED_SOURCE", "Only meeting and project sources are supported in this MVP.", 400)
    post = BlogPost(user_id=current_user.id, title=title, slug=unique_slug(db, title), summary=f"{payload.content_type} 초안", content=content, category=payload.content_type, source_type=payload.source_type, source_id=payload.source_id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/publish", response_model=BlogPostRead)
async def publish_blog_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> BlogPost:
    post = get_owned_post(db, post_id, current_user)
    post.status = "published"
    post.published_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/unpublish", response_model=BlogPostRead)
async def unpublish_blog_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> BlogPost:
    post = get_owned_post(db, post_id, current_user)
    post.status = "draft"
    post.published_at = None
    db.commit()
    db.refresh(post)
    return post
