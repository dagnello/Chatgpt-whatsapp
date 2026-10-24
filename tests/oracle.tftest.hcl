# Mock plans validate the deployment without accessing a real Oracle account.
mock_provider "oci" {
  mock_data "oci_identity_region_subscriptions" {
    defaults = {
      region_subscriptions = [{
        region_name    = "us-ashburn-1"
        is_home_region = true
        region_key     = "IAD"
        status         = "READY"
      }]
    }
  }
  mock_data "oci_core_images" {
    defaults = {
      images = [{ id = "ocid1.image.oc1.iad.example" }]
    }
  }
}

variables {
  tenancy_ocid           = "ocid1.tenancy.oc1..example"
  compartment_ocid       = "ocid1.compartment.oc1..example"
  region                 = "us-ashburn-1"
  availability_domain    = "example:US-ASHBURN-AD-1"
  ssh_public_key         = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakePublicKeyOnlyForValidation"
  ssh_source_cidr        = "203.0.113.7/32"
  confirm_free_allowance = true
}

run "free_shape_and_private_administration" {
  command = plan
  assert {
    condition     = oci_core_instance.relay.shape == "VM.Standard.A1.Flex" && oci_core_instance.relay.shape_config[0].ocpus == 2 && oci_core_instance.relay.shape_config[0].memory_in_gbs == 4 && oci_core_instance.relay.source_details[0].boot_volume_size_in_gbs == 50
    error_message = "The deployment must stay within the reviewed VM/disk limits."
  }
  assert {
    condition     = toset([for r in oci_core_security_list.relay.ingress_security_rules : r.tcp_options[0].max if r.protocol == "6"]) == toset([22, 80, 443])
    error_message = "Only SSH and HTTPS gateway ports may be permitted; never publish the dashboard."
  }
  assert {
    condition     = alltrue([for r in oci_core_security_list.relay.ingress_security_rules : r.source == "203.0.113.7/32" if r.protocol == "6" && try(r.tcp_options[0].max == 22, false)])
    error_message = "SSH must stay limited to the supplied administration address."
  }
}

run "reject_other_region" {
  command = plan
  variables {
    region = "us-phoenix-1"
  }
  expect_failures = [oci_core_instance.relay]
}

run "require_unused_allowance" {
  command = plan
  variables {
    confirm_free_allowance = false
  }
  expect_failures = [oci_core_instance.relay]
}

run "reject_public_ssh" {
  command = plan
  variables {
    ssh_source_cidr = "0.0.0.0/0"
  }
  expect_failures = [var.ssh_source_cidr]
}
