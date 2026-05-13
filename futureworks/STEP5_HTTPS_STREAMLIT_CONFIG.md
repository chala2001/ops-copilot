# STEP 5 — HTTPS Configuration (Streamlit + Nginx)

## Why HTTPS Is Non-Negotiable

Your current setup serves the app over plain **HTTP**. Every byte transmitted between the user's
browser and the Streamlit server is in clear text. This means:

- **Passwords are visible**: When a user types their password in the login form and submits it,
  the password travels as plain text over the network. Anyone on the same WiFi network (or a
  network switch) running Wireshark can capture it in real time.
- **Query content is visible**: Every question an SRE asks (which may include customer names,
  issue descriptions, or infrastructure details) is readable on the network.
- **Answers are visible**: The Gemini response (which may reference internal systems, IPs, or
  deployment configs) is also readable.

With HTTPS, all of this is encrypted with TLS. Even if someone captures the network traffic,
they see only encrypted bytes that are computationally infeasible to decrypt.

---

## Two-Level HTTPS Setup

This guide covers two setups:

**Level 1 — Local development HTTPS (self-signed certificate)**
Use this to test the full HTTPS flow on your local machine before deploying.
Your browser will show a warning because the certificate is self-signed (not from a
trusted Certificate Authority), but everything else works identically to production.

**Level 2 — Production HTTPS with Nginx (Let's Encrypt certificate)**
Use this on the Azure VM. Nginx sits in front of Streamlit and handles TLS termination.
Let's Encrypt provides a free, browser-trusted certificate. This is what users will access.

---

## Files You Need to Create

| File | Change |
|------|--------|
| `.streamlit/config.toml` | Configure Streamlit server settings |
| `certs/` | Directory for SSL certificates (local dev only) |
| `nginx-sre-copilot.conf` | Nginx config (reference file for Azure deployment) |
| `Dockerfile` | Minor security hardening |
| `docker-compose.yml` | Minor security hardening |

---

## Step 5.1 — Create Streamlit Configuration

Streamlit reads its configuration from `.streamlit/config.toml`. This file controls server
behavior, HTTPS settings, and browser options.

```bash
mkdir -p .streamlit
```

**File: `.streamlit/config.toml`** (new file — create from scratch)

```toml
# .streamlit/config.toml
# ── Streamlit Server Configuration ────────────────────────
# This file is safe to commit to Git (no secrets here).
# SSL certificate paths below are for LOCAL DEVELOPMENT ONLY.
# On the Azure server, Nginx handles HTTPS — Streamlit runs HTTP internally.

[server]
# Disable CORS to prevent cross-origin requests from other domains.
# CORS attacks involve a malicious website making requests to your app
# on behalf of a logged-in user. Disabling CORS prevents this.
enableCORS = false

# Enable CSRF (Cross-Site Request Forgery) protection.
# Streamlit adds a hidden token to forms; requests without the token are rejected.
# This prevents a malicious site from submitting the login form on a user's behalf.
enableXsrfProtection = true

# Maximum file upload size in MB (only relevant if you add file upload features)
maxUploadSize = 50

# Keep headless=true so Streamlit doesn't try to open a browser automatically.
# This is required for server/Docker deployments.
headless = true

# Port number (must match Docker expose and Nginx upstream config)
port = 8501

# For LOCAL HTTPS TESTING with self-signed certs (see Step 5.2):
# Uncomment these two lines ONLY when testing locally with a self-signed cert.
# LEAVE COMMENTED on the Azure server — Nginx handles HTTPS there.
# sslCertFile = "certs/cert.pem"
# sslKeyFile = "certs/key.pem"

[browser]
# Do not send usage statistics to Streamlit Inc.
# In a corporate environment, analytics opt-out is typically required.
gatherUsageStats = false

[theme]
# Optional: set the app theme
# base = "light"  # or "dark"
```

**Why `enableCORS = false` and `enableXsrfProtection = true`?**

CORS (Cross-Origin Resource Sharing) controls whether other websites can make requests to your
Streamlit app. By disabling it, you ensure that only requests coming directly from the same
origin (your Streamlit URL) are accepted.

XSRF (Cross-Site Request Forgery) protection adds a secret token to every form submission.
A forged request from another site won't have this token and will be rejected. This is
particularly important for your login form.

---

## Step 5.2 — Generate Self-Signed Certificate (Local Dev Testing Only)

```bash
cd ~/ops-copilot_gemini
mkdir -p certs

# Generate a self-signed certificate valid for 365 days.
# This creates two files:
# - certs/key.pem  : Your private key (keep secret, never commit to Git)
# - certs/cert.pem : Your certificate (contains public key, safe to share)
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -days 365 \
  -subj "/C=LK/ST=Western/L=Colombo/O=WSO2/OU=SRE/CN=localhost"

# Verify the files were created
ls -lh certs/
# Expected:
# -rw-rw-r-- 1 chalaka chalaka 1.9K cert.pem
# -rw------- 1 chalaka chalaka 3.2K key.pem

# Set restrictive permissions on the private key
chmod 600 certs/key.pem
```

**What does this OpenSSL command do?**
- `-x509`: Generate a self-signed X.509 certificate (skips the CSR step)
- `-newkey rsa:4096`: Generate a new 4096-bit RSA key pair
- `-nodes`: No DES passphrase (so the server can start unattended)
- `-keyout certs/key.pem`: Write private key here
- `-out certs/cert.pem`: Write certificate here
- `-days 365`: Certificate valid for 1 year
- `-subj "..."`: Certificate metadata (country, org, common name = hostname)

**Test HTTPS locally:**

1. Uncomment the two SSL lines in `.streamlit/config.toml`:
   ```toml
   sslCertFile = "certs/cert.pem"
   sslKeyFile = "certs/key.pem"
   ```
2. Run: `streamlit run app.py`
3. Open: `https://localhost:8501` (note **https**, not http)
4. Browser will show a security warning (expected for self-signed certs)
5. Click "Advanced" → "Proceed to localhost (unsafe)"
6. Login form should appear over HTTPS

**After local testing:**
- Comment out the SSL lines in `config.toml` again (Nginx handles HTTPS in production)
- The `certs/` directory is in `.gitignore` — never commit the private key

---

## Step 5.3 — Nginx Configuration for Azure Production

This is the Nginx configuration file you will create on the Azure VM.
**Keep this file in your project as a reference** but it is deployed on the server, not the container.

**File: `nginx-sre-copilot.conf`** (keep in project as reference — deploy to /etc/nginx/sites-available/ on Azure VM)

```nginx
# /etc/nginx/sites-available/sre-copilot
# ── Nginx Reverse Proxy for WSO2 SRE Ops Copilot ──────────
#
# Architecture:
#   Internet → Nginx (port 443, TLS) → Streamlit (port 8501, plain HTTP)
#
# Nginx sits in front and:
# 1. Handles TLS encryption/decryption (TLS termination)
# 2. Forwards decrypted requests to Streamlit on localhost:8501
# 3. Adds security headers to all responses
# 4. Redirects HTTP → HTTPS
# 5. Handles WebSocket upgrades (required for Streamlit's live updates)

# ── Upstream: Streamlit server on localhost ────────────────
upstream streamlit_backend {
    server 127.0.0.1:8501;
    # Streamlit runs on localhost only (not exposed to internet directly)
    # Only Nginx can reach it, which is correct.
}

# ── HTTP: Redirect all traffic to HTTPS ───────────────────
server {
    listen 80;
    listen [::]:80;
    server_name wso2-sre-copilot.southeastasia.cloudapp.azure.com;

    # 301 permanent redirect → browser caches this and goes to HTTPS directly next time
    return 301 https://$server_name$request_uri;
}

# ── HTTPS: Main application server ────────────────────────
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name wso2-sre-copilot.southeastasia.cloudapp.azure.com;

    # ── SSL Certificate ───────────────────────────────────
    # These paths are set automatically by Certbot (Let's Encrypt).
    # Run: sudo certbot --nginx -d your-domain.azure.com
    ssl_certificate     /etc/letsencrypt/live/wso2-sre-copilot.southeastasia.cloudapp.azure.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wso2-sre-copilot.southeastasia.cloudapp.azure.com/privkey.pem;

    # ── SSL Protocol and Cipher Configuration ─────────────
    # Only allow TLS 1.2 and 1.3. TLS 1.0 and 1.1 are deprecated and broken.
    ssl_protocols TLSv1.2 TLSv1.3;

    # Only use strong cipher suites. These are all ECDHE (Elliptic Curve
    # Diffie-Hellman Ephemeral) which provide Forward Secrecy — even if the
    # private key is compromised later, past sessions cannot be decrypted.
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';
    ssl_prefer_server_ciphers off;  # TLS 1.3 selects its own ciphers

    # ── SSL Session Caching ────────────────────────────────
    # Clients that reconnect within 10 minutes reuse the TLS session,
    # avoiding a full handshake and making the connection faster.
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;  # Session tickets have had vulnerabilities; disable

    # ── Security Headers ──────────────────────────────────
    # These headers are added to EVERY response Nginx sends.
    # They instruct the browser on how to handle security.

    # HSTS: Tell browser to ALWAYS use HTTPS for this domain for 1 year.
    # includeSubDomains: Apply to *.wso2.internal too.
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # X-Frame-Options: Prevent this page from being embedded in an iframe.
    # Mitigates clickjacking attacks where attackers overlay an invisible iframe.
    add_header X-Frame-Options "SAMEORIGIN" always;

    # X-Content-Type-Options: Prevent browser from guessing content type.
    # Mitigates MIME-type confusion attacks.
    add_header X-Content-Type-Options "nosniff" always;

    # X-XSS-Protection: Enable browser's built-in XSS filter (legacy browsers).
    add_header X-XSS-Protection "1; mode=block" always;

    # Referrer-Policy: Don't send the full URL in the Referer header to external sites.
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ── Logging ───────────────────────────────────────────
    access_log /var/log/nginx/sre-copilot.access.log;
    error_log  /var/log/nginx/sre-copilot.error.log;

    # ── Proxy to Streamlit ────────────────────────────────
    location / {
        proxy_pass http://streamlit_backend;

        # Use HTTP 1.1 for the proxy connection (required for WebSocket)
        proxy_http_version 1.1;

        # WebSocket upgrade headers — CRITICAL for Streamlit.
        # Streamlit uses WebSockets for real-time updates (streaming answers,
        # live metrics, etc.). Without these headers, the WebSocket handshake
        # fails and Streamlit appears to hang or shows a connection error.
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Forward the original host so Streamlit can generate correct URLs
        proxy_set_header Host $host;

        # Forward the real client IP so your logs show actual IPs,
        # not just 127.0.0.1 (which is all Nginx would appear as)
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts — Streamlit streaming responses can take 30-60 seconds
        # for long answers. These timeouts must be longer than that.
        proxy_connect_timeout 60s;
        proxy_send_timeout    120s;
        proxy_read_timeout    120s;

        # Buffer settings — disable buffering for streaming responses
        # so text appears word-by-word as Gemini generates it.
        proxy_buffering off;
    }
}
```

---

## Step 5.4 — Update Dockerfile for Security Hardening

**File: `Dockerfile`** (full content — replace entire file)

```dockerfile
# Dockerfile
# ── WSO2 SRE Ops Copilot Container ────────────────────────

# ── Base image ────────────────────────────────────────────
# Use slim variant (smaller attack surface — fewer installed packages)
FROM python:3.11-slim

# ── Environment variables ─────────────────────────────────
# PYTHONDONTWRITEBYTECODE: Don't create .pyc files (smaller image)
# PYTHONUNBUFFERED: Print logs immediately (no buffering in Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── Working directory ─────────────────────────────────────
WORKDIR /app

# ── System dependencies ───────────────────────────────────
# Only install what the app actually needs.
# git: needed by LangChain's GitLoader
# curl: needed by the health check
# --no-install-recommends: skip optional packages (smaller image)
# Clean up apt cache in the same layer to minimize image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────
# Copy requirements.txt first (Docker layer caching).
# If only app code changes (not requirements), this layer is cached
# and pip install is skipped — much faster rebuilds.
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────
# Copy app files AFTER dependencies so code changes don't invalidate the pip layer.
COPY app.py auth.py auth_guard.py config.py logger.py rag.py ingest.py scheduler.py ./
COPY session_manager.py audit_log.py rate_limiter.py ./
COPY pages/ ./pages/
COPY .streamlit/ ./.streamlit/
COPY data/ ./data/

# ── Security: Create non-root user ────────────────────────
# Running as root inside a container is a security risk.
# If there's a container escape vulnerability, the attacker gets root on the host.
# Running as 'appuser' limits blast radius significantly.
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --no-create-home --shell /bin/false appuser

# Set ownership of the app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user for all subsequent commands including CMD
USER appuser

# ── Port ──────────────────────────────────────────────────
EXPOSE 8501

# ── Health check ──────────────────────────────────────────
# Docker checks this every 30 seconds.
# If it fails 3 times in a row, the container is marked unhealthy.
# docker-compose.yml's depends_on uses this to wait for the app to be ready.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Start command ─────────────────────────────────────────
# --server.address=0.0.0.0: Listen on all interfaces (required in containers)
# --server.headless=true: Don't try to open a browser
# --server.port=8501: Explicit port (matches EXPOSE above)
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

**Key security change: non-root user**
The original Dockerfile ran as root. The new version creates `appuser` (UID 1000) and
switches to it before starting the application. If an attacker finds a vulnerability in
Streamlit or one of the Python dependencies and achieves code execution, they get `appuser`
privileges inside the container — not root — significantly limiting what they can do.

---

## Step 5.5 — Update docker-compose.yml for Security

**File: `docker-compose.yml`** (full content — replace entire file)

```yaml
# docker-compose.yml
# ── SRE Ops Copilot — Container Orchestration ─────────────
#
# Services:
#   app       — Streamlit web app (port 8501, internal only)
#   scheduler — Background ingestion job
#
# In production (Azure), Nginx runs on the HOST (not in Docker) and
# proxies to the app container's port 8501.

services:

  app:
    build: .
    container_name: ops-copilot-app
    image: ops-copilot:latest

    # Only bind to localhost — not exposed to the internet.
    # Nginx (on the host) connects to localhost:8501 and handles HTTPS.
    # If this were "0.0.0.0:8501:8501", anyone could bypass Nginx and
    # hit Streamlit directly over HTTP.
    ports:
      - '127.0.0.1:8501:8501'

    # Load environment variables from .env file.
    # .env is NOT committed to Git (see .gitignore).
    env_file:
      - .env

    # Volumes: mount data directories as named volumes for persistence.
    # Using named volumes (not bind mounts to /home/user) is more portable
    # and easier to backup on Azure.
    volumes:
      - ./data:/app/data:ro            # Documents: read-only from app's perspective
      - chroma_data:/app/chroma_db     # Vector DB: persistent named volume
      - app_logs:/app/logs             # Logs: persistent named volume

    # Resource limits: prevent a runaway process from consuming all server memory.
    # Adjust based on your Azure VM size.
    deploy:
      resources:
        limits:
          memory: 2G    # Max RAM the container can use
          cpus: '1.5'   # Max CPU cores
        reservations:
          memory: 512M  # Minimum RAM reserved

    restart: unless-stopped

    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:8501/_stcore/health']
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3

  scheduler:
    build: .
    container_name: ops-copilot-scheduler
    image: ops-copilot:latest
    command: python scheduler.py

    env_file:
      - .env

    volumes:
      - ./data:/app/data:ro
      - chroma_data:/app/chroma_db

    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'

    restart: unless-stopped

    depends_on:
      app:
        condition: service_healthy

# Named volumes — Docker manages these, easier to backup with docker cp or Azure snapshots
volumes:
  chroma_data:
    driver: local
  app_logs:
    driver: local
```

**Key security changes in docker-compose.yml:**
- `ports: '127.0.0.1:8501:8501'` instead of `'8501:8501'` — binds only to localhost,
  so Streamlit is only reachable from the local machine (via Nginx), not from the internet
- Added `deploy.resources.limits` — prevents OOM killing other processes on the VM
- Changed data volume to `:ro` (read-only) for the documents directory — app can read
  documents but cannot write to the data directory (least privilege principle)
- Named volumes for chroma_db and logs — easier to manage and backup than bind mounts

---

## How the HTTPS Flow Works End-to-End

```
User's Browser (HTTPS)
    │
    │ Encrypted TLS connection on port 443
    ▼
Azure NSG (Network Security Group)
    │ Allows port 443 from internet
    ▼
Azure VM — Nginx (port 443)
    │ TLS termination (decrypts HTTPS → plain HTTP)
    │ Adds security headers (HSTS, X-Frame-Options, etc.)
    │ Checks for WebSocket upgrade
    ▼
Docker Container — Streamlit (127.0.0.1:8501)
    │ Receives plain HTTP request from Nginx
    │ Processes the Streamlit request
    │ Returns response to Nginx
    ▼
Nginx
    │ Sends encrypted response back to browser
    ▼
User's Browser
    │ Decrypts response, renders UI
```

Streamlit only ever sees plain HTTP — it has no awareness of TLS. Nginx handles all
encryption. This separation is the standard "TLS termination at the proxy" pattern used
by virtually all production web services.
