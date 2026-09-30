# Deploying to AWS

This gets the whole app — AuthService, LibraryService, and the web frontend —
running on a single EC2 instance behind nginx, using `docker-compose.yml` in
the repo root. Total moving parts: one EC2 instance, one Elastic IP, one
domain, one TLS certificate.

## 1. Launch the instance

- **AMI**: Ubuntu 22.04 or 24.04 LTS
- **Instance type**: `t3.micro` is enough for a personal project (this whole
  stack is three lightweight containers and SQLite — it's not doing much
  work). Free-tier eligible in your first 12 months on some plans.
- **Storage**: default 8–20 GB is plenty.
- **Security group** — this is the part that actually matters:
  - Port 22 (SSH) — restrict to **your IP only**, not `0.0.0.0/0`. Leaving
    SSH open to the world is the single most common way small AWS projects
    get compromised.
  - Port 80 (HTTP) — open to everyone (`0.0.0.0/0`).
  - Port 443 (HTTPS) — open to everyone, once you set up TLS in step 5.
  - Nothing else. AuthService (8000) and LibraryService (8001) are never
    exposed outside the Docker network — only nginx talks to them.

Allocate and associate an **Elastic IP** with the instance, so the public IP
doesn't change if you stop/restart it. You'll point your domain at this.

## 2. Install Docker

SSH in, then:
```
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
```
Log out and back in (or run `newgrp docker`) so your user can run `docker`
without `sudo`.

## 3. Get the code onto the instance

Easiest path — push this project to a GitHub repo (which also gives you
something to link on your resume), then on the instance:
```
git clone https://github.com/yourusername/ReadingListMicroservices.git
cd ReadingListMicroservices
```
(Or `scp` the folder over directly if you'd rather not use git yet.)

## 4. Configure secrets

```
cp AuthService/.env.example AuthService/.env
cp LibraryService/.env.example LibraryService/.env
```

Generate a real secret:
```
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Edit both `.env` files:
- `SECRET_KEY` — paste the generated value into **both** files. It must be
  identical in both, or LibraryService won't be able to verify tokens
  AuthService issues.
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` /
  `SMTP_FROM_EMAIL` (in `AuthService/.env`) — needed for password reset
  emails to actually go out. Without these, reset links just print to the
  container's logs (`docker compose logs auth`), which nobody but you can
  see. A Gmail account with an app password works fine for a personal
  project; SES or Mailgun if you want something more robust.
- `FRONTEND_URL` (in `AuthService/.env`) — set this to your real domain
  once you have one (step 6), so reset links in emails point somewhere
  that actually works instead of `localhost`.

You generally don't need to touch `DATABASE_URL`, `LIBRARY_SERVICE_URL`,
`AUTH_SERVICE_URL`, or `ALLOWED_ORIGINS` — the `.env.example` defaults are
already set up correctly for the docker-compose network.

There's no admin code to set anymore — see "Create your first admin"
below, after the containers are up.

## 5. Build and run

```
docker compose build
docker compose up -d
```

Check it's healthy:
```
docker compose ps
docker compose logs -f
```

At this point, visiting `http://<your-elastic-ip>` in a browser should show
the login screen. Register your own account now.

**Create your first admin.** SSH into the instance and run this against
the running `auth` container:
```
docker compose exec auth python bootstrap_admin.py <your-username>
```
Log back in (or just refresh) and the Users page should now show up in the
sidebar. From here on, manage further admins from that page — no more need
for `bootstrap_admin.py` unless you're recovering from having zero admins
somehow.

## 6. Point your domain at it

In your DNS provider (Route 53 or wherever you bought the domain), add an
A record pointing your domain (or subdomain, e.g. `reading.yourdomain.com`)
at the Elastic IP.

## 7. Add HTTPS

Once the domain resolves to your instance, get a free certificate:
```
sudo apt install -y certbot python3-certbot-nginx
sudo docker compose stop web   # free up port 80 for certbot
sudo certbot certonly --standalone -d yourdomain.com
```
This drops certificates in `/etc/letsencrypt/live/yourdomain.com/`. Mount
them into the nginx container and add a TLS server block — update
`docker-compose.yml`'s `web` service:
```yaml
  web:
    image: nginx:alpine
    volumes:
      - ./WebApp:/usr/share/nginx/html:ro
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    ports:
      - "80:80"
      - "443:443"
```
And add to `nginx/default.conf`, alongside the existing `server` block:
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    # ... same location blocks as the port 80 server ...
}
```
Then `docker compose up -d` again. Certbot certificates renew automatically
via a systemd timer it installs — no action needed for renewal, just make
sure `docker compose restart web` happens after a renewal (a cron job or
certbot's `--deploy-hook` can do this).

**Simpler alternative**: put an Application Load Balancer in front of the
instance with an ACM-issued certificate, and let the ALB handle TLS entirely
— nginx just serves plain HTTP behind it. More AWS-native, no certbot/renewal
to think about, but costs a few dollars a month for the ALB itself. Either
approach is a reasonable, explainable choice for a resume project.

## Day-to-day operations

- **View logs**: `docker compose logs -f auth` (or `library`, `web`)
- **Restart everything**: `docker compose restart`
- **Deploy a code update**: `git pull && docker compose up -d --build`
- **Stop everything**: `docker compose down` (data survives — it's in named
  volumes, not the containers themselves)
- **Back up your data**: the SQLite files live in Docker volumes
  (`auth_data`, `library_data`). `docker compose exec auth cat /app/data/auth.db > auth_backup.db`
  is a quick way to grab a copy.

## What this setup gets you (worth mentioning on a resume)

- Multi-container orchestration with `docker-compose`
- A reverse proxy (nginx) as the single public entry point, with the actual
  application services isolated on an internal-only Docker network
- Environment-based configuration (secrets never baked into images or
  committed to git)
- Rate limiting on authentication endpoints
- A self-healing database migration step (new columns get added
  automatically on deploy, no manual migration step required)
