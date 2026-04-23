from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DB_URI: str = f"sqlite:///{BASE_DIR}/db/data/prosopography.db"
    DB_ECHO: bool = False

settings = Settings()