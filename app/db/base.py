from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import action_item, blog_post, decision, meeting, notion, project, transcript, user  # noqa: E402,F401
from app.models import workspace  # noqa: E402,F401
from app.models import workflow  # noqa: E402,F401
