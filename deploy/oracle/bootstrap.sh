#!/usr/bin/env bash
set -euo pipefail
umask 077
export DEBIAN_FRONTEND=noninteractive

revision="${1:?A pinned application commit is required}"
[[ "$revision" =~ ^[a-f0-9]{40}$ ]] || exit 2
test "$(id -u)" = 0
test "$(uname -m)" = aarch64
systemctl enable --now docker
docker compose version

# Preserve the Ubuntu OCI image's existing firewall. Insert only the HTTPS
# gateway's ports before any default reject rule. Port 3000 stays loopback-only.
for port in 80 443; do
  iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null ||
    iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT
done
install -d -m 0755 /etc/iptables
iptables-save > /etc/iptables/rules.v4

app_dir=/opt/whatsapp-proxy
if ! test -e "$app_dir"; then
  install -d -o ubuntu -g ubuntu -m 0750 "$app_dir"
  runuser -u ubuntu -- git -C "$app_dir" init --quiet
  runuser -u ubuntu -- git -C "$app_dir" remote add origin https://github.com/dagnello/Chatgpt-whatsapp.git
fi
runuser -u ubuntu -- git -C "$app_dir" fetch --depth 1 origin "$revision"
runuser -u ubuntu -- git -C "$app_dir" checkout --detach "$revision"
runuser -u ubuntu -- python3 -m venv "$app_dir/.venv"
runuser -u ubuntu -- "$app_dir/.venv/bin/pip" install -r "$app_dir/requirements.txt"
cd "$app_dir"
if ! test -e .env; then
  runuser -u ubuntu -- .venv/bin/python configure.py
  printf '\nWAHA_IMAGE=devlikeapro/waha:arm\n' >> .env
  chown ubuntu:ubuntu .env
  chmod 0600 .env
fi

# Let the owner administer Docker through sudo without granting membership in
# the root-equivalent docker group. Start only the private pairing service.
docker compose up -d waha
touch /var/lib/whatsapp-bootstrap-ready
printf 'WhatsApp host ready. Pair through SSH, then run whatsapp-setup.\n'
