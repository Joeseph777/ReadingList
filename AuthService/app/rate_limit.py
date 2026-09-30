from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared across main.py (registers the exception handler) and routers that
# want to decorate specific endpoints with @limiter.limit(...).

def real_ip(request):
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else get_remote_address(request)

limiter = Limiter(key_func=real_ip)