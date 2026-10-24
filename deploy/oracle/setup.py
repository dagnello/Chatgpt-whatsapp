#!/usr/bin/env python3
"""Finish configuration on the VM interactively, never through Terraform state."""
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.request import Request, urlopen

from dotenv import dotenv_values, set_key

APP_DIR = Path("/opt/whatsapp-proxy")


def ask(label, default="", secret=False):
    prompt = label + (f" [{default}]" if default and not secret else "") + ": "
    value = getpass.getpass(prompt) if secret else input(prompt)
    value = value.strip() or default
    if not value or any(c in value for c in "\r\n\x00"):
        raise ValueError(f"{label} is required and must be one line")
    return value


def main():
    os.umask(0o077)
    os.chdir(APP_DIR)
    env_path = APP_DIR / ".env"
    if not env_path.is_file():
        raise ValueError("Bootstrap has not finished. Check sudo cloud-init status --wait.")
    existing = dotenv_values(env_path)
    hostname = ask("Public DNS hostname")
    if len(hostname) > 253 or not re.fullmatch(r"(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}", hostname):
        raise ValueError("Enter a DNS hostname, without https:// or a path")
    origin = "https://" + hostname.lower()
    login = ask("GitHub username allowed to use this proxy")
    if not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?", login):
        raise ValueError("Invalid GitHub username")
    req = Request("https://api.github.com/users/" + login, headers={"User-Agent": "whatsapp-proxy-setup"})
    with urlopen(req, timeout=15) as response:
        owner = json.load(response)
    owner_id = owner.get("id")
    if type(owner_id) is not int or owner_id <= 0:
        raise ValueError("GitHub did not return a valid numeric account ID")
    if input(f"Allow GitHub account {owner['login']} (ID {owner_id})? Type yes: ").strip() != "yes":
        raise ValueError("Owner not confirmed; configuration unchanged")
    print("Create an OAuth App at https://github.com/settings/developers")
    print("Homepage:", origin)
    print("Callback:", origin + "/auth/callback")
    client_id = ask("GitHub OAuth client ID", existing.get("GITHUB_CLIENT_ID", ""))
    client_secret = ask("GitHub OAuth client secret (hidden)", existing.get("GITHUB_CLIENT_SECRET", ""), secret=True)
    chat_id = ask("Verified WhatsApp chat ID", existing.get("WAHA_CHAT_ID", ""))
    if not re.fullmatch(r"[0-9-]+@(?:g\.us|c\.us)", chat_id):
        raise ValueError("Use the exact group @g.us or direct @c.us ID from WAHA")
    if input("Confirm this is the intended chat and you checked its participants. Type yes: ").strip() != "yes":
        raise ValueError("Destination not confirmed; configuration unchanged")
    updates = {
        "DOMAIN": hostname.lower(), "PUBLIC_URL": origin,
        "GITHUB_OWNER_ID": str(owner_id), "GITHUB_CLIENT_ID": client_id,
        "GITHUB_CLIENT_SECRET": client_secret, "WAHA_CHAT_ID": chat_id,
        "WAHA_IMAGE": "devlikeapro/waha:arm",
    }
    for key, value in updates.items():
        set_key(env_path, key, value, quote_mode="always")
    env_path.chmod(0o600)
    subprocess.run(["sudo", "docker", "compose", "up", "-d", "--build"], check=True)
    print("Services started. Check HTTPS health at", origin + "/healthz")
    print("Connect ChatGPT using OAuth at", origin + "/mcp")
    print("WhatsApp pairing, health and an authenticated read must be verified before scheduling.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        # Do not dump arguments, HTTP payloads or secrets into logs.
        raise SystemExit(f"Setup stopped: {type(exc).__name__}. Check the inputs and retry.") from None
