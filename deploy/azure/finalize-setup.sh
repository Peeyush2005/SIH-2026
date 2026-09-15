#!/usr/bin/env bash
# ==============================================================================
# BluEcho Sonar - Finalize Azure Roles & GitHub Secrets
# ==============================================================================
set -euo pipefail

ACR_ID=$(az acr show --name bluecosih26acr --resource-group blueco-sih26-rg --query id -o tsv)
RG_ID=$(az group show --name blueco-sih26-rg --query id -o tsv)

echo "--> 1. Granting AcrPull role to Web App Managed Identity on ACR..."
az role assignment create \
  --assignee "87b52d44-7a6f-4cb9-957d-691c955123f4" \
  --scope "${ACR_ID}" \
  --role AcrPull \
  -o none || true

echo "--> 2. Granting Contributor role to GitHub Actions Entra App on Resource Group..."
az role assignment create \
  --assignee "05a1e6e9-8ce1-4449-9d64-1b8bff0a2a4b" \
  --scope "${RG_ID}" \
  --role Contributor \
  -o none || true

echo "--> 3. Setting GitHub Secrets for Peeyush2005/SIH-2026..."
gh secret set AZURE_CLIENT_ID --repo Peeyush2005/SIH-2026 --body "05a1e6e9-8ce1-4449-9d64-1b8bff0a2a4b"
gh secret set AZURE_TENANT_ID --repo Peeyush2005/SIH-2026 --body "84c31ca0-ac3b-4eae-ad11-519d80233e6f"
gh secret set AZURE_SUBSCRIPTION_ID --repo Peeyush2005/SIH-2026 --body "ebcd3515-ff10-4139-b72d-a1c1ebbcd1f2"
gh secret set AZURE_RESOURCE_GROUP --repo Peeyush2005/SIH-2026 --body "blueco-sih26-rg"
gh secret set AZURE_ACR_NAME --repo Peeyush2005/SIH-2026 --body "bluecosih26acr"
gh secret set AZURE_WEBAPP_NAME --repo Peeyush2005/SIH-2026 --body "bluecho-sonar"

echo "======================================================================"
echo " All Azure Roles & GitHub Secrets Configured Successfully!"
echo " Web App URL: https://bluecho-sonar.azurewebsites.net"
echo "======================================================================"
