from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .database import engine, Base, sync_schema
from .config import settings
from .rate_limit import limiter
from .routers import auth

# Create database tables (if not exist)
Base.metadata.create_all(bind=engine)
# Add any columns that exist in the models but not yet in an older database file
sync_schema()

app = FastAPI(title="Auth Service", version="1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow the web frontend (served from a different origin/port) to call this API.
# ALLOWED_ORIGINS in .env controls this — "*" for local dev, your real domain(s) in production.
_origins = ["*"] if settings.ALLOWED_ORIGINS.strip() == "*" else [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Auth Service is running"}

print(">>> main.py loaded successfully")