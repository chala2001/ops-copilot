#!/usr/bin/env python3
# migrate_passwords.py
# ONE-TIME SCRIPT: Convert users.json from SHA-256 to bcrypt hashes.
# Run once, then DELETE this file (it contains plain-text passwords).

import bcrypt
import json
from datetime import datetime
from pathlib import Path

# ── EDIT THESE PASSWORDS ──────────────────────────────────────────────────────
# Set the new passwords for each user here.
# After running this script, share passwords with users via a secure channel
# (NOT email, NOT Slack — use a password manager or face-to-face).
NEW_PASSWORDS = {
    "alice":   "Alice@WSO2#2026!",
    "carol":   "Carol@WSO2#2026!",
    "admin":   "Admin@WSO2#VerySecure2026!!",
    "chalaka": "Chalaka@WSO2#2026!",
}
# ─────────────────────────────────────────────────────────────────────────────

USERS_FILE = "users.json"

print("=" * 60)
print("SRE Ops Copilot — Password Migration: SHA-256 → bcrypt")
print("=" * 60)
print()

# Load existing users.json
try:
    with open(USERS_FILE, "r") as f:
        data = json.load(f)
    users = data["users"]
    print(f"Loaded {len(users)} users from {USERS_FILE}")
except FileNotFoundError:
    print(f"ERROR: {USERS_FILE} not found!")
    exit(1)

# Create a timestamped backup before making any changes
backup_name = f"users.json.sha256.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
with open(backup_name, "w") as f:
    json.dump(data, f, indent=2)
print(f"Backup created: {backup_name}")
print()

# Generate new bcrypt hashes
print("Generating bcrypt hashes (about 1 second per user — this is intentional)...")
print("-" * 60)

new_users = {}
for username, user_data in users.items():
    if username in NEW_PASSWORDS:
        password = NEW_PASSWORDS[username]
    else:
        # User not in the list — generate a temporary password
        password = f"{username}@TempPW#2026"
        print(f"WARNING: No password defined for '{username}' — using temporary: {password}")

    # bcrypt.gensalt(rounds=12) + bcrypt.hashpw() takes ~100ms intentionally
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

    new_users[username] = {
        "password_hash": hashed.decode("utf-8"),
        "display_name":  user_data.get("display_name", username),
        "customers":     user_data.get("customers", ["ALL"]),
        "role":          user_data.get("role", "sre"),
    }

    # Verify the hash works correctly before saving
    assert bcrypt.checkpw(password.encode("utf-8"), hashed), f"Hash verification failed for {username}!"
    print(f"  {username:15s} → bcrypt hash generated and verified")

print("-" * 60)
print()

# Save updated users.json
data["users"] = new_users
with open(USERS_FILE, "w") as f:
    json.dump(data, f, indent=2)

print(f"users.json updated with bcrypt hashes.")
print()
print("=" * 60)
print("CREDENTIALS — Store in a password manager, NOT email/Slack:")
print("=" * 60)
for username, password in NEW_PASSWORDS.items():
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print()

print("NEXT STEPS:")
print("1. Test login for each user in the Streamlit app")
print("2. Distribute new passwords securely (password manager)")
print("3. DELETE this script: rm migrate_passwords.py")
print("4. DELETE the backup file once confirmed working")