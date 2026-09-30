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

    # Password reset emails. If SMTP_HOST is empty (the default), reset links are
    # printed to the server console instead of emailed — fine for local testing,
    # not fine for production. Fill these in with a real provider before deploying.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "no-reply@example.com")
    # Where the web app is served from, used to build the link in reset emails.
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5500")

    # Comma-separated list of origins allowed to call this API, e.g.
    # "https://yourdomain.com,https://www.yourdomain.com". Defaults to "*" (allow
    # everyone) for local development — set this to your real domain(s) in
    # production, since "*" plus credentials means any website can call your
    # API using a logged-in visitor's browser.
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

settings = Settings()