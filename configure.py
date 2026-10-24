"""Create local credentials without printing them or overwriting an existing setup."""
import hashlib
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet


if __name__ == "__main__":
    os.umask(0o077)
    key = secrets.token_hex(32)
    content = "\n".join([
        "# Set these before starting the proxy:",
        "DOMAIN=whatsapp.example.com",
        "PUBLIC_URL=https://whatsapp.example.com",
        "GITHUB_OWNER_ID=", "GITHUB_CLIENT_ID=", "GITHUB_CLIENT_SECRET=",
        "WAHA_CHAT_ID=", "WAHA_SESSION=default", "",
        "# Generated credentials. Keep this file private:",
        f"WAHA_API_KEY={key}",
        f"WAHA_API_KEY_HASH=sha512:{hashlib.sha512(key.encode()).hexdigest()}",
        "WAHA_DASHBOARD_USERNAME=admin",
        f"WAHA_DASHBOARD_PASSWORD={secrets.token_hex(24)}",
        f"OAUTH_SIGNING_KEY={secrets.token_hex(32)}",
        f"OAUTH_STORAGE_KEY={Fernet.generate_key().decode()}", "",
    ])
    with Path(".env").open("x") as stream:
        stream.write(content)
    print("Created .env. Edit its blank fields before starting the proxy. No secrets printed.")
