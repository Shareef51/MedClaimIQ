variable "environment" {
  type = string
}
variable "location" {
  type = string
}
variable "kubernetes_version" {
  type    = string
  default = "1.36"
}
variable "postgres_admin_username" {
  type    = string
  default = "medclaimiq_admin"
}
variable "postgres_admin_password" {
  type      = string
  sensitive = true
}
variable "tenant_id" {
  type = string
}
variable "tags" {
  type    = map(string)
  default = {}
}
