# Public demo deployment

This directory contains deployment-only configuration for the public demo stand.
It is separated from the application code so that the repository keeps a clean
boundary between:

- source code and tests;
- environment-specific deployment configuration;
- real secrets stored outside Git.

## Files

- `docker-compose.yml` — demo Docker Compose stack: PostgreSQL, backend and frontend.
- `.env.example` — non-secret template for required environment variables.
- `nginx.conf` — reverse proxy example for `/`, `/api`, `/docs` and `/openapi.json`.

## Demo branch policy

The `demo` branch is used as a deployment branch for the public demonstration
stand. In a commercial project the same idea is usually implemented as a
separate **environment** rather than as a long-lived branch:

- `main` / `master` — stable production-ready code;
- `develop` — integration branch for current development;
- `feature/*` — task branches;
- `deploy/demo/` — environment-specific demo deployment files;
- GitHub Actions / CI/CD — tests, builds and deployments;
- GitHub Secrets / Vault / secret manager — real credentials.

## Server setup

Run these commands from the repository root on the demo server.

```bash
cp deploy/demo/.env.example .env
chmod 600 .env
```

Edit `.env` and set real values for:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `BACKEND_CORS_ORIGINS`
- `VITE_ALLOWED_HOSTS`

Then build and start the stack:

```bash
docker compose --env-file .env -f deploy/demo/docker-compose.yml up -d --build
```

The containers bind only to loopback ports:

- frontend: `127.0.0.1:15173`
- backend: `127.0.0.1:18000`
- PostgreSQL: internal Docker network only

Use nginx as the public entry point. Copy `deploy/demo/nginx.conf` to
`/etc/nginx/sites-available/devopsdiploma`, replace `example.com`, enable the
site and issue a certificate:

```bash
sudo ln -s /etc/nginx/sites-available/devopsdiploma /etc/nginx/sites-enabled/devopsdiploma
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d example.com
```

## Smoke checks

```bash
curl -fsS https://example.com/api/health
curl -fsS https://example.com/docs >/dev/null
curl -fsS https://example.com/ >/dev/null
```

Expected health response:

```json
{
  "status": "ok",
  "service": "devops-ticket-system",
  "environment": "demo",
  "database": "ok"
}
```

## Demo users

All seeded demo users use the password `password`:

- `employee`
- `executor`
- `admin`
- `manager`
