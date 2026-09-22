from pathlib import Path
from uuid import uuid4
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort
import markdown
from sqlalchemy import inspect, or_, text
from werkzeug.utils import secure_filename
from config import Config
from models import db, Profile, Project, Experience, Skill, Archive, RecordComment
from seed import seed_database

app = Flask(__name__)
app.config.from_object(Config)
Path(app.instance_path).mkdir(parents=True, exist_ok=True)
RECORD_UPLOAD_DIR = Path(app.static_folder) / "uploads" / "records"
RECORD_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
BLOG_CATEGORIES = ["맛집 · 카페", "여행", "사주 연구", "독서 모임"]
ARCHIVE_CATEGORIES = ["AI / ML", "DATA", "DEVELOPMENT", "PROJECT", "LECTURE", "CERTIFICATION", "WORK", "THINKING"]
db.init_app(app)

with app.app_context():
    db.create_all()
    # create_all() does not add columns to an existing SQLite table.
    existing = {column["name"] for column in inspect(db.engine).get_columns("archive")}
    record_columns = {"content_type": "VARCHAR(40) NOT NULL DEFAULT 'archive'", "tags": "VARCHAR(400)", "thumbnail": "VARCHAR(400)", "source_type": "VARCHAR(80)", "source_url": "VARCHAR(400)", "is_featured": "BOOLEAN NOT NULL DEFAULT 0", "is_pinned": "BOOLEAN NOT NULL DEFAULT 0", "view_count": "INTEGER NOT NULL DEFAULT 0", "like_count": "INTEGER NOT NULL DEFAULT 0", "recommendation_count": "INTEGER NOT NULL DEFAULT 0"}
    for name, definition in record_columns.items():
        if name not in existing:
            db.session.execute(text(f"ALTER TABLE archive ADD COLUMN {name} {definition}"))
    db.session.commit()
    seed_database()
    project_links = {
        "Mood Code": ("https://mood-code-latest.onrender.com/", "/static/images/moodcode.png"),
        "CaloDetect": ("https://iris-app-app-huwkr4lpdcttdyjviv6cec.streamlit.app/", "/static/images/calodetect.svg"),
    }
    for title, (url, thumbnail) in project_links.items():
        project = Project.query.filter_by(title=title).first()
        if project:
            project.github_url = url
            project.thumbnail = thumbnail
    db.session.commit()

@app.context_processor
def globals_for_templates():
    return {"profile": Profile.query.first(), "project_count": Project.query.count(), "archive_count": Archive.query.filter_by(content_type="archive").count(), "skill_count": Skill.query.count(), "blog_categories": BLOG_CATEGORIES, "archive_categories": ARCHIVE_CATEGORIES}

@app.route("/profile-image")
def profile_image():
    image = Path(app.root_path).parent / "profile" / "image" / "IMG_6733.jpeg"
    if not image.exists(): abort(404)
    return send_file(image)

@app.route("/")
def home():
    return render_template("home-reference.html", projects=Project.query.order_by(Project.id).all(), experiences=Experience.query.order_by(Experience.sort_order).all(), skills=Skill.query.order_by(Skill.category, Skill.sort_order).all(), archives=Archive.query.filter_by(content_type="archive").order_by(Archive.created_at.desc()).limit(5).all())

@app.route("/projects")
def projects(): return render_template("projects/list.html", projects=Project.query.order_by(Project.id).all())

@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template("projects/detail.html", project=project)

@app.route("/archive")
def archive():
    category = request.args.get("category", "ALL")
    query = Archive.query.filter_by(content_type="archive").order_by(Archive.created_at.desc())
    if category != "ALL": query = query.filter_by(category=category)
    return render_template("archive/list.html", archives=query.all(), category=category)

@app.route("/archive/<int:archive_id>")
def archive_detail(archive_id):
    record = Archive.query.filter_by(content_type="archive", id=archive_id).first_or_404()
    record.view_count += 1; db.session.commit()
    rendered_content = markdown.markdown(record.content or "", extensions=["extra", "fenced_code", "tables"])
    return render_template("records/detail.html", record=record, rendered_content=rendered_content, back_url=url_for("archive"), back_label="아카이브")

def content_detail_url(record):
    if record.content_type == "blog": return url_for("blog_detail", record_id=record.id)
    if record.content_type == "archive": return url_for("archive_detail", archive_id=record.id)
    return url_for("record_detail", record_id=record.id)

def record_query():
    sort = request.args.get("sort", "latest")
    query = Archive.query
    if sort == "popular": query = query.order_by(Archive.recommendation_count.desc(), Archive.like_count.desc(), Archive.view_count.desc(), Archive.created_at.desc())
    else: query = query.order_by(Archive.is_pinned.desc(), Archive.created_at.desc())
    category = request.args.get("category", "ALL")
    if category != "ALL": query = query.filter_by(category=category)
    return query, category, sort

@app.route("/records")
def records():
    query, category, sort = record_query()
    return render_template("records/list.html", records=query.all(), category=category, sort=sort)

@app.route("/blog")
def blog():
    category = request.args.get("category", "ALL")
    search = request.args.get("q", "").strip()
    query = Archive.query.filter_by(content_type="blog").order_by(Archive.is_pinned.desc(), Archive.created_at.desc())
    if category != "ALL":
        query = query.filter_by(category=category)
    if search:
        keyword = f"%{search}%"
        query = query.filter(or_(Archive.title.ilike(keyword), Archive.summary.ilike(keyword), Archive.content.ilike(keyword), Archive.tags.ilike(keyword)))
    categories = BLOG_CATEGORIES
    posts = query.all()
    featured = next((post for post in posts if post.is_featured or post.thumbnail), posts[0] if posts else None)
    return render_template("blog/list.html", posts=posts, featured=featured, categories=categories, category=category, search=search)

@app.route("/blog/<int:record_id>")
def blog_detail(record_id):
    record = Archive.query.filter_by(content_type="blog", id=record_id).first_or_404()
    record.view_count += 1; db.session.commit()
    rendered_content = markdown.markdown(record.content or "", extensions=["extra", "fenced_code", "tables"])
    return render_template("records/detail.html", record=record, rendered_content=rendered_content, back_url=url_for("blog"), back_label="블로그")

def save_record_image(image):
    if not image or not image.filename:
        return None
    original_name = secure_filename(image.filename)
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("PNG, JPG, GIF, WEBP 이미지만 업로드할 수 있습니다.")
    filename = f"{uuid4().hex}.{extension}"
    image.save(RECORD_UPLOAD_DIR / filename)
    return f"/static/uploads/records/{filename}"

def remove_record_image(image_url):
    prefix = "/static/uploads/records/"
    if not image_url or not image_url.startswith(prefix):
        return
    image_path = (RECORD_UPLOAD_DIR / Path(image_url).name).resolve()
    if image_path.parent == RECORD_UPLOAD_DIR.resolve() and image_path.exists():
        image_path.unlink()

@app.route("/records/new", methods=["GET", "POST"])
def new_record():
    content_type = request.args.get("type", "archive").lower()
    if content_type not in {"archive", "blog"}: content_type = "archive"
    if request.method == "POST":
        content_type = request.form.get("content_type", "archive").lower()
        if content_type not in {"archive", "blog"}: content_type = "archive"
        allowed_categories = BLOG_CATEGORIES if content_type == "blog" else ARCHIVE_CATEGORIES
        category = request.form.get("category", allowed_categories[0])
        if category not in allowed_categories: category = allowed_categories[0]
        if not request.form.get("title", "").strip() or not request.form.get("content", "").strip():
            flash("Title과 Content는 필수입니다.", "error")
            return render_template("records/form.html", record=None, content_type=content_type)
        try:
            thumbnail = save_record_image(request.files.get("thumbnail"))
        except ValueError as error:
            flash(str(error), "error")
            return render_template("records/form.html", record=None, content_type=content_type)
        record = Archive(title=request.form["title"].strip(), category=category, summary=request.form.get("summary"), content=request.form["content"], content_type=content_type, tags=request.form.get("tags"), thumbnail=thumbnail, source_type=request.form.get("source_type"), source_url=request.form.get("source_url"), is_featured="is_featured" in request.form, is_pinned="is_pinned" in request.form)
        db.session.add(record); db.session.commit(); return redirect(content_detail_url(record))
    return render_template("records/form.html", record=None, content_type=content_type)

@app.route("/archive/new")
def archive_new_redirect():
    return redirect(url_for("new_record"))

@app.route("/records/<int:record_id>")
def record_detail(record_id):
    record = Archive.query.get_or_404(record_id)
    record.view_count += 1; db.session.commit()
    rendered_content = markdown.markdown(record.content or "", extensions=["extra", "fenced_code", "tables"])
    return render_template("records/detail.html", record=record, rendered_content=rendered_content, back_url=url_for("records"), back_label="기록 목록")

@app.post("/records/<int:record_id>/like")
def like_record(record_id):
    record = Archive.query.get_or_404(record_id)
    liked_records = set(session.get("liked_records", []))
    if record_id in liked_records:
        record.like_count = max(0, record.like_count - 1); liked_records.remove(record_id)
    else:
        record.like_count += 1; liked_records.add(record_id)
    session["liked_records"] = list(liked_records); db.session.commit()
    return redirect(request.referrer or url_for("record_detail", record_id=record.id))

@app.post("/records/<int:record_id>/recommend")
def recommend_record(record_id):
    record = Archive.query.get_or_404(record_id)
    recommended_records = set(session.get("recommended_records", []))
    if record_id in recommended_records:
        record.recommendation_count = max(0, record.recommendation_count - 1); recommended_records.remove(record_id)
    else:
        record.recommendation_count += 1; recommended_records.add(record_id)
    session["recommended_records"] = list(recommended_records); db.session.commit()
    return redirect(request.referrer or url_for("record_detail", record_id=record.id))

@app.post("/records/<int:record_id>/comments")
def add_comment(record_id):
    record = Archive.query.get_or_404(record_id)
    author = request.form.get("author", "Anonymous").strip() or "Anonymous"
    content = request.form.get("content", "").strip()
    if content:
        db.session.add(RecordComment(record_id=record_id, author=author, content=content)); db.session.commit()
    return redirect(content_detail_url(record) + "#comments")

@app.route("/records/<int:record_id>/edit", methods=["GET", "POST"])
def edit_record(record_id):
    record = Archive.query.get_or_404(record_id)
    if request.method == "POST":
        for field in ["title", "summary", "content", "tags", "source_type", "source_url"]:
            setattr(record, field, request.form.get(field))
        requested_type = request.form.get("content_type", record.content_type).lower()
        record.content_type = requested_type if requested_type in {"archive", "blog"} else record.content_type
        allowed_categories = BLOG_CATEGORIES if record.content_type == "blog" else ARCHIVE_CATEGORIES
        requested_category = request.form.get("category", record.category)
        record.category = requested_category if requested_category in allowed_categories else allowed_categories[0]
        try:
            new_thumbnail = save_record_image(request.files.get("thumbnail"))
        except ValueError as error:
            flash(str(error), "error")
            return render_template("records/form.html", record=record)
        if "remove_thumbnail" in request.form:
            remove_record_image(record.thumbnail); record.thumbnail = None
        if new_thumbnail:
            remove_record_image(record.thumbnail); record.thumbnail = new_thumbnail
        record.is_featured = "is_featured" in request.form; record.is_pinned = "is_pinned" in request.form
        db.session.commit(); return redirect(content_detail_url(record))
    return render_template("records/form.html", record=record)

@app.post("/records/<int:record_id>/delete")
def delete_record(record_id):
    record = Archive.query.get_or_404(record_id)
    content_type = record.content_type
    remove_record_image(record.thumbnail)
    db.session.delete(record); db.session.commit()
    flash("기록을 삭제했습니다.", "success")
    return redirect(url_for("blog" if content_type == "blog" else "archive" if content_type == "archive" else "records"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == "hyarchive": session["admin"] = True; return redirect(url_for("admin"))
        flash("비밀번호가 올바르지 않습니다.", "error")
    return render_template("admin/login.html")

@app.before_request
def protect_admin():
    if request.path.startswith("/admin") and request.endpoint != "admin_login" and not session.get("admin"): return redirect(url_for("admin_login"))

@app.route("/admin")
def admin(): return render_template("admin/dashboard.html", projects=Project.query.all(), experiences=Experience.query.all(), skills=Skill.query.all(), archives=Archive.query.all())

@app.post("/admin/<string:model>/<int:item_id>/delete")
def delete_item(model, item_id):
    mapping = {"projects": Project, "experiences": Experience, "skills": Skill, "archive": Archive}
    item = mapping.get(model, Archive).query.get_or_404(item_id); db.session.delete(item); db.session.commit(); flash("삭제했습니다.", "success"); return redirect(url_for("admin"))

@app.post("/admin/<string:model>/create")
def create_item(model):
    data = request.form
    if model == "projects": item = Project(title=data.get("title", "Untitled"), subtitle=data.get("subtitle"), description=data.get("description"), tech_stack=data.get("tech_stack"))
    elif model == "experiences": item = Experience(company=data.get("company", "New"), position=data.get("position"), start_date=data.get("start_date"), end_date=data.get("end_date"), description=data.get("description"), achievement=data.get("achievement"))
    elif model == "skills": item = Skill(category=data.get("category", "WORK"), name=data.get("name", "New skill"), level=int(data.get("level", 80)))
    else: item = Archive(title=data.get("title", "New note"), category=data.get("category", "THINKING"), summary=data.get("summary"), content=data.get("content"))
    db.session.add(item); db.session.commit(); flash("저장했습니다.", "success"); return redirect(url_for("admin"))

@app.route("/admin/<string:model>/<int:item_id>/edit", methods=["GET", "POST"])
def edit_item(model, item_id):
    mapping = {"projects": (Project, ["title", "subtitle", "description", "tech_stack"]), "experiences": (Experience, ["company", "position", "start_date", "end_date", "description", "achievement"]), "skills": (Skill, ["category", "name", "level"]), "archive": (Archive, ["title", "category", "summary", "content"])}
    model_class, fields = mapping.get(model, mapping["archive"]); item = model_class.query.get_or_404(item_id)
    if request.method == "POST":
        for field in fields:
            value = request.form.get(field, "")
            if field == "level": value = int(value or 0)
            setattr(item, field, value)
        db.session.commit(); flash("수정했습니다.", "success"); return redirect(url_for("admin"))
    return render_template("admin/edit.html", item=item, fields=fields)

if __name__ == "__main__": app.run(debug=True)
