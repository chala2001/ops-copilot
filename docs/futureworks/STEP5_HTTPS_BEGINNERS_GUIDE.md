# STEP 5 — HTTPS Setup: Complete Beginner Guide

> **Who this is for:** You know how to run Python and Docker but have never set up
> a website, SSL certificate, or web server before. Every term is explained from scratch.

---

## Part 1 — Understanding the Problem (Read This First)

### What Happens Right Now (HTTP)

When your Streamlit app runs, users open it in a browser at:
```
http://localhost:8501
```

The `http://` at the start is the protocol — it is the *language* the browser and your
app use to talk to each other.

Here is the problem: **HTTP sends everything as plain readable text.**

Imagine you are passing a note in a classroom. HTTP is like writing your note on a
**transparent piece of paper**. Every person who handles it — every router, every network
switch between you and your server — can read exactly what is written.

When an SRE logs in to your app over HTTP, this is what travels over the network:

```
POST /login HTTP/1.1
Host: your-server.com

username=alice&password=MySecretPassword123
```

Anyone on the same network running a free tool called Wireshark can see this.
In an office WiFi, coffee shop, or shared network this is a real risk.

---

### What HTTPS Does

HTTPS is HTTP + a security layer called **TLS** (Transport Layer Security).

Think of it like this: instead of a transparent note, you put the note inside a
**locked metal box**. Only you and the server have the key to open it. Everyone in the
middle sees only the locked box, not what is inside.

```
HTTP  (no protection):
Browser ──── "username=alice&password=Secret" ────► Server
              ↑
         Anyone can read this

HTTPS (with TLS):
Browser ──── "Xk92!@#mK0p3$..." ────► Server
              ↑
         Encrypted gibberish — useless to eavesdroppers
```

With HTTPS:
- Passwords travel encrypted — no one in the middle can read them
- Your customer data and queries are protected
- The browser shows a padlock icon (users trust it)
- Required for corporate compliance (SOC2, ISO27001)

---

### What TLS Is

TLS stands for **Transport Layer Security**. It is the encryption system that powers HTTPS.

You do not need to understand cryptography. What you need to know:

1. **TLS uses two keys**: a public key (anyone can have it) and a private key (only your
   server has it). Messages encrypted with the public key can only be decrypted with the
   private key.

2. **The handshake**: when a browser first connects, it and the server agree on an
   encryption method in a fraction of a second. After that, everything is encrypted.

3. **You never touch the encryption yourself** — TLS does it automatically once configured.

---

### What a Certificate Is

A certificate (also called SSL certificate or TLS certificate) is a **digital ID card for
your server**.

Think of it like a passport. When you visit a country, officials check your passport to
confirm you are who you say you are. A TLS certificate lets browsers verify that the
server they are connecting to is actually YOUR server, not an attacker pretending to be it.

A certificate contains:
- Your domain name (e.g. `sre-copilot.wso2.internal`)
- A public key (the "lock" half of the key pair)
- A signature from a trusted Certificate Authority (CA) — an organisation that vouches for you

**Two types you will use:**

| Type | Who signs it | Browser trusts it? | Use case |
|------|-------------|-------------------|----------|
| Self-signed | You sign your own | ❌ Shows warning | Local testing only |
| Let's Encrypt | Trusted CA (free) | ✅ Green padlock | Production on Azure |

---

### What Nginx Is

Nginx (pronounced "engine-x") is a **web server and reverse proxy**.

**Reverse proxy** sounds complicated. Here is the simple explanation:

Imagine a **receptionist** at a company building. People from outside call the main
reception number. The receptionist picks up, finds out who the caller wants, and
forwards the call to the right desk inside the building. The caller never dials the
internal desk directly.

Nginx is that receptionist:

```
Internet users
      │
      │  HTTPS request on port 443 (the "main reception number")
      ▼
┌─── NGINX ────────────────────────────────────┐
│  - Receives the encrypted HTTPS request       │
│  - Decrypts it (TLS termination)              │
│  - Forwards it to Streamlit on port 8501      │
│  - Gets Streamlit's response                  │
│  - Encrypts the response and sends it back    │
└──────────────────────────────────────────────┘
      │
      │  Plain HTTP (inside the same server — safe)
      ▼
Streamlit app (port 8501)
```

**Why not just give Streamlit HTTPS directly?**

You could, but Nginx gives you extra things for free:
- Automatic HTTP → HTTPS redirect (users who type `http://` get moved to `https://` automatically)
- Security headers added to every response (extra browser protections)
- Better logging (access logs)
- Easy certificate renewal (Certbot integrates with Nginx automatically)
- If you ever add a second app, Nginx can route to both

---

## Part 2 — Local Testing (Your Laptop, Before Azure)

This section sets up HTTPS on your own machine using a **self-signed certificate**.
The browser will show a warning — that is expected and OK for local testing.

### What You Are Building Locally

```
Your Browser (Firefox/Chrome)
      │
      │  https://localhost:8501
      │
      ▼
Streamlit app (running with a self-signed certificate)
```

We are not using Nginx locally — Streamlit can serve HTTPS directly for testing.

---

### Step A — Check OpenSSL Is Installed

OpenSSL is a tool that generates certificates. It is almost always pre-installed on Ubuntu.

```bash
openssl version
```

Expected output:
```
OpenSSL 3.0.2 15 Mar 2022
```

If you see a version number, you are good. If you see "command not found":
```bash
sudo apt install openssl
```

---

### Step B — Create a Folder for Certificates

```bash
# Go to your project folder
cd ~/ops-copilot_gemini

# Create a folder to store the certificate files
mkdir certs

# Check it was created
ls -la
# You should see a "certs" folder in the list
```

**Why a separate folder?** Keeping certificates in `certs/` makes it easy to add the
whole folder to `.gitignore` so you never accidentally commit your private key to Git.

---

### Step C — Generate a Self-Signed Certificate

This is the one command that creates both your private key and your certificate at the same time.

```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -days 365 \
  -subj "/C=LK/ST=Western/L=Colombo/O=WSO2/OU=SRE/CN=localhost"
```

**What every part of this command means:**

| Part | What it means |
|------|--------------|
| `openssl` | The certificate tool |
| `req` | "I want to make a certificate request" |
| `-x509` | Make it self-signed (skip submitting to a CA) |
| `-newkey rsa:4096` | Generate a new RSA key that is 4096 bits long (very strong) |
| `-nodes` | No password on the key (so the server can start without you typing a password) |
| `-keyout certs/key.pem` | Save the private key to this file |
| `-out certs/cert.pem` | Save the certificate to this file |
| `-days 365` | The certificate is valid for 365 days |
| `-subj "..."` | The identity info baked into the certificate |
| `C=LK` | Country code: Sri Lanka |
| `ST=Western` | State/Province |
| `L=Colombo` | City |
| `O=WSO2` | Organisation name |
| `OU=SRE` | Department |
| `CN=localhost` | The domain this certificate is for (localhost for local testing) |

After running this, check what was created:

```bash
ls -lh certs/
```

Expected output:
```
-rw-rw-r-- 1 chalaka chalaka 1.9K cert.pem   ← the certificate (public, shareable)
-rw------- 1 chalaka chalaka 3.2K key.pem    ← the private key  (KEEP SECRET)
```

The private key (`key.pem`) must stay on your server only. If anyone gets it, they can
impersonate your server. The certificate (`cert.pem`) is public — browsers receive it to
verify your server's identity.

---

### Step D — Protect the Private Key

```bash
# Make the private key readable only by you (owner)
# 600 means: owner can read+write, nobody else can do anything
chmod 600 certs/key.pem

# Verify
ls -la certs/key.pem
# Should show: -rw------- (the dashes mean "nobody else")
```

---

### Step E — Tell Streamlit to Use Your Certificate

Streamlit reads its settings from a file at `.streamlit/config.toml`.
The `.streamlit` folder must be in your project root.

```bash
# Create the .streamlit folder if it does not exist
mkdir -p .streamlit

# Create the config file
nano .streamlit/config.toml
```

Add exactly this content:

```toml
[server]
enableCORS = false
enableXsrfProtection = true
headless = true
port = 8501
sslCertFile = "certs/cert.pem"
sslKeyFile = "certs/key.pem"

[browser]
gatherUsageStats = false
```

**What each line does:**

| Line | What it does |
|------|-------------|
| `enableCORS = false` | Block requests from other websites (prevents cross-site attacks) |
| `enableXsrfProtection = true` | Add hidden tokens to forms (prevents forged form submissions) |
| `headless = true` | Do not try to open a browser automatically (needed for servers) |
| `port = 8501` | Run on port 8501 |
| `sslCertFile = "certs/cert.pem"` | Here is our certificate |
| `sslKeyFile = "certs/key.pem"` | Here is our private key |
| `gatherUsageStats = false` | Do not send data to Streamlit Inc. |

Save with: **Ctrl+X → Y → Enter**

---

### Step F — Run the App and Test HTTPS

```bash
cd ~/ops-copilot_gemini
source venv/bin/activate
streamlit run app.py
```

Now open your browser and go to:
```
https://localhost:8501
```

**IMPORTANT:** Notice the `https://` — not `http://`.

Your browser will show a warning page like this:

```
⚠️ Warning: Potential Security Risk Ahead
    Firefox detected a potential security threat...
```

This is **expected and normal** for a self-signed certificate. The browser does not know
this certificate is yours because no trusted CA signed it. On the real Azure server, we
will use a free certificate from Let's Encrypt that browsers already trust — no warning.

To proceed past the warning:
- **Firefox:** Click "Advanced" → "Accept the Risk and Continue"
- **Chrome:** Click "Advanced" → "Proceed to localhost (unsafe)"

You should now see your login page over HTTPS. The padlock in the address bar will show
(though with a warning indicator because it is self-signed).

---

### Step G — Remove SSL Config Before Moving to Azure

After testing locally, comment out the SSL lines in `.streamlit/config.toml` because
on Azure, Nginx will handle HTTPS (not Streamlit directly):

```toml
[server]
enableCORS = false
enableXsrfProtection = true
headless = true
port = 8501
# sslCertFile = "certs/cert.pem"   ← commented out for Azure
# sslKeyFile = "certs/key.pem"     ← commented out for Azure

[browser]
gatherUsageStats = false
```

On Azure, Streamlit will run on plain HTTP internally, and Nginx will provide HTTPS
to the outside world. This is the correct production architecture.

---

## Part 3 — Production HTTPS on Azure (The Real Thing)

### What You Are Building on Azure

```
World / SRE Team's browsers
           │
           │  https://your-server.southeastasia.cloudapp.azure.com
           │  (port 443 — the standard HTTPS port)
           ▼
┌──── Azure Virtual Machine ─────────────────────────────────────┐
│                                                                  │
│  ┌── Nginx (the "receptionist") ──────────────────────────────┐ │
│  │  - Receives HTTPS request                                   │ │
│  │  - Decrypts it using the Let's Encrypt certificate          │ │
│  │  - Forwards plain HTTP to Streamlit on 127.0.0.1:8501       │ │
│  │  - Adds security headers to every response                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                      │                                           │
│             plain HTTP (internal, safe)                          │
│                      │                                           │
│  ┌── Streamlit app (port 8501) ────────────────────────────────┐ │
│  │  - Receives requests from Nginx only (not from internet)    │ │
│  │  - Sends responses back to Nginx                            │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

The key point: **Streamlit never talks to the internet directly.** Only Nginx does.
Nginx is the only thing the outside world can reach.

---

### Step 1 — SSH Into Your Azure VM

On your local machine, open a terminal and run:

```bash
ssh -i ~/.ssh/azure_wso2_sre sreadmin@YOUR_VM_PUBLIC_IP
```

Replace `YOUR_VM_PUBLIC_IP` with the IP address Azure gave you when you created the VM.

You should see a welcome message and a prompt like:
```
sreadmin@vm-sre-copilot:~$
```

All the following steps run ON the Azure VM (not your laptop).

---

### Step 2 — Install Nginx

Nginx is software you install like any other Linux program.

```bash
# Update the list of available packages
sudo apt update

# Install Nginx
sudo apt install nginx -y

# Check it installed correctly — see its version
nginx -v
```

Expected output:
```
nginx version: nginx/1.18.0 (Ubuntu)
```

```bash
# Start Nginx now
sudo systemctl start nginx

# Tell the OS to start Nginx automatically every time the server reboots
sudo systemctl enable nginx

# Verify it is running
sudo systemctl status nginx
```

Expected output:
```
● nginx.service - A high performance web server
     Active: active (running) since ...
```

**Quick test:** Open a browser on your laptop and go to `http://YOUR_VM_PUBLIC_IP`.
You should see the default Nginx welcome page: "Welcome to nginx!"
This confirms Nginx is installed and responding to requests.

---

### Step 3 — Install Certbot (the Certificate Tool)

Let's Encrypt is a free Certificate Authority (CA) — the organisation that signs your
certificate so browsers trust it. Certbot is the tool that talks to Let's Encrypt for you.

```bash
# Install Certbot and its Nginx plugin
sudo apt install certbot python3-certbot-nginx -y

# Verify installation
certbot --version
```

---

### Step 4 — Open the Correct Ports in the Azure Firewall

Azure has a firewall called a **Network Security Group (NSG)**. By default, only port 22
(SSH) is open. We need to open ports 80 and 443.

**Why port 80?** HTTP. Even though we want HTTPS, users might type `http://` in their
browser. Nginx will automatically redirect them to `https://`. Port 80 must be open
to receive that initial HTTP request before redirecting.

**Why port 443?** This is the standard HTTPS port. All HTTPS traffic goes through 443.

Run these commands on your LOCAL MACHINE (not the VM), in a terminal where you have
Azure CLI logged in:

```bash
# Open port 443 (HTTPS) — where users will connect
az vm open-port \
  --resource-group rg-wso2-sre-copilot \
  --name vm-sre-copilot \
  --port 443 \
  --priority 1001

# Open port 80 (HTTP) — for the redirect to HTTPS
az vm open-port \
  --resource-group rg-wso2-sre-copilot \
  --name vm-sre-copilot \
  --port 80 \
  --priority 1002
```

**What each part means:**

| Part | Meaning |
|------|---------|
| `az vm open-port` | Azure CLI command to open a port |
| `--resource-group` | The container where your VM lives |
| `--name` | Your VM's name |
| `--port 443` | Which port to open |
| `--priority 1001` | Processing order (lower number = checked first, does not matter much here) |

---

### Step 5 — Get a Free HTTPS Certificate from Let's Encrypt

**Prerequisites before this step:**
- Your Azure VM must have a public DNS name
  (when you created the VM with `--public-ip-address-dns-name wso2-sre-copilot`,
  Azure gave it a name like `wso2-sre-copilot.southeastasia.cloudapp.azure.com`)
- Ports 80 and 443 must be open (Step 4 above)

On your Azure VM, run:

```bash
sudo certbot --nginx \
  -d wso2-sre-copilot.southeastasia.cloudapp.azure.com \
  --email your.email@wso2.com \
  --agree-tos \
  --no-eff-email
```

**What each part means:**

| Part | Meaning |
|------|---------|
| `sudo certbot` | Run Certbot as administrator |
| `--nginx` | Tell Certbot to configure Nginx automatically |
| `-d wso2-sre-copilot...` | The domain name this certificate is for |
| `--email your.email@wso2.com` | Let's Encrypt sends expiry reminders here |
| `--agree-tos` | Agree to Let's Encrypt terms of service |
| `--no-eff-email` | Do not sign up for EFF newsletter |

**What Certbot does automatically:**
1. Contacts Let's Encrypt servers
2. Proves you own this domain (by temporarily serving a file on port 80)
3. Let's Encrypt sees the file → confirms you own the domain → signs your certificate
4. Certbot saves the certificate files to `/etc/letsencrypt/live/your-domain/`
5. Certbot edits your Nginx config to use the certificate
6. Sets up a timer to auto-renew the certificate before it expires (Let's Encrypt
   certificates expire after 90 days — Certbot renews automatically)

Expected output at the end:
```
Congratulations! Your certificate and chain have been saved at:
/etc/letsencrypt/live/wso2-sre-copilot.southeastasia.cloudapp.azure.com/fullchain.pem

Successfully deployed certificate for wso2-sre-copilot...
```

---

### Step 6 — Create the Nginx Configuration for Your App

Now you tell Nginx how to handle requests to your domain and where to forward them.

```bash
# Create a new configuration file for your app
sudo nano /etc/nginx/sites-available/sre-copilot
```

Copy and paste this entire block:

```nginx
# This tells Nginx about a "backend" called streamlit_backend
# It lives at localhost port 8501 — where your Streamlit app runs
upstream streamlit_backend {
    server 127.0.0.1:8501;
}

# ── Rule 1: Anyone who comes in on port 80 (HTTP) ─────────
# Redirect them to HTTPS automatically
server {
    listen 80;
    server_name wso2-sre-copilot.southeastasia.cloudapp.azure.com;
    return 301 https://$server_name$request_uri;
}

# ── Rule 2: Handle HTTPS requests on port 443 ─────────────
server {
    listen 443 ssl http2;
    server_name wso2-sre-copilot.southeastasia.cloudapp.azure.com;

    # Certificate files (Certbot created these in Step 5)
    ssl_certificate     /etc/letsencrypt/live/wso2-sre-copilot.southeastasia.cloudapp.azure.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wso2-sre-copilot.southeastasia.cloudapp.azure.com/privkey.pem;

    # Only allow modern TLS versions (1.2 and 1.3)
    # Old versions (1.0, 1.1) have known security flaws
    ssl_protocols TLSv1.2 TLSv1.3;

    # Security headers — instructions we attach to every response
    # telling the browser how to protect itself
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Log files — where Nginx records who visited and any errors
    access_log /var/log/nginx/sre-copilot.access.log;
    error_log  /var/log/nginx/sre-copilot.error.log;

    # ── How to handle requests ──────────────────────────────
    location / {
        # Forward the request to Streamlit
        proxy_pass http://streamlit_backend;

        # Required for Streamlit's live updates (WebSocket)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Tell Streamlit the original request details
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Wait up to 2 minutes for Streamlit to respond
        # (some answers take time to generate)
        proxy_read_timeout 120s;

        # Do not buffer — show streaming text as it arrives
        proxy_buffering off;
    }
}
```

Save and exit: **Ctrl+X → Y → Enter**

**Why `proxy_buffering off`?** Your app streams answers word by word. If Nginx buffers
the response, it would wait until Streamlit finishes the entire answer before sending
anything to the browser. With buffering off, each word appears as soon as Streamlit
generates it.

**Why the WebSocket headers?** Streamlit uses a technology called WebSockets to push
live updates to the browser (the streaming text, metric updates, etc.). Without these
three lines, Streamlit's live features break.

---

### Step 7 — Enable the Configuration

Nginx has two folders:
- `sites-available/` — all config files (active or not)
- `sites-enabled/` — only configs Nginx actually uses

You link from enabled to available to turn a config on:

```bash
# Create a link (shortcut) from enabled to available
sudo ln -s /etc/nginx/sites-available/sre-copilot /etc/nginx/sites-enabled/

# Remove the default Nginx page (the "Welcome to nginx!" page)
sudo rm /etc/nginx/sites-enabled/default

# Check your config file has no typos
sudo nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

If you see any errors, check the config file for typos.

```bash
# Apply the new config (no downtime — Nginx reloads gracefully)
sudo systemctl reload nginx
```

---

### Step 8 — Start Your Streamlit App as a System Service

You want Streamlit to start automatically when the server boots and restart if it crashes.
Linux has a system called `systemd` for managing background services.

```bash
# Create a service definition file
sudo nano /etc/systemd/system/sre-copilot.service
```

Copy this content:

```ini
[Unit]
Description=WSO2 SRE Ops Copilot
After=network.target

[Service]
Type=simple
User=sreadmin
WorkingDirectory=/home/sreadmin/ops-copilot-gemini
EnvironmentFile=/home/sreadmin/ops-copilot-gemini/.env
ExecStart=/home/sreadmin/ops-copilot-gemini/venv/bin/streamlit run app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**What each section means:**

| Setting | Meaning |
|---------|---------|
| `After=network.target` | Wait until the network is up before starting |
| `User=sreadmin` | Run the app as this user (not root — safer) |
| `WorkingDirectory=...` | Run from this folder |
| `EnvironmentFile=...` | Load your `.env` file (your API keys) |
| `ExecStart=...` | The exact command to start the app |
| `--server.address 127.0.0.1` | Only accept connections from localhost (Nginx) |
| `Restart=always` | If the app crashes, restart it automatically |
| `RestartSec=10` | Wait 10 seconds before restarting after a crash |

```bash
# Tell systemd about the new service file
sudo systemctl daemon-reload

# Start the service
sudo systemctl start sre-copilot

# Tell systemd to start it automatically on every boot
sudo systemctl enable sre-copilot

# Check it is running
sudo systemctl status sre-copilot
```

Expected output:
```
● sre-copilot.service - WSO2 SRE Ops Copilot
     Active: active (running) since ...
```

---

### Step 9 — Test Everything

Open your browser on your laptop:

```
https://wso2-sre-copilot.southeastasia.cloudapp.azure.com
```

What you should see:
- **Padlock icon** in the address bar (no warning — this is a real certificate)
- Your login page loads
- You can log in and use the app normally

**Test that HTTP redirects to HTTPS:**
```
http://wso2-sre-copilot.southeastasia.cloudapp.azure.com
```
This should automatically redirect you to the `https://` version.

---

### Step 10 — Verify Certificate Auto-Renewal

Let's Encrypt certificates expire every 90 days. Certbot sets up auto-renewal
automatically, but test it to confirm:

```bash
# Test the renewal process (does not actually renew, just simulates)
sudo certbot renew --dry-run
```

Expected output at the end:
```
Congratulations, all simulated renewals succeeded
```

Certbot will automatically renew your certificate before it expires. You do not
need to do anything — it runs on a schedule by itself.

---

## Part 4 — Understanding the Security Headers

When you include `add_header` lines in the Nginx config, you are attaching small
instructions to every response that tell the browser how to protect itself.

Here is what each one does in plain English:

### `Strict-Transport-Security`
```nginx
add_header Strict-Transport-Security "max-age=31536000" always;
```
This tells the browser: **"For the next year (31,536,000 seconds), always use HTTPS
for this website. Never try HTTP, even if someone asks you to."**

Once a browser sees this once, it will always go to HTTPS automatically — even if someone
sends the user a link starting with `http://`. Prevents downgrade attacks where an
attacker tricks your browser into using the insecure HTTP version.

### `X-Frame-Options`
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
```
This prevents your app from being embedded inside another website's `<iframe>`.

Attackers use iframes for "clickjacking" — they overlay your app invisibly inside their
site and trick users into clicking buttons they cannot see (like confirming a transaction).
`SAMEORIGIN` means only your own domain can embed your pages in a frame.

### `X-Content-Type-Options`
```nginx
add_header X-Content-Type-Options "nosniff" always;
```
Browsers sometimes try to "guess" what type of file they received if the server did not
specify. This guessing has caused security bugs. `nosniff` tells the browser to believe
what the server says and not guess.

---

## Part 5 — Quick Reference: What Each File Does

| File / Tool | What it is | What it does in this project |
|-------------|-----------|------------------------------|
| `cert.pem` | Certificate file | Your server's ID card. Sent to browsers. |
| `key.pem` | Private key file | The secret key. Never leave the server. |
| Nginx | Web server software | Receives HTTPS, decrypts, forwards to Streamlit |
| Certbot | Certificate tool | Gets free certificate from Let's Encrypt |
| Let's Encrypt | Certificate Authority | The trusted organisation that signs your cert |
| `systemd` | Linux service manager | Keeps Streamlit running in background, auto-restarts |
| Port 443 | Network port | The standard door for HTTPS traffic |
| Port 80 | Network port | The standard door for HTTP (we redirect to 443) |
| Port 8501 | Network port | Streamlit's private door (only Nginx can reach it) |

---

## Part 6 — What To Do If Something Goes Wrong

### "I see the browser warning even on Azure"
Certbot did not complete or the domain does not match. Check:
```bash
sudo certbot certificates
# Shows your certificates and their domains
```

### "502 Bad Gateway" in the browser
Nginx is running but cannot reach Streamlit. Check:
```bash
sudo systemctl status sre-copilot
# Is Streamlit actually running?

sudo journalctl -u sre-copilot -n 50
# View the last 50 lines of Streamlit logs
```

### "nginx -t shows an error"
There is a typo in your Nginx config. The error message tells you the line number.
Open the file and check that line:
```bash
sudo nano /etc/nginx/sites-available/sre-copilot
```

### "Certbot says domain not found"
The Azure DNS name must be correct and ports 80/443 must be open in the NSG.
Test port 80 is open:
```bash
curl http://YOUR_VM_IP
# Should show nginx welcome page
```

### View Nginx logs to see what is happening
```bash
# Live access log (shows every request)
sudo tail -f /var/log/nginx/sre-copilot.access.log

# Error log (shows Nginx errors)
sudo tail -f /var/log/nginx/sre-copilot.error.log
```
