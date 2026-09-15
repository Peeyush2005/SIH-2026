#!/usr/bin/env bash
# ==============================================================================
# BluEcho Sonar - Automated Azure Infrastructure & GitHub OIDC Setup Script
# ==============================================================================
# This script provisions:
#   1. Azure Resource Group
#   2. Azure Container Registry (ACR)
#   3. Azure App Service Plan (Linux)
#   4. Azure Web App for Containers (with Managed Identity & AcrPull)
#   5. Microsoft Entra ID App + Federated Identity Credentials for GitHub OIDC
#   6. Outputs the exact GitHub Secrets needed for .github/workflows/azure-deploy.yml
# ==============================================================================

set -euo pipefail

# Configuration defaults (override by setting environment variables)
RESOURCE_GROUP="${RESOURCE_GROUP:-bluecho-rg}"
LOCATION="${LOCATION:-eastus}"
PLAN_NAME="${PLAN_NAME:-bluecho-plan}"
PLAN_SKU="${PLAN_SKU:-B2}" # B1 or B2 recommended for containerized workload
GITHUB_REPO="${GITHUB_REPO:-Peeyush2005/SIH-2026}" # format: owner/repo

# Unique suffix for ACR and Web App naming
RANDOM_SUFFIX="${RANDOM_SUFFIX:-$(LC_ALL=C tr -dc 'a-z0-9' </dev/urandom | head -c 4 || echo "1024")}"
ACR_NAME="${ACR_NAME:-bluechoacr${RANDOM_SUFFIX}}"
WEBAPP_NAME="${WEBAPP_NAME:-bluecho-sonar-${RANDOM_SUFFIX}}"
ENTRA_APP_NAME="${ENTRA_APP_NAME:-bluecho-github-actions-${RANDOM_SUFFIX}}"

echo "======================================================================"
echo "BluEcho Sonar - Azure Infrastructure & GitHub Actions Setup"
echo "======================================================================"
echo "Resource Group    : ${RESOURCE_GROUP}"
echo "Location          : ${LOCATION}"
echo "ACR Name          : ${ACR_NAME}"
echo "App Service Plan  : ${PLAN_NAME} (${PLAN_SKU})"
echo "Web App Name      : ${WEBAPP_NAME}"
echo "GitHub Repo       : ${GITHUB_REPO}"
echo "Entra App Name    : ${ENTRA_APP_NAME}"
echo "======================================================================"

# 1. Verify Azure CLI login
echo ""
echo "--> Checking Azure CLI authentication..."
if ! az account show > /dev/null 2>&1; then
  echo "Error: You are not logged into the Azure CLI. Please run 'az login' first."
  exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "    Using Subscription ID: ${SUBSCRIPTION_ID}"
echo "    Using Tenant ID      : ${TENANT_ID}"

# 2. Create Resource Group
echo ""
echo "--> Step 1/6: Creating Resource Group '${RESOURCE_GROUP}' in '${LOCATION}'..."
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}" -o none

# 3. Create Azure Container Registry
echo ""
echo "--> Step 2/6: Creating Azure Container Registry '${ACR_NAME}'..."
az acr create \
  --name "${ACR_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku Basic \
  --admin-enabled false \
  -o none

ACR_ID=$(az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --query id -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --query loginServer -o tsv)

# 4. Create App Service Plan
echo ""
echo "--> Step 3/6: Creating Linux App Service Plan '${PLAN_NAME}' (${PLAN_SKU})..."
az appservice plan create \
  --name "${PLAN_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --is-linux \
  --sku "${PLAN_SKU}" \
  -o none

# 5. Create Web App for Containers & Configure Managed Identity
echo ""
echo "--> Step 4/6: Creating Web App '${WEBAPP_NAME}'..."
az webapp create \
  --name "${WEBAPP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${PLAN_NAME}" \
  --deployment-container-image-name "mcr.microsoft.com/appsvc/staticsite:latest" \
  -o none

echo "    Assigning System-Assigned Managed Identity to Web App..."
az webapp identity assign --name "${WEBAPP_NAME}" --resource-group "${RESOURCE_GROUP}" -o none
WEBAPP_PRINCIPAL_ID=$(az webapp identity show --name "${WEBAPP_NAME}" --resource-group "${RESOURCE_GROUP}" --query principalId -o tsv)

echo "    Granting AcrPull role to Web App Managed Identity on ACR..."
az role assignment create \
  --assignee "${WEBAPP_PRINCIPAL_ID}" \
  --scope "${ACR_ID}" \
  --role AcrPull \
  -o none || true

echo "    Configuring Web App application settings..."
az webapp config appsettings set \
  --name "${WEBAPP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --settings \
    WEBSITES_PORT=8000 \
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=false \
    DOCKER_REGISTRY_SERVER_URL="https://${ACR_LOGIN_SERVER}" \
  -o none

# 6. Configure Entra ID App & Federated Credentials for GitHub Actions OIDC
echo ""
echo "--> Step 5/6: Configuring Microsoft Entra ID App & OIDC Federated Credentials..."
CLIENT_ID=$(az ad app create --display-name "${ENTRA_APP_NAME}" --query appId -o tsv)
az ad sp create --id "${CLIENT_ID}" -o none || true

echo "    Creating Federated Credential for branch 'main'..."
az ad app federated-credential create \
  --id "${CLIENT_ID}" \
  --parameters "{
    \"name\": \"github-main\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GITHUB_REPO}:ref:refs/heads/main\",
    \"description\": \"GitHub Actions OIDC for branch main\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" -o none || true

echo "    Creating Federated Credential for environment 'azure'..."
az ad app federated-credential create \
  --id "${CLIENT_ID}" \
  --parameters "{
    \"name\": \"github-azure-env\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GITHUB_REPO}:environment:azure\",
    \"description\": \"GitHub Actions OIDC for azure environment\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" -o none || true

echo "    Assigning Contributor role to Entra Application on Resource Group..."
RG_ID=$(az group show --name "${RESOURCE_GROUP}" --query id -o tsv)
az role assignment create \
  --assignee "${CLIENT_ID}" \
  --scope "${RG_ID}" \
  --role Contributor \
  -o none

# 7. Summary & Output GitHub Secrets
echo ""
echo "======================================================================"
echo " Azure Infrastructure & GitHub OIDC Setup Complete!"
echo "======================================================================"
echo " Web App URL: https://${WEBAPP_NAME}.azurewebsites.net"
echo ""
echo " Add the following secrets to your GitHub Repository:"
echo " (GitHub -> Repository Settings -> Secrets and variables -> Actions)"
echo "----------------------------------------------------------------------"
echo " AZURE_CLIENT_ID        : ${CLIENT_ID}"
echo " AZURE_TENANT_ID        : ${TENANT_ID}"
echo " AZURE_SUBSCRIPTION_ID  : ${SUBSCRIPTION_ID}"
echo " AZURE_RESOURCE_GROUP   : ${RESOURCE_GROUP}"
echo " AZURE_ACR_NAME         : ${ACR_NAME}"
echo " AZURE_WEBAPP_NAME      : ${WEBAPP_NAME}"
echo "----------------------------------------------------------------------"
echo ""

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo "--> Setting GitHub Secrets on repository '${GITHUB_REPO}' via gh CLI..."
  gh secret set AZURE_CLIENT_ID --repo "${GITHUB_REPO}" --body "${CLIENT_ID}"
  gh secret set AZURE_TENANT_ID --repo "${GITHUB_REPO}" --body "${TENANT_ID}"
  gh secret set AZURE_SUBSCRIPTION_ID --repo "${GITHUB_REPO}" --body "${SUBSCRIPTION_ID}"
  gh secret set AZURE_RESOURCE_GROUP --repo "${GITHUB_REPO}" --body "${RESOURCE_GROUP}"
  gh secret set AZURE_ACR_NAME --repo "${GITHUB_REPO}" --body "${ACR_NAME}"
  gh secret set AZURE_WEBAPP_NAME --repo "${GITHUB_REPO}" --body "${WEBAPP_NAME}"
  echo "    Successfully configured all 6 GitHub repository secrets!"
else
  echo " Quick setup via GitHub CLI (gh):"
  echo "   gh secret set AZURE_CLIENT_ID --body \"${CLIENT_ID}\""
  echo "   gh secret set AZURE_TENANT_ID --body \"${TENANT_ID}\""
  echo "   gh secret set AZURE_SUBSCRIPTION_ID --body \"${SUBSCRIPTION_ID}\""
  echo "   gh secret set AZURE_RESOURCE_GROUP --body \"${RESOURCE_GROUP}\""
  echo "   gh secret set AZURE_ACR_NAME --body \"${ACR_NAME}\""
  echo "   gh secret set AZURE_WEBAPP_NAME --body \"${WEBAPP_NAME}\""
fi
echo "======================================================================"
