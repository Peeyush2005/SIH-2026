# Azure CI/CD Deployment Guide for BluEcho Sonar

This directory contains the production container deployment configuration and automation scripts to deploy **BluEcho Sonar** to **Azure App Service (Linux Web App for Containers)** using **Azure Container Registry (ACR)** and **GitHub Actions** with secretless **OpenID Connect (OIDC)** authentication.

---

## Architecture Overview

```
                      +-------------------------------------+
                      |          GitHub Repository          |
                      |    (Push to main / Dispatch)        |
                      +------------------+------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |     GitHub Actions CI/CD Pipeline     |
                     |  1. Pytest & Frontend Test Suite      |
                     |  2. OIDC Azure Authentication         |
                     |  3. Cloud Image Build in ACR          |
                     |  4. Azure Web App Container Deploy    |
                     |  5. Health Check Verification         |
                     +-------------------+-------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
     +-------------------------------+       +-------------------------------+
     | Azure Container Registry(ACR) |       |       Azure App Service       |
     | - Container image with ONNX   |<------+ - Linux Web App for Container |
     | - Tagged with Git SHA & latest|AcrPull| - Port 8000 (FastAPI/Uvicorn) |
     +-------------------------------+       | - Managed Identity            |
                                             | - /api/v1/health probe        |
                                             +---------------+---------------+
                                                             |
                                                             v
                                                    Public HTTPS Endpoint
                                              https://<app>.azurewebsites.net
```

### Key Highlights
- **Passwordless Security**: Uses GitHub Actions OIDC Federated Credentials with Microsoft Entra ID — no long-lived client secrets or passwords stored in GitHub.
- **Managed Identity**: The Azure Web App pulls images from ACR using its own System-Assigned Managed Identity (`AcrPull` role).
- **Self-Contained & Offline Inference**: Model weights (`fls11-debris`) are fetched and checksum-verified at Docker build time so the running container operates without external model downloads.
- **Hosted Isolation**: Session-scoped storage, rate limiting, and CORS/Host header validation protect the FastAPI inspection endpoints.

---

## Directory Structure

```
deploy/azure/
├── Dockerfile          # Production container image with Python 3.12, PyTorch CPU, ONNX model
├── app.py              # FastAPI entrypoint configuring hosted mode & allowed origins
├── setup-azure.sh      # Automated Bash script to provision Azure infrastructure & OIDC
├── main.bicep          # Infrastructure-as-Code Bicep template
└── README.md           # This deployment guide
.github/workflows/
└── azure-deploy.yml    # GitHub Actions CI/CD workflow
.dockerignore           # Excludes development artifacts from ACR build context
```

---

## Option 1: Automated Setup via Script (Recommended)

Run the automated setup script locally with Azure CLI installed and logged in (`az login`):

```bash
# Optional: customize environment variables
export RESOURCE_GROUP="bluecho-rg"
export LOCATION="eastus"
export PLAN_SKU="B2" # B1 or B2 recommended
export GITHUB_REPO="Peeyush2005/SIH-2026" # Format: owner/repo

# Run the provisioning script
./deploy/azure/setup-azure.sh
```

The script will:
1. Create the Resource Group (`bluecho-rg`).
2. Create the Azure Container Registry.
3. Create the Linux App Service Plan (`B2`).
4. Create the Web App for Containers, configure System-Assigned Managed Identity, and assign the `AcrPull` role on ACR.
5. Configure the Microsoft Entra ID App and OIDC Federated Identity Credentials for both `main` branch and `azure` environment.
6. Print the exact secrets to configure in your GitHub Repository.

---

## Option 2: Declarative Setup via Bicep

If you prefer Infrastructure-as-Code (IaC):

```bash
RG=bluecho-rg
LOCATION=eastus

az group create --name $RG --location $LOCATION

az deployment group create \
  --resource-group $RG \
  --template-file deploy/azure/main.bicep \
  --parameters baseName=bluechosonar appServicePlanSku=B2
```

---

## Configuring GitHub Repository Secrets

Add the following 6 secrets in your GitHub repository (**Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**):

| Secret Name | Description | Example Value |
|---|---|---|
| `AZURE_CLIENT_ID` | Application (client) ID of the Entra ID App | `11111111-2222-3333-4444-555555555555` |
| `AZURE_TENANT_ID` | Microsoft Entra Directory (tenant) ID | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | `xxxxxxxx-yyyy-zzzz-wwww-vvvvvvvvvvvv` |
| `AZURE_RESOURCE_GROUP` | Azure Resource Group name | `bluecho-rg` |
| `AZURE_ACR_NAME` | Azure Container Registry name | `bluechoacr1024` |
| `AZURE_WEBAPP_NAME` | Azure Web App service name | `bluecho-sonar-1024` |

*Tip: If you have GitHub CLI (`gh`) installed, the setup script prints ready-to-run `gh secret set` commands.*

---

## CI/CD Pipeline (`.github/workflows/azure-deploy.yml`)

The workflow triggers on every push to the `main` branch or via manual execution (**Actions** -> **Deploy to Azure** -> **Run workflow**):

1. **`test` Job**:
   - Builds frontend assets (`npm ci`, `npm run build`).
   - Installs PyTorch CPU wheels and full inspection suite.
   - Runs `pytest tests -q`.
2. **`build-and-deploy` Job**:
   - Runs under the `azure` environment.
   - Authenticates to Azure using OIDC (`azure/login@v2`).
   - Builds container image directly in Azure Container Registry (`az acr build`).
   - Deploys updated container to Azure Web App (`azure/webapps-deploy@v3`).
   - Restarts Web App and verifies the `/api/v1/health` endpoint.

---

## Testing Container Locally (Optional)

To test the container image locally before pushing:

```bash
# 1. Build frontend bundle into static directory
npm run build --prefix frontend

# 2. Build Docker container
docker build -t bluecho-sonar:local -f deploy/azure/Dockerfile .

# 3. Run container
docker run -p 8000:8000 \
  -e WEBSITE_HOSTNAME=localhost \
  bluecho-sonar:local

# 4. Verify endpoints
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/capabilities
```

Open `http://localhost:8000` in your browser to access the live dashboard.

---

## Operational Commands & Troubleshooting

### View Live Container Logs
```bash
az webapp log tail --name <AZURE_WEBAPP_NAME> --resource-group <AZURE_RESOURCE_GROUP>
```

### Restart Web App
```bash
az webapp restart --name <AZURE_WEBAPP_NAME> --resource-group <AZURE_RESOURCE_GROUP>
```

### Custom Domain Configuration
To add custom domains, configure DNS in Azure App Service and update `BLUECHO_ALLOWED_HOSTS`:
```bash
az webapp config appsettings set \
  --name <AZURE_WEBAPP_NAME> \
  --resource-group <AZURE_RESOURCE_GROUP> \
  --settings BLUECHO_ALLOWED_HOSTS="sonar.mycompany.com,sonar-backup.mycompany.com"
```
