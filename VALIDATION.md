# Verification

- 12 automated tests passed using Python 3.12 and the pinned dependencies.
- MCP discovery exposes exactly `read_messages` and `post_update`.
- In-process MCP calls succeed against a fake WAHA backend.
- HTTP requests without OAuth are rejected with 401; OAuth discovery advertises
  PKCE S256 and dynamic client registration.
- A different authenticated GitHub owner cannot use either tool.
- Fixed chat routing, bounded reads, persistent and concurrent retry prevention,
  and uncertain send outcomes are covered.
- Python compilation and basic Compose structure checks passed.

Docker is not installed in the build environment, so the Docker image and
Compose deployment have not been run locally. The repository's CI workflow
includes image building and Compose validation. See the repository's Actions tab
for the status of those checks after a push.

Not yet verified live: host provisioning, DNS/TLS, WhatsApp QR pairing, selected
chat identity, GitHub OAuth browser login, ChatGPT plugin installation, and
scheduled unattended posting. No real WhatsApp messages were sent during tests.
