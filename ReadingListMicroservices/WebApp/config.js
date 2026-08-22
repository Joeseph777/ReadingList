// Local dev: `python -m http.server 5500` inside WebApp/, talking to AuthService
// on :8000 and LibraryService on :8001 directly (see the main README).
//
// Deployed (Docker/nginx, see DEPLOYMENT.md): the web app, AuthService, and
// LibraryService are all served from the same origin, with nginx routing
// /auth/* and /books/* to the right backend container. Empty strings here
// mean "same origin as this page" — no cross-origin requests, no CORS to
// configure, no hardcoded domain to edit before deploying.
const IS_LOCAL_DEV = (location.hostname === "localhost" || location.hostname === "127.0.0.1") && location.port === "5500";

const AUTH_API = IS_LOCAL_DEV ? "http://localhost:8000" : "";
const LIBRARY_API = IS_LOCAL_DEV ? "http://localhost:8001" : "";
