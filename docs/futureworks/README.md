# Security Implementation Guides — SRE Ops Copilot

These guides implement every security upgrade described in `ENTERPRISE_DEPLOYMENT_GUIDE.md`.
No code has been automatically changed — every modification is documented here for you to
apply yourself and understand fully before applying.

---

## Do These Steps IN ORDER

| Step | File | What It Does | Priority |
|------|------|--------------|----------|
| [STEP 1](STEP1_BCRYPT_AUTH.md) | `auth.py`, `pages/5_Admin_Panel.py`, `requirements.txt`, `users.json` | Replace SHA-256 with bcrypt password hashing | 🔴 Critical |
| [STEP 2](STEP2_SESSION_TIMEOUT.md) | `session_manager.py` (new), `app.py`, `auth_guard.py` | Add 60-min inactivity timeout + 8-hour max session | 🔴 Critical |
| [STEP 3](STEP3_ENV_AND_GITIGNORE.md) | `.gitignore`, `config.py`, `.env.example` (new) | Protect secrets from Git, validate env vars at startup | 🔴 Critical |
| [STEP 4](STEP4_AUDIT_AND_RATE_LIMITING.md) | `audit_log.py` (new), `rate_limiter.py` (new), `auth.py`, `app.py` | Security event logging + brute-force/cost protection | 🟡 High |
| [STEP 5](STEP5_HTTPS_STREAMLIT_CONFIG.md) | `.streamlit/config.toml` (new), `Dockerfile`, `docker-compose.yml`, `nginx-sre-copilot.conf` (new) | HTTPS encryption, security headers, non-root Docker | 🟡 High |
| [STEP 6](STEP6_LOCAL_TESTING_CHECKLIST.md) | (no code changes — testing only) | Verify all changes locally before Azure deployment | ✅ Required |

---

## Summary of All New/Changed Files

### New files to create
```
session_manager.py         — Session timeout logic
audit_log.py               — Security event logging
rate_limiter.py            — Query and login rate limiting
migrate_passwords.py       — One-time password migration script (delete after use)
.streamlit/config.toml     — Streamlit HTTPS + security settings
.env.example               — Safe template to commit to Git
nginx-sre-copilot.conf     — Nginx config (reference, deployed to Azure server)
```

### Files to fully replace
```
auth.py                    — bcrypt + audit logging + rate limiting
auth_guard.py              — Session timeout awareness
pages/5_Admin_Panel.py     — bcrypt via create_user(), password validation
config.py                  — Startup validation for GOOGLE_API_KEY
.gitignore                 — Extended to cover all sensitive files
requirements.txt           — Add bcrypt==4.1.2
Dockerfile                 — Non-root user, COPY specific files
docker-compose.yml         — localhost-only port bind, resource limits
```

### Files with targeted additions
```
app.py — 4 changes:
  1. Import session_manager at top
  2. init_session_tracking() after successful login
  3. check_session_timeout() after the authenticated guard
  4. logout_user() instead of inline state clearing in Sign Out button
  5. check_query_rate_limit() before processing each query
```

### One-time actions
```
python3 migrate_passwords.py   — Convert users.json SHA-256 → bcrypt
chmod 600 .env                 — Fix file permissions
chmod 600 users.json           — Fix file permissions
git rm --cached .env           — If .env was previously committed
git rm --cached users.json     — If users.json was previously committed
```

---

## Security Improvements Summary

| Vulnerability | Before | After |
|---------------|--------|-------|
| Password hashing | SHA-256 (10B hashes/sec) | bcrypt cost=12 (~100ms/hash) |
| Session lifetime | Infinite | 60-min inactivity, 8-hr max |
| Login brute force | Unlimited attempts | 5 attempts/hour lockout |
| Query rate | Unlimited Gemini calls | 10/min, 100/hour per user |
| Security audit trail | None | Full audit_log.json |
| Network encryption | HTTP (plaintext) | HTTPS via Nginx + Let's Encrypt |
| API key protection | .env (may be in Git) | .gitignore + startup validation |
| Docker user | root | appuser (UID 1000) |
| Container network exposure | 0.0.0.0:8501 | 127.0.0.1:8501 (localhost only) |

---

## After Local Testing → Azure Deployment

Once STEP 6 checklist is fully complete, follow Section 4 of `ENTERPRISE_DEPLOYMENT_GUIDE.md`
for the Azure VM setup, which covers:
- Creating the Azure VM (Standard_B2ms, 2 vCPU, 8 GB RAM)
- Installing Nginx + Certbot (Let's Encrypt SSL)
- Setting up systemd service for auto-start
- Using the `nginx-sre-copilot.conf` reference file from STEP 5
