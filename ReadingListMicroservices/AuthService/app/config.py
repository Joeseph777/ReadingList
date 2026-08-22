import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./auth.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-ultra-secret-key-change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    LIBRARY_SERVICE_URL: str = os.getenv("LIBRARY_SERVICE_URL", "http://localhost:8001")
    # Anyone who supplies this code on registration becomes an admin. Change it in .env.
    ADMIN_ACCESS_CODE: str = os.getenv("ADMIN_ACCESS_CODE", "change-me-admin-code")
    # Comma-separated list of origins allowed to call this API, e.g.
    # "https://yourdomain.com,https://www.yourdomain.com". Defaults to "*" (allow
    # everyone) for local development — set this to your real domain(s) in
    # production, since "*" plus credentials means any website can call your
    # API using a logged-in visitor's browser.
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

settings = Settings()