variable "environment" {
  type = string
}

variable "region" {
  type = string
}

variable "kubernetes_version" {
  type    = string
  default = "1.36"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "availability_zones" {
  type = list(string)
  validation {
    condition     = length(var.availability_zones) >= 3
    error_message = "Production-grade deployment requires at least three availability zones."
  }
}

variable "database_instance_class" {
  type    = string
  default = "db.r7g.large"
}

variable "redis_node_type" {
  type    = string
  default = "cache.r7g.large"
}

variable "database_name" {
  type    = string
  default = "medclaimiq"
}

variable "database_username" {
  type    = string
  default = "medclaimiq_admin"
}

variable "database_password" {
  type      = string
  sensitive = true
}

variable "redis_auth_token" {
  type      = string
  sensitive = true
}

variable "allowed_ingress_cidrs" {
  type    = list(string)
  default = []
}

variable "object_replication_destination_bucket_arn" {
  type        = string
  default     = ""
  description = "Optional pre-created DR bucket ARN in a secondary region/account."
}

variable "tags" {
  type    = map(string)
  default = {}
}
