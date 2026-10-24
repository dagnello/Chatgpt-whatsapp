"""Run locally on the host to identify the intended group before enabling tools."""
import os
import httpx
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()
    session = os.getenv("WAHA_SESSION", "default")
    response = httpx.get(
        f"http://127.0.0.1:3000/api/{session}/groups",
        headers={"X-Api-Key": os.environ["WAHA_API_KEY"]},
        params={"limit": 100, "offset": 0}, timeout=30, trust_env=False,
    )
    response.raise_for_status()
    groups = response.json()
    items = groups.values() if isinstance(groups, dict) else groups
    for group in items:
        if isinstance(group, dict):
            print(group.get("id"), "|", group.get("subject") or group.get("name"))
    print("First 100 groups only. Verify the selected group's members in WhatsApp before setting WAHA_CHAT_ID.")
