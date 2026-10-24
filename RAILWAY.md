# Railway deployment plan

Target: one Railway project containing two container services. ChatGPT performs
the AI work using the user's existing plan. These containers make no model API
calls. Railway hosting charges are separate from ChatGPT usage.

| Service | Source | Persistent mount | Networking |
| --- | --- | --- | --- |
| `waha` | `devlikeapro/waha` Docker image | `/app/.sessions` | Private API; authenticated dashboard exposed only as needed for pairing |
| `proxy` | This repository's Dockerfile | `/data` | Public HTTPS endpoint, OAuth protected MCP at `/mcp` |

Railway supplies HTTPS; do not deploy this repository's Caddy container there.
`railway.toml` applies to the proxy service only, not the WAHA image service.
Keep one replica per service and disable auto-sleep for the linked WhatsApp
connection. Use the same Railway region and environment for both services.

## Cost and authorization

Railway Hobby has a $5/month minimum including $5 of resource usage. Additional
resource usage is metered. The actual cost depends on both services' measured
memory, CPU, storage, and traffic. There is no flat $5 promise for this setup.
Review the account's existing plan and limits before deploying; do not upgrade
or subscribe without the account owner's authorization.

## Deployment order

1. Install/connect Railway in ChatGPT so the deployment can be created in the
   intended account. Inspect the workspace, plan, and any existing projects.
2. Create the dedicated project and both services with persistent volumes.
   Deploy WAHA first. Give the proxy a generated HTTPS domain, then use that
   exact origin for `PUBLIC_URL` and the GitHub OAuth App callback.
3. Generate credentials with `configure.py` locally and enter them through
   Railway's secret-variable controls. Do not commit a generated `.env` or paste
   credentials into the chat. The GitHub OAuth app needs only `read:user`.
4. Pair WhatsApp by opening the protected WAHA dashboard, starting the default
   session, and scanning its QR code from WhatsApp's Linked devices screen.
5. Verify the intended chat and its participants; set the exact `WAHA_CHAT_ID`.
6. Deploy the proxy with all required variables. Verify `/healthz` returns 200,
   anonymous `/mcp` requests return 401, and the correct owner can use both tools.
7. Connect the exact deployed HTTPS `/mcp` URL as a custom ChatGPT MCP plugin.
   Test a harmless read and one explicitly requested post, verify it in WhatsApp,
   then create the actual scheduled task using the user's chosen topic/timing.

## Variables

For WAHA, use the WAHA variables from `compose.yaml`. The `WAHA_API_KEY` value on
the WAHA service is the generated `sha512:` hash. The proxy receives the matching
plain key as `WAHA_API_KEY`. Keep the dashboard and Swagger login protection.

For the proxy, copy its variables from `compose.yaml`, with these differences:

- `WAHA_URL`: use WAHA's actual Railway private domain and listening port, not
  Docker Compose's `waha` hostname. Verify connectivity after deployment.
- `PUBLIC_URL`: use the exact Railway-generated HTTPS origin (no `/mcp` suffix).
- `STATE_DIR=/data`: mount a persistent volume there.
- `PORT`: Railway provides it; `server.py` reads it.
- Volume permission caveat: the image normally runs as UID 10001. Railway's docs
  say non-root images may not be able to write mounted volumes. Before relying
  on the deployment, initialize `/data` with owner UID/GID 10001 through Railway's
  supported administrative shell, then keep the app running as that user.
  Railway documents `RAILWAY_RUN_UID=0` as a fallback, but it is not enabled by
  this repository. Do not assume a successful image build verifies volume writes.

## Verification status

This file is a deployment runbook, not evidence of a deployed service. No Railway
project, URL, WhatsApp pairing, or scheduled delivery exists until those steps
have succeeded in the connected account.

References:

- <https://docs.railway.com/pricing/plans>
- <https://docs.railway.com/volumes/reference>
- <https://docs.railway.com/reference/config-as-code>
- <https://docs.railway.com/guides/docker-compose>
