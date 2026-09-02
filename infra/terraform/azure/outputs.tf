output "cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}
output "resource_group" {
  value = azurerm_resource_group.main.name
}
output "oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.main.oidc_issuer_url
}
output "key_vault_id" {
  value = azurerm_key_vault.main.id
}
output "postgres_fqdn" {
  value     = azurerm_postgresql_flexible_server.main.fqdn
  sensitive = true
}
output "redis_hostname" {
  value     = azurerm_redis_cache.main.hostname
  sensitive = true
}
output "storage_account" {
  value = azurerm_storage_account.evidence.name
}
output "container_registry" {
  value = azurerm_container_registry.main.login_server
}
output "waf_policy_id" {
  value = azurerm_web_application_firewall_policy.edge.id
}

output "application_client_id" {
  value = azurerm_user_assigned_identity.application.client_id
}
