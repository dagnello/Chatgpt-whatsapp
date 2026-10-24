output "public_ip" {
  value       = oci_core_instance.relay.public_ip
  description = "Point your chosen hostname's DNS A record to this address."
}

output "ssh_command" {
  value       = "ssh ubuntu@${oci_core_instance.relay.public_ip}"
  description = "Use your matching private key if it is not your default SSH identity."
}

output "dashboard_tunnel" {
  value       = "ssh -N -L 3000:127.0.0.1:3000 ubuntu@${oci_core_instance.relay.public_ip}"
  description = "Then open http://localhost:3000/dashboard privately on your computer."
}

output "next_step" {
  value       = "Wait for cloud-init status --wait over SSH, pair WhatsApp through the tunnel, then run whatsapp-setup. See ORACLE.md."
  description = "A Terraform apply provisions the VM; it does not establish a WhatsApp session or a working public MCP endpoint."
}
