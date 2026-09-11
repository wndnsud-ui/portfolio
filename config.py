from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = "hy-archive-dev-key"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'portfolio.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

