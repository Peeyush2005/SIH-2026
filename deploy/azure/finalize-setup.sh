#!/usr/bin/env bash
# ==============================================================================
# BluEcho Sonar - Finalize Azure Roles & GitHub Secrets
# ==============================================================================
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-blueco-sih26-rg}"
ACR_NAME="${ACR_NAME:-bluecosih26acr}"
WEBAPP_NAME="${WEBAPP_NAME:-bluecho-sonar}"
ENTRA_APP_NAME="${ENTRA_APP_NAME:-bluecho-github-actions}"
GITHUB_REPO="${GITHUB_REPO:-Peeyush2005/SIH-2026}"

echo "--> Fetching Azure IDs dynamically from active session..."
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
ACR_ID=$(az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --query id -o tsv)
RG_ID=$(az group show --name "${RESOURCE_GROUP}" --query id -o tsv)
WEBAPP_PRINCIPAL_ID=$(az webapp identity show --name "${WEBAPP_NAME}" --resource-group "${RESOURCE_GROUP}" --query principalId -o tsv)
CLIENT_ID=$(az ad app list --display-name "${ENTRA_APP_NAME}" --query "[0].appId" -o tsv)

echo "--> 1. Granting AcrPull role to Web App Managed Identity on ACR..."
az role assignment create \
  --assignee "${WEBAPP_PRINCIPAL_ID}" \
  --scope "${ACR_ID}" \
  --role AcrPull \
  -o none || true

echo "--> 2. Granting Contributor role to GitHub Actions Entra App on Resource Group..."
az role assignment create \
  --assignee "${CLIENT_ID}" \
  --scope "${RG_ID}" \
  --role Contributor \
  -o none || true

echo "--> 3. Configuring Federated Identity Credentials for GitHub Actions..."
az ad app federated-credential create \
  --id "${CLIENT_ID}" \
  --parameters "{
    \"name\": \"github-azure-env-with-ids\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:Peeyush2005@116378935/SIH-2026@1371223089:environment:azure\",
    \"description\": \"GitHub Actions OIDC with IDs for azure environment\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" -o none || true

az ad app federated-credential create \
  --id "${CLIENT_ID}" \
  --parameters "{
    \"name\": \"github-main-with-ids\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:Peeyush2005@116378935/SIH-2026@1371223089:ref:refs/heads/main\",
    \"description\": \"GitHub Actions OIDC with IDs for main branch\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" -o none || true

echo "--> 4. Setting GitHub Secrets for ${GITHUB_REPO}..."
gh secret set AZURE_CLIENT_ID --repo "${GITHUB_REPO}" --body "${CLIENT_ID}"
gh secret set AZURE_TENANT_ID --repo "${GITHUB_REPO}" --body "${TENANT_ID}"
gh secret set AZURE_SUBSCRIPTION_ID --repo "${GITHUB_REPO}" --body "${SUBSCRIPTION_ID}"
gh secret set AZURE_RESOURCE_GROUP --repo "${GITHUB_REPO}" --body "${RESOURCE_GROUP}"
gh secret set AZURE_ACR_NAME --repo "${GITHUB_REPO}" --body "${ACR_NAME}"
gh secret set AZURE_WEBAPP_NAME --repo "${GITHUB_REPO}" --body "${WEBAPP_NAME}"

echo "======================================================================"
echo " All Azure Roles & GitHub Secrets Configured Successfully!"
echo " Web App URL: https://${WEBAPP_NAME}.azurewebsites.net"
echo "======================================================================"
