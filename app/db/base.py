from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import action_item, decision, meeting, notion, project, transcript  # noqa: E402,F401

