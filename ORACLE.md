# Oracle Cloud deployment

Selected hosting: a dedicated Oracle Cloud Always Free candidate. ChatGPT does
the AI work; this VM only runs the WhatsApp connection and authenticated proxy.

[Deploy to Oracle Cloud](https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https%3A%2F%2Fgithub.com%2Fdagnello%2FChatgpt-whatsapp%2Farchive%2Frefs%2Fheads%2Fmain.zip)

The link loads this repository into Oracle Resource Manager. Signing in and
creating/applying the stack are required. This repository is not evidence of a
running VM, public API, successful WhatsApp pairing or ChatGPT connection.

## Resources and cost boundaries

- One `VM.Standard.A1.Flex` ARM VM: **2 OCPUs, 4 GB RAM, 50 GB boot disk**.
- Ubuntu 24.04, Docker Compose, WAHA's ARM image, and the existing Python proxy.
- A dedicated VCN/subnet/internet gateway. No load balancer, NAT gateway,
  managed database, paid DNS zone, premium disk performance or backup schedule.
- SSH from your chosen IPv4 `/32` or trusted narrow subnet only; public web
  ports 80/443. WAHA's port 3000 binds only to `127.0.0.1`.
- Docker volumes persist the WhatsApp session, OAuth tokens and duplicate-send
  protection across application/container restarts. They are on the VM's boot
  volume; destroying that disk loses them. Back up securely before replacing it.

Oracle's current total Always Free A1 allowance is **2 OCPUs and 12 GB RAM**, with
200 GB combined boot/block storage, shared across the tenancy. Use the **home
region** and check remaining allowances before Apply. Terraform rejects a
different region and requires you to confirm unused allowances, but it cannot
prove billing eligibility across an unseen tenancy. There is no automatic paid
fallback if the free shape is out of capacity. Try another availability domain
within the home region, or wait; do not resize to a paid shape.

Oracle may reclaim idle Always Free VMs. This is a free personal deployment with
that availability limitation, not a guaranteed always-on service. Do not create
artificial activity to evade reclamation.

## 1. Create the Oracle stack

1. Create/sign in to your own [Oracle Cloud account](https://cloud.oracle.com/).
   New accounts can start at [Oracle Free Tier signup](https://signup.oraclecloud.com/).
   Complete account/identity/payment-card verification directly with Oracle if
   requested. Do not put credentials, payment information or private keys in chat.
2. Switch to your tenancy's **home region**, then open the deploy link above.
3. Accept the configuration source. Keep the repository root as the Terraform
   working directory. Choose a Resource Manager-supported Terraform version
   **1.5 or newer**. Resource Manager provides the Oracle authentication; there
   are no cloud API credentials to add to this public repository.
4. Choose a compartment and availability domain. Supply a **public** SSH key and
   your current public IPv4 address with `/32`. Keep the matching private key.
   If needed, create a key on your own computer with `ssh-keygen -t ed25519`.
5. Check your existing free usage and tick the allowance confirmation. Review
   the fixed shape and disk above, then create/apply the stack. If your account
   cannot provision these within its free allowance, stop rather than upgrade.
6. Read the `public_ip`, `ssh_command` and `dashboard_tunnel` outputs. An Apply
   success means VM provisioning succeeded; bootstrap still runs afterward.

## 2. Finish bootstrap and pair WhatsApp

Use the output's SSH command and, on the VM, run:

```bash
sudo cloud-init status --wait
sudo test -f /var/lib/whatsapp-bootstrap-ready
cd /opt/whatsapp-proxy
sudo docker compose ps
```

Bootstrap checks out the reviewed application commit
`9a73c1598278dfa1154869b22a24fd2e798f70bc`; it does not execute a moving branch.
It creates private `.env` credentials and starts **only WAHA**. If bootstrap
fails, inspect `sudo less /var/log/cloud-init-output.log`; it does not print
generated credentials. Fix the cause, then rerun
`sudo /usr/local/sbin/whatsapp-bootstrap 9a73c1598278dfa1154869b22a24fd2e798f70bc`.

From your computer, run the `dashboard_tunnel` output and open
`http://localhost:3000/dashboard`. Privately view `/opt/whatsapp-proxy/.env` on
the VM for the dashboard username/password and plain `WAHA_API_KEY`. Do not paste
these into chat or copy them to Oracle stack variables. Link the default session
with WhatsApp's **Linked devices** QR scan. Wait until the session is WORKING.

Find the exact chat ID on the VM:

```bash
cd /opt/whatsapp-proxy
.venv/bin/python groups.py
```

Verify the intended chat and participants in WhatsApp before selecting its ID.
The helper lists the first 100 groups; use WAHA's pagination if needed.

## 3. Configure HTTPS and the owner login

Point a hostname you control at the VM's `public_ip` with a DNS **A record**.
Use a new hostname such as `whatsapp.your-domain.example`; do not change the
other app's production record. Keep this record DNS-only while checking Caddy
certificate issuance. Do not add an AAAA record for this IPv4 deployment.

On the VM, run:

```bash
whatsapp-setup
```

The helper asks for the hostname, allowed GitHub username, GitHub OAuth app
credentials and verified chat ID. It displays the exact OAuth homepage/callback
URLs. Create that app at <https://github.com/settings/developers>, then enter its
client ID and secret directly in your SSH terminal. Secret entry is hidden.
The helper resolves and confirms the numeric owner ID, preserves generated
signing/storage keys, writes `.env` privately, and starts the proxy/Caddy.

Verify the public deployment from outside the VM:

- `https://YOUR_HOSTNAME/healthz` returns 200 with `{"status":"ok"}`.
- An anonymous request to `https://YOUR_HOSTNAME/mcp` is denied with 401.
- Port 3000 is not reachable publicly. The SSH tunnel still reaches the dashboard.

## 4. Connect ChatGPT, then schedule

Follow [the ChatGPT connection steps](README.md#4-connect-it-to-chatgpt) using
`https://YOUR_HOSTNAME/mcp` and OAuth. First verify an authenticated read of the
intended chat, then an explicitly requested test post. Only after those work,
configure the requested source/topic and schedule in ChatGPT. No model API key
is used on this server.

## Operations

- Docker restarts existing containers after a VM reboot. Use
  `cd /opt/whatsapp-proxy && sudo docker compose ps` to inspect them.
- Update the SSH CIDR in the Oracle stack if your administration IP changes.
  Terraform must use this existing stack/state, not a second stack duplicating
  the VM and consuming additional free resources.
- Do not run `docker compose down -v`, delete the boot volume, or destroy/recreate
  the stack as an application update. Preserve volumes and `.env`.
- Application revisions, container tags and operating-system packages need
  periodic reviewed updates. WAHA/Caddy image tags remain upstream tags;
  Docker image builds and a Terraform plan do not verify live WhatsApp behavior.
- The proxy runs as UID 10001. The standard Docker named volume initializes
  from its owned `/data` directory; verify it is writable after the first build.
  Keep the proxy non-root.

## References

- [Oracle Always Free resources and limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Deploy to Oracle Cloud button](https://docs.oracle.com/en-us/iaas/Content/ResourceManager/Tasks/deploybutton.htm)
- [Resource Manager](https://www.oracle.com/cloud/cloud-native/resource-manager/)
- [WAHA ARM images](https://waha.devlike.pro/docs/how-to/engines/#docker-images)
