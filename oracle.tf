terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 7.0"
    }
  }
}

# Resource Manager supplies the signed-in account's authentication. No API key
# or WhatsApp/OAuth secret belongs in Terraform variables or state.
provider "oci" {
  region = var.region
}

data "oci_identity_region_subscriptions" "account" {
  tenancy_id = var.tenancy_ocid
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
  state                    = "AVAILABLE"
}

resource "oci_core_vcn" "relay" {
  compartment_id = var.compartment_ocid
  cidr_block     = "10.73.0.0/16"
  display_name   = "whatsapp-proxy"
  dns_label      = "whatsapp"
}

resource "oci_core_internet_gateway" "relay" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.relay.id
  display_name   = "whatsapp-proxy"
  enabled        = true
}

resource "oci_core_route_table" "relay" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.relay.id
  display_name   = "whatsapp-proxy"
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.relay.id
  }
}

resource "oci_core_security_list" "relay" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.relay.id
  display_name   = "whatsapp-proxy"

  ingress_security_rules {
    protocol = "6"
    source   = var.ssh_source_cidr
    tcp_options {
      min = 22
      max = 22
    }
  }
  dynamic "ingress_security_rules" {
    for_each = [80, 443]
    content {
      protocol = "6"
      source   = "0.0.0.0/0"
      tcp_options {
        min = ingress_security_rules.value
        max = ingress_security_rules.value
      }
    }
  }
  # Required for path MTU discovery, not an administrative service.
  ingress_security_rules {
    protocol = "1"
    source   = "0.0.0.0/0"
    icmp_options {
      type = 3
      code = 4
    }
  }
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

resource "oci_core_subnet" "relay" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.relay.id
  cidr_block                 = "10.73.1.0/24"
  display_name               = "whatsapp-proxy"
  dns_label                  = "relay"
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.relay.id
  security_list_ids          = [oci_core_security_list.relay.id]
}

resource "oci_core_instance" "relay" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = "whatsapp-proxy"
  shape               = "VM.Standard.A1.Flex"

  # Fixed Always Free candidate. Never fall back to a paid shape or larger disk.
  shape_config {
    ocpus         = 2
    memory_in_gbs = 4
  }
  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = 50
    boot_volume_vpus_per_gb = 10
  }
  create_vnic_details {
    subnet_id        = oci_core_subnet.relay.id
    assign_public_ip = true
    hostname_label   = "whatsapp"
  }
  metadata = {
    ssh_authorized_keys = trimspace(var.ssh_public_key)
    user_data = base64encode(templatefile("${path.module}/deploy/oracle/cloud-init.yaml.tftpl", {
      bootstrap_base64 = base64encode(file("${path.module}/deploy/oracle/bootstrap.sh"))
      setup_base64     = base64encode(file("${path.module}/deploy/oracle/setup.py"))
      app_revision     = "9a73c1598278dfa1154869b22a24fd2e798f70bc"
    }))
  }
  lifecycle {
    precondition {
      condition     = var.confirm_free_allowance
      error_message = "Check unused tenancy-wide Always Free allowances before deploying this VM."
    }
    precondition {
      condition = var.region == one([
        for subscription in data.oci_identity_region_subscriptions.account.region_subscriptions :
        subscription.region_name if subscription.is_home_region
      ])
      error_message = "Always Free compute must be created in the tenancy's home region. Switch to that region."
    }
    # Updating the infrastructure template must not replace a paired VM to rerun
    # cloud-init. Apply application updates separately and preserve its volumes.
    ignore_changes = [source_details[0].source_id, metadata["user_data"]]
  }
  depends_on = [oci_core_internet_gateway.relay]
}
