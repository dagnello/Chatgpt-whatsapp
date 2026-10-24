variable "tenancy_ocid" {
  type        = string
  description = "Your Oracle tenancy. Resource Manager fills this automatically."
}

variable "compartment_ocid" {
  type        = string
  description = "The compartment for this dedicated deployment."
}

variable "region" {
  type        = string
  description = "Your tenancy's home region. Resource Manager fills this automatically."
}

variable "availability_domain" {
  type        = string
  description = "Availability domain in your home region with free A1 capacity."
}

variable "ssh_public_key" {
  type        = string
  description = "A PUBLIC SSH key. Keep the private key on your own computer."
  validation {
    condition     = can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp[0-9]+) [A-Za-z0-9+/=]+", trimspace(var.ssh_public_key)))
    error_message = "Enter an OpenSSH public key, never a private key."
  }
}

variable "ssh_source_cidr" {
  type        = string
  description = "Your administration IPv4 address with /32, or a trusted IPv4 subnet."
  validation {
    condition     = can(cidrnetmask(var.ssh_source_cidr)) && try(tonumber(split("/", var.ssh_source_cidr)[1]) >= 24, false)
    error_message = "Use your IPv4 address with /32 or a trusted /24 or narrower subnet. Public SSH access is not accepted."
  }
}

variable "confirm_free_allowance" {
  type        = bool
  default     = false
  description = "Confirm this tenancy has 2 free A1 OCPUs, 4 GB free A1 memory and 50 GB free block storage remaining in its home region."
}
