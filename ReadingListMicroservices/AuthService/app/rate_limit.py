from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared across main.py (registers the exception handler) and routers that
# want to decorate specific endpoints with @limiter.limit(...).
limiter = Limiter(key_func=get_remote_address)
